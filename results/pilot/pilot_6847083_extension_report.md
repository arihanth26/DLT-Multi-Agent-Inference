# QuALITY load extension — 2026-11-06

Exploratory follow-up on 64 distinct validation stories with the same problem selection for all complete groups. One H100 80 GB, four allocated CPUs, Llama-3.1-8B-Instruct bf16, vLLM 0.31.0; temperature 0.7, top-p 0.9, maximum 512 output tokens; three agents and two rounds. Full messages, request seeds, sampling settings and responses were recorded. Each configuration starts with a reset prefix cache; APC on/off use separate server processes. The original 30/20-problem grid is preserved separately.

Validated **1024 records**; **16 complete 64-problem groups**. Partial groups: none. Missing priority groups: none. Counts, problem IDs, request hashes/seeds/settings, round-2 message construction from recorded round-1 outputs, call counts, token counts, APC-off cache counts, response parsing and final votes were checked. Only complete groups enter comparisons below.

This is not the preregistered evaluation: 64 problems rather than 100/300, an approximate released-workflow implementation, short closed-loop windows, and exploratory follow-up selected after the initial pilot. C=32 has only two waves of 32 problems, so startup/drain effects can be substantial. Task bootstraps do not capture within-run queue dependence and are descriptive at load. Recording adds client work; do not pool these timings with the uninstrumented original pilot. Raw Prometheus snapshots and server logs are retained, including first-use JIT warnings. Per-call finish reasons and rendered token IDs are not recorded; token-cap hits below are a proxy, not definitive truncation labels.

## Main observations

- The raw BASE/parallel latency ratio falls from **2.36× at C=1** to **1.63× at C=16** and **1.42× at C=32**. The C=32 add-one gain is 31% of its C=1 value. This is descriptive pilot evidence for contention, not preregistered acceptance.
- Disabling caching adds **0.77 s at C=1**, **13.72 s at C=16**, and **24.33 s at C=32** to median parallel latency. Caching is a major contributor under load on these long prompts.
- At the registered target load C=16, full L3 changes prefill estimates by **-7.7%** and median latency by **+9.8%** relative to L1+L2. The current pilot implementation does not meet the proposed 30% prefill / 10% latency reduction targets in this sample.
- Accuracy and request/response differences remain separate from timing gains. Preserve the earlier C=4 quality warnings; this new grid does not replace them. A missing numerical flag in a new group is not proof of non-inferiority.

## Sampling seed 0

| C | Configuration | n | Median T (s) | p95 (s) | BASE/config latency ratio | Accuracy | Computed prefill/task | Mean answer tokens |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | BASE | 64 | 7.13 | 9.26 | 1.00× | 64.06% | 7318 | 171.3 |
| 1 | L1+L2 | 64 | 3.02 | 4.25 | 2.36× | 70.31% | 7294 | 170.2 |
| 1 | Parallel, APC off | 64 | 3.80 | 5.26 | 1.88× | 68.75% | 36851 | 168.3 |
| 16 | BASE | 64 | 13.76 | 19.40 | 1.00× | 70.31% | 7297 | 170.1 |
| 16 | L1+L2 | 64 | 8.42 | 16.24 | 1.63× | 70.31% | 7265 | 166.1 |
| 16 | L1+L2+L3a | 64 | 8.55 | 11.86 | 1.61× | 71.88% | 7320 | 169.5 |
| 16 | L1+L2+L3 | 64 | 9.24 | 12.71 | 1.49× | 73.44% | 6704 | 185.1 |
| 16 | Parallel, APC off | 64 | 22.14 | 30.21 | 0.62× | 75.00% | 36921 | 171.1 |
| 32 | BASE | 64 | 20.38 | 28.18 | 1.00× | 73.44% | 7284 | 165.0 |
| 32 | L1+L2 | 64 | 14.33 | 25.37 | 1.42× | 71.88% | 7316 | 169.4 |
| 32 | L1+L2+L3 | 64 | 13.78 | 21.06 | 1.48× | 75.00% | 6710 | 184.8 |
| 32 | Parallel, APC off | 64 | 38.66 | 58.74 | 0.53× | 70.31% | 36860 | 167.3 |

### C=1 paired comparisons

Raw BASE-to-parallel latency ratio: **2.36×**, paired bootstrap 95% interval **[2.18, 2.59]** (4,000 resamples).
Caching leave-one-out loss: **0.77 s**, **25.5%** of parallel+APC time.

| Configuration vs BASE | Accuracy delta (pp) | BASE-only / config-only correct | Answer agreement | Exact McNemar p | Quality warning |
|---|---:|---:|---:|---:|---|
| L1+L2 | +6.25 | 1/5 | 55/64 | 0.2188 | No numerical flag in this sample; not proof of non-inferiority |
| Parallel, APC off | +4.69 | 2/5 | 54/64 | 0.4531 | No numerical flag in this sample; not proof of non-inferiority |
seq: round-1 agents 2–3 cached share **99.9%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **1/192**.
par: round-1 agents 2–3 cached share **98.2%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **0/192**.

### C=16 paired comparisons

Raw BASE-to-parallel latency ratio: **1.63×**, paired bootstrap 95% interval **[1.45, 1.79]** (4,000 resamples).
Caching leave-one-out loss: **13.72 s**, **163.0%** of parallel+APC time.
L1+L2+L3a vs L1+L2: computed prefill **+0.8%**, median latency **+1.5%**.
L1+L2+L3 vs L1+L2: computed prefill **-7.7%**, median latency **+9.8%**.

| Configuration vs BASE | Accuracy delta (pp) | BASE-only / config-only correct | Answer agreement | Exact McNemar p | Quality warning |
|---|---:|---:|---:|---:|---|
| L1+L2 | +0.00 | 3/3 | 56/64 | 1.0000 | No numerical flag in this sample; not proof of non-inferiority |
| L1+L2+L3a | +1.56 | 2/3 | 59/64 | 1.0000 | No numerical flag in this sample; not proof of non-inferiority |
| L1+L2+L3 | +3.12 | 1/3 | 56/64 | 0.6250 | No numerical flag in this sample; not proof of non-inferiority |
| Parallel, APC off | +4.69 | 1/4 | 55/64 | 0.3750 | No numerical flag in this sample; not proof of non-inferiority |
seq: round-1 agents 2–3 cached share **99.9%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **0/192**.
par: round-1 agents 2–3 cached share **89.1%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **1/192**.
l3a: round-1 agents 2–3 cached share **99.9%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **0/192**.
l3: round-1 agents 2–3 cached share **99.9%**; final-agent calls at the 512-token cap **2/192**; final responses without boxed answers **4/192**.

### C=32 paired comparisons

Raw BASE-to-parallel latency ratio: **1.42×**, paired bootstrap 95% interval **[1.29, 1.61]** (4,000 resamples).
Caching leave-one-out loss: **24.33 s**, **169.8%** of parallel+APC time.
L1+L2+L3 vs L1+L2: computed prefill **-8.3%**, median latency **-3.9%**.

| Configuration vs BASE | Accuracy delta (pp) | BASE-only / config-only correct | Answer agreement | Exact McNemar p | Quality warning |
|---|---:|---:|---:|---:|---|
| L1+L2 | -1.56 | 4/3 | 56/64 | 1.0000 | No numerical flag in this sample; not proof of non-inferiority |
| L1+L2+L3 | +1.56 | 2/3 | 58/64 | 1.0000 | No numerical flag in this sample; not proof of non-inferiority |
| Parallel, APC off | -3.12 | 4/2 | 57/64 | 0.6875 | YES — do not claim quality preservation |
seq: round-1 agents 2–3 cached share **99.9%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **0/192**.
par: round-1 agents 2–3 cached share **90.5%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **0/192**.
l3: round-1 agents 2–3 cached share **99.9%**; final-agent calls at the 512-token cap **1/192**; final responses without boxed answers **2/192**.

Exact McNemar p-values are two-sided, exploratory and unadjusted for multiple comparisons. Non-significance does not override the numerical >2 pp accuracy-loss guardrail. The same problems across seeds remain repeated measurements, not independent new problems.

## Sampling seed 1

| C | Configuration | n | Median T (s) | p95 (s) | BASE/config latency ratio | Accuracy | Computed prefill/task | Mean answer tokens |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 16 | BASE | 64 | 13.59 | 19.59 | 1.00× | 68.75% | 7303 | 168.6 |
| 16 | L1+L2 | 64 | 8.11 | 12.27 | 1.67× | 75.00% | 7267 | 166.0 |

### C=16 paired comparisons

Raw BASE-to-parallel latency ratio: **1.67×**, paired bootstrap 95% interval **[1.59, 1.81]** (4,000 resamples).

| Configuration vs BASE | Accuracy delta (pp) | BASE-only / config-only correct | Answer agreement | Exact McNemar p | Quality warning |
|---|---:|---:|---:|---:|---|
| L1+L2 | +6.25 | 2/6 | 54/64 | 0.2891 | No numerical flag in this sample; not proof of non-inferiority |
seq: round-1 agents 2–3 cached share **99.9%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **0/192**.
par: round-1 agents 2–3 cached share **84.9%**; final-agent calls at the 512-token cap **1/192**; final responses without boxed answers **2/192**.

Exact McNemar p-values are two-sided, exploratory and unadjusted for multiple comparisons. Non-significance does not override the numerical >2 pp accuracy-loss guardrail. The same problems across seeds remain repeated measurements, not independent new problems.

## Sampling seed 2

| C | Configuration | n | Median T (s) | p95 (s) | BASE/config latency ratio | Accuracy | Computed prefill/task | Mean answer tokens |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 16 | BASE | 64 | 13.78 | 20.27 | 1.00× | 70.31% | 7326 | 171.5 |
| 16 | L1+L2 | 64 | 8.37 | 12.73 | 1.65× | 68.75% | 7310 | 169.6 |

### C=16 paired comparisons

Raw BASE-to-parallel latency ratio: **1.65×**, paired bootstrap 95% interval **[1.55, 1.78]** (4,000 resamples).

| Configuration vs BASE | Accuracy delta (pp) | BASE-only / config-only correct | Answer agreement | Exact McNemar p | Quality warning |
|---|---:|---:|---:|---:|---|
| L1+L2 | -1.56 | 3/2 | 57/64 | 1.0000 | No numerical flag in this sample; not proof of non-inferiority |
seq: round-1 agents 2–3 cached share **99.9%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **0/192**.
par: round-1 agents 2–3 cached share **93.8%**; final-agent calls at the 512-token cap **0/192**; final responses without boxed answers **1/192**.

Exact McNemar p-values are two-sided, exploratory and unadjusted for multiple comparisons. Non-significance does not override the numerical >2 pp accuracy-loss guardrail. The same problems across seeds remain repeated measurements, not independent new problems.

## First-round request/response audit

Compare recorded message hashes, sampling settings and request seeds for the same problem/agent, excluding warm-up requests. Exact response matching is stricter than final-answer matching. Matching here concerns API messages/parameters; tokenized prompt identity was not directly logged.

| Seed | C | Comparison | Identical recorded request tuples | Exact response matches | Parsed round-1 answer matches |
|---:|---:|---|---:|---:|---:|
| 0 | 1 | seq vs par | 192/192 | 53/192 | 177/192 |
| 0 | 16 | seq vs par | 192/192 | 58/192 | 179/192 |
| 0 | 16 | par vs l3a | 192/192 | 54/192 | 172/192 |
| 0 | 16 | par vs l3 | 192/192 | 52/192 | 169/192 |
| 0 | 32 | seq vs par | 192/192 | 65/192 | 165/192 |
| 0 | 32 | par vs l3 | 192/192 | 52/192 | 175/192 |
| 1 | 16 | seq vs par | 192/192 | 65/192 | 169/192 |
| 2 | 16 | seq vs par | 192/192 | 66/192 | 174/192 |

If identical recorded first-round request tuples yield different response text, divergence is already observable before any round-2 transcript rewrite. This does not identify the server-side cause; fixed seeds alone are insufficient evidence of identical answers. Later rounds can then legitimately have different inputs because their upstream answers differ. Every saved round-2 request was also checked against the expected construction of this harness using its own recorded upstream answers; this checks execution/history handling, not equivalence with the released Du et al. implementation. Full L3 intentionally changes round-2 messages and still requires its separate accuracy check.

## Aggregate round-1 prefill check

Normalize the sum of uncached round-1 tokens across all three agents (plus any round-1 warm-up) by one agent prompt length. This avoids assuming agent 1 is always the first prefiller under asynchronous dispatch. It is an API-token estimate, not a kernel execution trace.

| Seed | C | Configuration | Mean uncached round-1 prompt copies, warm-up included | Call reporting largest round-1 prefill |
|---:|---:|---|---:|---|
| 0 | 1 | BASE | 1.000 | agent 1: 64 |
| 0 | 1 | L1+L2 | 1.000 | agent 1: 61, agent 3: 3 |
| 0 | 16 | BASE | 1.000 | agent 1: 64 |
| 0 | 16 | L1+L2 | 1.000 | agent 1: 48, agent 2: 6, agent 3: 10 |
| 0 | 16 | L1+L2+L3a | 1.002 | warm-up: 64 |
| 0 | 16 | L1+L2+L3 | 1.002 | warm-up: 64 |
| 0 | 32 | BASE | 1.000 | agent 1: 64 |
| 0 | 32 | L1+L2 | 1.000 | agent 1: 52, agent 2: 8, agent 3: 4 |
| 0 | 32 | L1+L2+L3 | 1.002 | warm-up: 64 |
| 1 | 16 | BASE | 1.000 | agent 1: 64 |
| 1 | 16 | L1+L2 | 1.000 | agent 1: 44, agent 2: 11, agent 3: 9 |
| 2 | 16 | BASE | 1.000 | agent 1: 64 |
| 2 | 16 | L1+L2 | 1.000 | agent 1: 54, agent 2: 6, agent 3: 4 |

The observed parallel round-1 estimate is already about one prompt copy, not three. Warming the prefix raises the agents-2/3 cached share but does not reduce aggregate round-1 prefill below that one-copy requirement. Under parallel dispatch the first/largest prefill is not always attributed to agent 1, so agents-2/3 cache share alone cannot establish duplicate prefill. This weakens the round-1 premise for L3 on this stack; it does not establish the internal mechanism or behavior of other vLLM versions.

## Server-side diagnostic counters

Before/after Prometheus deltas cover the measured configuration plus its three short setup warm-up requests. Means are per server request, not a wall-clock decomposition of debate time. Local-compute tokens are the server-reported source counter; API prefill estimates above are prompt minus cached tokens and may omit internal recomputation when preemption occurs.

| Seed | C | Configuration | Completed server requests | Mean queue (ms) | Mean prefill (ms) | Mean decode (s) | Preemptions | Server local-compute tokens/debate, setup included |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | 1 | BASE | 387 | 0.01 | 37.13 | 1.106 | 0 | 7319 |
| 0 | 1 | L1+L2 | 387 | 0.01 | 64.27 | 1.136 | 0 | 7294 |
| 0 | 1 | Parallel, APC off | 387 | 0.21 | 256.77 | 1.280 | 0 | 36853 |
| 0 | 16 | BASE | 387 | 28.59 | 66.41 | 2.158 | 0 | 7298 |
| 0 | 16 | L1+L2 | 387 | 247.36 | 242.60 | 3.294 | 0 | 7266 |
| 0 | 16 | L1+L2+L3a | 451 | 106.04 | 99.30 | 2.530 | 0 | 7321 |
| 0 | 16 | L1+L2+L3 | 515 | 94.24 | 79.48 | 2.264 | 0 | 6704 |
| 0 | 16 | Parallel, APC off | 387 | 407.72 | 418.49 | 7.760 | 0 | 36923 |
| 0 | 32 | BASE | 387 | 149.94 | 94.32 | 3.026 | 0 | 7284 |
| 0 | 32 | L1+L2 | 387 | 537.25 | 240.69 | 5.253 | 0 | 7317 |
| 0 | 32 | L1+L2+L3 | 515 | 463.73 | 134.67 | 3.399 | 0 | 6711 |
| 0 | 32 | Parallel, APC off | 387 | 2547.53 | 409.08 | 12.906 | 4 | 36862 |
| 1 | 16 | BASE | 387 | 29.66 | 65.38 | 2.135 | 0 | 7304 |
| 1 | 16 | L1+L2 | 387 | 91.08 | 141.12 | 3.049 | 0 | 7268 |
| 2 | 16 | BASE | 387 | 26.16 | 66.70 | 2.171 | 0 | 7327 |
| 2 | 16 | L1+L2 | 387 | 80.61 | 138.49 | 3.113 | 0 | 7311 |

## Scope

No thresholds were changed. BASE remains sequential with prefix caching on; APC off is an ablation. L3a warms round 1 only in this harness; full L3 warms both rounds and changes round-2 inputs. Prefill estimates include warm-up requests and use prompt minus cached tokens. The released workflow, full sample sizes, formal multi-seed aggregation, and a 300-story sampling policy still need completion before preregistered claims. Metrics snapshots include the three short pre-measurement warm-up requests; do not interpret their aggregate counters as exact per-debate timing decomposition.
