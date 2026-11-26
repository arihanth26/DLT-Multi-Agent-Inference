# QuALITY C=1 three-seed pilot — 2026-11-06

Separate uniform runs on the same 20 distinct stories as the original pilot, with problem seed 0 and sampling seeds 0,1,2. Three agents, two rounds, one H100 80 GB, four CPUs, pinned vLLM 0.31.0, Llama-3.1-8B-Instruct bf16, temperature 0.7, top-p 0.9, maximum 512 output tokens. Both modes use APC on and reset the prefix cache before each configuration. Requests and responses were recorded. This is a fresh exploratory run; it does not replace earlier measurements or satisfy the registered 100-problem headline sample size.

Validated 120 records. Complete groups: [(0, 'par'), (0, 'seq'), (1, 'par'), (1, 'seq'), (2, 'par'), (2, 'seq')]. Incomplete groups: none. Request hashes/seeds/settings, history reconstruction, response parsing, votes, token counts and timings were checked. Only complete pairs enter the table.

| Sampling seed | BASE median (s) | Parallel median (s) | BASE/parallel latency ratio | BASE correct | Parallel correct | Accuracy delta | BASE-only / parallel-only correct | Exact McNemar p |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 7.20 | 2.99 | 2.41× | 13/20 | 14/20 | +5.0 pp | 0/1 | 1.0000 |
| 1 | 7.13 | 3.14 | 2.27× | 13/20 | 15/20 | +10.0 pp | 1/3 | 0.6250 |
| 2 | 6.65 | 2.97 | 2.24× | 12/20 | 13/20 | +5.0 pp | 1/2 | 1.0000 |

Descriptive mean of the three per-seed medians: BASE **6.99 s**, parallel **3.03 s**, ratio **2.31×**. Mean accuracy over seeds: BASE **63.33%**, parallel **70.00%**, difference **+6.67 pp**.

These are 20 unique problems repeated under three seeds, not 60 independent problems. Exact two-sided McNemar p-values are per seed, exploratory, and unadjusted; non-significance does not prove non-inferiority or cancel a numerical accuracy-loss warning. No pooled significance test is claimed. The small sample, approximate released-workflow prompts, same-seed variability and first-use compilation caveats remain. The separate 64-story load extension should be interpreted independently.
