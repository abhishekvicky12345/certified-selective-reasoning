"""Shared helpers for Stage 1. Importable without a GPU."""
import hashlib
import json
import os
import re
import time
import urllib.request
from pathlib import Path

# ============================================================================
# PROMPTS
# ----------------------------------------------------------------------------
# BUMP THIS STRING whenever you change any prompt text below. The fingerprint
# guard uses it to stop you from mixing outputs from two different prompts in
# one file.
#
# p1-v1 notes:
#   * Rule 3 explicitly ALLOWS helper constants for middle steps. This is the
#     style that worked. Do NOT switch to "pure declarative / all-Z3" phrasing:
#     that was tried, it made translators buggier, coverage dropped, and the
#     `answer` naming convention got dropped. It is retired.
#   * The translator NEVER sees the generator's answer. Independence between
#     the two translators and the generator is the whole mechanism. If a
#     translator saw the candidate answer it would anchor on it, error
#     correlation rho would rise, and the decorrelation bound would collapse.
# ============================================================================
PROMPT_VERSION = "p1-v1"

GEN_SYSTEM = (
    "You are a careful mathematician. You solve grade-school word problems exactly."
)

GEN_USER = """Problem:
{question}

Solve it step by step. Keep each step short.
Then write the last line of your reply in exactly this format:

FINAL: <number>

After FINAL: write only the number. No units, no words, no commas, no dollar sign."""

TRANS_SYSTEM = (
    "You convert word problems into SMT-LIB 2 code. "
    "You never state the answer in words. You output code only."
)

TRANS_USER = """Word problem:
{question}

Write SMT-LIB 2 code that describes this problem.

Rules:
1. Use (declare-const ...) for every quantity you need.
2. You MUST declare exactly one constant named answer. It holds the number the
   question is asking for.
3. You MAY declare extra helper constants for middle steps, for example
   (declare-const step1 Real).
4. Use (assert ...) to state every fact and every relation in the problem.
5. Use Real for anything that could be a fraction. Use Int only when the value
   must be a whole number.
6. Do NOT write (check-sat), (get-value ...), (get-model), (get-info), or (exit).
7. Do NOT explain. Output exactly one code block and nothing else:

```smt2
your code here
```"""


def build_gen_messages(question):
    # .replace not .format: the prompt text may contain braces one day, and
    # .format would crash on them.
    return [
        {"role": "system", "content": GEN_SYSTEM},
        {"role": "user", "content": GEN_USER.replace("{question}", question)},
    ]


def build_trans_messages(question):
    return [
        {"role": "system", "content": TRANS_SYSTEM},
        {"role": "user", "content": TRANS_USER.replace("{question}", question)},
    ]


# ============================================================================
# DATASETS
# Every loader returns a list of dicts, all with the same shape:
#   {"pid": "svamp/0000", "question": str, "gold": str, "meta": {...}}
# `gold` is kept as a STRING on purpose. Stage 2 decides how to compare
# numbers (tolerance, Int vs Real). Stage 1 must not make that decision.
# ============================================================================
def _squash(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def load_svamp(cache_dir):
    """SVAMP, 1000 problems, from the authors' repo (the authoritative copy)."""
    url = "https://raw.githubusercontent.com/arkilpatel/SVAMP/main/SVAMP.json"
    path = Path(cache_dir) / "SVAMP.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, path)
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert len(rows) == 1000, f"expected 1000 SVAMP rows, got {len(rows)}"

    out = []
    for i, r in enumerate(rows):
        body = _squash(r["Body"])
        ques = _squash(r["Question"])
        # SVAMP bodies usually have no end punctuation. Add one so the two
        # halves do not run together into a single confusing sentence.
        if body and body[-1] not in ".?!":
            body += "."
        op = r.get("Type", "")
        if op == "Common-Divison":      # one genuine typo in the source file
            op = "Common-Division"
        out.append({
            "pid": f"svamp/{i:04d}",
            "question": f"{body} {ques}",
            "gold": str(r["Answer"]),
            "meta": {"src_id": r["ID"], "op_type": op, "equation": _squash(r["Equation"])},
        })
    return out


def load_gsm8k(cache_dir):
    """GSM8K test split, 1319 problems. The only CRC-eligible dataset."""
    from datasets import load_dataset
    ds = load_dataset("openai/gsm8k", "main", split="test", cache_dir=cache_dir)
    out = []
    for i, r in enumerate(ds):
        gold = r["answer"].split("####")[-1].strip().replace(",", "").replace("$", "")
        out.append({
            "pid": f"gsm8k/{i:04d}",
            "question": _squash(r["question"]),
            "gold": gold,
            "meta": {"has_rationale": True},
        })
    assert len(out) == 1319, f"expected 1319 GSM8K test rows, got {len(out)}"
    return out


def load_gsm_hard(cache_dir):
    """GSM-Hard, 1319 problems. GSM8K with large / awkward numbers."""
    from datasets import load_dataset
    err = None
    ds = None
    for repo in ["reasoning-machines/gsm-hard", "reasoning-machines/gsm_hard"]:
        for split in ["train", "test"]:
            try:
                ds = load_dataset(repo, split=split, cache_dir=cache_dir)
                break
            except Exception as e:
                err = e
        if ds is not None:
            break
    if ds is None:
        raise RuntimeError(f"could not load GSM-Hard. last error: {err}")

    cols = set(ds.column_names)
    qcol = "input" if "input" in cols else "question"
    acol = "target" if "target" in cols else "answer"
    out = []
    for i, r in enumerate(ds):
        out.append({
            "pid": f"gsm_hard/{i:04d}",
            "question": _squash(r[qcol]),
            "gold": repr(r[acol]) if isinstance(r[acol], float) else str(r[acol]),
            "meta": {"code": r.get("code", "")},
        })
    return out


LOADERS = {"svamp": load_svamp, "gsm8k": load_gsm8k, "gsm_hard": load_gsm_hard}


def get_records(dataset, cache_dir, limit=0):
    recs = LOADERS[dataset](cache_dir)
    recs.sort(key=lambda r: r["pid"])       # fixed order, every time
    if limit and limit > 0:
        recs = recs[:limit]
    return recs


# ============================================================================
# CHECKPOINTS
# Append-only JSONL. One line = one problem. Flushed and fsynced after every
# chunk, so a crash or a preempted instance costs you one chunk, not the run.
# ============================================================================
def append_jsonl(path, rows):
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())          # force it to the actual disk, not the OS buffer


def read_done_pids(path):
    """Return pids already finished. Repairs a torn last line from a crash."""
    if not os.path.exists(path):
        return set(), 0
    good, done, bad = [], set(), 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                done.add(rec["pid"])
                good.append(line)
            except Exception:
                bad += 1               # almost always a half-written final line
    if bad:
        tmp = path + ".repair"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(good) + ("\n" if good else ""))
        os.replace(tmp, path)
    return done, bad


# ============================================================================
# PRODUCER FINGERPRINT
# Encodes everything that changes the model's text: model id, prompt version,
# sampling settings, dtype, context length.
#
# NOT included: gpu_memory_utilization, batch size, enforce_eager. These do not
# change what the model is asked. Caveat worth writing in the paper: vLLM greedy
# decoding is not guaranteed bitwise identical across different batch sizes, so
# "deterministic" here means the decision rule is deterministic, not that the
# floating-point kernels are bit-reproducible.
# ============================================================================
def fingerprint(producer):
    blob = json.dumps(producer, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def guard_meta(meta_path, producer):
    """Refuse to append outputs from a different producer into the same file."""
    fp = fingerprint(producer)
    if os.path.exists(meta_path):
        old = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        if old.get("fingerprint") != fp:
            raise SystemExit(
                "\n*** PRODUCER CHANGED — REFUSING TO RUN ***\n"
                f"  meta file : {meta_path}\n"
                f"  on disk   : {old.get('fingerprint')}\n"
                f"  right now : {fp}\n\n"
                "Something that changes the model's output was edited: model id,\n"
                "prompt version, temperature, top_p, n, max tokens, dtype, or\n"
                "context length.\n\n"
                "Mixing two producers in one JSONL silently corrupts your\n"
                "statistical denominator. Per your own checkpoint rule, this means\n"
                "the raw file must be regenerated:\n\n"
                f"  rm {meta_path.replace('meta_', 'raw_').replace('.json', '.jsonl')}\n"
                f"  rm {meta_path}\n\n"
                "Old fields, for comparison:\n"
                + json.dumps(old.get("producer", {}), indent=2, sort_keys=True)
            )
        return fp
    Path(meta_path).write_text(
        json.dumps({"fingerprint": fp, "producer": producer,
                    "created": time.strftime("%Y-%m-%dT%H:%M:%S")},
                   indent=2, sort_keys=True),
        encoding="utf-8")
    return fp


def paths_for(ckpt_dir, role, dataset, tag=""):
    base = f"{role}_{dataset}{tag}"
    return (os.path.join(ckpt_dir, f"raw_{base}.jsonl"),
            os.path.join(ckpt_dir, f"meta_{base}.json"))
