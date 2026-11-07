# Exploratory quality-repeat check — 2026-11-06

## Same-seed C=4 accuracy follow-up

Triggered after the original grid showed an accuracy warning. Two additional BASE/parallel comparisons used the same 20 QuALITY problems, sampling seed 0, problem seed 0, APC on, and the same H100/four-CPU allocation. The repeat server was restarted once before these checks; each configuration reset its prefix cache. Step 6847083.2 completed successfully in 3m45s; all 80 additional records passed validation.

| Run | BASE median (s) | Parallel median (s) | BASE correct | Parallel correct | Accuracy change | BASE-only / parallel-only correct | Exact McNemar p |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original grid | 8.95 | 4.58 | 16/20 | 14/20 | -10 pp | 3 / 1 | 0.6250 |
| Repeat 1 | 8.70 | 4.60 | 16/20 | 11/20 | -25 pp | 5 / 0 | 0.0625 |
| Repeat 2 | 8.52 | 4.37 | 13/20 | 12/20 | -5 pp | 2 / 1 | 1.0000 |

**Interpretation:** latency gains recur, but the parallel configuration is below its paired BASE accuracy in all three comparisons. BASE itself varies from 65% to 80%, and parallel from 55% to 70%, despite the same seed mapping. This demonstrates final-answer variability in this setup; it does not establish its cause or excuse the quality losses. Each comparison crosses the numerical >2 pp regression criterion. Do not claim a quality-preserving C=4 speedup.

The repeats reuse the same problems and are not independent new datasets. Do not pool the 60 problem exposures as 60 distinct examples, select a favorable repeat as baseline, or replace the original grid. Exact p-values above are two-sided and exploratory; non-significance does not override the numerical accuracy guardrail. Next, capture raw responses, tokenized requests, finish reasons and seeds, test fixed upstream-input equivalence, and complete the registered multi-seed evaluation before larger claims.
