"""Cluster-aware CRC for GSM-Symbolic. Extends crc_core; does not replace it.

crc_core's own docstring says it: GSM-Symbolic has template structure, a random
row split leaks templates across calibration and test, and that module does not
implement a grouped split. This does.

--------------------------------------------------------------------------
WHY THE ROW-LEVEL PROCEDURE IS NOT WRONG, ONLY ANSWERING A DIFFERENT QUESTION

Split conformal needs calibration and test exchangeable. A random permutation of
ROWS delivers that, so the row-level bound is a valid guarantee - for a new
INSTANCE of one of these 100 templates. It says nothing about a template the
calibration set never saw, because 50 instances of one template are near
duplicates: same structure, different numbers.

Two guarantees, both real, reported side by side:

  within-template   random row split, Wilson bound.
                    "a fresh instance of a template we calibrated on"
  across-template   grouped split, cluster bootstrap bound.
                    "an instance of a template we have never seen"

The SECOND is the one a reader assumes you mean. The gap between them is the
part of the certificate that is template memorisation rather than generalisation,
and it is worth reporting as a number rather than a caveat.

--------------------------------------------------------------------------
THE BOUND ALSO HAS TO CHANGE, NOT JUST THE SPLIT

Wilson assumes n independent Bernoulli trials. With 50 instances per template
the rows are not independent, the effective sample size is nearer the template
count than the row count, and Wilson on n=2500 is far too tight. Here the
exchangeable unit is the TEMPLATE: resample templates with replacement, pool
within each draw, and take the (1-delta) percentile. Zero-event cells fall back
to rule-of-three on the number of GATED TEMPLATES, not gated rows - the
difference between a 0.12% and a 6% honest upper bound.
"""
from __future__ import annotations

import json
import os
import random
from collections import Counter, defaultdict

import crc_core as C


# ---------------------------------------------------------------------------
# GROUPS
# ---------------------------------------------------------------------------
def load_groups(ckpt_dir, dataset, pids, role="gen"):
    """pid -> template_id, read from meta written at Stage 1."""
    raw = C.load_raw(ckpt_dir, role, dataset)
    if raw is None:
        raise FileNotFoundError(f"no raw_{role}_{dataset}.jsonl in {ckpt_dir}")
    groups = {}
    for p in pids:
        meta = (raw[p] or {}).get("meta") or {}
        tid = meta.get("template_id")
        if tid is None:
            raise KeyError(f"{p} has no meta.template_id - regenerate with the "
                           f"GSM-Symbolic loader")
        groups[p] = tid
    return groups


def group_split(pids, groups, cal_frac, rng):
    """Split by TEMPLATE so no template appears in both halves."""
    gs = sorted({groups[p] for p in pids})
    rng.shuffle(gs)
    cut = int(len(gs) * cal_frac)
    cal_g = set(gs[:cut])
    cal = [p for p in pids if groups[p] in cal_g]
    tst = [p for p in pids if groups[p] not in cal_g]
    return cal, tst, len(cal_g), len(gs) - len(cal_g)


# ---------------------------------------------------------------------------
# CLUSTER-AWARE UPPER BOUND
# ---------------------------------------------------------------------------
def per_group(counts, correct, pids, groups, k):
    """template_id -> (n_gated, n_cw) at threshold k."""
    out = defaultdict(lambda: [0, 0])
    for p in pids:
        if counts[p] >= k:
            out[groups[p]][0] += 1
            if not correct[p]:
                out[groups[p]][1] += 1
    return {g: tuple(v) for g, v in out.items()}


def cluster_upper(pg, delta, B=2000, seed=0):
    """One-sided upper bound on the pooled CW rate, resampling TEMPLATES.

    pg: {template_id: (n_gated, n_cw)}. Returns (upper, n_rows, n_err,
    n_groups_gated, method).
    """
    gated = [(n, e) for n, e in pg.values() if n > 0]
    n_rows = sum(n for n, _ in gated)
    n_err = sum(e for _, e in gated)
    G = len(gated)
    if G == 0:
        return 1.0, 0, 0, 0, "no_coverage"
    if n_err == 0:
        # Rule of three on GATED TEMPLATES. Using gated ROWS here would claim a
        # bound ~50x tighter than the data can support.
        return min(1.0, 3.0 / G), n_rows, 0, G, "rule_of_three_groups"

    rng = random.Random(seed)
    draws = []
    for _ in range(B):
        num = den = 0
        for _ in range(G):
            n, e = gated[rng.randrange(G)]
            num += e
            den += n
        if den:
            draws.append(num / den)
    if not draws:
        return 1.0, n_rows, n_err, G, "bootstrap_failed"
    draws.sort()
    idx = min(len(draws) - 1, int(round((1.0 - delta) * len(draws))))
    return draws[idx], n_rows, n_err, G, "cluster_bootstrap"


def risk_at_k_grouped(counts, correct, pids, groups, k, delta, B=2000, seed=0):
    pg = per_group(counts, correct, pids, groups, k)
    up, n, err, G, method = cluster_upper(pg, delta, B, seed)
    return dict(k=k, n=n, err=err, rate=(err / n if n else 0.0), upper=up,
                n_groups=G, method=method,
                coverage=(n / len(pids) if pids else 0.0))


# ---------------------------------------------------------------------------
# SELECTION + AUDIT, GROUPED
# ---------------------------------------------------------------------------
def select_k_grouped(counts, correct, cal_pids, groups, alpha, delta, m,
                     bonferroni=True, B=2000, seed=0):
    """Smallest k (highest coverage) whose cluster bound is <= alpha."""
    d = delta / m if bonferroni else delta
    table, chosen = [], None
    for k in range(1, m + 1):
        row = risk_at_k_grouped(counts, correct, cal_pids, groups, k, d, B, seed)
        table.append(row)
        if chosen is None and row["n"] > 0 and row["upper"] <= alpha:
            chosen = k
    return chosen, {"table": table, "per_k_delta": d, "bonferroni": bonferroni}


def audit_grouped(counts, correct, pids, groups, alpha, delta, m,
                  trials=200, seed=0, bonferroni=True, cal_frac=0.5, B=500):
    """Repeat split-calibrate-test with GROUPED splits and count violations.

    Not part of the guarantee - the empirical test of it. Fewer trials and a
    smaller inner bootstrap than the row-level audit because each trial now
    costs a nested resample.
    """
    rng = random.Random(seed)
    picks, rates, covs, viol, abstain, skipped = [], [], [], 0, 0, 0
    for t in range(trials):
        cal, tst, ng_cal, ng_tst = group_split(pids, groups, cal_frac, rng)
        k, _ = select_k_grouped(counts, correct, cal, groups, alpha, delta, m,
                                bonferroni, B, seed + t)
        if k is None:
            abstain += 1
            continue
        picks.append(k)
        n, err, rate = C.risk_at_k(counts, correct, tst, k)
        if n == 0:
            skipped += 1
            continue
        rates.append(rate)
        covs.append(n / len(tst))
        if rate > alpha:
            viol += 1
    return {"trials": trials, "abstained": abstain, "selected": len(picks),
            "no_coverage_on_test": skipped,
            "k_distribution": dict(sorted(Counter(picks).items())),
            "mean_test_cw_rate": (sum(rates) / len(rates)) if rates else None,
            "mean_test_coverage": (sum(covs) / len(covs)) if covs else None,
            "violations": viol,
            "violation_rate": (viol / len(rates)) if rates else None,
            "target_violation_rate": delta}


# ---------------------------------------------------------------------------
# CLUSTER BOOTSTRAP FOR rho
# ---------------------------------------------------------------------------
def cluster_boot_rho(cert, correct, pids, groups, a, b, B=3000, seed=0):
    """rho between two translators' wrong-certification indicators.

    Resamples whole TEMPLATES. The row bootstrap in the base notebook treats 50
    instances of one template as 50 independent draws and reports an interval
    roughly sqrt(50) too narrow.
    """
    wrong = [p for p in pids if not correct[p]]
    if not wrong:
        return None, None, None, 0
    by_g = defaultdict(list)
    for p in wrong:
        by_g[groups[p]].append(p)
    gs = list(by_g)
    e1 = [1 if cert[a][p] else 0 for p in wrong]
    e2 = [1 if cert[b][p] else 0 for p in wrong]
    point = C_correlation(e1, e2)

    rng = random.Random(seed)
    out = []
    for _ in range(B):
        s1, s2 = [], []
        for _ in range(len(gs)):
            for p in by_g[gs[rng.randrange(len(gs))]]:
                s1.append(1 if cert[a][p] else 0)
                s2.append(1 if cert[b][p] else 0)
        r = C_correlation(s1, s2)
        if r is not None:
            out.append(r)
    if len(out) < B * 0.5:
        return point, None, None, len(wrong)
    out.sort()
    return (point, out[int(0.025 * len(out))], out[int(0.975 * len(out))],
            len(wrong))


def C_correlation(x, y):
    """Phi coefficient. Local copy so this module does not depend on import
    order of stage2_lib."""
    n = len(x)
    if n == 0:
        return None
    sx, sy = sum(x), sum(y)
    if sx in (0, n) or sy in (0, n):
        return None
    sxy = sum(a * b for a, b in zip(x, y))
    num = sxy / n - (sx / n) * (sy / n)
    den = ((sx / n) * (1 - sx / n) * (sy / n) * (1 - sy / n)) ** 0.5
    return num / den if den > 0 else None


# ---------------------------------------------------------------------------
# SHARED-TEMPLATE RESTRICTION
# ---------------------------------------------------------------------------
def shared_templates(ckpt_dir, datasets, role="gen"):
    """Template ids present in EVERY listed split.

    p2 covers 50 of main's 100 templates. Comparing rho measured on 50 against
    rho measured on 100 confounds difficulty with which problems are in the
    pool, which is the one thing this dataset exists to control.
    """
    sets = []
    for ds in datasets:
        raw = C.load_raw(ckpt_dir, role, ds)
        if raw is None:
            raise FileNotFoundError(f"no raw_{role}_{ds}.jsonl in {ckpt_dir}")
        sets.append({(r.get("meta") or {}).get("template_id") for r in raw.values()})
    out = set.intersection(*sets)
    out.discard(None)
    return sorted(out)
