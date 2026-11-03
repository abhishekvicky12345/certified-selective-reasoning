<!-- P7 amendment 1. Written 25 Oct 2026 (A5 added 3 Nov), after Phase 0/1, before Phase 2 and before any faithfulness verdict. -->

# P7 amendment 1: G0.3, H5 and the faithfulness sample

Oct 25, 2026 (A5 added Nov 3) · @Abhishek

This amends `prereg/PREREG_verifier_ceiling.md` (P7; SHA-256 `f6dfbdd8f03a7677…`; commit 7a7856f). Everything this amendment doesn't name stands as registered.

## Timing: what had been seen when this was written

Phase 0 and Phase 1 ran on 24 Oct. A second machine (a Windows laptop) reproduced them on 25 Oct. Phase 2 has not started.

Already seen:

- Every Phase 0/1 output: the gates, the consensus sets, λ and R(s\_g) for each generator, the A6 certificate and S6.
- The H5 test and every variant listed for it. The first dry run of the Phase 0/1 notebook computed them before the notebook enforced B2's gate (24 Oct). That was a deviation from B2, and the notebook now skips H5 whenever a gate fails.
  - Primary: exact conditional one-sided p = 2.66 × 10⁻⁴³.
  - Conditional MLE of the common odds ratio: 0.007, with a one-sided 95% upper bound of 0.016.
- The G0.3 diagnosis runs described under A1.

Not yet seen:

- Any Phase 2 verdict on the 131 F\_3 problems outside the 21 audited before registration (B4). No Phase 2 packet has been built, and no LLM first pass has run.
- Any comparison with GSM8K-Platinum's labels (T2).
- Any faithfulness verdict on a certified-correct answer. The A5 sample had not been drawn when A5 was written.

## A1. G0.3 becomes a reported diagnostic, not a blocking gate

As registered, G0.3 failed. With promotion off, stage2\_lib gives:

| Cell | Got | Registered target |
| --- | --- | --- |
| GSM8K, k ≥ 3: \|C\| / \|F\|, Qwen A / W | 485 / 18, 467 / 7 | 461 / 16, 445 / 7 |
| GSM-Hard, k ≥ 3 | 390 / 55, 301 / 24 | 371 / 49, 286 / 22 |
| GSM8K, k = 4: \|C\| / \|F\| | 191 / 4 | 175 / 3 |
| GSM-Hard, k = 4 | 142 / 16 | 129 / 13 |

B2 stops every hypothesis test until all four gates pass, and a failure is reported, never patched around. This amendment keeps the failure in the record and changes only its consequence.

The evidence suggests the gate's target was misspecified, not the verifier:

- The target is the 25 Sep run, made with GPT ASTRA's direct-consensus code of 21 Sep. That code isn't available, and the target counts were reconstructed from printed rates (B2).
- Turning promotion off and counting only the votes cvc5 also certifies:
  - reproduces GSM8K at k ≥ 3 exactly (461 / 16, Qwen 445 / 7)
  - comes within two problems on GSM-Hard (373 / 50 against 371 / 49; Qwen 286 / 21 against 286 / 22)
  - gives 176 / 3 and 132 / 14 at k = 4 (targets 175 / 3 and 129 / 13)
- So the 25 Sep run most likely also dropped the encodings that a strict SMT-LIB parser rejects.
- This diagnosis ran after G0.3 failed, so it is post hoc.

What checks the implementation instead:

- G0.1: all 82,036 aggregate and 164,072 per-translator verdicts reproduced, and every headline cell is exact.
- CVC5 1.4.2 re-checked the 14,549 Z3 votes behind C\_3: 14,218 confirmed, none contradicted, 331 not parsed.
- The second machine gave the same certified values and the same outputs, apart from run stamps and floating-point noise in the 17th decimal place.

Consequence:

- G0.3 no longer blocks Phase 2 or H3a.
- The paper reports G0.3 as failed under the registered rule, together with this amendment, its date and the diagnosis.
- If GPT ASTRA's code turns up, it is run on the frozen artifacts and the result is reported. This amendment stands either way.

## A2. H5 becomes descriptive; H3a is the only primary test

- H5 was computed and seen before this amendment, so it can't be confirmatory.
  - It moves to the secondary analyses, with no decision attached.
  - Report R(s\_Pro), R(Pro) and λ(Pro) with intervals on every dataset, the per-dataset Fisher tests and the sensitivity runs, all marked as computed before Phase 2.
  - B6's H5 readings become descriptive. The paper may say the veto looks selective, never that H5 was confirmed.
- H3a stays primary, because its inputs, the Phase 2 L / M / Amb verdicts, are unseen.
- Level: one-sided α = 0.025.
  - This is the stricter of the two levels Holm could have given H3a. An amendment written after seeing H5 may make H3a's test stricter, never looser.
  - It replaces the 23 Oct decision "Holm across the two primaries".
  - B5's power figures at 0.025 apply: 6 Pro-favoured pairs are needed with no Qwen-favoured pair, 10 with 2, and 15 with all 5.
- Decision: supported if p < 0.025. Reversed if Qwen-favoured pairs outnumber Pro-favoured ones. Otherwise not supported.
- The test itself is unchanged (B5): an exact one-sided sign test on discordant L-problems, pooled over SVAMP, GSM8K and GSM-Hard, on the filtered population.

## A3. When Phase 2 starts

- Phase 2 starts when a rater first opens a packet. B4's second-rater rule refers to that moment.
- This amendment is committed before any Phase 2 packet is built and before the LLM first pass runs.
- The second rater's packets carry no LLM or author verdicts.

## A4. GSM8K-Platinum as an external check (new secondary analysis S8)

- For each GSM8K problem in F\_3, record whether GSM8K-Platinum keeps it unchanged, changes its label, or removes it.
- Report how the raters' L verdicts on those problems compare with Platinum's changes, with counts.
- Re-score every generator's certified GSM8K answers against Platinum's labels, and report W and R under both label sets.
- Order: Platinum's labels are matched to F\_3 problems only after every GSM8K verdict is locked (both raters', if there are two).
- No decision is attached.

## A5. The certified-correct faithfulness sample (new secondary analysis S9)

B4 says that if a faithfulness sample of certified-correct answers runs, its count with truth ≠ gold is reported with a one-sided upper bound. A5 fixes that sample before any of it is read. The sample also measures verdict-preserving unfaithfulness (VPU): an encoding that misstates the problem but still entails the right value.

**Population**

- C\_3 \\ F\_3 on the five in-scope datasets: filtered population, stage2\_lib semantics, primary scorer.
- Every generator's certified-correct answers lie in this set, because no problem has two values in S\_3 (G0.2).
- Stratum sizes: SVAMP 576, GSM8K 468, GSM-Hard 386, main 1,788, p1 925.

**Sample**

- 20 problems per dataset, 100 in total, drawn without replacement.
- Dataset i (in the order SVAMP, GSM8K, GSM-Hard, main, p1; i = 0 to 4) uses Python's `random.Random(20261103 + i)` on the stratum's pids sorted.
- On main and p1, first draw 20 distinct templates from the sorted template list, then one instance per template, in draw order, from its sorted instances.
- The draw script and the list of 100 pids are committed with the results.

**Packet**

- The question, the gold answer and the consensus value.
- The four encodings as the verifier read them. Each is marked with whether it entails the consensus value, and through which reading.
- No generator answers.

**Labels for each encoding that entails the consensus value**

- Faithful: the problem's quantities and relations are encoded as stated, and the answer variable is what the question asks.
- Literal: entails the right value with little or no modelling, for example a bare number or arithmetic on the problem's numbers, so the solver checks little more than the arithmetic.
- Unfaithful (VPU): misstates the problem, for example with a wrong relation, a missing or extra constraint, or a wrong quantity or question, yet still entails the right value. A short note says how.
- Unclear.

**Labels for each problem**

- Truth = gold.
- Truth ≠ gold: the consensus and the gold share an error (H).
- Ambiguous or ill-posed.

**Derived**

- A certificate is VPU-dependent if fewer than 3 of its entailing encodings are faithful or literal. Without its unfaithful encodings, it would not exist.
- A certificate is literal-dependent if fewer than 3 of its entailing encodings are faithful.

**Raters**

- An LLM first pass, then the author checks every verdict. Both are recorded.
- A second rater is optional.
- A5 doesn't touch F\_3, so it can run before, during or after Phase 2.

**Reported (descriptive; no decision attached)**

- Per dataset and pooled: the counts of VPU-dependent certificates, literal-dependent certificates and truth ≠ gold.
- Each count gets a one-sided 95% upper bound: Wilson at z = 1.645 if non-zero, 1 − 0.05^(1/n) if zero. So 0 of 20 gives 13.9%, and 0 of 100 gives 2.95%.
- The share of each encoding label.
- The pooled share both unweighted, with its bound, and weighted by stratum size, as a point estimate.

## Unchanged

Everything else in P7 stands:

- B0, B1 and B3.
- B4: all 152 filtered F\_3 problems, the labels, packets, masking and rater rules.
- B5's secondary analyses S1–S7 (S8 and S9 are added by A4 and A5).
- B6, apart from the H5 readings.
