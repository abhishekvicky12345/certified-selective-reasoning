# Pre-registrations

Each file was written before the run it registers. Outcomes, including every falsified prediction, are reported in the paper.

| ID | File | Written (stated in the file) | SHA-256 | What it registers |
|---|---|---|---|---|
| P4 | `PREREG_weak_to_strong.md` | 2026-08-07 21:18:03 IST, before any Gemini generation | `4f05d4d998795287…` | Qwen2.5-7B → Gemini-3.1-Pro swap with translators t1, t2, t3, t6: accuracy, coverage falls, CW rate rises on GSM-Hard |
| P4, GSM-Symbolic main | `PREREG_weak_to_strong_gsm_symbolic__gsm_symbolic_main.md` | 2026-08-11 00:29:12 IST | `8459abaa31445600…` | The P4 text for GSM-Symbolic main |
| P4, GSM-Symbolic p2 | `PREREG_weak_to_strong_gsm_symbolic__gsm_symbolic_p2.md` | 2026-08-11 03:30:50 IST | `8e79c462829df5f2…` | The P4 text for p2 |
| P4, GSM-Symbolic p1 | `PREREG_weak_to_strong_gsm_symbolic.md` | 2026-08-12 02:10:41 IST | `733fc6dab4b15e7c…` | The P4 text for p1 |
| P7 | `PREREG_verifier_ceiling.md` | 2026-10-23 | `f6dfbdd8f03a7677…` (full hash in the `.sha256` file) | Verifier-ceiling analyses on existing artifacts |

**Timestamps.**
- The P4 files were written to dated files outside the pipeline's regenerable output folder and were not under version control.
- So their written-at times are self-reported. Each file's filesystem modification time matches the time it states.
- The P4 files were committed here on 24 Oct 2026, after their runs.
- P7 was committed here before its analysis ran: commit 7a7856f, 23 Oct 2026.

**Deviations from P4**, disclosed in the paper:
- No registration names a gating rule; the headline rule, k≥3 over t1/t2/t3/t6, was chosen after the runs.
- The GSM-Symbolic files register `thinking=max`, but the runs used `high`.
- The GSM-Symbolic files copy the P4 text verbatim, including its references to GSM-Hard, and name t1–t6 instead of the four translators used.

The other registrations, including P5 (decorrelation) and P6 (adjudication), will be added here once they are located.
