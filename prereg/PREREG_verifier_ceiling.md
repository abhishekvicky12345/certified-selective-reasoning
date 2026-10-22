<!-- P7 registration copy. Exported 23 Oct 2026 from the Claude Docs doc "Verifier ceiling: bound and pre-registration (P7)", revision 40. The doc's A4 diagram is reproduced as the table under A4; nothing else is changed. -->

# Verifier ceiling: bound and pre-registration (P7)

Oct 23, 2026 · @Abhishek

## What this adds

At k ≥ 3 over m4, CSR certifies an answer only when it equals the translators' consensus value. So certified errors for any generator are capped by a set F that is measured with no generator at all.

- Part A states the cap, an exact split of the certified-error odds into a verifier term and a generator term, and the label floor of a truth-matching generator. It also covers a strategic generator that attacks the cap, and a certificate on joint error that holds for every generator.
- Part B pre-registers analyses that use existing artifacts only: validation gates, one problem-level adjudication of F, two primary tests and a short list of secondary ones.
- Nothing here has been computed under stage2\_lib. It becomes a registration only when exported to prereg, dated, hashed and committed before Phase 1 runs.

## Part A — The bound

### A1. Setup

Notation follows the paper where it can; each new symbol is defined once here.

- p: an eligible problem, N per dataset. y(p): its gold label. τ(p): adjudicated truth, where it can be determined.
- a ≈ b: the scorer's match (exact rationals or relative tolerance 1e-6, as in answers\_match).
- t1…tm: translators that see the question only. E\_i(p): translator i's encoding of p. Headline pool m4 = {t1, t2, t3, t6}, rule k of m.
- V\_i(p): the values that verify() certifies for E\_i(p) under its semantics (satisfiability guard, strict, then Int→Real promotion).
- votes\_p(v): the number of encodings i with v in V\_i(p).
- S\_k(p) = {v : votes\_p(v) ≥ k}: the values the pool would certify, whoever proposes them.
- C\_k: problems with S\_k(p) non-empty (the consensus set).
- F\_k: problems where some v in S\_k(p) has v ≉ y(p) (the false-certification set).
- g(p): generator g's answer as extract\_final\_v2 reads it (B0), or ⊥, which is never certified. A(g), W(g) and R(g) = W/A are the paper's accepted count, certified-wrong count and certified-wrong rate.

### A2. One value per encoding, one ceiling

Every certified-wrong answer, from any generator, sits on a problem in F\_k, so |F\_k| caps W.

**Lemma 1.** Under one fixed semantics, an encoding that passes the satisfiability guard certifies at most one value.

Proof: E ⊨ (ans = v1) and E ⊨ (ans = v2) with v1 ≠ v2 give E ⊨ ⊥, which the guard rules out. ∎

With strict semantics only, |V\_i(p)| ≤ 1. Promotion fires after any failed strict check (C1), so |V\_i(p)| ≤ 2, one value per reading. Two values need integer division: answer = 2·(div 9 2) certifies 8 strictly and 9 promoted. Without div, every Int model is also a Real model, so the two readings cannot certify different values.

**Lemma 2.** If every |V\_i(p)| ≤ 1 and 2k > m, then S\_k(p) holds at most one value.

Proof: the votes sum to at most m, which is below 2k, so two values cannot both reach k. ∎

This covers k ≥ 3 over m4 and m5, and k ≥ 4 over m6. Write c\_k(p) for that value.

**Corollary 1.** Under Lemma 2, g's answer on p is certified exactly when p is in C\_k and g(p) = c\_k(p), equality in the verifier's matching, which is exact (C1).

So CSR's accepted set is the direct-consensus set, filtered by the generator's agreement. This is the formal form of the direct-consensus result (run 21 Sep, checked 25 Sep): CSR is a strict subset of consensus.

**Proposition 1 (ceiling).** For every generator g, including one that has seen the translators' outputs, W(g) ≤ |F\_k| and A(g) ≤ |C\_k|. No uniqueness is needed.

Proof: if p counts in W(g), then g(p) is in S\_k(p) and g(p) ≉ y(p), so p is in F\_k. ∎

F\_k depends on the translators, the verifier's semantics, the questions and the gold labels. No generator enters it.

### A3. Odds identity

The certified-error odds split exactly into a verifier term, measured with no generator, and a generator term.

Under Corollary 1, define on each dataset:

- r\_0 = |F\_k| / |C\_k|: the error rate of direct consensus.
- a\_F(g): the share of F\_k where g(p) = c\_k(p). a\_G(g): the same share on C\_k \\ F\_k.
- λ(g) = a\_F(g) / a\_G(g): how readily g agrees with a wrong consensus, relative to a right one.

Then W = a\_F · |F\_k| and A = a\_F · |F\_k| + a\_G · |C\_k \\ F\_k|, so

```latex
\frac{R}{1-R} \;=\; \frac{r_0}{1-r_0}\,\lambda(g)
```

- λ < 1 is the selective veto. At λ = 1 the generator lowers coverage but not error relative to direct consensus.
- With the verifier fixed, "R flat across generators" is the same statement as "λ flat across generators".
- Like R = εe/c, this is an identity: it relocates the question and is not evidence. W sits inside R, ε and λ alike, so none corroborates another.
- What it buys: a change of verifier shows up in r\_0 directly, while a generator swap acts only through λ.

### A4. Truth split and the label floor

Adjudicated truth splits the consensus set into four cells, and F\_k is the two on the right.

*Scoring only sees the right column; truth splits it in two.*

| | Consensus matches gold | Consensus differs from gold |
| --- | --- | --- |
| **Consensus matches truth** | **Clean**: gold right, consensus right. Certified answers here are correct. | **L · label defect**: gold wrong, consensus right. A truth-matching generator is certified here and scored wrong. |
| **Consensus differs from truth** (the dashed row: genuine-error ceiling) | **H · hidden error**: consensus and gold share an error. Scored correct, genuinely wrong. | **M · shared misformalization**: consensus wrong. Hit only by a generator that makes the same error, or copies the consensus. |

Right column = F\_k, the scored ceiling, measured with no generator.

Ill-posed or ambiguous problems (Amb) sit outside the grid and are reported separately.

For a generator that always outputs the truth, Amb aside, the certified set is Clean plus L. Its scored certified-wrong count is |L|, and none of its certificates is genuinely wrong. Its rate is the label floor:

```latex
R^{*} \;=\; \frac{|L|}{|\mathrm{Clean}| + |L|}
```

- For any generator, genuinely wrong certificates number at most |M| + |H|, plus Amb: the dashed row.
- The camera-ready's perfect-generator limit (e = 0 gives R = 0) is a generator that matches gold. One that matches truth keeps R\* above 0 whenever gold has defects the consensus gets right. This is the exact form of the 27 Sep label-floor model (H3).
- On every problem in F\_k the certified value is c\_k(p), whoever answered. So one verdict per problem serves every generator: the adjudication unit is the problem, not the arm.

### A5. Strategic generator

A generator that copies the consensus wherever its base model disagrees turns the selective veto into an attack. Its success rate is the veto statistic already computed.

**Definition.** For a base generator b, s\_b outputs c\_k(p) wherever p is in C\_k and b(p) ≠ c\_k(p), and ⊥ elsewhere. Under Corollary 1:

- A(s\_b) = the number of problems b vetoes; W(s\_b) = the vetoed problems in F\_k; R(s\_b) = the share of b's vetoes that land in F\_k.
- The consensus copier (output c\_k wherever it exists) reaches the ceiling count W = |F\_k|, at R = r\_0.
- An adversary that also knows the gold can certify only F\_k and reach R = 1. So no generator-free bound exists for R itself; A6 gives one for joint error.
- Genuine attack success = the share of b's vetoes that land in M or H (A4). It needs the adjudication in B4.

Threat model: s\_b needs the consensus value, so it models a white-box verifier (open translators and prompts) or a generator able to simulate them. It is an upper reference, not a typical case.

Illustration only: not the paper's verifier, do not quote. These are the counts the no-promotion direct-consensus run implies for Qwen. Recompute under stage2\_lib (gate G0.3).

| Dataset | C\_3 | F\_3 | r\_0 | Qwen A / W | λ | Vetoes / in F\_3 | R(s\_Qwen) | R(Qwen) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSM8K | 461 | 16 | 3.47% | 445 / 7 | 0.44 | 16 / 9 | 56.25% | 1.57% |
| GSM-Hard | 371 | 49 | 13.21% | 286 / 22 | 0.55 | 85 / 27 | 31.76% | 7.69% |

C\_3 and F\_3 are reconstructed from the recorded coverage and error rates; each is the only integer that prints them. They reproduce the recorded vetoes (9 of 16, 27 of 85) and chance expectations (0.6, 11.2). The identity in A3 reproduces both R values exactly.

### A6. A certificate on joint error that holds for every generator

The ceiling yields a guarantee on P(certified and wrong) that holds for all generators at once, adversarial ones included. Selective risk R has no such guarantee.

**Proposition 2.** Draw n calibration problems i.i.d. from the distribution of test problems. Let f be the number of them in F\_k, and U(f, n) the one-sided (1 − δ) Clopper–Pearson upper bound. With probability at least 1 − δ over the calibration draw, every generator g satisfies

```latex
P_{\text{test}}(\text{certified} \wedge \text{wrong}) \;\le\; P(p \in F_k) \;\le\; U(f, n)
```

Proof: a certified wrong answer on p requires p to be in F\_k (proof of Proposition 1). That event does not involve g, and U is an ordinary binomial bound on its probability. ∎

- Computing U needs no generator output: the translators, the verifier and gold on the calibration half suffice.
- One event covers every generator, so the bound holds for all of them at once, adaptive or adversarial.
- It needs only that the generator cannot touch the translators' encodings, which answer-blind translation provides.
- This is the joint-error scale (A·W) raised in the 12 Oct guarantee check. That scale admits a generator-free bound; the selective rate the implementation controls does not (A5).
- With adjudicated truth in place of gold on the calibration half, the same argument bounds genuinely wrong certificates.
- GSM-Symbolic: rows share templates, so they are not i.i.d. Use the template as the unit, as for the zero-cell bounds; the bound is then on templates, not rows.
- Before calling this new, check [COVCAL (arXiv:2605.28365)](https://arxiv.org/abs/2605.28365) and [Kiyani et al. (arXiv:2602.17633)](https://arxiv.org/abs/2602.17633v1) for an equivalent statement.

### A7. What is new, what is definitional, what to check

The algebra is short, so any contribution has to come from measuring F\_k, splitting it with raters and testing predictions out of sample.

- One-liners: Lemmas 1–2, Proposition 1 and the odds identity. Reviewers will call them obvious; present them as the frame, not the result.
- Candidate contributions, if Part B holds up: a generator-free measure of a verifier (r\_0, |F\_k|/N); a mechanism for flatness (A4, H3a); the honest-versus-strategic gap (H5); the joint-error certificate (A6).
- Nothing here changes the submitted camera-ready. A6 waits for the main-track version; the rest reaches arXiv v1 only if the Phase 0 gates pass first.

Checks before any claim, answered 21–22 Oct (probe\_verify\_c1.ipynb: 37 of 37 rows matched on the laptop, Z3 5.3.1):

- C1. (a) Promotion runs after every failed strict check: not entailed, unsat over Int, a sort mismatch, a timeout or a parse error. So an encoding contradictory over Int can still certify through its Real reading (2·price = 5 certifies 10). (b) The guard also runs on the promoted reading. (c) The verifier matches the target exactly; the 1e-6 tolerance belongs to the scorer (answers\_match). That explains the 13 of 85 GSM-Hard vetoes between two answers both correct under 1e-6.
- C2. An unknown never certifies, but a strict unknown triggers promotion, so machine speed can change which reading certifies. The code labels every unknown "timeout". G0.1 logs reason\_unknown() and the Z3 version; a certificate mismatch is a finding, never forced into agreement.
- C3. ⊥ is never certified. The as-run reader kept only the numerator of a fraction on the FINAL: line: 107 of 48,414 answers, 94 of them Pro on GSM-Hard. Every count here uses extract\_final\_v2 (22 Oct), with the as-run value beside it where they differ (CORRECTIONS.md).
- C4. The stop rule does not fire: the guard runs on the promoted reading too.

## Part B — Pre-registration

### B0. Status, scope and mapping

This draft registers analyses on existing artifacts only: no new generation, no new translator runs, no API spend.

- Status: P7. Drafted 16 Oct 2026; final text 23 Oct 2026, after the C1–C4 verifier checks and the corrected answer reader. It becomes the registration when exported to prereg\\PREREG\_verifier\_ceiling.md, dated, hashed and committed before Phase 1. Later edits are dated amendments.
- Generators (frozen outputs): Qwen2.5-7B-Instruct, Gemini-3.1-Flash-Lite, Gemini-3.1-Pro.
- Verifier: m4 = {t1, t2, t3, t6}; headline rule k ≥ 3, k = 4 secondary; semantics as implemented in stage2\_lib (C1–C4).
- Answers and scoring: answers are read with extract\_final\_v2 (22 Oct), which reads a fraction on the FINAL: line in full; as-run values are reported beside v2 wherever they differ. Correct means stage2\_lib.answers\_match (exact, else relative 1e-6). GSM-Hard is also reported at the gold's stored precision (S7).
- Datasets: SVAMP, GSM8K, GSM-Hard, GSM-Symbolic main and p1, with template 76 excluded and the unfiltered result reported beside it. p2 is out of scope (below MIN\_COVERAGE 0.05).
- Mapping to the 27 Sep plan: H3a sharpens H3 (label-floor convergence). H5 scopes H1, so invariance is claimed for honest generators only. New translator pools (H2) and new generators (H4) need their own registration before any run.

### B1. Prior exposure

Some inputs were seen before registration, so the predictions are blind only where listed as unseen.

Seen:

- The no-promotion direct-consensus run for Qwen on GSM8K and GSM-Hard: coverage, error and vetoes (9 of 16, 27 of 85).
- Qwen→Pro transition counts on SVAMP, GSM8K and GSM-Hard: shared CW 4, 5, 23; Pro-only CW 1, 2, 18 (GSM-Hard 14 as run); Qwen-only CW 0, 2, 3.
- Verdicts on 21 of Qwen's 37 headline CW: 13 wrong label, 4 ill-posed or ambiguous, 4 genuine.
- Screen B flags on GSM-Hard CW, unadjudicated: Pro 26 of 41 (25 of 37 as run), Qwen 13 of 26, Flash-Lite 16 of 29. Screen A: Pro 10 of 41, Qwen 5 of 26, Flash-Lite 7 of 29.
- Translator verdicts on the 107 answers extract\_final\_v2 reads differently (C3 extraction audit, 22 Oct, flagged\_rows.csv), and their 438 re-verifications with the v2 target (v2\_reverified\_rows.json).
- rerun\_with\_v2 (run 20261023\_014600): every arms cell under both readers, the k ≥ 1–4 sweep, TOST, exact and stored-precision matching, and the scorer check. That check names the certified answers at k ≥ 3 that only the 1e-6 tolerance accepts: Qwen 1150; Flash-Lite 0486, 1111, 1150; Pro 0486, 1111, 1150, 1250.
- Wrong-answer overlap on GSM-Hard (answers only, no certificates): Flash-Lite and Pro 233, all three 228.
- The C1–C4 probe: hand-written encodings only, no dataset consensus.

Unseen:

- Every consensus set under stage2\_lib semantics, and any SVAMP or GSM-Symbolic consensus.
- Verdicts on the 21 Pro-only CW (17 as run; GSM-Hard's 18 include 0329, 0676, 0801 and 1261, new under extract\_final\_v2), the 16 unaudited Qwen GSM-Hard CW and every F-problem no generator hit.
- Vetoes with Flash-Lite or Pro as the base generator, apart from the transition counts above. That includes what Qwen and Pro did on problems where only Flash-Lite is certified wrong, which is why T1 (S6) runs only after registration.

### B2. Phase 0: validation gates (blocking)

All four gates must pass before any hypothesis test. A failure is reported, never patched around.

**G0.1 Agreement reproduces the certificates.** For every dataset, generator and problem, the certificate files' verdict must equal \[votes\_p(g(p)) ≥ k\], at k = 3 and k = 4. On the 107 rows extract\_final\_v2 reads differently, the reference is v2\_reverified\_rows.json, not the certificate files. Every unknown is logged with reason\_unknown() and the Z3 version (C2). Mismatches are listed by cause. These headline cells (A / W at k ≥ 3, extract\_final\_v2) must come out exactly:

| Generator | SVAMP | GSM8K | GSM-Hard | main | p1 |
| --- | --- | --- | --- | --- | --- |
| Qwen | 560 / 4 | 467 / 7 | 320 / 26 | 1,710 / 0 | 845 / 0 |
| Pro | 577 / 5 | 475 / 7 | 421 / 41 (400 / 37 as run) | 1,788 / 0 | 925 / 0 |

Also Flash-Lite on GSM-Hard 383 / 29, main 1,786 / 0 and p1 924 / 0, and unfiltered main: Qwen 1,749 / 28, Pro 1,828 / 29.

**G0.2 Uniqueness.** Count encodings that certify two values, and problems with two values in S\_3. Under strict-only semantics both must be 0 (Lemma 2); otherwise it is a bug. Under the implemented semantics, report both counts. If either is non-zero, Corollary 1 and A3 switch to the vote-set form. C1 showed the double-value case is real (integer division), so this gate is live.

**G0.3 Independent check.** With promotion switched off, reproduce the 25 Sep run: GSM8K |C\_3| 461, |F\_3| 16, Qwen 445 / 7; GSM-Hard 371, 49, 286 / 22; k = 4 consensus GSM8K 175 / 3, GSM-Hard 129 / 13. These counts are reconstructed from the recorded rates (each the only integer that prints them). Then list the GSM-Hard rows promotion adds for Qwen (286 / 22 → 320 / 26: a net 34 accepted, 4 of them wrong) and the reading that certified each.

**G0.4 Engineering.** The ok filter and a per-dataset assert on every load; the loader is the invariant; absent pids via set(loader) − set(pids). Failed API rows are never scored wrong. Every file opens with encoding='utf-8'.

### B3. Phase 1: compute (no adjudication)

Phase 1 produces the generator-free quantities and every generator's decomposition from existing files, on CPU.

For each dataset, at k = 3 and k = 4:

1. Entailed values per encoding with stage2\_lib's semantics: candidate values come from Z3 models, at most two per encoding (one per reading, C1), and a vote counts only when verify() certifies the value. Then votes, S\_k, C\_k and F\_k.
2. |C\_k|, |F\_k| and r\_0, with one-sided 95% upper bounds per the standing rules (Wilson; cluster bootstrap over templates on GSM-Symbolic).
3. For Qwen, Flash-Lite and Pro: A, W, a\_F, a\_G and λ. The identity must reproduce each R exactly from integer counts.
4. The strategic generators s\_Qwen, s\_FlashLite and s\_Pro, and the consensus copier: A, W and R.
5. Ceiling check: W(g) ≤ |F\_k| for every arm. A violation is a bug, not a result.
6. The A6 certificate on the existing calibration halves (SVAMP 500 / 500, GSM8K 659 / 660; GSM-Hard if its split is stored). U comes from the calibration half. On the test half, compare the realised share in F\_k with U, and each generator's W / n with that share.
7. Main is reported filtered and unfiltered together.
8. The T1 overlap for S6.

Output goes to out\\verifier\_ceiling\<timestamp>\\ from a new CPU-only notebook that opens ckpt\\ read-only. The size of F\_3 on each dataset is reported before any Phase 2 packet is built. S6 needs only the certificate files and v2\_reverified\_rows.json, so it may run as soon as this registration is committed, before Phase 0.

### B4. Phase 2: adjudicate F\_3 once, by problem

Each problem in F\_3 gets one verdict, which then serves every generator and the strategic analysis (A4).

- Scope: every problem in F\_3 on the five in-scope datasets; F\_4 lies inside F\_3. If F\_3 exceeds 200 problems in total, adjudicate every problem any generator hit, plus a seeded random sample of 50 others per dataset.
- Labels, with the 13–15 Oct rubric: wrong label → L; genuine misformalization → M; ill-posed or ambiguous → Amb. Tolerance artifacts get their own bucket, outside L and M.
- Packet per problem: question, gold, consensus value, the four encodings and which reading (strict or promoted) certified each. No generator identity, hit status or Screen B flag; order shuffled with a recorded seed.
- Masking: generator-masked by construction, since hit and un-hit problems enter alike. For the author it is partial, because 21 of these problems were audited before; those verdicts are reused and marked. Phase 1 output, S6 included, also shows the author which problems each generator hit; a second rater who has not seen it is fully masked.
- Raters: the author's verdicts after an LLM first pass, as in the camera-ready audit. A second independent rater covers all of F\_3 if recruited before Phase 2 starts; then report κ and both verdicts on every disagreement. If none is recruited by then, Phase 2 runs author-only and the paper says so.
- H (consensus and gold share an error) cannot be seen from F\_3. If the certified-correct faithfulness sample runs, report its count with truth ≠ gold and a one-sided upper bound.

### B5. Hypotheses, tests and decision rules

Two primary tests, Holm-corrected at a one-sided familywise α of 0.05. Everything else is secondary and reported in full.

**H3a (primary): stronger generators hit more label defects.** On L-problems, Pro agrees with the consensus more often than Qwen.

- Test: exact one-sided sign test on discordant L-problems (Pro agrees and Qwen does not, against the reverse). Pooled over SVAMP, GSM8K and GSM-Hard, filtered population.
- Why those three: no generator certifies a wrong answer on filtered main or p1, so no discordant pairs arise there.
- Decision: supported if the Holm-adjusted p < 0.05; reversed if Qwen-favoured pairs outnumber Pro-favoured ones; otherwise not supported.
- Power: pairs are capped at 21 Pro-favoured and 5 Qwen-favoured (the Pro-only and Qwen-only CW under extract\_final\_v2; 17 and 5 as run). At Holm's first-step level 0.025, Pro-favoured pairs needed: 6 with no Qwen-favoured pair, 10 with 2, 15 with all 5. At 0.05: 5, 9 and 13.

**H5 (primary): the veto is selective.** With Pro as the base, Pro agrees with the consensus less often on F\_3 than on C\_3 \\ F\_3. Equivalently, R(s\_Pro) > R(Pro).

- Test: exact conditional test of a common odds ratio below 1 on the agree/veto by in-F\_3/not table. Strata: SVAMP, GSM8K, GSM-Hard. Per-dataset Fisher tests are reported but do not decide.
- Agreement means the verifier's exact match. A Pro answer that differs from c\_3(p) only within the scorer's tolerance (for example 3.3333333333 against 10/3) counts as a veto. Sensitivity: the same test without those problems.
- Decision: supported if the Holm-adjusted p < 0.05; otherwise not supported. Report R(s\_Pro), R(Pro) and λ(Pro) with intervals on every dataset, GSM-Symbolic included.
- Pro is primary because its vetoes are unseen, apart from the five on Qwen-only CW problems (B1); Qwen and Flash-Lite are secondary. The Qwen illustration makes rejection likely, so the registered content is the size of the gap.

**Secondary (no decision attached):**

- S1, mirror of H3a: on M-problems, Qwen agrees with the consensus at least as often as Pro. Sign test, reported with counts.
- S2, label floor: R\* per dataset (A4) against R(Qwen), R(Flash-Lite) and R(Pro). Directional prediction: |R(Pro) − R\*| < |R(Qwen) − R\*| on GSM-Hard.
- S3, genuine attack success: the share of M and H among the F\_3-problems Pro vetoes. Directional prediction: above 50%.
- S4: λ per generator and dataset; r\_0 and |F\_3|/N per dataset; the A6 certificate and its test-half check.
- S5: all of the above at k = 4 and on unfiltered main.
- S6, T1 overlap: per dataset at k ≥ 3, the certified-wrong problems shared by all three generators, by each pair only, and by one generator only, with their pids. Descriptive.
- S7, matching: everything on GSM-Hard again, with answers matched at the gold's stored precision (match\_stored\_precision, 23 Oct) instead of the 1e-6 tolerance.

Deviations are dated and reported beside the result they affect.

### B6. Interpretation, kill criteria, exclusions

Each outcome has a reading fixed now, before any number exists.

- G0.1 fails beyond timeout cases → stop. Corollary 1 does not describe the implemented verifier; fix the definitions before any claim.
- H3a supported → the label-floor mechanism explains the swap, and the main-track framing moves to the plan's label-floor branch (unify with Story A).
- H3a not supported or reversed → the shared-misformalization branch stands, and G2 (vary the verifier) becomes the core experiment.
- H5 supported → the paper says invariance holds for honest generators and |F\_k| is the worst case. It never says certificates bound R for any generator.
- H5 not supported → Pro's veto is not selective. Report λ near 1 and drop the strategic framing.
- S6 mostly shared by all three generators → the floor sits on particular problems, as A4 expects; mostly generator-specific → errors depend on the generator. Phase 2's verdicts, not S6, say which kind of problem.
- |F\_3| < 5 on a dataset → descriptive only there.

Not covered, each needing its own registration: new translator pools (H2); new generators, including a weak one (H4); a non-GSM domain. Also excluded is RL with certificates as the reward. A5 suggests it would push a policy toward the consensus copier, but that is an untested conjecture.

### Decisions (23 Oct 2026)

Made by the author on 23 Oct 2026, before any Phase 1 output:

- [x] P-number P7; file prereg\\PREREG\_verifier\_ceiling.md.
- [x] Second rater: recruit one before Phase 2 if possible; otherwise author-only, disclosed (B4).
- [x] Flash-Lite: secondary; H3a stays Pro against Qwen.
- [x] Multiplicity: Holm across the two primaries.
- [x] A6: the main-track version, not arXiv v1.
- [x] H5: a difference only within the scorer's tolerance counts as a veto; sensitivity without those problems.
- [x] T1 runs after registration, as S6.
- [x] Answers are read with extract\_final\_v2; GSM-Hard is also scored at the gold's stored precision (S7).
