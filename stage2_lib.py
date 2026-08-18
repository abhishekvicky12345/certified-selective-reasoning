"""Stage 2 core: turn raw model text into certified / not-certified verdicts.

Runs on CPU. Reads the Stage 1 JSONL files and never writes to them.
"""
import re
import signal
from fractions import Fraction

import z3

# ============================================================================
# 1. PULLING NUMBERS OUT OF TEXT
# ============================================================================
# The exponent group is not optional decoration. Without it "FINAL: 1.5e10"
# matches only "1.5" and yields a plausible number that is wrong by ten orders
# of magnitude - silent corruption, and worst on GSM-Hard where answers are huge.
_NUM = r"-?(?:\d[\d,]*(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?"
_FINAL_RE = re.compile(r"FINAL:\s*\$?\s*(" + _NUM + r")", re.I)
_ANYNUM_RE = re.compile("(" + _NUM + ")")


def to_fraction(text):
    """'1,234.50' -> Fraction(2469, 2).  Returns None if it is not a number."""
    if text is None:
        return None
    t = str(text).strip().replace(",", "").replace("$", "").rstrip(".")
    if not t:
        return None
    try:
        return Fraction(t)
    except (ValueError, ZeroDivisionError):
        try:
            return Fraction(float(t))
        except (ValueError, OverflowError):
            return None


def extract_final(text):
    """The generator's answer. Last FINAL: wins; fall back to the last number."""
    hits = _FINAL_RE.findall(text or "")
    if hits:
        return to_fraction(hits[-1]), "final_tag"
    nums = _ANYNUM_RE.findall(text or "")
    if nums:
        return to_fraction(nums[-1]), "last_number_fallback"
    return None, "no_number"


def answers_match(pred, gold, rel_tol=Fraction(1, 10**6)):
    """Exact where possible, relative tolerance for the huge GSM-Hard floats."""
    if pred is None or gold is None:
        return False
    if pred == gold:
        return True
    if gold == 0:
        return abs(pred) <= rel_tol
    return abs(pred - gold) / abs(gold) <= rel_tol


# ============================================================================
# 2. PULLING SMT-LIB OUT OF TEXT
# ============================================================================
_FENCE_RE = re.compile(r"```(?:smt2?|smtlib2?|lisp|scheme|z3)?\s*\n?(.*?)```", re.S | re.I)

# Commands the prompt forbids. Translators emit them anyway (GLM did on 10% of
# the smoke set), so strip rather than reject: an otherwise perfect encoding
# should not lose coverage over a trailing (check-sat).
_BANNED_RE = re.compile(
    r"^\s*\(\s*(check-sat|get-value|get-model|get-info|get-unsat-core|exit|echo|push|pop)\b.*$",
    re.M | re.I)
# set-logic must go too: a QF_LIA header makes the Int->Real pass ill-typed.
_SETUP_RE = re.compile(r"^\s*\(\s*(set-logic|set-option|set-info)\b.*$", re.M | re.I)


def extract_smt(text):
    """Return (smt_body, note). Empty body means nothing usable was produced."""
    if not text:
        return "", "empty_output"
    m = _FENCE_RE.search(text)
    if m:
        body, note = m.group(1), "fenced"
    elif "(declare-" in text or "(assert" in text:
        body, note = text, "unfenced_fallback"
    else:
        return "", "no_smt_found"
    n_banned = len(_BANNED_RE.findall(body))
    body = _BANNED_RE.sub("", body)
    body = _SETUP_RE.sub("", body)
    body = body.strip()
    if n_banned:
        note += f"+stripped{n_banned}"
    return body, note


# ============================================================================
# 3. THE `answer` VARIABLE
# ============================================================================
_DECL_CONST = re.compile(r"\(\s*declare-const\s+([^\s()]+)\s+([A-Za-z]+)\s*\)")
_DECL_FUN0 = re.compile(r"\(\s*declare-fun\s+([^\s()]+)\s*\(\s*\)\s*([A-Za-z]+)\s*\)")
_DEF_FUN0 = re.compile(r"\(\s*define-fun\s+([^\s()]+)\s*\(\s*\)\s*([A-Za-z]+)")


def answer_sort(body):
    """Sort of the constant named `answer`, or None if it is not declared."""
    for rx in (_DECL_CONST, _DECL_FUN0, _DEF_FUN0):
        for name, sort in rx.findall(body):
            if name == "answer":
                return sort
    return None


def promote_ints(body):
    """Int -> Real in every 0-arity declaration. The second semantics.

    Why: a translator that writes (declare-const answer Int) cannot be compared
    against 51.0 without a sort error, and integer division silently truncates.
    Re-reading the same encoding over the reals catches encodings that are
    right in substance but wrong in sort.
    """
    body = _DECL_CONST.sub(
        lambda m: f"(declare-const {m.group(1)} "
                  f"{'Real' if m.group(2) == 'Int' else m.group(2)})", body)
    body = _DECL_FUN0.sub(
        lambda m: f"(declare-fun {m.group(1)} () "
                  f"{'Real' if m.group(2) == 'Int' else m.group(2)})", body)
    body = _DEF_FUN0.sub(
        lambda m: f"(define-fun {m.group(1)} () "
                  f"{'Real' if m.group(2) == 'Int' else m.group(2)}", body)
    # Int-only operators are ill-typed over Real; map to their Real equivalents.
    body = re.sub(r"\(\s*div\s", "(/ ", body)
    return body


def smt_literal(frac, sort):
    """Exact SMT-LIB literal. No floats: 0.1 is not 1/10 in binary."""
    if frac is None:
        return None
    num, den = frac.numerator, frac.denominator
    if sort == "Int":
        if den != 1:
            return None                      # a non-integer cannot equal an Int
        return str(num) if num >= 0 else f"(- {abs(num)})"
    neg = num < 0
    a = abs(num)
    lit = f"{a}.0" if den == 1 else f"(/ {a}.0 {den}.0)"
    return f"(- {lit})" if neg else lit


# ============================================================================
# 4. ENTAILMENT
# ============================================================================
def _check(smt_src, timeout_ms):
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    s.from_string(smt_src)
    return s.check()


def check_one_semantics(body, target, timeout_ms=10000):
    """Does this encoding force answer == target?

    Two solver calls, and the first one is the important one:

      1. constraints alone must be SAT. A self-contradictory encoding entails
         EVERYTHING, so without this guard a broken translation would certify
         any answer at all. That is the single most dangerous failure mode for
         a certification claim, so it is checked first and fails closed.

      2. constraints AND (not (answer = target)) must be UNSAT. Then no model
         of the problem allows any other value, which is entailment.

    An under-determined encoding fails step 2 naturally: some other value is
    still possible, so the negation is satisfiable and nothing is certified.
    """
    sort = answer_sort(body)
    if sort is None:
        return "no_answer_var", None
    lit = smt_literal(target, sort)
    if lit is None:
        return "sort_mismatch", sort
    try:
        r1 = _check(body, timeout_ms)
    except z3.Z3Exception as e:
        return "parse_error", str(e).split("\n")[0][:120]
    if r1 == z3.unsat:
        return "unsat_constraints", sort            # vacuous - reject
    if r1 == z3.unknown:
        return "timeout_sat", sort
    try:
        r2 = _check(body + f"\n(assert (not (= answer {lit})))\n", timeout_ms)
    except z3.Z3Exception as e:
        return "parse_error", str(e).split("\n")[0][:120]
    if r2 == z3.unsat:
        return "certified", sort
    if r2 == z3.unknown:
        return "timeout_entail", sort
    return "not_entailed", sort


def verify(raw_text, target, timeout_ms=10000):
    """Full dual-semantics verdict for one translator on one problem."""
    body, note = extract_smt(raw_text)
    out = {"extract": note, "certified": False,
           "as_written": None, "int_promoted": None, "sort": None}
    if not body:
        out["as_written"] = out["int_promoted"] = "no_code"
        return out
    if target is None:
        out["as_written"] = out["int_promoted"] = "no_target"
        return out

    v1, sort = check_one_semantics(body, target, timeout_ms)
    out["as_written"], out["sort"] = v1, sort
    if v1 == "certified":
        out["certified"] = True
        out["int_promoted"] = "skipped"
        return out

    v2, _ = check_one_semantics(promote_ints(body), target, timeout_ms)
    out["int_promoted"] = v2
    out["certified"] = (v2 == "certified")
    return out


# ============================================================================
# 5. STATISTICS
# ============================================================================
import math
from collections import Counter


def wilson(k, n, z=1.96):
    """Wilson score interval. Behaves sensibly at k=0, which normal-approx does not."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - s) / d), min(1.0, (c + s) / d))


def rule_of_three(n):
    """95% upper bound on a rate when zero events were seen in n trials."""
    return 3.0 / n if n else 1.0


def arm_stats(gated, correct):
    """gated / correct are aligned lists of bools over the same problems."""
    n = len(gated)
    cov = [i for i in range(n) if gated[i]]
    nc = len(cov)
    cw = sum(1 for i in cov if not correct[i])
    lo, hi = wilson(cw, nc)
    out = {
        "n_total": n,
        "n_covered": nc,
        "coverage": nc / n if n else 0.0,
        "n_confident_wrong": cw,
        "cw_rate": cw / nc if nc else 0.0,
        "cw_wilson_95": [lo, hi],
        "acc_on_covered": (nc - cw) / nc if nc else 0.0,
    }
    if cw == 0 and nc:
        out["cw_rule_of_three_95_upper"] = rule_of_three(nc)
    return out


def correlation(a, b):
    """Pearson rho between two 0/1 lists. None if either has no variation."""
    n = len(a)
    if n < 2:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va == 0 or vb == 0:
        return None
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    return cov / math.sqrt(va * vb)


def decorrelation_check(e1, e2):
    """Empirical test of the decorrelation bound, on the wrong-answer subset.

        Pr[both certify] <= e1*e2 + rho*sqrt(e1(1-e1) * e2(1-e2))

    e1 / e2 are 0/1 lists: did translator i certify the generator's answer,
    restricted to problems where that answer is WRONG. So eps_i is exactly the
    single-translator wrong-certification rate, and the joint is what the
    AND-rule lets through.
    """
    n = len(e1)
    if n == 0:
        return {"n_wrong": 0, "note": "no wrong answers in this slice"}
    eps1 = sum(e1) / n
    eps2 = sum(e2) / n
    joint = sum(1 for i in range(n) if e1[i] and e2[i]) / n
    rho = correlation(e1, e2)
    indep = eps1 * eps2
    bound = None
    if rho is not None:
        bound = indep + rho * math.sqrt(eps1 * (1 - eps1) * eps2 * (1 - eps2))
    return {
        "n_wrong": n,
        "eps1_t1_wrongly_certifies": eps1,
        "eps2_t2_wrongly_certifies": eps2,
        "rho": rho,
        "independent_product": indep,
        "theorem_bound": bound,
        "observed_joint": joint,
        # None means "not computable" (rho undefined). Do not conflate that
        # with False, which would read as a violated bound.
        "bound_holds": None if bound is None else (joint <= bound + 1e-12),
    }


def majority_vote(fracs):
    """maj@k over extracted answers. Ties break toward the first-seen value."""
    vals = [f for f in fracs if f is not None]
    if not vals:
        return None
    c = Counter(vals)
    top = max(c.values())
    for v in vals:
        if c[v] == top:
            return v
    return None

# ============================================================================
# 6. PARALLEL WORKER
# ============================================================================
def verify_pair(payload):
    """One problem: extract, score, and verify both translators.

    This lives in the module rather than in a notebook cell on purpose.
    ProcessPoolExecutor pickles the callable to send it to the child, and a
    function defined in a Jupyter cell belongs to an interactive __main__ that
    the child cannot import — so a cell-defined worker raises PicklingError the
    moment you try to parallelise it.
    """
    pid, gen_text, t1_text, t2_text, gold, meta, timeout_ms = payload
    pred, how = extract_final(gen_text)
    gold_f = to_fraction(gold)
    r1 = verify(t1_text, pred, timeout_ms)
    r2 = verify(t2_text, pred, timeout_ms)
    return {
        "pid": pid,
        "pred": str(pred) if pred is not None else None,
        "pred_source": how,
        "gold": str(gold_f) if gold_f is not None else None,
        "correct": answers_match(pred, gold_f),
        "t1_certified": r1["certified"], "t1_detail": r1,
        "t2_certified": r2["certified"], "t2_detail": r2,
        "and_rule": bool(r1["certified"] and r2["certified"]),
        "meta": meta,
    }
