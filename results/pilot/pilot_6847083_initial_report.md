# Initial exploratory results — 2026-11-06

Completed pilot on one NVIDIA H100 80 GB, vLLM 0.31.0, Llama-3.1-8B-Instruct bf16. Three agents, two rounds, temperature 0.7, top-p 0.9, 512 output tokens, sampling/problem seed 0. GSM8K: 30 problems per configuration; QuALITY: 20 distinct stories per configuration. Load points C=1 and C=4. All configurations use the same problems within each task.

**Exploratory only:** the debate prompts approximate the released workflow, sample sizes are below preregistration, and only one seed was used. No claim that preregistered hypotheses or the quality guardrail have been established. The pilot used four CPUs in existing VS Code allocation 6847083 (80 GB host-memory allocation), step 6847083.1. The prior two-example smoke test used eight CPUs; do not combine their timings.

## Main observations

- Parallel dispatch with APC on reduced C=1 median latency from 5.40 to 2.47 s on GSM8K (2.19×; paired bootstrap interval 1.96–2.46) and from 7.03 to 2.92 s on QuALITY (2.41×; interval 2.08–2.57). These are one-seed exploratory intervals, not the registered headline analysis.
- Under parallel dispatch, disabling APC added only 0.4% to GSM8K C=1 median latency, versus 28.9% on QuALITY C=1 and 69.3% on QuALITY C=4. This supports further testing of context/load effects, without establishing the C=16 decision rule.
- Full L3 reduced computed prefill tokens by 7.8% on QuALITY C=1 and 8.4% at C=4, while increasing median latency by 13.3% and 4.4%, respectively, relative to L1+L2. Its mean answer lengths were also longer. There is no observed median-latency benefit for L3 in this pilot; the registered C=16 test remains unrun.
- At QuALITY C=4, BASE was 16/20 correct, versus 14/20 for both L1+L2 and full L3. Keep the 10 pp quality warning even though paired tests are not significant. Additional same-seed repeats were initiated after observing this warning to assess variability; they are reported separately and do not replace these results.

## Completion and provenance

- Verified 430 unique debate records in 18 configurations, with expected problem IDs, call counts, token ranges and timings. APC-off cached-token counts are zero.
- Source base on ICE: 7fa8afe; the exact working-tree patch and package freeze are saved alongside the results. Model snapshot: 0e9e39f249a16976918f6564b8830bc894c89659.
- Reported p95 uses the nearest-rank definition; all warm-up request time and tokens inside each debate are included. Three preliminary server warm-up calls per configuration are excluded, as in the pilot code.

## gsm8k, C=1

| Configuration | n | Median T (s) | p95 (s) | Latency ratio BASE/config | Accuracy | Tasks/min | Computed prefill/task | Mean output tokens/call |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | 30 | 5.40 | 11.61 | 1.00× | 90.0% | 9.5 | 1619 | 165.4 |
| Sequential, APC off | 30 | 6.15 | 9.46 | 0.88× | 96.7% | 9.2 | 2845 | 170.1 |
| Parallel, APC off | 30 | 2.48 | 4.60 | 2.18× | 93.3% | 22.1 | 2863 | 172.2 |
| L1+L2 | 30 | 2.47 | 5.83 | 2.19× | 93.3% | 21.4 | 1638 | 172.9 |
| L1+L2+L3a | 30 | 2.45 | 5.85 | 2.21× | 90.0% | 22.0 | 1641 | 170.9 |
| L1+L2+L3 | 30 | 3.10 | 5.79 | 1.74× | 90.0% | 18.7 | 1016 | 200.9 |
| Single agent | 30 | 1.07 | 2.51 | 5.02× | 90.0% | 46.8 | 98 | 208.0 |

L1 latency ratio with APC on: **2.19×**, paired problem-bootstrap 95% interval **[1.96, 2.46]** (4,000 resamples, one seed).
L2 leave-one-out loss under parallel dispatch: **0.01 s**, or **0.4%** of L1+L2 time.
Dispatch × cache interaction in median seconds, (T_seq,off − T_par,off) − (T_seq,on − T_par,on): **+0.74 s** (descriptive difference of differences).
L1+L2+L3a vs L1+L2: computed prefill **+0.2%**; median time **-0.9%**.
L1+L2+L3 vs L1+L2: computed prefill **-37.9%**; median time **+25.6%**.

| Configuration vs BASE | Answer agreement | Accuracy change (pp) | BASE-only correct | Config-only correct | Exact McNemar p |
|---|---:|---:|---:|---:|---:|
| L1+L2 | 29/30 | +3.3 | 0 | 1 | 1.0000 |
| L1+L2+L3a | 27/30 | +0.0 | 1 | 1 | 1.0000 |
| L1+L2+L3 | 28/30 | +0.0 | 0 | 0 | 1.0000 |
| Parallel, APC off | 28/30 | +3.3 | 0 | 1 | 1.0000 |
| Sequential, APC off | 28/30 | +6.7 | 0 | 2 | 0.5000 |

Exact two-sided McNemar p-values are exploratory and unadjusted for multiple comparisons. A non-significant result does not prove equal accuracy; the registered >2.0 pp regression rule remains separate.
Round-1 cached-token share, agents 2–3, seq: 94.2%.
Round-1 cached-token share, agents 2–3, par: 94.2%.
Round-1 cached-token share, agents 2–3, l3a: 94.2%.

## quality, C=1

| Configuration | n | Median T (s) | p95 (s) | Latency ratio BASE/config | Accuracy | Tasks/min | Computed prefill/task | Mean output tokens/call |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | 20 | 7.03 | 8.97 | 1.00× | 65.0% | 8.7 | 7441 | 172.4 |
| Sequential, APC off | 20 | 7.73 | 9.58 | 0.91× | 70.0% | 7.6 | 37620 | 175.6 |
| Parallel, APC off | 20 | 3.76 | 5.36 | 1.87× | 60.0% | 15.6 | 37518 | 168.1 |
| L1+L2 | 20 | 2.92 | 3.75 | 2.41× | 70.0% | 20.1 | 7392 | 170.2 |
| L1+L2+L3a | 20 | 3.10 | 3.87 | 2.27× | 65.0% | 19.6 | 7429 | 173.7 |
| L1+L2+L3 | 20 | 3.30 | 4.39 | 2.13× | 75.0% | 18.3 | 6819 | 187.7 |
| Single agent | 20 | 1.39 | 1.98 | 5.05× | 60.0% | 40.7 | 5902 | 207.3 |

L1 latency ratio with APC on: **2.41×**, paired problem-bootstrap 95% interval **[2.08, 2.57]** (4,000 resamples, one seed).
L2 leave-one-out loss under parallel dispatch: **0.84 s**, or **28.9%** of L1+L2 time.
Dispatch × cache interaction in median seconds, (T_seq,off − T_par,off) − (T_seq,on − T_par,on): **-0.14 s** (descriptive difference of differences).
L1+L2+L3a vs L1+L2: computed prefill **+0.5%**; median time **+6.3%**.
L1+L2+L3 vs L1+L2: computed prefill **-7.8%**; median time **+13.3%**.

| Configuration vs BASE | Answer agreement | Accuracy change (pp) | BASE-only correct | Config-only correct | Exact McNemar p |
|---|---:|---:|---:|---:|---:|
| L1+L2 | 18/20 | +5.0 | 0 | 1 | 1.0000 |
| L1+L2+L3a | 17/20 | +0.0 | 1 | 1 | 1.0000 |
| L1+L2+L3 | 15/20 | +10.0 | 0 | 2 | 0.5000 |
| Parallel, APC off | 18/20 | -5.0 | 1 | 0 | 1.0000 |
| Sequential, APC off | 18/20 | +5.0 | 0 | 1 | 1.0000 |

**Pilot quality warning:** Parallel, APC off is -5.0 pp vs BASE (exact McNemar p=1.0000). This crosses a numerical guardrail criterion in this exploratory sample; do not present it as a quality-preserving speedup.

Exact two-sided McNemar p-values are exploratory and unadjusted for multiple comparisons. A non-significant result does not prove equal accuracy; the registered >2.0 pp regression rule remains separate.
Round-1 cached-token share, agents 2–3, seq: 99.8%.
Round-1 cached-token share, agents 2–3, par: 93.7%.
Round-1 cached-token share, agents 2–3, l3a: 99.8%.

## quality, C=4

| Configuration | n | Median T (s) | p95 (s) | Latency ratio BASE/config | Accuracy | Tasks/min | Computed prefill/task | Mean output tokens/call |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | 20 | 8.95 | 9.85 | 1.00× | 80.0% | 27.5 | 7454 | 172.2 |
| Parallel, APC off | 20 | 7.76 | 11.14 | 1.15× | 75.0% | 28.4 | 37551 | 174.2 |
| L1+L2 | 20 | 4.58 | 8.43 | 1.95× | 70.0% | 44.3 | 7445 | 177.1 |
| L1+L2+L3 | 20 | 4.79 | 6.11 | 1.87× | 70.0% | 46.4 | 6822 | 191.6 |

L1 latency ratio with APC on: **1.95×**, paired problem-bootstrap 95% interval **[1.60, 2.08]** (4,000 resamples, one seed).
L2 leave-one-out loss under parallel dispatch: **3.18 s**, or **69.3%** of L1+L2 time.
L1+L2+L3 vs L1+L2: computed prefill **-8.4%**; median time **+4.4%**.

| Configuration vs BASE | Answer agreement | Accuracy change (pp) | BASE-only correct | Config-only correct | Exact McNemar p |
|---|---:|---:|---:|---:|---:|
| L1+L2 | 15/20 | -10.0 | 3 | 1 | 0.6250 |
| L1+L2+L3 | 18/20 | -10.0 | 2 | 0 | 0.5000 |
| Parallel, APC off | 18/20 | -5.0 | 1 | 0 | 1.0000 |

**Pilot quality warning:** L1+L2 is -10.0 pp vs BASE (exact McNemar p=0.6250). This crosses a numerical guardrail criterion in this exploratory sample; do not present it as a quality-preserving speedup.

**Pilot quality warning:** L1+L2+L3 is -10.0 pp vs BASE (exact McNemar p=0.5000). This crosses a numerical guardrail criterion in this exploratory sample; do not present it as a quality-preserving speedup.

**Pilot quality warning:** Parallel, APC off is -5.0 pp vs BASE (exact McNemar p=1.0000). This crosses a numerical guardrail criterion in this exploratory sample; do not present it as a quality-preserving speedup.

Exact two-sided McNemar p-values are exploratory and unadjusted for multiple comparisons. A non-significant result does not prove equal accuracy; the registered >2.0 pp regression rule remains separate.
Round-1 cached-token share, agents 2–3, seq: 99.8%.
Round-1 cached-token share, agents 2–3, par: 89.7%.

## Interpretation limits and next gates

- These are workflow measurements, not isolated serving-kernel speedups. Output lengths and sampled intermediate answers can differ across dispatch modes despite fixed seeds.
- Full L3 changes round-2 prompts. L3a warms round 1 only in this pilot and uses one generated token; it is not a literal zero-decode prefill or a validated per-round implementation.
- The trace does not retain raw responses, serialized/tokenized inputs, finish reasons, per-call server queue/prefill/decode timings, or a global timeline. Computed prefill is prompt tokens minus server-reported cached tokens, including warm-up requests. Timing ends just before answer parsing/voting in this pilot; align it with preregistration before formal runs.
- Full C=16/32 contention claims, multi-seed accuracy guardrails, and the 300-problem dataset policy remain untested. Keep the original thresholds and record any later design changes with dates and reasons.
- See docs/proposal_alignment_review.md for the full proposal/feedback audit.

## Same-seed C=4 accuracy follow-up

Triggered after the original grid showed an accuracy warning. Two additional BASE/parallel comparisons used the same 20 QuALITY problems, sampling seed 0, problem seed 0, APC on, and the same H100/four-CPU allocation. The repeat server was restarted once before these checks; each configuration reset its prefix cache. Step 6847083.2 completed successfully in 3m45s; all 80 additional records passed validation.

| Run | BASE median (s) | Parallel median (s) | BASE correct | Parallel correct | Accuracy change | BASE-only / parallel-only correct | Exact McNemar p |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original grid | 8.95 | 4.58 | 16/20 | 14/20 | -10 pp | 3 / 1 | 0.6250 |
| Repeat 1 | 8.70 | 4.60 | 16/20 | 11/20 | -25 pp | 5 / 0 | 0.0625 |
| Repeat 2 | 8.52 | 4.37 | 13/20 | 12/20 | -5 pp | 2 / 1 | 1.0000 |

**Interpretation:** latency gains recur, but the parallel configuration is below its paired BASE accuracy in all three comparisons. BASE itself varies from 65% to 80%, and parallel from 55% to 70%, despite the same seed mapping. This demonstrates final-answer variability in this setup; it does not establish its cause or excuse the quality losses. Each comparison crosses the numerical >2 pp regression criterion. Do not claim a quality-preserving C=4 speedup.

The repeats reuse the same problems and are not independent new datasets. Do not pool the 60 problem exposures as 60 distinct examples, select a favorable repeat as baseline, or replace the original grid. Exact p-values above are two-sided and exploratory; non-significance does not override the numerical accuracy guardrail. Next, capture raw responses, tokenized requests, finish reasons and seeds, test fixed upstream-input equivalence, and complete the registered multi-seed evaluation before larger claims.
