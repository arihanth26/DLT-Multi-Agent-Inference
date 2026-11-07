# Milestone Check-in: Multi-Agent Inference Optimizations: Parallel Dispatch and Prefix Caching

CSE 8803, Fall 2026. Team: Tanishk Deo, Arihanth Jayavijayan, Malhar Jadhav. Submitted Nov 7 (the due date was Oct 29).

**Progress.**
- **Serving stack.** vLLM 0.31.0 (pinned) serves Llama-3.1-8B-Instruct in bf16 on one H100 80GB HBM3 in PACE-ICE's `ice-gpu` partition. H100 availability is confirmed.
- **End-to-end harness.** A 3-agent, 2-round debate on GSM8K and QuALITY, with:
  - a per-call tracer recording times, prompt, cached and output tokens, request hashes, seeds and responses;
  - vLLM Prometheus counters for queue, prefill, decode and preemptions;
  - a closed-loop load generator;
  - paired bootstrap and McNemar analysis.
- **TA feedback, keeping caching separate from the baseline.** BASE is the released sequential order with prefix caching (APC) **on**. APC off is an ablation. Each configuration runs on its own server process and starts with an empty prefix cache.
- **TA feedback, L3 inputs.** L3 is split into two configurations. **L3a** only adds a prefill warm-up, so prompts are unchanged. **L3** adds the shared round-2 transcript, so prompts change. Any change in inputs or quality can then be attributed separately.
- **Runs so far** (about 1.2 H100-hours):
  - a 430-debate grid at C=1 and C=4;
  - a 1,024-debate QuALITY load extension (64 stories; C=1, 16 and 32; seeds 0–2 at C=16);
  - an 80-debate repeat check.

**Preliminary results.** These are exploratory: the debate prompts approximate the released code, n is below the preregistered size, and the intervals are paired 95% bootstraps.

| | GSM8K C=1 (n=30) | QuALITY C=1 (n=64) | QuALITY C=16 | QuALITY C=32 |
|---|---|---|---|---|
| BASE median time per debate | 5.40 s | 7.13 s | 13.76 s | 20.38 s |
| L1 speedup (BASE / L1+L2) | 2.19× [1.96, 2.46] | 2.36× [2.18, 2.59] | 1.63× [1.45, 1.79] | 1.42× [1.29, 1.61] |
| L2 leave-one-out loss | 0.4% | 0.77 s (26%) | 13.7 s (163%) | 24.3 s (170%) |
| L3 vs L1+L2: prefill / median time | −38% / +26% | −8% / +13% (n=20) | −8% / +10% | −8% / −4% |

- **H1 and H3 point the predicted way.**
  - L1 clears 1.5× at C=1. At C=32 its gain is 31% of its C=1 value, below the preregistered 50%.
  - Caching barely matters on GSM8K but grows with context length and load on QuALITY.
- **H4 is not supported so far.**
  - vLLM 0.31 already computes the shared round-1 prompt about once per debate under parallel dispatch, so a warm-up request adds nothing.
  - The shared transcript cuts prefill, but answers get longer, so latency rises.
  - The 30% / 10% targets are not met.
- **Quality is noisy.**
  - Identical requests with fixed seeds returned identical round-1 text in only 53 of 192 cases.
  - BASE accuracy on the same 20 stories ranged from 65% to 80% across repeats.
  - At C=4, parallel was below BASE in all three repeats (−5, −10, −25 pp; none significant).
  - On 64 stories at C=16, the differences were 0, +6.3 and −1.6 pp across seeds 0–2.
  - At this n, the 2 pp guardrail is smaller than run-to-run noise.
- **Compute.** A BASE debate costs 5–7 s, not the 14 s assumed in the proposal, so the compute need drops from about 50 to about 25 H100-hours.

**Blockers.**
1. The prompts approximate Du et al.; the released code still has to be wrapped.
2. Sampling is not reproducible at fixed seeds, and that noise is larger than the 2 pp guardrail.
3. QuALITY has only 265 distinct stories (115 validation + 150 train), fewer than the 300 needed under load.
4. `ice-gpu` H100 queue waits reach about 12 hours, and storage quota limits are tight.
5. The repository scaffold followed an earlier draft (Qwen models, APC-off baseline); it is being aligned with the approved proposal.

**Revised plan.** Preregistered thresholds are unchanged. Each revision below is logged with its date and reason.

| Dates | Plan |
|---|---|
| Nov 7–11 | Wrap the released debate code. Log token IDs and finish reasons. Run the fixed-upstream replay test for L3. Log revisions: QuALITY sampling under load, how accuracy is pooled across seeds for the guardrail plus a BASE-vs-BASE noise floor, and that L3a warms round 1 only. |
| Nov 12–18 | C=1 headline: 100 problems × 2 tasks × 3 seeds × 7 configurations (about 6 H100-hours). |
| Nov 19–25 | Load sweep at C = 4, 16, 32 with 300 problems (about 4 h). KV-memory sweep. Rounds sweep if time allows. Analysis. |
| Nov 26–Dec 2 | Thanksgiving buffer and reruns. Stretch goals dropped unless ahead of schedule. |
| Dec 3 | Report, video, rerunnable repository. |
