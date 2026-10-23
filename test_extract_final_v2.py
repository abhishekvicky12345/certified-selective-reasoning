"""Checks for extract_final_v2 against the as-run reader (stage2_lib.extract_final).

CPU only. Opens ckpt\\ read-only; writes nothing.
Run from the folder holding stage2_lib.py, extract_final_v2.py and ckpt\\:
    python test_extract_final_v2.py
or in Jupyter:  %run test_extract_final_v2.py

1. v2's copied pieces (_NUM, both regexes, to_fraction) match stage2_lib.py.
2. Unit tests on hand-written answers.
3. Gate: v1 reproduces the 18 published all-row wrong counts (and the eligible
   counts for main and p1, template 76 out).
4. On all 18 generator files: v2 finds the same FINAL: hits as v1, returns the
   same tags, and differs from v1 only on rows with a fraction on the FINAL: line.
5. If the C3 output folder is given, those rows must be exactly C3's 107 flagged
   rows, with v2 equal to C3's careful reading.
"""
import csv
import hashlib
import importlib.util
import inspect
import json
import os
import sys
from collections import Counter
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
STAGE2_PATH = os.environ.get("STAGE2_PATH", os.path.join(HERE, "stage2_lib.py"))
V2_PATH = os.environ.get("V2_PATH", os.path.join(HERE, "extract_final_v2.py"))
CKPT_DIR = os.environ.get("CKPT_DIR", os.path.join(HERE, "ckpt"))
# The C3 run folder holding flagged_rows.csv; set to "" to skip check 5.
C3_DIR = os.environ.get("C3_DIR", os.path.join(
    HERE, "c3_extraction_output", "extraction_audit_20261022_202416"))

AS_RUN_SHA256_LF = "ae042d0c48c9d0f088ade4fc718ba5b56fc37328c9b0e47ca1306f2c20941388"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


s2 = load(STAGE2_PATH, "stage2_lib_as_run")
v2 = load(V2_PATH, "extract_final_v2")
with open(STAGE2_PATH, "rb") as fh:
    lf = fh.read().replace(b"\r\n", b"\n")
print("stage2_lib.py:", STAGE2_PATH)
print("  as-run copy:", hashlib.sha256(lf).hexdigest() == AS_RUN_SHA256_LF)
print(v2.VERSION, "|", V2_PATH)

# ---- 1. Verbatim pieces ------------------------------------------------------
assert v2._NUM == s2._NUM, "_NUM differs from stage2_lib"
assert v2._FINAL_RE.pattern == s2._FINAL_RE.pattern and v2._FINAL_RE.flags == s2._FINAL_RE.flags
assert v2._ANYNUM_RE.pattern == s2._ANYNUM_RE.pattern
src = lambda f: inspect.getsource(f).replace("\r\n", "\n").strip()
assert src(v2.to_fraction) == src(s2.to_fraction), "to_fraction differs from stage2_lib"
print("1. copied pieces identical to stage2_lib: ok")

# ---- 2. Unit tests -------------------------------------------------------------
LONG = "3" * 32485
UNIT = [  # text, v2 value, v2 tag, v1 value (None = not checked against v1)
    ("FINAL: 42", F(42), "final_tag", F(42)),
    ("FINAL: $1,234.50", F(2469, 2), "final_tag", F(2469, 2)),
    ("FINAL: 1.5e10", F(15000000000), "final_tag", F(15000000000)),
    ("FINAL: 7/2", F(7, 2), "final_tag", F(7)),
    ("FINAL: -7/2", F(-7, 2), "final_tag", F(-7)),
    ("FINAL: $-42159089/3", F(-42159089, 3), "final_tag", F(-42159089)),
    ("FINAL: 1/16", F(1, 16), "final_tag", F(1)),
    ("FINAL: 7 / 2", F(7, 2), "final_tag", F(7)),
    ("FINAL: 7/2.", F(7, 2), "final_tag", F(7)),
    ("FINAL: 7/2, so 3.5", F(7, 2), "final_tag", F(7)),
    ("FINAL: 1.5/2", F(3, 4), "final_tag", F(3, 2)),
    ("FINAL: 1,000/3", F(1000, 3), "final_tag", F(1000)),
    ("FINAL: 12/4 = 3", F(3), "final_tag", F(12)),
    ("FINAL: 8000/G", F(8000), "final_tag", F(8000)),        # letter after the slash
    ("FINAL: 10/22/2026", F(10), "final_tag", F(10)),         # a/b/c: v1's reading
    ("FINAL: 1/12/3", F(1), "final_tag", F(1)),               # no partial denominator
    ("FINAL: 7/-2", F(7), "final_tag", F(7)),                 # signed denominator: v1's reading
    ("FINAL: 7/0", None, "final_tag", F(7)),
    ("FINAL: 3 1/2", F(3), "final_tag", F(3)),                # mixed number: not handled (as v1)
    ("FINAL: 7\n/2", F(7), "final_tag", F(7)),                # slash on the next line: as v1
    ("Work: 1/2 of 10.\nFINAL: 5", F(5), "final_tag", F(5)),
    ("FINAL: 1/2\nFINAL: 3", F(3), "final_tag", F(3)),        # last FINAL: wins
    ("FINAL: 3\nFINAL: 1/2", F(1, 2), "final_tag", F(1)),
    ("FINAL: 3\nFINAL: none", F(3), "final_tag", F(3)),       # last FINAL: with a number
    ("final: 9/4", F(9, 4), "final_tag", F(9)),               # case-insensitive, as v1
    ("1310 * 6 / 7 =", F(7), "last_number_fallback", F(7)),  # fallback ignores "/", as v1
    ("so x = 3/4", F(4), "last_number_fallback", F(4)),
    ("no digits here", None, "no_number", None),
    ("", None, "no_number", None),
    (None, None, "no_number", None),
    ("FINAL: " + LONG, None, "final_tag", None),
    ("FINAL: 1/" + LONG, None, "final_tag", None),
    ("The result is " + LONG, None, "last_number_fallback", None),
    ("FINAL: " + "9" * 1000 + "/3", F(int("9" * 1000), 3), "final_tag", None),
]
for text, want, want_tag, want_v1 in UNIT:
    got = v2.extract_final_v2(text)
    assert got == (want, want_tag), (repr(text)[:60], got, want, want_tag)
    if want_v1 is not None:
        g1 = s2.extract_final(text)
        assert g1[0] == want_v1 and g1[1] == want_tag, ("v1", repr(text)[:60], g1, want_v1)
print(f"2. {len(UNIT)} unit tests: ok")

# ---- 3-4. The 18 frozen generator files ---------------------------------------
DATASETS = ["svamp", "gsm8k", "gsm_hard", "gsm_symbolic_main", "gsm_symbolic_p1", "gsm_symbolic_p2"]
GEN_FILES = {"qwen": "raw_gen_{ds}.jsonl", "flashlite": "raw_gen_flashlite_{ds}.jsonl",
             "pro": "raw_gen_gemini_{ds}.jsonl"}
N_EXPECTED = {"svamp": 1000, "gsm8k": 1319, "gsm_hard": 1319,
              "gsm_symbolic_main": 5000, "gsm_symbolic_p1": 5000, "gsm_symbolic_p2": 2500}
EXCLUDED = {"gsm_symbolic_main": {76}, "gsm_symbolic_p1": {76}}
# Published wrong counts on all rows (Qwen / Flash-Lite / Pro), and eligible
# counts with template 76 out (main, p1). C3 reproduced all of them on 22 Oct.
WRONG_ALL = {"svamp": (79, 34, 22), "gsm8k": (139, 45, 23), "gsm_hard": (518, 314, 313),
             "gsm_symbolic_main": (641, 211, 65), "gsm_symbolic_p1": (1194, 299, 114),
             "gsm_symbolic_p2": (972, 223, 122)}
WRONG_ELIG = {"gsm_symbolic_main": (602, 172, 26), "gsm_symbolic_p1": (1173, 285, 100)}
GENS = list(GEN_FILES)


def rows_of(gen, ds):
    path = os.path.join(CKPT_DIR, GEN_FILES[gen].format(ds=ds))
    with open(path, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    pids = [r["pid"] for r in rows]
    assert len(rows) == N_EXPECTED[ds], (path, len(rows))
    assert len(set(pids)) == len(pids), (path, "duplicate pids")
    assert not any(r.get("ok") is False for r in rows), (path, "ok=False rows")
    return rows


def text_of(r):
    o = r.get("outputs")
    return (o[0] if o else "") if isinstance(o, list) else (o or "")


def template_of(pid):
    return int(pid.split("/")[1].split("_")[0])


diff_rows = {}
counts = {}
for ds in DATASETS:
    for gi, gen in enumerate(GENS):
        c = Counter()
        for r in rows_of(gen, ds):
            t = text_of(r)
            gold = s2.to_fraction(r.get("gold"))
            e1, tag1 = s2.extract_final(t)
            e2, tag2 = v2.extract_final_v2(t)
            assert [h[0] for h in v2._FINAL_RE_V2.findall(t)] == s2._FINAL_RE.findall(t), r["pid"]
            assert tag1 == tag2, (gen, r["pid"], tag1, tag2)
            ok1, ok2 = s2.answers_match(e1, gold), s2.answers_match(e2, gold)
            elig = ds not in EXCLUDED or template_of(r["pid"]) not in EXCLUDED[ds]
            c["wrong_all_v1"] += not ok1
            c["wrong_all_v2"] += not ok2
            c["wrong_elig_v1"] += elig and not ok1
            c["wrong_elig_v2"] += elig and not ok2
            if e1 != e2:
                assert tag2 == "final_tag", (gen, r["pid"])
                diff_rows[(gen, r["pid"])] = (e1, e2, ok1, ok2)
                c["diff"] += 1
                c["to_right"] += ok2 and not ok1
                c["to_wrong"] += ok1 and not ok2
        assert c["wrong_all_v1"] == WRONG_ALL[ds][gi], ("GATE", gen, ds, c["wrong_all_v1"])
        if ds in WRONG_ELIG:
            assert c["wrong_elig_v1"] == WRONG_ELIG[ds][gi], ("GATE", gen, ds, c["wrong_elig_v1"])
        counts[(gen, ds)] = c
print("3. gate: v1 reproduces all 18 published wrong counts (and 6 eligible counts): ok")
print("4. v1 -> v2 on the frozen files (wrong answers on all rows; eligible for main/p1):")
for (gen, ds), c in counts.items():
    if c["diff"]:
        el = (f"; eligible {c['wrong_elig_v1']} -> {c['wrong_elig_v2']}"
              if ds in WRONG_ELIG else "")
        print(f"   {gen:<9} {ds:<18} {c['diff']:>3} rows read differently; wrong "
              f"{c['wrong_all_v1']} -> {c['wrong_all_v2']}{el}; "
              f"wrong->right {c['to_right']}, right->wrong {c['to_wrong']}")
tot = Counter()
for c in counts.values():
    tot.update(c)
print(f"   total {tot['diff']} rows; wrong->right {tot['to_right']}; right->wrong {tot['to_wrong']}; "
      "every other row reads the same")

# ---- 5. Same rows and values as the C3 audit ----------------------------------
if C3_DIR and os.path.exists(os.path.join(C3_DIR, "flagged_rows.csv")):
    with open(os.path.join(C3_DIR, "flagged_rows.csv"), encoding="utf-8-sig") as fh:
        flagged = {(r["generator"], r["pid"]): r for r in csv.DictReader(fh)
                   if r["status"] == "disagree"}
    assert set(flagged) == set(diff_rows), (
        "rows differ from C3", sorted(set(flagged) ^ set(diff_rows))[:10])
    for key, (e1, e2, ok1, ok2) in diff_rows.items():
        r = flagged[key]
        assert F(r["extracted"]) == e1 and F(r["careful"]) == e2, (key, r["extracted"], r["careful"], e1, e2)
        assert (r["right_extracted"] == "True") == ok1 and (r["right_careful"] == "True") == ok2, key
    print(f"5. the {len(diff_rows)} rows are exactly C3's flagged rows, with C3's careful values: ok")
else:
    print("5. skipped (no C3 flagged_rows.csv at C3_DIR)")
print("ALL CHECKS PASSED")
