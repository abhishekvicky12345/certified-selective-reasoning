# Certified Selective Reasoning

### Decorrelated Neuro-Symbolic Verification with Distribution-Free Safety Guarantees

> **One line:** We use two small, cheap models plus a formal solver to decide when a large, expensive language model's maths answer can be trusted — and we put a real statistical certificate on that decision.

<p align="left">
  <img alt="Status" src="https://img.shields.io/badge/status-active%20research-blue">
  <img alt="Phase" src="https://img.shields.io/badge/phase-P1%20complete-green">
  <img alt="Problems evaluated" src="https://img.shields.io/badge/problems%20evaluated-3%2C638%20full--set-informational">
  <img alt="Target" src="https://img.shields.io/badge/target-MATH--AI%20%40%20NeurIPS%202026-orange">
  <img alt="License" src="https://img.shields.io/badge/license-MIT%20(code)-lightgrey">
</p>

**Author:** Abhishek — Independent Researcher
**Focus:** AI Safety · Scalable Oversight · Formal Verification of LLM Reasoning
**Last updated:** 5 August 2026

---

## ⚠️ Read This First — An Honesty Note

This README reports **what actually happened**, not what we hoped would happen.

Our main pre-registered mechanism — the idea that using two model *families* would make their errors independent — **did not survive contact with full-scale data**. We ran the control experiment we said we would run, and it came out against us.

We report that here, in full, with numbers, before we report anything that worked.

We do this for three reasons:

1. It is the correct thing to do.
2. A reviewer would find it anyway. Better that we find it first.
3. The parts that *did* work are more believable when you can see that we did not hide the parts that did not.

If you are a professor reading this to judge research taste: **the honest failure sections are the ones we would like you to read.** They start at [Section 7](#7-what-worked-and-what-did-not).

---

## Table of Contents

1. [The Problem in Plain Words](#1-the-problem-in-plain-words)
2. [The Core Idea](#2-the-core-idea)
3. [How the System Works](#3-how-the-system-works)
4. [Why This Is a Safety Project](#4-why-this-is-a-safety-project)
5. [The Exact Setup](#5-the-exact-setup)
6. [All Results So Far](#6-all-results-so-far)
7. [What Worked and What Did Not](#7-what-worked-and-what-did-not)
8. [Pre-Registered Predictions and Their Outcomes](#8-pre-registered-predictions-and-their-outcomes)
9. [Known Problems With Our Own Work](#9-known-problems-with-our-own-work)
10. [What We Are Building Next](#10-what-we-are-building-next)
11. [Timeline and Milestones](#11-timeline-and-milestones)
12. [Repository Layout](#12-repository-layout)
13. [How to Reproduce Everything](#13-how-to-reproduce-everything)
14. [Hardware, Cost, and Compute Discipline](#14-hardware-cost-and-compute-discipline)
15. [Engineering Lessons](#15-engineering-lessons)
16. [Statistical Rules We Follow](#16-statistical-rules-we-follow)
17. [Related Work](#17-related-work)
18. [Datasets and Licences](#18-datasets-and-licences)
19. [Citation](#19-citation)
20. [Contact](#20-contact)

---

## 1. The Problem in Plain Words

Large language models can solve school-level maths word problems very well. A 7-billion-parameter model gets about **9 out of 10** right on standard tests.

That is not the problem.

The problem is the **1 out of 10 it gets wrong**. When a model is wrong, it does not say so. It writes the wrong answer in the same calm, confident tone it uses for right answers. There is no shake in its voice.

We call this a **confident-wrong error**, or **CW error**.

CW errors are the dangerous kind, because:

- A right answer is fine.
- A wrong answer that the system flags as "not sure" is also fine — a human checks it.
- A wrong answer the system presents as certain is the one that gets used, trusted, and acted on.

The usual fixes do not remove CW errors:

| Usual fix | What it does | Why it does not solve CW |
|---|---|---|
| Make the model bigger | Fewer errors overall | The remaining errors are still confident |
| Sample 8 answers, take the majority vote | Fewer errors overall | If the model is confused, all 8 samples are confused the same way |
| Ask a stronger model to judge | Fewer errors overall | You now need a stronger model, which is the thing you were trying to avoid |
| Have a human check | Works | Too slow and too expensive to do for every answer |

Every one of these makes errors **rarer**. None of them makes errors **detectable**.

**Our question is different.** We do not ask "how do we make the model right more often?" We ask:

> **Can we build a cheap checker that reliably knows when it does not know — and prove it with a number?**

---

## 2. The Core Idea

The idea has three parts.

### Part 1 — Selective prediction

Instead of forcing the system to answer everything, we let it say **"I don't know."**

The system answers a subset of questions and abstains on the rest. Abstained questions go to a human, or to a more expensive fallback.

Two numbers describe this:

- **Coverage** — what fraction of questions we answer.
- **CW rate** — of the questions we *did* answer, what fraction were confidently wrong.

The goal is not high coverage. **The goal is a low CW rate, with coverage as high as we can get for free.** A system that answers 30% of questions with almost no confident errors is far more useful for safety than one that answers 100% with 6% confident errors.

### Part 2 — Cheap verification of an expensive model

The generator is the expensive, capable, untrusted part.

The verifier is the cheap, simple, trusted part.

We never ask a small model to be *smarter* than the big one. We only ask it to do something much easier: **translate a word problem into equations.** Checking that equations force a specific answer is then done by a formal solver — a piece of software with no opinions, no hallucinations, and no confidence.

This is the general shape of **scalable oversight**: use something weak and trustworthy to keep something strong and untrustworthy honest.

### Part 3 — Redundancy across independent checkers

One translator can misread a problem. So we use **two** translators, and we accept the generator's answer only if **both** independently produce equations that force that same answer.

Our original hypothesis was that translators from **different companies** would make **unrelated** mistakes, so both being wrong at once would be very rare.

**We tested this. It is not true.** See [Section 7](#7-what-worked-and-what-did-not). The redundancy still helps, but not for the reason we expected, and not by as much as we predicted.

---

## 3. How the System Works

### The pipeline

```
                    ┌───────────────────────────────┐
   word problem ──▶ │  GENERATOR (frozen, untrusted)│ ──▶  answer  g
                    │  Qwen2.5-7B-Instruct, greedy  │
                    └───────────────────────────────┘
                                  │
             ┌────────────────────┴────────────────────┐
             ▼                                         ▼
  ┌────────────────────────┐              ┌────────────────────────┐
  │ TRANSLATOR t1          │              │ TRANSLATOR t2          │
  │ DeepSeek-Coder-V2-Lite │              │ GLM-4-9B-0414          │
  │ (DeepSeek family)      │              │ (Zhipu family)         │
  │ word problem → SMT-LIB │              │ word problem → SMT-LIB │
  └───────────┬────────────┘              └───────────┬────────────┘
              │  constraints C1                       │  constraints C2
              ▼                                       ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  Z3 SOLVER  —  two questions asked IN THIS ORDER              │
  │                                                                │
  │  STEP 1 (satisfiability guard):                                │
  │      Is C satisfiable at all?                                  │
  │      If NO → reject. (Broken equations prove everything.)      │
  │                                                                │
  │  STEP 2 (entailment):                                          │
  │      Is  C ∧ ¬(answer = g)  unsatisfiable?                     │
  │      If YES → C forces the answer g. Certificate granted.      │
  └──────────────────────────────────────────────────────────────┘
              │                                       │
              └──────────────────┬────────────────────┘
                                 ▼
             ┌────────────────────────────────────────┐
             │  DECISION RULE (deterministic, no ML)  │
             │  Both certify?   → ACCEPT  g           │
             │  Otherwise       → ABSTAIN             │
             └────────────────────────────────────────┘
                                 │
                                 ▼
             ┌────────────────────────────────────────┐
             │  CONFORMAL RISK CONTROL (CRC) layer    │
             │  Tunes k-of-N agreement threshold to   │
             │  meet a user-chosen risk level α       │
             │  with distribution-free confidence     │
             └────────────────────────────────────────┘
```

### Worked example

**Question:** *"Jack has 7 boxes. Each box has 6 pens. How many pens does he have?"*

**Generator says:** `42`

**Translator t1 writes:**

```lisp
(declare-const boxes Int)
(declare-const per_box Int)
(declare-const answer Int)
(assert (= boxes 7))
(assert (= per_box 6))
(assert (= answer (* boxes per_box)))
```

**Z3, Step 1:** Are these equations satisfiable? Yes — `boxes=7, per_box=6, answer=42` works.

**Z3, Step 2:** Add `(assert (not (= answer 42)))`. Is it now unsatisfiable? Yes. So the equations *force* `answer = 42`.

**t1 certifies.** If t2 also certifies, we accept.

### Why the satisfiability guard is not optional

This is one of our real findings, and it is easy to get wrong.

In logic, **a contradiction proves everything.** If a translator writes equations that contradict each other, then `C ∧ ¬(answer = g)` is unsatisfiable *for every possible value of g*. A naive checker will "certify" any answer you hand it.

And translators do this often. Here is the real failure we found by pulling unsat cores:

```lisp
(assert (= boxes 7))
(assert (= per_box 6))
(assert (= total (* boxes per_box)))   ; correct chain
(assert (= total 48))                  ; ← the model's own wrong mental arithmetic
```

The model wrote a *correct* relationship **and** hardcoded its *incorrect* head-computed value. The two contradict. Without the guard, this encoding certifies literally anything.

**How often this happens (measured, not estimated):**

| Dataset | t1 self-contradictory | t2 self-contradictory |
|---|---:|---:|
| SVAMP | 11.9% | 9.8% |
| GSM-Hard | 21.5% | 15.0% |

On GSM-Hard, **roughly one in five** encodings would have been vacuously certified without this guard. That is about a fifth of our coverage — worthless coverage.

**Design decision:** we do **not** patch the prompt to suppress this behaviour. It is a genuine translator error mode and the guard catching it is a feature, not a workaround.

Under-determined encodings (too few constraints) fail Step 2 naturally, so they need no extra guard.

---

## 4. Why This Is a Safety Project

This is not a maths-benchmark project. Maths is the **testbed**, chosen because ground truth is unambiguous and formal verification is tractable there.

The framings we care about:

**Cheap trusted verification of expensive untrusted models.**
As models get stronger, we lose the ability to check them by inspection. We need verification methods where the *verifier* stays simple and auditable even as the *generator* races ahead. A 7B translator plus Z3 is auditable. A frontier model acting as judge is not.

**Scalable oversight.**
The weak-to-strong direction — a weak verifier constraining a strong generator — is the central open problem in oversight. Our planned weak-to-strong experiment (Gemini 3.1 Pro as generator, small local translators as verifiers) tests exactly this asymmetry.

**Driving confident-wrong errors toward zero as a certified property.**
The goal is not "better accuracy." It is a *property you can state and check*: under stated assumptions, the confident-wrong rate on accepted answers is at most α, with confidence 1−δ. That is the shape of a safety guarantee.

**A micro-instantiation of Guaranteed-Safe AI.**
The Guaranteed-Safe AI agenda asks for systems with formal, auditable safety arguments. Full versions of that are far off. This project is a small, complete, honest instance of the pattern: world model (SMT constraints) + verifier (Z3) + certificate (conformal bound).

**Auditability by construction.**
There is **no learned router** in the decision path. The decision rule is deterministic and inspectable. All flexibility in the operating point comes from the conformal layer, which is itself a stated, checkable procedure. A reviewer can read the rule and know exactly what it does. This was a deliberate design choice, and we removed an earlier trained router to get it.

---

## 5. The Exact Setup

Configuration locked **19 July 2026**. Nothing below has been changed since. This section supersedes all earlier drafts.

### Models

| Role | Model | Family | Notes |
|---|---|---|---|
| **Generator** | Qwen2.5-7B-Instruct | Alibaba | **Frozen.** Greedy decoding. No fine-tuning. |
| **Translator t1** | DeepSeek-Coder-V2-Lite-Instruct | DeepSeek | 15.7B MoE |
| **Translator t2** | GLM-4-9B-0414 | Zhipu | `zai-org` release, **not** THUDM |
| Translator t3 | Qwen2.5-Coder-7B-Instruct | Alibaba | Comparison rows only — shares family with generator |
| Translator t4 | Mistral-7B-Instruct-v0.3 | Mistral | **Unusable** — see below |
| Translator t5 | DeepSeek-V2-Lite-Chat | DeepSeek | **Unusable** — see below |
| Translator t6 | deepseek-coder-6.7b-instruct | DeepSeek | Same-family control (works) |
| **Verifier** | Z3 | — | Dual semantics (C3), Int→Real promotion |
| Verifier cross-check | CVC5 | — | Planned, P2 |
| BoN judge | Gemini 3.1 Pro | Google | Batch API |
| Weak-to-strong generator | Gemini 3.1 Pro | Google | Planned, P5 |

**Why the generator stays frozen.** If we tuned the generator on GSM8K training data, we could no longer tell whether a CW improvement came from the verifier or from the tuning. That is an attribution confound that destroys the entire claim. It also creates a benchmark-tuning optics problem. So: **frozen, forever, no exceptions.**

**Why two translators were unusable.** They almost never certify anything, so they produce too few wrong-certification events for ρ to be measurable:

| Translator | Coverage: SVAMP / GSM8K / GSM-Hard | Verdict |
|---|---|---|
| t4 Mistral-7B-Instruct-v0.3 | 17.6% / 5.8% / 4.0% | Too few events for ρ |
| t5 DeepSeek-V2-Lite-Chat | 3.0% / 0.6% / 0.4% | Cannot produce SMT-LIB at all |

The t5 case is instructive: it is the **chat** variant, not the coder variant. In 443 of 462 SVAMP failures it never wrote the word `answer` — it simply cannot follow the SMT-LIB format. This is a model-selection lesson, not a result.

**Usable set for ρ analysis:** t1, t2, t3, t6. Of these, t3 is comparison-rows-only because it shares the Alibaba family with the generator.

### Datasets

| Dataset | Size | Purpose | Status |
|---|---:|---|---|
| SVAMP | 1,000 | Simple problems, tests over-verification | ✅ Full run done |
| GSM8K test | 1,319 | Standard reference; CRC calibration lives here | ✅ Full run done |
| GSM-Hard | 1,319 | Large-number stress test | ✅ Full run done |
| GSM-Symbolic main | 5,000 | Template structure → hardness-conditioned ρ | ⬜ Planned P2 |
| GSM-Symbolic p1 | 5,000 | Distribution shift | ⬜ Planned P2 |
| GSM-Symbolic p2 | 2,500 | Distribution shift, harder | ⬜ Planned P2 |
| **Total** | **16,138** | | **3,638 done** |

**Run order:** SVAMP → GSM-Hard → GSM8K → GSM-Symbolic main → p1/p2.

**Scope rule for guarantees:** conformal guarantees are claimed **only on GSM8K test**, where exchangeability holds. On shift datasets we report cluster-aware bootstrap confidence intervals and nothing stronger. This restriction is deliberate and stated in the paper.

### The decision rule

Deterministic. No learned component.

```
accept(g)  ⟺  sat(C1) ∧ entails(C1, answer = g)
              ∧ sat(C2) ∧ entails(C2, answer = g)
```

Generalised for the conformal layer to a **k-of-N agreement** rule over N usable translators, where k is chosen by the CRC procedure.

### Family-disjointness invariant (as originally designed)

| Family | Roles assigned |
|---|---|
| Alibaba | generator only |
| DeepSeek | t1, teacher 1 |
| Zhipu | t2, teacher 2 |
| Google | BoN judge, weak-to-strong oversight generator |

**Note:** this invariant was designed to enforce a mechanism we have since failed to confirm. We keep it because it remains good hygiene, but we no longer claim it *causes* decorrelation. See [Section 7](#7-what-worked-and-what-did-not).

### Baselines

- Greedy generator (no verification)
- **maj@8** — majority vote over 8 samples at T=0.8, top-p 0.95
- **pass@8** — upper bound on any reranker
- BoN-8 with Gemini 3.1 Pro judge (optional; see Prediction (i))
- BoN-8 self-judge

---

## 6. All Results So Far

### 6.1 Generator baselines (full datasets, no subsampling)

| Metric | SVAMP (1,000) | GSM8K test (1,319) | GSM-Hard (1,319) |
|---|---:|---:|---:|
| Generator, greedy | 92.1% | 89.5% | 60.7% |
| maj@8 | 93.6% | 92.6% | 64.0% |
| **pass@8** (any-reranker ceiling) | **96.6%** | **96.1%** | **71.7%** |

`pass@8` matters because it caps what *any* Best-of-n reranker could ever achieve, no matter how good the judge. Maximum possible BoN lift over majority vote is therefore **+3.0 pp** (SVAMP), **+3.5 pp** (GSM8K), **+7.7 pp** (GSM-Hard).

### 6.2 Cross-family AND-rule (t1 × t2) — headline numbers

| Dataset | Coverage | CW count | CW rate | Reduction vs. single translator |
|---|---:|---:|---:|---:|
| SVAMP | 43.6% | 3 / 436 | **0.69%** | 1.96× |
| GSM8K test | 28.9% | 7 / 381 | **1.84%** | 1.56× |
| GSM-Hard | 19.9% | 26 / 262 | **9.92%** | 1.01× |

Relative coverage loss vs. a single translator: roughly **35–43%**.

**Against our stated success criteria:**

| Criterion (pre-registered) | Target | Actual | Verdict |
|---|---|---|---|
| Pooled AND-rule CW = 0 | 0 | 3 / 7 / 26 | ❌ **Not met** |
| Pooled 95% upper bound ≤ 0.15% | ≤0.15% | unreachable (floor ~1.06%) | ❌ **Not met** |
| ≥10× CW reduction vs. single | ≥10× | 1.96× / 1.56× / 1.01× | ❌ **Not met** |
| Relative coverage loss ≤ 40% | ≤40% | 35–43% | ⚠️ **Roughly holds** |
| Monotone CW–ρ relationship | monotone | monotone on 3 points | ✅ **Met** |

The earlier banked `CW = 0` results — GSM-Symbolic at n≈200 and a smoke test at n=40 — **did not survive full-scale evaluation.** They were small-sample artefacts. This is exactly why we require full dataset runs.

### 6.3 Correlation ρ between translator errors

ρ is the correlation between the two translators' wrong-certification events. Higher ρ means their mistakes overlap more, so redundancy buys you less.

| Dataset | ρ(t1 × t2) — cross-family | AND-rule CW rate |
|---|---:|---:|
| SVAMP | 0.248 | 0.69% |
| GSM8K test | 0.411 | 1.84% |
| GSM-Hard | 0.580 | 9.92% |

**This is monotone and clean.** As ρ rises, the benefit of the AND-rule decays to nothing. By ρ ≈ 0.58 on GSM-Hard, the two-translator rule buys essentially zero improvement over one translator (1.01×).

This is a genuine, well-powered finding and is currently our second-strongest result.

### 6.4 Same-family control — the result that contradicts us

We ran the control we pre-registered. The prediction was **ρ(same-family) ≫ ρ(cross-family)**.

| Dataset | ρ(t1, t6) same-family | ρ(t1, t2) cross-family | Direction |
|---|---:|---:|---|
| SVAMP | 0.276 | 0.248 | Same higher (weakly powered) |
| GSM8K test | **0.187** | **0.411** | ❌ **Same LOWER** |
| GSM-Hard | **0.372** | **0.580** | ❌ **Same LOWER** |

On **both well-powered datasets**, same-family correlation is *lower* than cross-family. On GSM-Hard, t1×t6 (both DeepSeek) has the **lowest ρ of all six pairs tested**.

**Family disjointness is not supported as the mechanism.**

First control attempt failed for a separate reason: t5 (DeepSeek-V2-Lite-Chat) covered only 3% of SVAMP, certified none of the 79 wrong answers, and left ρ undefined. We replaced it with t6 (deepseek-coder-6.7b-instruct), which works.

**Alternative hypothesis (stated as a hypothesis, not a finding):** ρ may track **capability similarity**, not family. The highest-ρ pairs are the highest-coverage translators. Two models that are similarly good at the task fail on similar problems, regardless of who trained them.

**Caveats we state explicitly:**
- t6 is 6.7B dense; t1 is 15.7B MoE, and a different coder generation. So t6 is a same-family but **not capability-matched** control.
- All confidence intervals overlap. This is directional evidence, not proof.
- A properly capability-matched same-family control is future work.

### 6.5 Conformal Risk Control — the result that works

This is what earns the words *"distribution-free guarantees"* in the title.

**The problem CRC solves.** A fixed 2-of-2 AND-rule has no tunable parameter. There is nothing to calibrate. But with four usable translators, the rule family becomes **k-of-4 agreement**, which is discrete, **nested** (we checked this — did not assume it), and monotone. That is exactly the structure conformal risk control needs.

**Procedure:**
1. Split into calibration and test sets.
2. At each k, compute a one-sided Wilson upper bound on the calibration CW rate.
3. Pick the smallest k (highest coverage) whose bound is ≤ α.
4. Apply Bonferroni correction δ/m over the m candidate thresholds, because k is chosen adaptively.

**Results (delivered 1 August 2026):**

| Dataset | Certificate | k | Coverage | Empirical violations |
|---|---|---:|---:|---|
| GSM8K test | CW ≤ **5%** at 95% confidence | 2 | 55.5% | 0 / 438 over 500 splits |
| SVAMP | CW ≤ **3%** at 95% confidence | 3 | 59.2% | 0% over 500 splits |
| GSM-Hard | **Abstains at every α** | — | — | Correct behaviour |

GSM-Hard abstaining is the right outcome, not a failure. The method correctly refuses to issue a certificate it cannot support.

**The ceiling result — more interesting than the certificate itself.**

No conformal method can certify below the rule family's own floor. We measured those floors:

| Dataset | CW floor |
|---|---:|
| SVAMP | 1.12% (rule-of-three on 0/268 — **not** 0.00%) |
| GSM8K test | 1.06% |
| GSM-Hard | 8.12% |

This is a genuine limit, and it is why our original ≤0.15% target was never reachable with this rule family. Reporting the ceiling alongside the certificate is, we think, the more useful scientific contribution.

**Caveat we state:** the k=2-of-4 rule can be satisfied by t1 + t6, **both DeepSeek**. So the CRC-selected rule is *not* a cross-family rule. We must either restrict roles explicitly, or frame CRC as operating over agreement *count* irrespective of family. We currently favour the second framing, since family disjointness failed anyway.

**Reproducibility:** every CRC number was independently reproduced bit-for-bit on separate hardware from seed 0.

### 6.6 Translator failure-mode analysis

Findings from inspecting encodings rather than just scoring them.

**Self-contradictory encodings** (the satisfiability guard section, [Section 3](#3-how-the-system-works)):

| Dataset | t1 | t2 |
|---|---:|---:|
| SVAMP | 11.9% | 9.8% |
| GSM-Hard | 21.5% | 15.0% |

**Invented SMT-LIB commands.** GLM (t2) hallucinates commands that do not exist in the SMT-LIB standard — `set-value`, `set-precision`, `apply-arith`, `clear-assertions` — in **5.9%** of SVAMP outputs, versus **0.4%** for DeepSeek.

This is dangerous in a subtle way: **Z3 emits a warning and silently drops the unrecognised command.** The constraint just vanishes. A weaker constraint set is easier to satisfy, which can silently inflate coverage. We catch these explicitly.

**Parse-error rate under difficulty shift.** t2 parse errors rise from **8.4%** (SVAMP) to **23.4%** (GSM-Hard). The formal-language skill degrades sharply as problems get harder — which is a real limitation of the "cheap verifier" premise and we say so.

### 6.7 Banked results from P0 (superseded — do not cite in current form)

Kept here for transparency and audit trail.

| Result | Numbers | Status |
|---|---|---|
| GSM-Symbolic n≈200: AND-rule CW=0 at 14% coverage, vs. CW=8 (t1 alone), CW=2 (t2 alone). Rule-of-three 95% UB ≈10.7% | — | ⚠️ Used the **P0 prompt**, whose exact text was not recovered. Cannot share a table with p1-v1 results. Small-n; did not replicate at full scale. |
| GSM8K test n=1,319: 72.4% answered, 5.65% CW rate, 76 confident-wrong cases | — | ⚠️ **Internal inconsistency:** 72.4% × 5.65% implies ~54 cases, not 76. Must be re-derived from raw JSONL before any citation. |
| GSM-Hard: 97.9% verified accuracy at 24% coverage | — | ⚠️ **Prior architecture.** Superseded by the locked-pair full run. |

**Prompt provenance is an unresolved open item.** All P1 results use `prompt_version = p1-v1`. Results from unrecovered prompt versions cannot be pooled with them.

---

## 7. What Worked and What Did Not

A plain summary. No hedging.

### ✅ What worked

| Thing | Evidence |
|---|---|
| **Conformal Risk Control gives a real certificate** | GSM8K: CW ≤ 5% at 95% confidence, 55.5% coverage, 0/438 empirical violations over 500 splits |
| **The method knows when to give up** | GSM-Hard correctly abstains at every α rather than issuing a certificate it cannot support |
| **ρ predicts how much redundancy helps** | Monotone across three datasets: ρ = 0.248 → 0.411 → 0.580 as AND-rule benefit decays to nothing |
| **The satisfiability guard is load-bearing** | 11.9–21.5% of encodings are self-contradictory; without the guard these vacuously certify anything |
| **Judge-free settlement of the BoN question** | pass@8 upper-bounds any reranker, so no judge choice can overturn the conclusion |
| **The CW ceiling is a real, measurable limit** | Floors of 1.12% / 1.06% / 8.12% — no conformal method beats the rule family's own floor |
| **Full pipeline reproduces bit-for-bit** | All CRC numbers independently reproduced from seed 0 on separate hardware |

### ❌ What did not work

| Thing | What happened |
|---|---|
| **Family disjointness as the mechanism** | Same-family ρ came out **lower** than cross-family on both well-powered datasets. The pre-registered control contradicts the hypothesis. |
| **CW = 0 at scale** | 3 / 7 / 26 CW cases. The banked n≈200 and n=40 zeros were small-sample artefacts. |
| **≥10× CW reduction** | Got 1.96× / 1.56× / 1.01×. On GSM-Hard the second translator adds essentially nothing. |
| **The ≤0.15% pooled upper bound** | Unreachable. The k-of-4 floor is ~1.06% on GSM8K. The target was set before we knew the floor existed. |
| **The "decorrelation theorem"** | It is an algebraic **identity**, not a bound. See [Section 9](#9-known-problems-with-our-own-work). |
| **Prediction (ii)** | Unsupportable as written — the required SVAMP labels are not in the public release. |
| **First same-family control (t5)** | Wrong model variant. Chat model cannot emit SMT-LIB. Replaced with t6. |
| **Declarative prompting** | Forcing all-Z3 formalisations made translators produce buggier output and drop the `answer` naming convention. Reverted. **Do not re-add.** |
| **The learned router** | Removed. It made certificates unauditable, which defeats the point. |

### 🔄 What we now believe

The original story was: *"Different families → independent errors → multiplied safety."*

The evidence does not support that. The revised, honest story is:

> **ρ is an empirically measured predictor of confident-wrong risk, not a quantity we can bound in advance from architectural facts about the models.**

That is a weaker claim. It is also, as far as we can tell, a true one. And it still supports a useful system: measure ρ on calibration data, then use conformal risk control to pick an operating point that meets a stated risk level. The certificate does not depend on the failed mechanism.

---

## 8. Pre-Registered Predictions and Their Outcomes

We wrote three predictions down before running the shift datasets. Here is what happened to each.

### Prediction (i) — BoN lift over majority vote shrinks on SVAMP

**Status: ✅ CONFIRMED, and settled judge-free.**

We settled this without running a judge at all, using `pass@8` — which upper-bounds Best-of-n under *any* reranker.

| | SVAMP | GSM8K | GSM-Hard |
|---|---:|---:|---:|
| maj@8 | 93.6% | 92.6% | 64.0% |
| pass@8 | 96.6% | 96.1% | 71.7% |
| **Max possible BoN lift** | **+3.0 pp** | **+3.5 pp** | **+7.7 pp** |

Smallest headroom is on SVAMP. Prediction holds.

**Why this is stronger than an empirical BoN number:** because it is an upper bound, no judge choice can overturn it. This pre-empts the standard reviewer objection *"you picked a weak judge."* The Gemini BoN run would only measure the *realised* fraction of this headroom, so it is now **optional**, not blocking.

### Prediction (ii) — Single-translator CW concentrates in SVAMP's question-sensitivity category

**Status: ❌ UNSUPPORTABLE AS WRITTEN.**

`SVAMP.json` carries only a `Type` column: Addition, Subtraction, Multiplication, Common-Division. The *question-sensitivity / reasoning-ability / structural-invariance* variation labels are described in the NAACL 2021 paper but are **not a column in the public release**.

Three options, all acceptable:
1. Find a released mapping from the authors.
2. Hand-label the CW subset under a pre-registered protocol.
3. Drop the prediction with a stated reason.

We will state clearly which option we took. We will not quietly delete the prediction.

### Prediction (iii) — CW rises monotonically with measured ρ

**Status: ✅ CONFIRMED, monotone on three points.**

ρ(t1×t2) = 0.248 → 0.411 → 0.580 for SVAMP → GSM8K → GSM-Hard, with AND-rule benefit decaying to nothing as ρ approaches 0.58.

This is our cleanest surviving positive result about the mechanism.

---

## 9. Known Problems With Our Own Work

Every one of these is a thing a reviewer could attack. We list them so that we fix them rather than hope.

### 9.1 The "decorrelation theorem" is an identity, not a bound 🔴 **BLOCKING**

We wrote:

```
Pr[CW] ≤ ε₁ε₂ + ρ·√(ε₁(1−ε₁)·ε₂(1−ε₂))
```

For binary indicators, that right-hand side is **exactly** `Pr[both certify]`. It is the definition of covariance, rearranged. It is not an inequality that could fail; it is an identity that must hold.

We confirmed this empirically: `measured bound == observed joint` to **five decimal places on every dataset.**

So the sentence *"the bound held empirically"* is **vacuous**. It could not have done anything else.

The formula only has content in the other direction:

- **Option A:** Bound ρ *a priori* from something independently establishable, then derive a CW bound. (This is what family disjointness was supposed to provide — and it failed.)
- **Option B:** Build a finite-sample version where ρ̂ carries a confidence interval, so the resulting bound is genuinely probabilistic.

Given the failed control, we are taking Option B, and reframing ρ as an empirically measured predictor rather than an a-priori-bounded quantity.

**Also fixed:** the `bound_holds` field previously returned `False` when ρ was undefined. It now correctly returns `None`.

### 9.2 The adjudication protocol must be written before reading CW cases 🔴 **BLOCKING**

Benchmark label noise is the **same order of magnitude** as our target CW rate. So distinguishing "model error" from "wrong gold label" is not a detail — it decides the headline number.

**We have already contaminated part of this.** Three SVAMP CW cases were inspected before a protocol existed, and all three look like **label noise, not model error**:

- `svamp/0679`: 4 − 2 + 3 = 5; gold says 1
- `svamp/0896`: (28 + 14) packages × 6 = 252; gold says 7
- `svamp/0640`: question is incoherent

That inspection **must be declared post-hoc** in the paper.

The 7 GSM8K CW cases are **still unread and must stay unread** until the protocol is fixed and written down. This is a hard rule for this project.

### 9.3 The CRC rule is not actually cross-family ⚠️

k = 2-of-4 can be satisfied by t1 + t6, both DeepSeek. Either restrict roles explicitly, or reframe CRC as operating over agreement count irrespective of family. We favour reframing, since family disjointness failed anyway.

### 9.4 SVAMP's ρ estimates are under-powered ⚠️

SVAMP has 79 wrong answers, giving only 8–12 wrong-certification events per pair. Bootstrap confidence intervals **span zero on 5 of 6 pairs.**

**Consequence:** SVAMP point estimates must **not** be plotted as if they were as precise as the others. GSM-Hard (518 wrong answers) is the only well-powered dataset — all six of its intervals exclude zero. The CW-vs-ρ figure must be redone with visible confidence intervals.

### 9.5 Prompt provenance ⚠️

The banked GSM-Symbolic CW=0 result used the P0 prompt, whose exact text was not recovered. It **cannot share a table** with p1-v1 results. Prompt version is now recorded in every JSONL record.

### 9.6 The banked GSM8K numbers are internally inconsistent ⚠️

72.4% answered × 5.65% CW implies ~54 cases, not the 76 recorded. **Must be re-derived from raw JSONL before any citation anywhere.**

### 9.7 The same-family control is not capability-matched ⚠️

t6 is 6.7B dense; t1 is 15.7B MoE from a different coder generation. So the control varies capability *and* family at once. A cleaner control is future work, and the current conclusion is stated with that caveat attached.

### 9.8 The LoRA label-masking bug 🟡 **NON-BLOCKING for the workshop paper**

A label-masking bug produces flat-zero training loss. This gates all conditional teacher-distillation tracks (P4). The publishable pipeline is currently **zero-shot only**, which is fine for the workshop paper.

**Hard go/no-go date: 15 October 2026.** If unfixed by then, the distillation track is cut from the main paper rather than allowed to slip the schedule.

---

## 10. What We Are Building Next

### Immediate — blocking the workshop paper

All of these are CPU and writing work. **No GPU needed.**

| # | Task | Why it blocks |
|---|---|---|
| 1 | **Settle the central claim** | Four pages cannot carry three co-equal stories. Recommended order: **(a) CRC certificate + its ceiling, (b) AND-rule benefit degrading with ρ, (c) the failed family-disjointness control.** Decide before writing a single word. |
| 2 | **Fix the identity-theorem** | Currently a vacuous claim. Must become a finite-sample statement with ρ̂ confidence intervals. |
| 3 | **Write the adjudication protocol** | Must be written *before* the 7 GSM8K CW cases are read. The 3 SVAMP inspections must be declared post-hoc. |
| 4 | **Resolve prompt provenance** | Decide what is poolable with p1-v1 and what is not. |
| 5 | **Write related work** | Ganguly 2025, VeriCoT, PAL, PoT, SatLM, Logic-LM, LINC, DTV. |
| 6 | **Redo the CW-vs-ρ figure** | With bootstrap CIs. SVAMP intervals span zero on 5 of 6 pairs. |
| 7 | **Push the code** | Repo is currently README-only. All artefacts exist and are tested locally. |

**Explicitly not blocking:** the BoN-8 Gemini run (settled by pass@8), and GSM-Symbolic (does not fit the workshop timeline).

### P2 — Scale and cross-check

- GSM-Symbolic full scale: **12,500 problems** (main 5,000 + p1 5,000 + p2 2,500)
- CVC5 cross-check against Z3 — a second independent solver
- Proper CRC calibration on a genuine held-out calibration set
- **Hardness-conditioned ρ** using GSM-Symbolic's repeated-measures template structure (100 templates × instances)
- Cluster-aware bootstrap CIs throughout

### P3 — Theory and mechanism

- Finite-sample version of the risk statement with ρ̂ confidence intervals
- ρ measured across **≥4 translator family pairs** with a proper CW-vs-ρ monotone plot
- Capability-matched same-family control (addressing [9.7](#97-the-same-family-control-is-not-capability-matched-))
- Test the capability-similarity hypothesis directly

### P4 — Teacher distillation (conditional)

**Gated on the LoRA bug. Go/no-go 15 October 2026.**

- Track 1 teacher: DeepSeek V4 Pro
- Track 2 teacher: GLM-5.2 (routed via OpenRouter, not Z.ai direct)

**Design rule:** the two tracks must be **parallel, never merged**. A merged cascade gives both students identical kept-sets, which correlates their coverage gaps and raises ρ *at the data level before training even begins*. Merging would sabotage the exact quantity we are measuring.

### P5 — Weak-to-strong oversight

Swap the generator for **Gemini 3.1 Pro** and keep the small local translators as verifiers. This directly tests the scalable-oversight asymmetry: can weak verifiers constrain a strong generator?

If OpenAI Researcher Access credits come through (December review cycle), they fund **full-scale weak-to-strong generation only**.

**Hard constraint:** OpenAI models are **never** allowed into the certified path — not as generator, translator, or verifier. Oversight-generation role only.

### P6 — Full paper

- Related work in depth
- Residual error analysis on surviving CW cases
- Ablations across every design choice
- **Judge-robustness subsample** — ~300 problems, ~$5, on a second judge family, to pre-empt the "you picked a friendly judge" objection
- Full reproducibility infrastructure
- Two-line cost reporting (see [Section 14](#14-hardware-cost-and-compute-discipline))

---

## 11. Timeline and Milestones

### Phase status

| Phase | Window | Content | Status |
|---|---|---|---|
| **P0** | — | Infrastructure, banked pilot results | ✅ Complete |
| **P1** | 20 Jul – 15 Aug 2026 | Full runs: SVAMP, GSM8K, GSM-Hard; six translators; first ρ; CRC | ✅ **Complete 1 Aug 2026, ahead of schedule** |
| **P2** | Aug – Sep 2026 | GSM-Symbolic 12,500; CVC5 | ⬜ Next |
| **P3** | Aug – Sep 2026 | Theory fix, adjudication protocol, writing | 🔄 In progress |
| **P4** | Conditional | Teacher distillation | 🔴 Blocked on LoRA bug |
| **P5** | Q4 2026 | Weak-to-strong oversight | ⬜ Planned |
| **P6** | Q4 2026 – Q1 2027 | Full paper | ⬜ Planned |

### Publication targets

| Venue | Deadline | Content | Status |
|---|---|---|---|
| **MATH-AI @ NeurIPS 2026** | **25 September 2026 (AoE)** | 4-page workshop paper on SVAMP / GSM8K / GSM-Hard | 🎯 Primary near-term target |
| arXiv v1 | Early October 2026 | Citable public version regardless of venue outcome | ⬜ Planned |
| **ICML 2027** | ~22 January 2027 | Full main-track paper | 🎯 Primary target |
| NeurIPS 2027 | ~mid-May 2027 | Fallback | ⬜ Contingency |

**MATH-AI 2026 details (verified 5 August 2026):**
Submission 25 Sep 2026 AoE · Notification 19 Oct · Camera-ready 29 Oct · Held in **Atlanta** as a NeurIPS satellite (main NeurIPS is 6–12 Dec in Sydney).

An earlier internal estimate put this deadline in **late August**, inferred backwards from the generic NeurIPS mandatory-notification date of 29 September. MATH-AI evidently has an exemption. **This gives roughly 8 weeks from early August, not 4.** We will re-check the site periodically in case the date is forced back.

**Results freeze for the full paper: 10 December 2026.**

---

## 12. Repository Layout

Planned structure. All artefacts below are **built and tested locally**; they are being cleaned and pushed.

```
.
├── README.md                          ← you are here
│
├── stage1/                            GPU generation — expensive, checkpointed
│   ├── stage1_generation.ipynb        generator + gen_k8 + t1/t2
│   ├── stage1b_extra_translators.ipynb  t3/t4 multi-role worker
│   └── stage1c_control_translators.ipynb t5/t6 same-family control
│
├── stage2/                            CPU verification & metrics — cheap, rerunnable
│   ├── stage2_lib.py                  Z3 dual-semantics verify, sat guard,
│   │                                  Wilson / rule-of-three, ρ, majority vote
│   ├── crc.py                         conformal risk control + audit
│   └── stage2_verification_and_crc.ipynb  14 verifier self-tests, ρ bootstrap CIs
│
├── judge/
│   └── bon8_judge.ipynb               Gemini BoN-8 (optional; see Prediction (i))
│
├── prompts/
│   └── p1-v1/                         exact prompt text, versioned
│
├── data/
│   └── regenerate/                    regeneration scripts (NOT derived JSONL —
│                                      GSM-Symbolic licence forbids redistribution)
│
├── results/
│   ├── raw/                           raw_*.jsonl checkpoints (Stage 1 output)
│   └── tables/                        computed metrics (Stage 2 output)
│
├── paper/
│   └── workshop/                      LaTeX skeleton, all four tables populated
│
└── docs/
    ├── adjudication_protocol.md       ⬜ TO BE WRITTEN BEFORE READING CW CASES
    └── infrastructure_notes.md        the hard-won operational lessons
```

### Artefacts already built and tested

| Artefact | What it does |
|---|---|
| **Stage 1 generation notebook** | Adaptive `gpu_util` derived from measured free VRAM; disk + VRAM preflight checks; HF prefetch cell; checkpoint restore from tarball; heartbeat runner with phase detection and live MB/s |
| **Stage 1b/1c notebooks** | Multi-role worker for extra translators. Includes a chat-template fallback for models like Mistral whose template *rejects* a system role — system text is folded into the first user turn |
| **`stage2_lib.py`** | Dual-semantics Z3 verification, satisfiability guard, Wilson and rule-of-three bounds, ρ estimation, majority vote. *(Note: the `FINAL:` regex needed an exponent group, or `FINAL: 1.5e10` silently parses as `1.5`.)* |
| **`crc.py` + combined notebook** | 14 verifier self-tests, ρ bootstrap CIs, CRC with an audit pass that flags anticonservative α |
| **`bon8_judge.ipynb`** | Only **1,247 of 3,638** problems need a judge call — when all 8 samples agree, BoN = maj@8 *exactly*, so skipping is not an approximation. Cost gate after a 50-problem smoke test. Per-problem seeded shuffle to measure position bias. |
| **LaTeX workshop skeleton** | All four tables populated with real numbers |

---

## 13. How to Reproduce Everything

### The two-stage design

This is the single most important operational idea in the project.

```
STAGE 1 (GPU, expensive, slow)          STAGE 2 (CPU, cheap, fast)
──────────────────────────────          ──────────────────────────
Load model → generate →                 Read JSONL → run Z3 →
write raw_*.jsonl checkpoint     ───▶   compute metrics → tables
```

**Checkpoint invalidation rule:**

> Delete a model's `raw_*.jsonl` **only** when its *producer* changes — that means the generation prompt, the sampling settings, or the model load config.
>
> **Verifier changes and metric changes are free.** They only require re-running Stage 2.

This rule is why we can iterate on verification logic dozens of times a day without touching a GPU. It is worth adopting in any project of this shape.

### Steps

```bash
# 1. Environment
pip install -r requirements.txt
export HF_TOKEN=hf_...        # NOT optional — see Section 15

# 2. Stage 1 — GPU. Run once per (model, dataset, prompt_version).
#    Writes raw_*.jsonl checkpoints. Restartable from tarball.
jupyter nbconvert --execute stage1/stage1_generation.ipynb

# 3. Stage 2 — CPU. Rerun freely.
python stage2/stage2_lib.py --input results/raw/ --output results/tables/
python stage2/crc.py --dataset gsm8k --alpha 0.05 --delta 0.05 --splits 500
```

### Verifying our numbers

- **Seed 0** reproduces every CRC number **bit-for-bit**. This has already been independently confirmed on separate hardware.
- The Stage 2 notebook runs **14 verifier self-tests** before computing anything. If a self-test fails, no numbers are produced.
- The CRC audit pass **flags anticonservative α** rather than silently reporting it.

---

## 14. Hardware, Cost, and Compute Discipline

This project runs on a personal budget. Every design choice reflects that.

### Compute

| Item | Detail |
|---|---|
| Primary GPU | **Vast.ai A100 40GB PCIe**, ~$0.40–0.475/hr, ≥99% reliability, ≥562GB disk |
| Smoke tests | Kaggle T4 |
| Inference engine | **vLLM** (production); HuggingFace transformers + bitsandbytes 4-bit (fallback) |
| **RTX 4090 24GB** | ❌ **Infeasible** for DeepSeek-Coder-V2-Lite: needs ~31.4GB vs. ~22.5GB usable |

### Budget

| Line | Amount |
|---|---:|
| GPU — all Stage-1 passes + contingency + conditional fine-tuning | **$16–27** |
| Gemini 3.1 Pro (Batch API, $2.00 / $12.00 per M input/output tokens — halved via Batch) | ~$96 |
| Gemini with contingency and forex | ~$150 |
| Judge-robustness subsample (~300 problems) | ~$5 |
| **Total project budget** | **$160–355** (hard ceiling $400) |

**Cost gate:** run **50 problems first** to measure actual thinking-token consumption before committing to any full judging run.

### Storage discipline

> Keep **only JSONL checkpoints (~5GB)** on persistent volumes. **Re-pull model weights every session.**

Model weights are tens of gigabytes and free to re-download. Storing them on a persistent volume can cost more than the GPU time itself. This one rule saved a meaningful fraction of the budget.

### Cost reporting in the paper

We will always report **two separate lines**, never one blended figure:

- **Line A** — the cheap certified pipeline (what we are proposing)
- **Line B** — the expensive baselines we are comparing against

Blending them would hide the entire economic argument of the paper.

---

## 15. Engineering Lessons

A full working day was lost to the issues below on 31 July 2026. They are written down so nobody — including us — loses that day again.

### Infrastructure

**1. `HF_TOKEN` is not optional, and the failure mode is silent.**
Unauthenticated Hugging Face Hub downloads are throttled, and the throttling produces **no error message**. vLLM prints `Loading model from scratch...` and then nothing for 45+ minutes. It is indistinguishable from a hang. Always set the token.

**2. Vast.ai GPUs can be shared, and you cannot see the other tenant.**
If `nvidia-smi` shows memory in use but an **empty process list**, another container holds that memory. It is invisible from your namespace and you cannot kill it.

> **Always check `nvidia-smi --query-gpu=memory.used` reads ~0 MiB *before* running `pip`.**

DeepSeek-Coder-V2-Lite needs 29.4 GiB of weights, so a 40GB card must be genuinely empty. A 48GB+ card removes the constraint entirely.

**3. Filter Vast.ai offers on four things.**
- CUDA ≥ 13 (torch 2.12+cu130 will not run on a CUDA 12.x driver)
- Disk ≥ 120GB set on the **rent slider** — the host's advertised free-disk figure is *not* your allocation
- Network ≥ 1000 Mbps
- Genuinely empty GPU (see above)

**4. vLLM 0.26 removed `swap_space`.**
Build engine kwargs dynamically and filter them against `EngineArgs` fields, rather than pinning a version. Pinning just moves the breakage.

**5. Set `enforce_eager=True`.**
Skips a 3–8 minute silent `torch.compile` / CUDA-graph phase that looks exactly like a hang.

**6. Derive `gpu_util` from measured free VRAM.**
Never hardcode it. The value that works on an empty card fails on a shared one.

**7. Do not launch vLLM from a `!command` cell.**
Interrupting one orphans vLLM's EngineCore child process, which then holds VRAM forever. Launch via `subprocess` with `preexec_fn=os.setsid`, and kill the whole process group.

**8. Cache growth is the only reliable download-progress signal.**
Use `du -sb`, not `du -sh` — you need byte-level resolution to see movement. **GPU memory jumps to the full model size within seconds**, because vLLM preallocates weight tensors and streams shards into them. That jump does **not** mean the download finished.

### Modelling

**9. Chat variants cannot do formal languages.**
t5 (DeepSeek-V2-Lite-Chat) never wrote the word `answer` in 443 of 462 failures. Use coder/instruct variants for structured-output roles. Check this with n=40 before committing to a full run.

**10. Some chat templates reject a system role.**
Mistral's does. Fold the system text into the first user turn as a fallback.

**11. Regex needs exponent groups.**
`FINAL: 1.5e10` silently parsed as `1.5`. Silent parse bugs are the worst kind, because the pipeline keeps running and produces numbers that look fine.

**12. Do not force declarative prompting.**
Forcing all-Z3 formalisations made translators produce buggier output and drop the `answer` naming convention. Reverted. **Do not re-add.**

---

## 16. Statistical Rules We Follow

Fixed rules, applied without exception. Written down so they cannot be quietly relaxed when a number is inconvenient.

| Rule | Reason |
|---|---|
| **Rule-of-three upper bounds are mandatory** when the numerator is zero | Zero out of 268 is **1.12%**, not 0.00%. Reporting 0% from a small denominator is the most common way to overclaim in selective prediction. |
| **Wilson confidence intervals** on every operating point | Normal approximations break at the extreme rates we work with. |
| **Cluster-aware bootstrap CIs** required for GSM-Symbolic | 100 templates × instances. Treating instances as independent inflates effective n and understates uncertainty. |
| **Conformal guarantees claimed only on GSM8K test** | Exchangeability holds there. On shift datasets we report bootstrap CIs and nothing stronger. |
| **Full dataset runs are mandatory, not optional** | Our own n≈200 CW=0 result did not survive n=1,319. That is the whole argument. |
| **Pre-register predictions before running shift datasets** | Prevents post-hoc storytelling. It also means we have to report when predictions fail — see [Section 8](#8-pre-registered-predictions-and-their-outcomes). |
| **Benchmark label noise is the same order as the target CW rate** | A hand-adjudication protocol is required before certified-and-scored-wrong items are inspected. |
| **Smoke test at n=40–200 before every full run** | Catches format failures cheaply. But smoke-test *results* are never reported as findings. |
| **Frontier APIs are assigned to roles, not to datasets** | The frozen evaluation pipeline runs identically across all datasets as local GPU jobs. Varying pipeline components per dataset confounds the distribution-shift axis and invalidates pooled denominators. |

---

## 17. Related Work

Work that must be engaged with explicitly in the paper.

| Work | Relation to this project |
|---|---|
| **Ganguly et al., "Grammars of Formal Uncertainty" (NeurIPS 2025)** | Closest prior work on uncertainty in formal translation of LLM output. Must be positioned against directly. |
| **Feng et al., VeriCoT** | Verification of chain-of-thought reasoning. |
| **PAL** (Program-Aided Language models) | Executes generated programs instead of verifying constraints. Complementary, not competing. |
| **PoT** (Program of Thoughts) | Same family as PAL. |
| **SatLM** | Satisfiability-aided language modelling — closest in machinery, different in goal (they solve; we *verify and abstain*). |
| **Logic-LM** | LLM + symbolic solver pipeline. |
| **LINC** | Neurosymbolic logical inference via translation to first-order logic. |
| **DTV** | Deductive verification of chain-of-thought. |

**Our position in one sentence:** most of this literature uses formal tools to make models *more accurate*; we use them to make models *know when to shut up*, and we attach a distribution-free certificate to that decision.

---

## 18. Datasets and Licences

| Dataset | Licence | Redistribution |
|---|---|---|
| SVAMP | MIT | Free |
| GSM8K | Standard research use | Free |
| GSM-Hard | Standard research use | Free |
| **GSM-Symbolic** | **CC-BY-NC-ND-4.0** | ⚠️ **No derivative JSONL redistribution.** We ship **regeneration scripts** only. |

The no-derivatives clause on GSM-Symbolic is why `data/regenerate/` contains scripts rather than data. Anyone reproducing our work regenerates the derived files locally.

Code in this repository is released under **MIT**.

---

## 19. Citation

```bibtex
@misc{certified-selective-reasoning-2026,
  title  = {Certified Selective Reasoning: Decorrelated Neuro-Symbolic
            Verification with Distribution-Free Safety Guarantees},
  author = {Abhishek},
  year   = {2026},
  note   = {Independent research. Work in progress.},
  url    = {https://github.com/<user>/Decorrelated-Neuro-Symbolic-Verification-with-Distribution-Free-Safety-Guarantees}
}
```

---

## 20. Contact

**Abhishek** — Independent Researcher
AI Safety · Scalable Oversight · Formal Verification of LLM Reasoning

Previously: M.Tech, Delhi Technological University (2023); Assistant Professor, KIET Group of Institutions, Ghaziabad (~2 years).
Currently conducting self-directed AI safety research, full-time.

I am happy to discuss any part of this work — especially the parts that did not work. If you think the capability-similarity hypothesis in [Section 6.4](#64-same-family-control--the-result-that-contradicts-us) is wrong, or you can see a way to make the ρ bound non-vacuous, I would very much like to hear it.

---

<p align="center">
<i>Everything in this README is reported as measured. Where a result did not replicate, we say so.<br>
Where our own hypothesis failed, we say so first.</i>
</p>
