# Certified Selective Reasoning

**Can a maths answer from a language model be *checked* well enough that we can put a real number on how often it is still wrong?**

This repo holds the code, data-processing scripts and results for a small solo research project on that question.

Short version of what we found: **the idea we started with did not work.** We say so openly below, and we show what *is* true instead.

---


## Table of contents

1. [What this project is, in plain words](#1-what-this-project-is-in-plain-words)
2. [Words you need to know](#2-words-you-need-to-know)
3. [How the system works, step by step](#3-how-the-system-works-step-by-step)
4. [What we said would happen, before we ran it](#4-what-we-said-would-happen-before-we-ran-it)
5. [What actually happened](#5-what-actually-happened)
6. [The things that *did* work](#6-the-things-that-did-work)
7. [The guarantee, and where it breaks](#7-the-guarantee-and-where-it-breaks)
8. [The baseline we had to add](#8-the-baseline-we-had-to-add)
9. [Setup: models, data, solver](#9-setup-models-data-solver)
10. [What it cost](#10-what-it-cost)
11. [Repo layout](#11-repo-layout)
12. [How to reproduce](#12-how-to-reproduce)
13. [Things that are still missing](#13-things-that-are-still-missing)
14. [Traps we fell into, so you don't have to](#14-traps-we-fell-into-so-you-dont-have-to)
15. [How we tried to keep this honest](#15-how-we-tried-to-keep-this-honest)
16. [Citing / contact / licence](#16-citing--contact--licence)

---

## 1. What this project is, in plain words

A language model answers a maths word problem. Sometimes it is right. Sometimes it is wrong. The hard part is that **it sounds equally confident either way**. That is the real problem. A wrong answer that admits it is unsure is annoying. A wrong answer that sounds sure is dangerous.

So we do not try to make the model *better*. We leave the answering model completely **frozen** — we never train it, never tune it, never change its prompt.

Instead we bolt a **checker** onto the outside.

The checker works like this:

1. Take the same word problem.
2. Give it to some **other** models, whose only job is to rewrite the problem as **equations** — not to solve it.
3. Hand those equations to **Z3**, a program that does exact maths logic. Z3 is not a language model. It does not guess. It either proves something or it does not.
4. Ask Z3: *given these equations, is the first model's answer forced to be true?*
5. If Z3 says yes → we mark the answer **certified**.
6. If Z3 says no, or the equations are broken → we **abstain**. The system says "I don't know" instead of answering.

Then, on top of that, we add a statistical layer (**conformal risk control**) that turns the whole thing into a sentence like:

> *"Among the answers this system marks as certified, no more than 5% are wrong — and we are 95% confident of that."*

That is what "distribution-free guarantee" means here. It is a promise about the error rate that does not depend on assuming the data looks a particular way.

**Why anyone should care:** the checker models are small and cheap. The model being checked can be big and expensive. That is the interesting direction — cheap trusted verification of expensive untrusted models.

---

## 2. Words you need to know

Read this once and the rest of the README will make sense.

| Word | Plain meaning |
|---|---|
| **Generator** | The model that answers the maths question. Frozen, never trained by us. |
| **Translator** | A separate model whose only job is to turn the question into equations. It never sees the generator's answer. |
| **SMT-LIB** | A plain-text format for writing down equations and constraints. Like a tiny programming language for maths facts. |
| **Z3** | A solver. You give it equations, it proves things about them. No guessing involved. |
| **Certify** | Z3 proved the generator's answer must follow from the equations. |
| **Abstain** | The system refuses to answer. This is a *good* outcome when it is unsure. |
| **Coverage** | How often the system answers instead of abstaining. Higher = more useful. |
| **CW (certified-wrong)** | The system said "certified" but the answer was actually wrong. **This is the number that matters.** Low = safe. |
| **ρ (rho)** | Correlation. How often two translators make the *same* mistake at the *same* time. High ρ = they fail together, so their agreement means little. |
| **k-of-4 rule** | We have 4 usable translators. "k=2" means at least 2 must certify before we accept the answer. Higher k = stricter = safer but answers less often. |
| **CRC** | Conformal risk control. The statistics that turn measurements into a guarantee. |
| **ε (epsilon)** | Of the generator's *own* mistakes, what share sneak past the checker. |
| **Satisfiability guard** | A safety check that throws away equations that contradict themselves. See §6.2 — it turned out to matter a lot. |
| **Pre-registration** | Writing down what you expect to find, with a date, **before** you look at the data. So you cannot fool yourself later. |

---

## 3. How the system works, step by step

```
                  maths word problem
                          |
        +-----------------+------------------+
        |                                    |
        v                                    v
   GENERATOR                          TRANSLATORS (t1, t2, t3, t6)
   (frozen)                           each writes SMT-LIB equations
        |                             from the QUESTION ONLY
        v                                    |
   candidate answer  g                       v
        |                              +-----------+
        |                              | Z3 solver |
        |                              +-----------+
        |                                    |
        |          step 1: are the equations even consistent?
        |                  if NO  -> throw them away (guard)
        |                  if YES -> continue
        |                                    |
        +----------------> step 2: is  equations AND (answer != g)  impossible?
                                   if impossible -> this translator CERTIFIES g
                                             |
                                             v
                              count how many translators certified
                                             |
                          at least k of them?  --- no ---> ABSTAIN
                                     |
                                    yes
                                     v
                              output g, marked CERTIFIED
                                     |
                                     v
                    CRC turns the observed rate into a guarantee
```

**One design choice makes this cheap, and it is worth calling out.** The translators only ever see the *question*. They never see any candidate answer. That means their equations are **generator-independent** — write them once, then re-check them against any generator's answers later, on a normal CPU, for free. This is why we could test three different generators without regenerating anything.

---

## 4. What we said would happen, before we ran it

We wrote three predictions down, with dates, before running the main experiments.

| # | Prediction | Result |
|---|---|---|
| (i) | Best-of-8 with a judge will lift accuracy more on harder datasets | ✅ **Confirmed** |
| (ii) | *(a prediction about SVAMP variation categories)* | ⚪ **Retired** — the labels are not in the public data release, so it was untestable. Retired before we looked at any results. |
| (iii) | Certified-wrong rate will rise as translator correlation (ρ) rises | ✅ **Confirmed**, and monotone |

And one **mechanism**, which was the actual point of the project:

> *Translators from different model families make different mistakes. So if two translators from different families both certify an answer, that agreement is strong evidence. Same-family translators would fail together and their agreement would be worth much less.*

That mechanism is the reason the word "decorrelated" is in the title.

**It is wrong.** See the next section.

---

## 5. What actually happened

### 5.1 The main idea failed

We built a **control**: a pair of translators from the *same* family (t1 and t6, both DeepSeek), to compare against a *cross*-family pair (t1 and t2, DeepSeek and GLM). If the mechanism were real, the same-family pair should be **much more** correlated.

Measured ρ (higher = they fail together more):

| Dataset | Same family (t1×t6) | Cross family (t1×t2) | Which is lower? |
|---|---|---|---|
| GSM8K (1,319 problems) | **0.187** | 0.411 | Same-family — **backwards** |
| GSM-Hard (1,319 problems) | **0.372** | 0.580 | Same-family — **backwards** |
| SVAMP (1,000 problems) | 0.276 | **0.248** | Cross-family — but see note |

On both datasets with enough wrong-certification events to say anything, the **same-family pair is the *less* correlated one**. That is the opposite of the prediction. On GSM-Hard the same-family pair is the least correlated of all six pairs tested.

SVAMP points the other way, but SVAMP is easy — there are very few errors to correlate — so it carries little weight. All the confidence intervals overlap. We report all three anyway.

**Conclusion: picking translators from different companies does not buy you independence.** Family disjointness is not the mechanism.

A hypothesis we offer but do **not** claim as a finding: ρ may track *capability similarity* rather than family. The highest-ρ pairs are also the highest-coverage translators. Caveat: t6 is a 6.7B dense model, t1 is a 15.7B mixture-of-experts model from a different generation, so this is a same-family control but **not** a capability-matched one.

### 5.2 The "theorem" was empty

The paper draft had this line:

```
ε₁ε₂ + ρ·√(ε₁(1−ε₁)·ε₂(1−ε₂))  =  Pr[both certify]
```

We originally called it a bound and showed it "holds empirically". It does hold — to five decimal places, on every dataset.

That is because **it is an algebraic identity**, not a bound. For binary yes/no indicators, that expression is literally the definition of covariance rearranged. It cannot fail. Showing it holds proves nothing.

We removed the claim. The honest version is: **ρ is a quantity we *measure*, and it *predicts* the certified-wrong rate.** It is not something guaranteed in advance by choosing different model families.

### 5.3 The headline number did not survive scale

An early run on ~200 problems gave "0 certified-wrong at 14% coverage". At the full 5,000 problems it became **28.0% coverage with 29 certified-wrong cases**. The clean result was a small-sample artefact. Reported as such.

### 5.4 The "10× better" target was never hit

We set ourselves a target: at least a 10× reduction in certified-wrong rate, at no more than 40% coverage loss. Measured reduction versus a single translator:

| Dataset | Reduction | Coverage lost |
|---|---|---|
| SVAMP | 1.96× | 43.8% |
| GSM8K | 1.56× | 58.1% |
| GSM-Hard | 1.01× | 83.8% |
| GSM-Symbolic main | 1.01× | — |
| GSM-Symbolic p1 | 13.84× | — |
| GSM-Symbolic p2 | ∞ (zero CW) | — |

So a 10× reduction **is** reachable — but only on hard data, and never inside the coverage budget we set. **0 of 6 datasets met the criterion.**

And the confirmed prediction (iii) *explains* the failure: on `main`, ρ is 0.68. When the two translators fail together that often, requiring both to agree buys you almost nothing. The successful prediction predicts the failure of the objective. That is a satisfying thing to be able to say about a negative result.

---

## 6. The things that *did* work

Four results survive, and honestly they are more interesting than the thing we set out to prove.

### 6.1 A better generator does **not** lower the certified-error rate

We ran three generators of very different strength through the exact same verification pipeline: Qwen2.5-7B, Gemini 3.1 Flash-Lite, Gemini 3.1 Pro.

Accuracy across an 11.5-point range. Certified-wrong rate on `main`:

| Generator | Accuracy | CW rate | Coverage |
|---|---|---|---|
| Qwen2.5-7B | 87.2% | 2.07% | 28.0% |
| Gemini 3.1 Flash-Lite | 94.8% | 2.02% | 28.7% |
| Gemini 3.1 Pro | 98.7% | 1.99% | 29.1% |

**Flat.** Every confidence interval overlaps, on all six datasets. This is a real measurement, not an absence of one — GSM-Hard alone carries 26/29/34 certified-wrong events at 20–25% coverage.

There is a bonus control hiding in GSM-Hard: Flash-Lite scores 76.2% and Pro scores 76.3% there — **equal ability, different architecture, 30× different price** — and they still produce the same certified-error rate. That separates "a different model" from "a better model" more cleanly than the capability ladder does.

**But you must report a second number alongside it.** ε — the share of the generator's *own* errors that survive certification — climbs steadily:

```
main, AND t1×t2:    4.5%  →  11.2%  →  44.6%
main, t1 alone:     8.1%  →  18.1%  →  58.5%
```

The rate is flat but the *composition* changes completely. **Always report the rate and ε together.** The rate alone hides this.

### 6.2 The satisfiability guard is load-bearing

Verification asks two questions, **in this order**:

1. Are these equations even consistent with themselves?
2. Do they force the generator's answer?

Skip step 1 and the whole thing collapses, because **a set of self-contradictory equations implies everything.** A broken translation will happily "prove" any answer you hand it.

How often does that happen? Often:

| Translator | Self-contradictory encodings |
|---|---|
| t1 (DeepSeek-Coder-V2-Lite) | 18.9% |
| t6 (deepseek-coder-6.7b) | 14.2% |
| t2 (GLM-4-9B) | 11.4% |
| t3 (Qwen2.5-Coder-7B) | 4.2% |

*(4–19% across translators; on GSM-Hard t1 hits 21.5%.)*

Turn the guard off and certified-wrong gets **4.8× worse** — 0.35% → 1.69% on `main` at k≥2.

We pulled the unsat cores to find out *why*. The pattern is consistent and interesting: **the translator writes a correct chain of constraints, and then also hardcodes its own wrong mental arithmetic.** For example:

```
boxes = 7
per_box = 6
total = boxes * per_box     ; correct
total = 48                  ; wrong — it did the multiplication in its head
```

Both lines are asserted, they contradict, and the encoding is now poison.

**We deliberately did not patch the prompt to suppress this.** It is a genuine failure mode of LLM-to-formal translation and it is worth measuring, not hiding.

### 6.3 The error floor is caused by **broken benchmarks**, not broken verification

This is the finding that reframed the project.

On GSM-Symbolic `main`, almost every certified-wrong case comes from **one single template** — template 76.

Here is the template, roughly:

> *"X caught **4** trouts. The **first** weighs 70kg, the **second** weighs 33kg, and the **last** weighs 32kg…"*

Four fish. Three weights. The third weight is never given. And the official answer **double-counts the last weight**:

| Instance | Sum of stated weights | Official answer | Difference |
|---|---|---|---|
| A | 70+33+32 = 135 | 167 | 32 (= last weight) |
| B | 47+55+24 = 126 | 150 | 24 (= last weight) |
| C | 63+54+23 = 140 | 163 | 23 (= last weight) |

Two independent language models *and* an independently produced SMT encoding all read the problem the same way. The benchmark is the thing that is wrong.

**Impact:** exclude template 76 and the certified-wrong rate on `main` drops from **2.07% to about 0.15%**, and unanimous 4-translator agreement certifies **zero wrong answers over 615 gated problems**.

> ℹ️ One number is being re-verified from the raw logs: our records carry both "27 of 29" and "all 29 of 29" AND-rule CW cases attributed to template 76. The exact figure will be pinned down before publication. Either way the conclusion is unchanged.

And a distinction that matters:

- **Defect** (template 76): the benchmark is simply *wrong*. That is a bug to report upstream.
- **Ambiguity** (templates 32 and 33 on `p2`): the English genuinely supports two readings. *"Brokerage fee 7% **of the selling price**, transfer fee 12% **of the selling price**, 20% discount **on the selling price**"* — apply the fees before the discount and you get $85,000; apply them after and you get $66,000. The official answer uses the second; both models use the first. **Both readings are defensible.** These two templates account for 99 of 122 errors on `p2`.

A defect is a bug. An ambiguity is a limit of using LLM-generated benchmarks as ground truth. They are not the same thing and the paper treats them separately.

This also explains §6.1 cleanly: **as a generator gets better, its remaining mistakes concentrate on benchmark defects** — and defects are clean, simple arithmetic that translators encode perfectly. So the checker faithfully certifies them. The floor is not a verification failure; it is a data failure.

### 6.4 ρ predicts certified-wrong, monotonically

The one prediction that survived, and it holds cleanly:

```
ρ(t1×t2):   0.248  →  0.411  →  0.580
             SVAMP     GSM8K     GSM-Hard
CW rate:     0.69%  →  1.84%  →  9.92%
```

As the two translators start failing together more, requiring both to agree stops helping. The benefit of the AND rule decays to nothing by ρ ≈ 0.58.

So ρ is a genuinely useful **measured diagnostic**. It just is not something you get for free by picking different companies' models.

---

## 7. The guarantee, and where it breaks

### 7.1 The certificates we earned

A fixed "both must agree" rule has nothing to tune, so there is nothing to calibrate. With four usable translators the rule becomes **k-of-4**, which is discrete, nested (we checked this, we did not assume it) and monotone — exactly what conformal risk control needs.

Procedure: split into calibration and test → compute a one-sided Wilson upper bound on the calibration certified-wrong rate at each k → pick the smallest k (highest coverage) whose bound is under α → apply a Bonferroni correction because k was chosen adaptively.

| Dataset | Certificate | k | Coverage | Violations |
|---|---|---|---|---|
| GSM8K | CW ≤ **5%** at 95% confidence | 2 | 55.5% | 0 / 438 over 500 splits |
| SVAMP | CW ≤ **3%** at 95% confidence | 3 | 59.2% | 0% |
| GSM-Hard | **abstains at every α** | — | — | — (correct behaviour) |
| GSM-Symbolic p2 | **abstains at every α** | — | — | — (correct behaviour) |

The abstentions are not failures. They are the system correctly declining to promise something it cannot deliver.

### 7.2 The floors — arguably more interesting than the bounds

Every rule family has a **floor**: an error rate it cannot get below, no matter how strict you make it. No conformal method can certify below the floor of its own rule family.

| Dataset | CW floor |
|---|---|
| SVAMP | 1.12% |
| GSM8K | 1.06% |
| GSM-Hard | 8.12% |
| GSM-Symbolic p2 | covers 1 problem in 2,500 |

Note SVAMP's floor is **1.12%, not 0.00%**, even though we observed 0 errors out of 268. When you see zero events you cannot claim a zero rate — you use the rule of three to get an honest upper bound.

⚠️ **And the rule of three must be applied to gated *templates*, not gated *rows*.** On identical data that difference gives 0.15% versus 7.50% — a **50× error**. Rows inside one template are not independent samples.

### 7.3 Where CRC breaks — a second negative result

Conformal risk control is formally correct. It still fails in practice here, and it fails **two different ways** on two different splits. This is worth publishing on its own.

**(A) `main` — concentration failure.**
At α=3%, 97 of 200 grouped trials select a threshold and 30.9% of them violate the bound. At α=2%, 94 select and **100% violate**.

The cause: 35 of the 41 certified-wrong cases (85%) live in **one template**. When template 76 lands in the calibration half, calibration reads 2.70% and the procedure correctly abstains. When it lands in the test half, calibration reads 0.21%, the bound passes, k=2 is selected — and every single error is sitting on the other side waiting.

A 50/50 template split simply cannot sample a defect that lives in one cluster.

**(B) `p1` — boundary-selection failure.**
Different mechanism entirely. At α=5%, 198 of 200 trials select and 16.7% violate. But the violations all come from the 33 trials that chose **k=1**. Over 400 splits:

| Threshold | Median test CW | p90 | Max | Exceeds 5% |
|---|---|---|---|---|
| k=1 | 3.74% | 5.87% | 8.70% | on 23.5% of splits |
| k=2 | 0.99% | — | 2.44% | never |

k=1 sits right on the α boundary. Calibration measures it just under; test comes in just over.

**(C) Tightening α looks safer but is not — it is survivorship.**
On `p1`, violations drop 16.7% → 6.8% → 4.3% as α tightens. That looks like the procedure getting safer. It is not. Selections drop 198 → 117 → 46 over the same range. **The denominator changed.** The splits that still select are the clean ones. We state this explicitly, because a reader will otherwise read α=2% as safe.

**(D) Within-template certificates are unaffected** — 0% violations at α=10% and α=5% on `main` — because a random row split puts template-76 instances on both sides. The gap between the two kinds of certificate is now a measured quantity: it is exactly how much template memorisation is going on.

---

## 8. The baseline we had to add

Our original baselines (majority vote at 8, best-of-8 with a judge, generator-as-own-judge) were all **accuracy** baselines — they answer *"which answer should I give?"*

But this system competes on a different axis: *"when should I refuse to answer?"* That is **selective prediction**. We had no baseline on that axis at all. Without one, the whole paper is refutable in one sentence: *"why not just sample eight times and see if they agree?"*

So we built it. It is free — it reuses sampling data we already had. Gate the same answer on *"at least m of 8 samples agree with it"* and compare at matched coverage.

The result is not flattering, and we report it:

| Dataset | Best SMT rule | Self-consistency 8/8 | Winner |
|---|---|---|---|
| `main` (gen acc 87.2%) | k≥2: 56.0% cov, 1.46% CW | **68.7% cov, 1.28% CW** | **SC dominates every SMT rule** |
| `p1` (gen acc 76.1%) | **k≥3: 17.0% cov, 0.00% CW** | bottoms out at 1.76%, never reaches 0 | **SMT** |
| `p2` (gen acc 61.1%) | k≥2: 8.0% cov, 1.99% CW | 20.1% cov, 5.96% CW | mixed |

On `main`, **self-consistency simply beats us** — more coverage *and* lower error. We say so.

But two things save the story:

1. **On hard problems, only the symbolic route reaches zero.** Sampling agreement bottoms out at 1.76% on `p1` and never gets to zero. SMT gets to 0.00%.
2. **The combination beats either alone.** On `p1`, "SMT k≥2 **and** SC 7/8" gives 30.9% coverage at 0.45% CW — versus SMT alone at 35.5%/0.96% and SC alone at 51.1%/1.76%.

**The honest reframing:** sampling agreement is enough when the generator is already accurate. Symbolic verification is what reaches zero certified-wrong on hard problems where sampling agreement cannot. The two signals are **complementary**, not competing.

---

## 9. Setup: models, data, solver

### Generators (the model being checked)

| Role | Model | Notes |
|---|---|---|
| Base | Qwen2.5-7B-Instruct | Frozen, greedy decoding. Never trained. |
| Middle | Gemini 3.1 Flash-Lite | `thinking_level=minimal`. $0.0004 per call. |
| Top | Gemini 3.1 Pro | `thinking_level=high`. $0.012–0.023 per call. Also used as the best-of-8 judge. |

### Translators (the models writing equations)

| ID | Model | Family | Status |
|---|---|---|---|
| t1 | DeepSeek-Coder-V2-Lite-Instruct | DeepSeek | ✅ primary |
| t2 | GLM-4-9B-0414 (`zai-org`, **not** THUDM) | Zhipu | ✅ primary |
| t3 | Qwen2.5-Coder-7B-Instruct | Alibaba | ⚠️ same family as base generator — comparison rows only |
| t4 | Mistral-7B-Instruct-v0.3 | Mistral | ⚠️ weak on SVAMP/GSM8K (4–18% coverage); usable on GSM-Symbolic (69–74%) |
| t5 | DeepSeek-V2-Lite-**Chat** | DeepSeek | ❌ **dead** — it is the chat variant and cannot write SMT-LIB. 443 of 462 outputs never wrote the word `answer`. Kept in the repo as a documented negative. |
| t6 | deepseek-coder-6.7b-instruct | DeepSeek | ✅ the same-family control |

The main 4-translator set (`k4`) is **t1, t2, t3, t6**.

### Solver

- **Z3** — primary verifier
- **CVC5** — planned cross-check, **not yet complete**

### Datasets

| Dataset | Size | Structure |
|---|---|---|
| SVAMP | 1,000 | flat |
| GSM8K (test) | 1,319 | flat |
| GSM-Hard | 1,319 | flat |
| GSM-Symbolic `main` | 5,000 | 100 templates × 50 instances |
| GSM-Symbolic `p1` | 5,000 | 100 templates × 50 instances |
| GSM-Symbolic `p2` | 2,500 | 50 templates × 50 instances |

⚠️ **`p2`'s 50 templates are a strict subset of `main`'s 100.** If you compare ρ measured on 50 templates against ρ measured on 100, you confound difficulty with template composition — the exact thing GSM-Symbolic exists to control. Restrict `main` and `p1` to the shared 50 before any ladder comparison. This is not cosmetic: `p1` generator accuracy is 76.1% on all 100 templates but 72.1% on the shared 50 — a 4-point gap from composition alone.

### Producer parity

Every run across all six datasets shares one configuration. Change any of it and the banked outputs are invalid:

```
prompt_version   = p1-v1
seed             = 1234
GEN_MAX_NEW      = 512
TRANS_MAX_NEW    = 768
MAX_MODEL_LEN    = 4096
dtype            = bfloat16
enforce_eager    = True
enable_prefix_caching = False    # deliberately off: reproducibility over speed
```

### Confidence intervals — pick the right one

- **GSM-Symbolic** → cluster bootstrap over templates. Rows inside a template are not independent. Wilson is about **2.3× too narrow** here.
- **SVAMP / GSM8K / GSM-Hard** → Wilson. These have no template structure and the rows genuinely are independent, so clustering would be wrong in the other direction.
- **Zero-event cells** → rule of three, on gated **templates** not gated rows.

---

## 10. What it cost

Total: **under $250**, self-funded, one person.

| Item | Cost |
|---|---|
| All GPU work (Stage 1, six datasets, eight roles) | ~$10 |
| Gemini Flash-Lite middle generator, all six datasets | ~$5.50 |
| Gemini Pro top generator (`main` + `p2`) | ~$116 |
| Best-of-8 judge, GSM-Symbolic ladder | ~$40 |
| Earlier best-of-8 and weak-to-strong runs | ~$57 |

The cost breakdown is itself a finding for the paper: **cheap trusted verification of expensive untrusted models**. The entire middle-generator arm across six datasets cost $5.50 — and $1.01 for 2,500 problems on `p2`.

One deliberate omission: Gemini Pro was never run on `p1` (~$90, unaffordable), which is why `p1` has a two-point generator ladder instead of three. Stated, not hidden.

⚠️ The Google Cloud $300 trial credit **did not** absorb these charges. Do not plan around it.

---

## 11. Repo layout

```
.
├── README.md                              ← you are here
├── stage1/
│   ├── stage1_lib.py                      # dataset loaders, record shape, prompts
│   ├── stage1_generation.ipynb            # generator + gen_k8 + translators
│   ├── stage1b_extra_translators.ipynb    # multi-role worker
│   └── stage1c_extra_translators.ipynb    # (library cell byte-identical to 1b)
├── stage2/
│   ├── stage2_lib.py                      # Z3 verify, sat guard, Wilson, rule-of-three, rho
│   ├── crc.py                             # conformal risk control + anticonservatism audit
│   └── stage2_verification_and_crc.ipynb  # 14 self-tests, bootstrap CIs, all tables
├── judge/
│   └── bon8_judge.ipynb                   # best-of-8 with a frontier judge
├── data/
│   └── (generated JSONL — see below)
├── results/
│   └── (tables, figures, CRC certificates)
├── prereg/
│   └── (dated pre-registration documents)
└── paper/
    └── (LaTeX source)
```

**On the JSONL files:** Stage 1 output is large. If it does not fit here it will be linked from `data/README.md` rather than committed. Every file is checkpointed and integrity-checked (equal row counts, zero duplicate pids, zero empty outputs, identical question and gold hashes across roles, one model and one prompt_version per file).

**Record shape** — keep this exactly, it is what makes everything comparable:

```json
{
  "pid": "gsm_symbolic_main/0000_00",
  "question": "...",
  "gold": "18",
  "meta": {"template_id": 0, "instance": 0, "original_id": 12},
  "outputs": ["..."],
  "finish": "stop",
  "ts": "2026-08-09T11:04:22Z"
}
```

Notes: `gold` is a **string**, not a float. `outputs` is a **list**. The final answer is parsed at Stage 2, not Stage 1. Pids are **zero-padded** — without padding, sorting puts `0_1` before `0_10`. In GSM-Symbolic, `template_id` is the clustering key; `original_id` indexes back into GSM8K-test and must **never** be used for clustering.

---

## 12. How to reproduce

The work splits cleanly in two, and this is the single most useful thing about the design.

### Stage 1 — needs a GPU, costs money, run once

Produces checkpointed JSONL: generator answers, 8 sampled answers, and SMT-LIB from each translator.

Hardware used: **Vast.ai A100 40GB**.

```bash
# filters that actually matter when renting
#   CUDA >= 13          (torch 2.12+cu130 will not run on a 12.x driver)
#   disk >= 120 GB      (set on the RENT SLIDER, not the host's free-disk figure)
#   net  >= 1000 Mbps
# sort by DLPerf per dollar, not raw price
```

Set your Hugging Face token **via a file**, never in a notebook cell:

```bash
# from a Jupyter TERMINAL, not a cell
printf '%s' 'hf_xxxxxxxx' > /workspace/.hf_token
chmod 600 /workspace/.hf_token
```

Then in the notebook, read env → file → `getpass` prompt, and validate:

```python
from huggingface_hub import whoami
whoami(token=HF_TOKEN)   # actually check it, don't just check the string exists
```

### Stage 2 — CPU only, free, rerun as often as you like

Everything downstream — Z3, CRC, ρ, bootstrap, McNemar, adjudication — runs on a normal laptop against the banked JSONL.

```bash
pip install z3-solver numpy scipy pandas
jupyter notebook stage2/stage2_verification_and_crc.ipynb
```

The notebook opens with **14 verifier self-tests**. If any fail, stop — do not read the numbers below them.

**Reproducibility note:** every CRC number in the results was independently reproduced **bit-for-bit from seed 0** on separate hardware.

---

## 13. Things that are still missing

Listed openly. Some are in progress, some may not make the workshop deadline.

| Item | Why it matters | Status |
|---|---|---|
| **Adjudication protocol** | Must be written and **dated before** any new case is opened, or the analysis is post-hoc. Scope: 15 (split, template) pairs, 13 distinct templates. The 7 GSM8K CW cases stay **sealed** until it exists — they are the only fully clean sample left. Template 76, templates 32/33 and the 3 SVAMP cases are declared post-hoc. | ⏳ next |
| **GSM8K-Platinum re-scoring** | Free, and it is the instrument that tests the benchmark-defect story on a **non-templated** dataset. If the CW cases vanish under the cleaned labels, that is independent confirmation. If they persist, the defect story is GSM-Symbolic-specific and we must say so. | ⏳ |
| **Satisfiability-guard ablation on all six** | Currently measured on `main` only. | ⏳ |
| **Full 15-pair ρ matrix + hardness-conditioned ρ** | Only 3 pairs are measured. CPU work, free. | ⏳ |
| **CVC5 cross-check** | Guards against a Z3-specific quirk. | ❌ not started |
| **Dual-semantics ablation** | Int vs Real handling. | ❌ not started |
| **~85 failed API calls (HTTP 429)** | These were written as empty and then **scored as wrong**, understating accuracy. Real figures on SVAMP/GSM8K are 96.56% and 96.55%, not 95.50% and 95.60%. Needs a retry pass. | ❌ |
| **Second judge family** | Gemini is currently **both** the judge and the top generator, so two results move together if it has a quirk. ~$5–15 on 300 already-judged problems. `JUDGE_MODEL_ALT` is already wired up. | ❌ blocked on budget |
| **Distillation track** | Within-family teacher distillation. This is the ICML story, not the workshop story — distilled translators are *new* translators, so every banked result would need regenerating. Go/no-go on **15 October 2026**. | ⏸️ deliberately deferred |
| **Truncation, reported as a limitation** | 768/512-token caps bind as questions lengthen. On `p2`: t5 33.04%, gen_k8 5.64%, t4 4.88%, t6 2.80%, t2 2.48%, t1 2.00%. **Do not raise the caps** — that breaks producer parity. | 📝 documented |
| **`k=2` is not necessarily cross-family** | k=2-of-4 can be satisfied by t1+t6, both DeepSeek. Family-diversity audit on `p2`: at k=1, 76% of gated problems are agreed by a single family; at k=2 that drops to 10%. Either set the threshold at k≥2 or describe the guarantee as operating over **agreement count irrespective of family**. | 📝 documented |

---

## 14. Traps we fell into, so you don't have to

A full day was lost to the first three. These are the ones worth writing down.

**Infrastructure**

- **An `HF_TOKEN` is not optional.** Unauthenticated Hub downloads are throttled, and the throttling is **silent**. vLLM prints "Loading model from scratch…" and then nothing for 45+ minutes. It is indistinguishable from a hang.
- **Rented GPUs can be shared.** If `nvidia-smi` shows memory used but an **empty process list**, another container holds it — invisible from your namespace and unkillable. Always confirm `memory.used` reads ~0 MiB *before* you start.
- **Never `pip install -U` on an image that already ships vLLM.** It half-upgrades torch and you get `ImportError: cannot import name '_EvalFrameOverride'` — the Python half and the compiled half at different versions. It can also jump transformers to 5.x when vLLM expects 4.x. Run `pip list | grep -E '^(torch|vllm|transformers)'` first and install only what is missing.
- **vLLM 0.26 removed `swap_space`.** Build engine kwargs and filter against `EngineArgs` fields instead of pinning a version.
- **`enforce_eager=True`** skips a 3–8 minute silent `torch.compile` phase.
- **Interrupting a `!command` cell** can orphan vLLM's `EngineCore` child, which then holds VRAM forever. Launch via `subprocess` with `preexec_fn=os.setsid` and kill the process group.
- **Disk is the binding constraint, not VRAM** — five models is ~95 GB. But passes are sequential, so the real requirement is the *largest single model* plus ~15 GB margin (~47 GB), not the sum. Use `os.lstat`, not `os.path.getsize`, when measuring the HF cache: `snapshots/` symlinks into `blobs/` and `getsize` follows the link, double-counting every shard.

**API**

- **Thinking tokens count against `max_output_tokens` in Gemini.** This invalidated two full runs. At a 1024 cap, the median GSM-Hard reply spent **979 tokens thinking and 41 on output** — replies were cut off, 58.6% carried no `FINAL:` tag, extraction fell back to "last number in the reply", and apparent accuracy read **39.7%** against a true 93.3%.
- **Build `GenerateContentConfig` in the constructor**, never as an attribute set afterwards inside a `try/except` — the rejection gets swallowed and it silently truncates anyway. Working values: `MAX_OUTPUT_TOKENS=32768`, `THINKING_BUDGET=None`.
- **Gate on `FINAL:`-tag compliance ≥95% in a smoke test** before any full run, and delete stale output files first, because resume-by-pid will otherwise keep the truncated rows.
- **Gemini 3.1 Pro is global-endpoint only** — `location="global"`, `us-central1` fails. Auth is ADC, not an API key. Preview quota is low; concurrency ~3 is safe, 8 trips the limit.

**Code**

- **Never write a `%%writefile` cell with placeholder content.** One did exactly that and overwrote a real 12,969-byte module with 134 bytes of comments. Verify size and required functions after writing.
- **Arm dictionaries must be keyed generator-independently.** Keying by family label breaks cross-generator lookup — t3 is Alibaba-family, same as Qwen but not as Gemini, so the *same pair* gets two different keys and you get a `KeyError` **after** the Z3 pass, i.e. after the money is spent. Assert `set(ARMS[a]) == set(ARMS[b])` before use.
- **The `FINAL:` regex needs an exponent group**, or `FINAL: 1.5e10` silently parses as `1.5`.
- **Failed API calls must not be scored as wrong.** `read_done` has to drop `ok: False` records so they retry.
- **Shared library cells must be byte-for-byte identical** across stage1 / 1b / 1c. That identity is exactly what keeps ρ(t1,t2) and ρ(t1,t6) comparable. Do **not** "improve" the chat-template probe in 1b/1c — it produced the existing t6 numbers, and changing it would make them incomparable.
- **Do not build a fresh Stage 1 notebook from scratch.** We tried. It diverged from the real pipeline in ~15 invisible ways — gold as float instead of string, `raw_text` instead of an `outputs` list, seed 0 instead of 1234, prefix caching on instead of off — and 5,000 records had to be thrown away. Patch the existing notebooks surgically instead.
- **Some chat templates reject a `system` role** (Mistral). Fold the system text into the first user turn.
- **Derive expected row counts from the loader**, never hardcode them. A wrong value makes the runner declare a partial file complete and stop early, silently.

**Security**

- **Never put a token in a notebook cell.** It is written into the `.ipynb` **and** into `.ipynb_checkpoints/`, so deleting the cell later does not remove it — and the repo still has to be pushed. Use the file route.
- `export HF_TOKEN=...` typed in a terminal does **not** reach an already-running Jupyter kernel. And `export HF_TOKEN= hf_...` with a stray space, or with curly quotes copied from a web page, silently sets an empty value.

---

## 15. How we tried to keep this honest

Listing this because a negative result is only worth anything if the process behind it is trustworthy.

- **The generator is frozen.** Never trained, never tuned, never prompt-engineered against results.
- **Predictions were pre-registered with dates**, before the shift datasets were run.
- **Prediction (ii) was retired before results were viewed**, because the labels it needed are not in the public data release.
- **Zero-event cells use the rule of three**, on gated templates. We never write "0.00%" for something we merely did not observe.
- **The CI method switches by dataset structure** — cluster bootstrap where there is clustering, Wilson where there is not.
- **Every number is recomputed from raw JSONL**, not copied forward from a previous write-up.
- **The CRC results were independently reproduced bit-for-bit from seed 0** on separate hardware.
- **A number-magnitude confound was ruled out before ρ was computed**, and in the unfavourable direction for us: the median integer in the question *falls* across the difficulty ladder (16 → 14 → 13, p90 250 → 150 → 130). So rising ρ cannot be blamed on bigger integers stressing Int/Real handling.
- **Encoding rates stay flat or rise while generator accuracy falls 27 points** across the ladder. The extra clauses make *reasoning* harder without making *formalisation* harder — so ρ movement is attributable to difficulty, not to translators degrading.
- **A falsified earlier write-up was withdrawn** by the author once its central claim was contradicted by this project's own data.
- **Failure modes were measured, not patched away.** We did not suppress self-contradictory encodings, and we report the dead translator (t5) rather than quietly dropping it.
- **Bugs found in our own analysis are listed here**, including one where a best-of-8 estimator reported an impossible 100.66% of the oracle ceiling because the subsample and the ceiling were computed on different bases.

---

## 16. Citing / contact / licence

**Paper:** *Certified Selective Reasoning: Decorrelated Neuro-Symbolic Verification with Distribution-Free Guarantees*
Under submission, MATH-AI @ NeurIPS 2026. A preprint will be posted to arXiv around October 2026.

```bibtex
@misc{certified-selective-reasoning-2026,
  author = {Abhishek},
  title  = {Certified Selective Reasoning: Decorrelated Neuro-Symbolic
            Verification with Distribution-Free Guarantees},
  year   = {2026},
}
```

**Related work this builds on:** Ganguly et al., *Grammars of Formal Uncertainty* (NeurIPS 2025) · Feng et al., *VeriCoT* · Olausson et al., *LINC* · Ye et al., *SatLM* · *Logic-LM* · Angelopoulos et al. on conformal risk control · Mirzadeh et al., *GSM-Symbolic* · Knight & Leveson (1986) on the failure of independence assumptions in N-version programming · Damani & Puri, *RLCR*.

**Contact:** abhishekvicky12345@gmail.com

**Issues and corrections are genuinely welcome.** If you think a number here is wrong, please open an issue — that is exactly the kind of help this project needs.

---

*Last updated: 17 August 2026*
