"""Conformal risk control over k-of-m translator agreement.

Reads Stage 1 raw JSONL, verifies with Z3, calibrates a selective-prediction
threshold, and reports a distribution-free bound on the confident-wrong rate.

    python crc.py --ckpt-dir ./ckpt --dataset gsm8k

CPU only. Rerunnable at zero cost: nothing here writes to the raw files.

--------------------------------------------------------------------------
WHAT IS BEING GUARANTEED, PRECISELY

Rule family: gate the generator's answer iff at least k of m translators
independently entail it. Increasing k shrinks the gated set (the family is
nested), so the confident-wrong rate is non-increasing in k. That nesting is
what makes a conformal argument possible at all; it is asserted and checked,
not assumed.

Procedure: split the dataset once into calibration and test. On calibration,
compute a one-sided upper confidence bound on the CW rate at each k, and take
the smallest k (highest coverage) whose bound is <= alpha.

Multiplicity: k is chosen adaptively over m candidates, so a single 95% bound
does not control the family. The per-k bound uses delta/m (Bonferroni). Without
this the procedure is anticonservative, and the difference is measurable - see
--audit.

--------------------------------------------------------------------------
THE CEILING, AND WHY IT MATTERS MORE THAN THE BOUND

No conformal method can certify a target below the rule family's own floor. If
unanimous agreement (k=m) still admits a CW rate of r, then alpha < r is
unreachable no matter how much calibration data you have. The floor is a
property of the translators, not of the statistics.

Measured floors: SVAMP 0.00%, GSM8K 1.06%, GSM-Hard 8.13%. So GSM-Hard admits
no useful certificate, and the procedure correctly refuses to emit one rather
than selecting a k that will violate on test.

--------------------------------------------------------------------------
EXCHANGEABILITY

The split-conformal guarantee needs calibration and test to be exchangeable.
That holds for a random split of GSM8K test. It does NOT hold across datasets:
pooling SVAMP with GSM-Hard breaks the assumption, and the CW rates differ by
almost an order of magnitude. Never pool.

GSM-Symbolic additionally has template structure (100 templates x instances),
so a random split leaks templates across calibration and test. Use a
template-grouped split there; this module does not implement one.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------------------------
_Z = {0.100: 1.2816, 0.050: 1.6449, 0.025: 1.9600, 0.0167: 2.1279,
      0.0125: 2.2414, 0.010: 2.3263, 0.005: 2.5758, 0.001: 3.0902}


def _z_for(delta):
    """One-sided normal quantile, nearest tabulated value."""
    return _Z[min(_Z, key=lambda d: abs(d - delta))]


def wilson_upper(errors, n, delta):
    """One-sided upper bound on a binomial rate.

    Wilson rather than normal-approximation: at n=188 with 2 errors the normal
    interval is badly wrong, and small certified denominators are the norm here.
    """
    if n == 0:
        return 1.0
    z = _z_for(delta)
    p = errors / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return min(1.0, (centre + half) / denom)


def hoeffding_upper(errors, n, delta):
    """Distribution-free alternative. Always valid, always looser than Wilson."""
    if n == 0:
        return 1.0
    return min(1.0, errors / n + math.sqrt(math.log(1.0 / delta) / (2 * n)))


def rule_of_three(n):
    """95% upper bound on a rate when zero events were observed in n trials."""
    return 3.0 / n if n else 1.0


# ---------------------------------------------------------------------------
# THE RULE FAMILY
# ---------------------------------------------------------------------------
def agreement_counts(cert, roles, pids):
    """pid -> how many of `roles` certified the generator's answer."""
    return {p: sum(1 for r in roles if cert[r][p]) for p in pids}


def gated(counts, pids, k):
    return [p for p in pids if counts[p] >= k]


def risk_at_k(counts, correct, pids, k):
    cov = gated(counts, pids, k)
    err = sum(1 for p in cov if not correct[p])
    return len(cov), err, (err / len(cov) if cov else 0.0)


def check_nested(counts, pids, m):
    """k+1 must gate a subset of k, or the conformal argument does not apply."""
    prev = None
    for k in range(1, m + 1):
        cur = set(gated(counts, pids, k))
        if prev is not None and not cur <= prev:
            return False
        prev = cur
    return True


# ---------------------------------------------------------------------------
# CALIBRATION
# ---------------------------------------------------------------------------
def select_k(counts, correct, cal_pids, alpha, delta, m, bound="wilson",
             bonferroni=True):
    """Smallest k whose calibration CW-rate upper bound is <= alpha.

    Returns (k, diagnostics). k is None when no threshold qualifies - which is
    the correct output when alpha sits below the family's floor, not a failure.
    """
    per_k_delta = (delta / m) if bonferroni else delta
    ub = wilson_upper if bound == "wilson" else hoeffding_upper
    rows = []
    chosen = None
    for k in range(1, m + 1):
        n, err, rate = risk_at_k(counts, correct, cal_pids, k)
        u = ub(err, n, per_k_delta)
        rows.append({"k": k, "n_cal": n, "err": err, "rate": rate, "upper": u,
                     "qualifies": bool(u <= alpha)})
        if chosen is None and u <= alpha:
            chosen = k
    return chosen, {"per_k_delta": per_k_delta, "table": rows}


def evaluate(counts, correct, test_pids, k):
    n, err, rate = risk_at_k(counts, correct, test_pids, k)
    out = {"k": k, "n_test": len(test_pids), "n_covered": n,
           "coverage": n / len(test_pids) if test_pids else 0.0,
           "cw": err, "cw_rate": rate,
           "cw_upper_95": wilson_upper(err, n, 0.05)}
    if err == 0 and n:
        out["cw_rule_of_three_95"] = rule_of_three(n)
    return out


def audit(counts, correct, pids, alpha, delta, m, trials=500, seed=0,
          bound="wilson", bonferroni=True, cal_frac=0.5):
    """Repeat the whole split-calibrate-test procedure and count violations.

    This is not part of the guarantee - it is the empirical check that the
    guarantee is actually delivered. A violation rate materially above delta
    means the procedure is anticonservative and the reported bound is wrong.
    """
    rng = random.Random(seed)
    picks, rates, covs, viol, abstain = [], [], [], 0, 0
    for _ in range(trials):
        sh = pids[:]
        rng.shuffle(sh)
        cut = int(len(sh) * cal_frac)
        k, _ = select_k(counts, correct, sh[:cut], alpha, delta, m, bound, bonferroni)
        if k is None:
            abstain += 1
            continue
        picks.append(k)
        n, err, rate = risk_at_k(counts, correct, sh[cut:], k)
        if n == 0:
            continue
        rates.append(rate)
        covs.append(n / len(sh[cut:]))
        if rate > alpha:
            viol += 1
    return {
        "trials": trials,
        "abstained": abstain,
        "selected": len(picks),
        "k_distribution": dict(sorted(Counter(picks).items())),
        "mean_test_cw_rate": (sum(rates) / len(rates)) if rates else None,
        "mean_test_coverage": (sum(covs) / len(covs)) if covs else None,
        "violations": viol,
        "violation_rate": (viol / len(rates)) if rates else None,
        "target_violation_rate": delta,
    }


# ---------------------------------------------------------------------------
# VERIFICATION (uses the same stage2_lib as every other result)
# ---------------------------------------------------------------------------
def load_raw(ckpt_dir, role, dataset):
    path = os.path.join(ckpt_dir, f"raw_{role}_{dataset}.jsonl")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return {json.loads(l)["pid"]: json.loads(l) for l in f if l.strip()}


def verify_all(ckpt_dir, dataset, roles, timeout_ms=10000, cache=None, verbose=True):
    """Return (pids, correct, cert, models). Cached: Z3 over 6x1319 is minutes."""
    if cache and os.path.exists(cache):
        d = json.load(open(cache, encoding="utf-8"))
        if d.get("dataset") == dataset and set(d["cert"]) == set(roles):
            if verbose:
                print(f"  loaded cached verdicts from {cache}")
            return d["pids"], d["correct"], d["cert"], d["models"]

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import stage2_lib as S

    gen = load_raw(ckpt_dir, "gen", dataset)
    if gen is None:
        raise SystemExit(f"missing raw_gen_{dataset}.jsonl in {ckpt_dir}")
    pids = sorted(gen)

    pred = {p: S.extract_final(gen[p]["outputs"][0])[0] for p in pids}
    correct = {p: bool(S.answers_match(pred[p], S.to_fraction(gen[p]["gold"])))
               for p in pids}

    cert, models = {}, {}
    for r in roles:
        d = load_raw(ckpt_dir, r, dataset)
        if d is None:
            raise SystemExit(f"missing raw_{r}_{dataset}.jsonl in {ckpt_dir}")
        if set(d) != set(pids):
            raise SystemExit(f"{r}: pid set differs from the generator - "
                             "a partial pass invalidates the denominators")
        pv = {x["prompt_version"] for x in d.values()}
        if len(pv) != 1:
            raise SystemExit(f"{r}: mixed prompt versions {pv}")
        models[r] = d[pids[0]]["model"]
        cert[r] = {p: bool(S.verify(d[p]["outputs"][0], pred[p], timeout_ms)["certified"])
                   for p in pids}
        if verbose:
            n = sum(cert[r].values())
            cw = sum(1 for p in pids if cert[r][p] and not correct[p])
            print(f"  {r}  cov {n/len(pids)*100:5.1f}%  CW {cw:3d}/{n:<5d}  {models[r]}")

    if cache:
        json.dump({"dataset": dataset, "pids": pids, "correct": correct,
                   "cert": cert, "models": models},
                  open(cache, "w", encoding="utf-8"))
    return pids, correct, cert, models
