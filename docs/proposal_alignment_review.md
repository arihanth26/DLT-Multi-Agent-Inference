# Proposal alignment review — 2026-11-06

Read against `proposal.pdf` (methods/evaluation on page 2 and preregistration on page 4),
the supplied instructor feedback, and the pilot implementation. This is an implementation
audit, not a revision of the preregistered thresholds.

## What is aligned and verified

- BASE is sequential debate with automatic prefix caching ON. APC OFF is an ablation,
  not the headline baseline. The pilot runs separate server processes for APC on/off,
  resets the prefix cache between configurations, and preserves vLLM's other optimizations.
- The pilot uses Llama-3.1-8B-Instruct, bf16, temperature 0.7, top-p 0.9, a 512-token
  output limit, per-request seeds, three agents and two rounds, on GSM8K and QuALITY.
- Job 6850879 completed on an NVIDIA H100 80GB HBM3 with vLLM 0.31.0 in 9m13s.
  All 18 smoke-test configurations produced two records each (36 total). Call counts,
  token counts and timings passed structural checks; APC-off cached-token counts were zero.
- Results are exploratory infrastructure checks, not evidence that preregistered rules pass.

## Gates before preregistered experiments

1. **Released workflow.** `pilot/debate.py` approximates Du et al.'s prompts. Wrap and pin
   the released implementation, with a documented QuALITY adaptation, before calling it
   the preregistered baseline. Resolve this with the harness owner before duplicating work.
2. **L3 input validation.** The proposal explicitly says full L3 changes round-2 prompts.
   It must not be described as preserving effective inputs. L3a isolates cache warming
   from transcript rewriting. Compare serialized/tokenized requests for fixed recorded
   upstream answers; live round-2 inputs may differ because earlier sampled answers differ.
   Same request seeds alone do not establish identical outputs. Record per-agent responses,
   request hashes, sampling settings and finish reasons. The original pilot traces omit
   these; the recorded load extension now retains messages, responses, hashes, seeds and
   sampling settings. Per-call finish reasons and rendered token IDs remain missing.
3. **Warm-up fidelity.** The pilot implements a warm-up with one generated token, not
   literally zero decode. Include its time and tokens in L3 cost. L3a currently warms
   round 1 only, despite its README claiming every round. Verify the actually reusable
   token prefix after chat templating, including round-2 boundaries for full L3.
4. **Accuracy guardrail.** Implement paired McNemar tests and the >2.0 percentage-point
   regression rule on the same problems/seeds. The pilot prints discordant counts but
   no test. Non-significance alone does not establish non-inferiority. Two examples cannot
   validate a quality guardrail; retain final-answer agreement and answer-length reporting.
5. **Metrics.** Capture vLLM queue, prefill, decode, and KV/cache measurements; client
   TTFT alone cannot separate queueing from prefill. The pilot's T ends before answer parsing
   and majority voting, whereas preregistration ends when the final answer is recorded.
   The p95 computation was corrected during this review to use nearest rank (the old
   index could be below the median for two rows). Still needed:
   calculate the factorial interaction, and define aggregation across seeds in advance.
   Treat the measured critical-path ratio as descriptive: service times/cache states and
   sampled output lengths can change with dispatch, so it is not a universal speedup bound.
   The follow-up load extension captures phase-level Prometheus deltas for queue, prefill,
   decode and preemptions; these are supporting per-request means, not a full per-call
   critical-path decomposition. Seeded/batch-shape first-use JIT warnings remain in the logs.
6. **Scale and data.** Run 100 problems per task with seeds 0,1,2 at C=1, then the
   preregistered 300-problem load grid at C=4,16,32, with bootstrap intervals. The smoke
   test's C=4 setting with only two problems reaches at most two simultaneous debates.
   QuALITY's one-question-per-story policy cannot supply 300 distinct stories from the
   available 115 validation plus 150 train stories. Decide and log the sampling/cache
   policy before full runs. Label pilot measurements already seen as exploratory.
7. **Documentation and provenance.** Root README, shared sampling defaults, serving
   documentation and older SLURM examples still describe the earlier Qwen/two-model
   design and APC-off baseline. Align these before team-wide runs. Record model revision,
   dataset selections, source commit, local modifications, dependencies and hardware.

## Interpretation of the smoke test

Round-1 cached-token shares for parallel agents 2–3 were already about 95% on GSM8K and
100% on QuALITY. This weakens the assumption that concurrent round-1 requests necessarily
repeat the entire prefill on this stack; it does not establish how the server achieves reuse.
Full L3 was slower at C=1 on these two examples. Preserve these observations and test the
registered C=16 hypothesis; do not change thresholds in response to pilot outcomes.

## Next action

A larger run of the existing pilot is appropriate for exploratory timing and infrastructure
validation. It is not a preregistered result. Prioritize released-workflow integration and
input/accuracy validation before spending the full experiment budget.

## Follow-up load evidence, Nov 6 evening

The 64-story QuALITY extension completed 1,024 debate runs in 16 groups, including C=1,
C=16, C=32 and three sampling seeds for BASE/parallel at C=16. See
`results/pilot/pilot_6847083_extension_report.md`. Raw requests verify the expected prompt
construction of this harness, but not equivalence with the released implementation.

The round-1 API estimate across all agents is already about one prompt copy under parallel
dispatch. The agent reporting the largest prefill varies, so agents-2/3 cache share alone
does not establish duplicate prefill. At C=16 full L3 reduced estimated prefill by 7.7% but
increased median latency by 9.8% relative to L1+L2. This is exploratory evidence against the
proposed benefit for the current implementation, not a reason to revise thresholds.
