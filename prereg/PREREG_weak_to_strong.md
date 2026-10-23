# Weak-to-strong oversight: pre-registered prediction

Written 2026-08-07 21:18:03 BEFORE any Gemini generation was run.

Generator under test: gemini-3.1-pro-preview
Verifiers: t1, t2, t3, t6 (existing encodings, unchanged)


Gemini will be substantially more accurate than Qwen2.5-7B (expect ~96% on
GSM8K/SVAMP, ~85% on GSM-Hard), shrinking the wrong-answer pool.

Coverage: I expect it to FALL. Gemini solves problems whose structure the 7B
translators cannot express in SMT-LIB, so fewer answers get certified.

CW rate: I expect it to RISE on GSM-Hard. Gemini remaining errors are on
genuinely hard problems where the translators are also weakest, so a larger
fraction of its wrong answers survive the entailment check.

Falsified if: coverage rises, or CW rate falls on GSM-Hard.

Caveat: SVAMP and GSM8K will likely have under 60 wrong answers each and are
expected to be underpowered.

