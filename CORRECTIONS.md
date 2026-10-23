# CORRECTIONS

Append-only log of corrections to published CSR numbers, code and paper text.
Add new entries at the bottom. Never edit an old entry; correct it with a new one.

This file was started on 2026-10-23. No earlier copy was found on this laptop. If one turns up (for example on the old laptop, C:\Users\HP), put its entries above the first entry below, in date order.

When the code goes into the GitHub repo, this file goes at the repo root.

## 2026-10-22: Fraction answers read as their numerator (extract_final, as run)

**Found by.** The C3 extraction audit (`c3_extraction_audit2.ipynb`, run `extraction_audit_20261022_202416`).

**What was wrong.** The number pattern in `stage2_lib.extract_final` stops at "/". So a fraction on the `FINAL:` line was read as its numerator: `FINAL: 42159089/3` became 42159089.

107 of the 48,414 generator answers are bare fractions (96 a/b, 11 −a/b):

| Generator and dataset | Fraction answers |
|---|---|
| Pro GSM-Hard | 94 |
| Flash-Lite GSM-Hard | 4 |
| Pro SVAMP | 3 |
| Qwen p2 | 3 |
| Pro p1 | 2 |
| Qwen GSM8K | 1 |

**Code.**

- `stage2_lib.py` is unchanged. It is the copy that produced every published number (sha256 `a53fe6035bca098f…`, CRLF; the same bytes as in the public repo).
- New file: `extract_final_v2.py`, dated 2026-10-22. On the `FINAL:` line it reads a number followed by "/" and an unsigned number as that fraction.
- Everything else is as in v1: the same hits, tags and fallback, and the same `to_fraction`.
- A number over 1,000 digits reads as None on every Python version.
- `test_extract_final_v2.py` checks it. v2 differs from v1 on exactly the 107 rows, each time giving C3's careful reading. 67 answers go wrong → right and none go right → wrong.
- **Not covered:** mixed numbers, `\frac`, `× 10^n`, a Unicode minus, `-$5`, and text after a bold answer. None of these occurs on a `FINAL:` line in the 18 frozen files.

**Rerun.**

- `rerun_with_v2.ipynb`, output in `out\rerun_v2\<ts>\`.
- The 107 rows were re-verified with Z3 5.3.1: 438 verdicts with the v2 target.
- Every as-run value was reproduced first (gates A–G): all 360 cells of `arms_three_generators.json`, TOST run `20260927_234744`, `crc_*.json`, exact matching, and the Screen A/B cross-tabs.

**Published numbers that change** (as run → v2; k≥3 over m4 unless stated)

| Quantity | As run | v2 |
|---|---|---|
| Pro GSM-Hard wrong / accuracy | 313 / 76.27% | 247 / 81.27% |
| Pro GSM-Hard certified / certified-wrong | 400 / 37 | 421 / 41 |
| Pro GSM-Hard coverage / CW rate | 30.33% / 9.250% | 31.92% / 9.739% |
| Pro GSM-Hard ε | 37/313 = 11.82% | 41/247 = 16.60% |
| Flash-Lite GSM-Hard wrong / accuracy / ε | 314 / 76.19% / 29/314 | 313 / 76.27% / 29/313 |
| Qwen→Pro accuracy gain, GSM-Hard | 15.54 pts | 20.55 pts |
| Qwen→Pro CW movement, GSM-Hard | 1.125 pts | 1.614 pts |
| Three-generator CW spread, GSM-Hard | 1.678 pts | 2.167 pts |
| Swap factors e ÷ / ε × / c × / R × | 1.655 / 2.355 / 1.250 / 1.138 | 2.097 / 3.307 / 1.316 / 1.199 |
| GSM-Hard TOST: 90% MN interval | [−2.45, +4.58] | [−1.96, +5.06] |
| GSM-Hard TOST: D_min / p at ±5 pp | 4.58 / 0.033 | 5.06 / 0.053 (not equivalent at ±5 pp) |
| GSM-Hard paired variance ratio / paired-adjusted interval | 0.246 / [−0.65, +2.84] | 0.282 / [−0.28, +3.44] |
| GSM-Hard transitions RC→AC, RC→RW, RW→AC, RW→AW, RW→RC, RW→RW | 23, 38, 47, 14, 195, 236 | 30, 9, 57, 18, 222, 195 |
| Pro GSM-Hard k≥1 / k≥2 / k≥4 CW | 111/913, 73/652, 14/156 | 125/971, 80/689, 14/159 |
| Pro SVAMP k≥1 / k≥2 CW | 14/933, 7/796 | 16/935, 9/798 |
| Qwen GSM8K k≥1 / k≥2 CW | 35/1033, 15/753 | 36/1034, 16/754 |
| Flash-Lite GSM-Hard k≥1 / k≥2 CW | 81/841, 55/609 | 83/844, 56/611 |
| Largest Qwen→Pro movement, k≥2 / k≥4 | 1.63 (p2) / 0.78 | 1.88 (GSM-Hard) / 0.61 |
| Pro below Qwen at k≥1 | 6 of 6 datasets | 5 of 6 (GSM-Hard 12.87% vs 12.65%) |
| Table 4, GSM8K α 0.10 (k=1), test | 509/660 = 77.1%, CW 15 (2.95%) | 510/660 = 77.3%, CW 16 (3.14%) |
| Table 4, GSM8K α 0.05 (k=2), test | 366/660 = 55.5%, CW 8 (2.19%) | 367/660 = 55.6%, CW 9 (2.45%) |
| GSM8K audit, α 0.05 / α 0.03 (violations / certifying resplits) | 0/438 / 8/29 | 3/425 / 4/27 |
| GSM-Hard exact-matching CW, Pro (see the next entry) | 48/400 = 12.00% | 69/421 = 16.39% |
| GSM-Hard non-negative integer targets, Pro | 31/324 = 9.568% | 34/328 = 10.366% |
| Flash-Lite ∩ Pro wrong sets / wrong for all three | 256 (Jaccard 0.690) / 249 | 233 (0.713) / 228 |
| Screen B, Pro: CW flagged vs other wrong | 25/37 vs 109/276, one-sided p 0.0011 | 26/41 vs 107/206, p 0.12 (two-sided 0.23) |
| Screen A, Pro | 10/37 vs 43/276, p 0.07 | 10/41 vs 43/206, p 0.38 |

Notes on the table:

- **Table 4.** The selected k doesn't change. The moved row, GSM8K item 1199 (`FINAL: 8/3`, gold 2), is in the test split.
- **Pair arms** move on GSM-Hard (Pro: all six; Flash-Lite: t1×t3, t2×t3), SVAMP (Pro: t1×t6, t2×t3) and GSM8K (Qwen: t1×t3). See `arms_cells_that_move.csv`.
- **New Pro GSM-Hard certified-wrong answers**, not yet adjudicated: 0329, 0676, 0801, 1261.
- **Screen B lead.** The 26 Sep lead for Pro doesn't survive v2. 70 rows leave Pro's "other wrong" group, and 68 of them are unflagged, so v1 understated that group's flag rate. Qwen's lead is unchanged: 13/26 vs 122/492, one-sided p 0.0063, two-sided 0.0096.

**Unchanged.**

- Every Qwen number at k≥3, so the 21/37 certified-wrong audit stands.
- SVAMP and GSM8K at k≥3.
- Everything on GSM-Symbolic, under every rule (m4, m5, m6 and pairs). The 5 changed rows there stay wrong and uncertified.
- Table 4 for SVAMP and GSM-Hard.
- Exact-rational accuracies (52.6 / 69.5 / 72.8).
- The conjunctive TOST claim: all five in-scope datasets are equivalent only above 5.21 pp.

**Camera-ready text affected.**

- **Abstract:** "within ±5 points on GSM-Hard". Under v2 GSM-Hard is equivalent only at margins above 5.06 points.
- **Introduction, Figure 1 caption and §4:** "at most 1.13 points" becomes 1.61, and the 1.68 spread becomes 2.17.
- **Table 2:** the Pro GSM-Hard row.
- **Table 5:** the GSM-Hard TOST row (p 0.033 becomes 0.053).
- **§4.2 and Limitations:** the exact-matching paragraphs (9.69 / 12.00 / 2.31; see the next entry).
- **Appendix A:** Pro and Flash-Lite GSM-Hard accuracy.
- **§4.2 and Appendix F:** "at k≥1 Pro lowers the rate on every dataset", if the paper states it. Under v2 this holds on 5 of 6.
- **Table 4:** the GSM8K test cells, and "audits clean".

arXiv v1 reports v2 with the as-run values beside them.

## 2026-10-22: GSM-Hard scorer check; exact matching measures the gold's storage noise

**The setup.** GSM-Hard golds are program outputs stored as floats rounded to 10 decimal places, such as 2.0107e-06 and 1386.6666666667. Large golds also carry float noise, such as 1285665.9000000004. Three consequences follow.

**1. The 1e-6 tolerance is too tight on tiny golds.**

- 23 golds are below 5×10⁻⁵, where 10-decimal rounding exceeds 1e-6 relative.
- Some answers are scored wrong although they are right at the gold's precision. Qwen has none. Flash-Lite has 5 (0218, 0588, 0768, 1052, 1075). Pro has 8 under v2 (0218, 0346, 0405, 0588, 0670, 0906, 1052, 1216).
- None is certified at k≥2. 3 of Pro's are certified at k≥1 only.
- So no published certified-wrong count at k≥2–4 changes.

**2. The tolerance is too loose on large golds.**

- Some answers count as right only because of the tolerance, though they miss by whole units (for example 82085208 vs 82085198). That is Qwen 91, Flash-Lite 56, and Pro 19 as run or 22 under v2.
- Certified at k≥3:
  - Qwen: 1150
  - Flash-Lite: 0486, 1111, 1150
  - Pro: 0486, 1111, 1150, and 1250 under v2
- All four have integer golds and non-integer answers within one unit. Adjudicate them before calling them errors.

**3. Exact rational equality overcorrects.**

- It counts the golds' own noise as error.
- As run, 4 of Qwen's 5 extra exact-matching CW answers are noise (0397, 0482, 0675, 0712), and 8 of Pro's 11.
- Under v2 it also scores every repeating fraction wrong, for example 10/3 against 3.3333333333. That gives Pro 69/421.
- So the published exact-matching figures (Qwen 31, Pro 48, a 2.31-point gap) mostly measure storage noise.

**A storage-aware match** accepts |p − g| ≤ 5e-11 + 1e-12·|g|. The counts are identical for any float-noise term from 1e-14 to 1e-9.

| Measure (k≥3, GSM-Hard) | As run | v2 |
|---|---|---|
| CW, Qwen / Flash-Lite / Pro | 27/320, 32/383, 40/400 | 27/320, 32/383, 45/421 |
| Qwen→Pro movement | 1.56 pts | 2.25 pts |
| TOST p at ±5 pp | 0.056 | 0.101 |

Under v2, accuracy is 53.83% for Qwen, 72.40% for Flash-Lite and 80.21% for Pro.

**Status.** This is a sensitivity check only; the published scorer is unchanged. Whether arXiv v1 reports the storage-aware match instead of exact matching is still undecided.

## 2026-10-22: §3.2 (Verification) misdescribes the verifier

The camera-ready text says four things the code does not do:

- **"If the strict pass is inconclusive, integer sorts are promoted to reals."** In fact promotion runs after any strict result other than certified: a refutation, unsat over Int, a sort mismatch, a timeout or a parse error. The encoding certifies if either reading entails the candidate.
- **"Encodings failing the guard are discarded."** In fact the guard runs on each reading. An encoding that is unsat over Int can still certify through its Real reading (probe C1: 2·price = 5 certifies 10).
- **"A candidate matches the encoded answer … within a relative tolerance of 10⁻⁶."** In fact the verifier tests entailment of an exact rational literal. The 1e-6 tolerance belongs to the scorer (`answers_match`), which compares the candidate with the gold.
- **"A response with no parsable answer is recorded as unparsable rather than folded into wrong."** In fact such a response is scored wrong; Flash-Lite GSM-Hard's 314 errors include 4 of them. A response without a `FINAL:` line is read by its last number.

**Status.** No published number depends on the wording. The replacement text is in `verifier_section_fix_2026-10-22.tex`, for arXiv v1 and any post-conference revision.

## 2026-10-23: Decision: GSM-Hard's matching-rule check uses the golds' stored precision

**Decision.** For arXiv v1, GSM-Hard's matching-rule sensitivity check scores answers at the precision the golds were stored with. This replaces exact rational equality. The primary scorer is unchanged: `stage2_lib.answers_match` (exact, else 1e-6 relative).

**Rule.** `match_stored_precision.py` (dated 2026-10-23) accepts an answer when |p − g| ≤ 5e-11 + 1e-14·|g|.

- 5e-11 is half a unit in the 10th decimal place. No stored GSM-Hard gold has more than 10 decimals, and 111 have exactly 10.
- 1e-14 covers float noise in the stored golds. The noise needs at most 3.4e-16 (gsm_hard/0292). The closest answer that really differs from its gold would need 9.1e-13 (Flash-Lite gsm_hard/1184). Any allowance between the two gives the same verdict on every row.
- Outside GSM-Hard, the rule agrees with `answers_match` on every row of all 18 files.

**Correction to the 22 Oct scorer-check entry.** That entry used 1e-12 for the float-noise term and said the counts were identical from 1e-14 to 1e-9. This holds for the certified-wrong counts (k≥1–4, both readers) but not for every row: at 1e-12, Flash-Lite's 1184 (179.9999262334855 vs 179.9999262337) counted as right. With 1e-14:

- Flash-Lite has 57 answers that are right only by the 1e-6 tolerance, not 56.
- Flash-Lite's accuracy at stored precision under v2 is 72.33%, not 72.40%.
- Every certified-wrong count is unchanged.

**Numbers** (GSM-Hard; reader v2, with the as-run reader in brackets)

| | Qwen | Flash-Lite | Pro |
|---|---|---|---|
| CW at k≥3, stored precision | 27/320 = 8.44% [same] | 32/383 = 8.36% [same] | 45/421 = 10.69% [40/400 = 10.00%] |
| CW at k≥3, primary scorer | 26/320 = 8.12% [same] | 29/383 = 7.57% [same] | 41/421 = 9.74% [37/400 = 9.25%] |
| Accuracy, stored precision | 53.83% [same] | 72.33% [72.25%] | 80.21% [74.83%] |
| Integer targets (900), CW at k≥3 | 22/271 [same] | 26/314 [same] | 38/328 [34/324] |

- **Qwen→Pro movement at k≥3:** 2.25 points [1.56]. Under the primary scorer it is 1.61 [1.125].
- **Three-generator spread at k≥3:** 2.33 points [1.64].
- **TOST at k≥3:** 90% MN interval [−1.41, +5.80] [[−2.09, +5.11]]; D_min 5.80 [5.11]; p at ±5 pp 0.101 [0.056].
- **Qwen→Pro movement at k≥1 / k≥2 / k≥4:** −0.41 / +2.19 / +1.87 points [−0.88 / +1.67 / +1.42].

**Superseded.** The exact-matching figures stay in this log as as-run values: Qwen 31/320 = 9.69%, Pro 48/400 = 12.00%, a 2.31-point gap, and exact-rational accuracies of 52.6 / 69.5 / 72.8. Don't quote them as the sensitivity result.

**To adjudicate.** The certified answers this rule reclassifies at k≥3 sit on four problems: 0486, 1111, 1150 and 1250. Each has an integer gold and a non-integer answer within one unit of it.

**Where.**

- Rerun: `rerun_with_v2.ipynb`, cell 11, which writes `gsm_hard_stored_precision.csv`.
- Paper text: `verifier_section_fix_2026-10-22.tex`. Part 1 covers the last sentences of §3.2; part 2 covers "Matching rule" in §4.2 and Limitations, and the Appendix A note.
