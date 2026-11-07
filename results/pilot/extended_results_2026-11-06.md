# Extended initial results — 2026-11-06

Completed and validated: 1,024 additional QuALITY debate runs on 64 distinct stories in 16 configurations. The main load extension finished successfully in 30m28s. All configurations use one Llama-3.1-8B-Instruct model in bf16 on one H100 80 GB, vLLM 0.31.0, four CPUs, temperature 0.7, top-p 0.9, maximum 512 output tokens. These remain exploratory results from an approximate debate harness.

| Concurrent debates | BASE median | Parallel + caching median | Latency ratio |
|---:|---:|---:|---:|
| 1 | 7.13 s | 3.02 s | 2.36× |
| 16 | 13.76 s | 8.42 s | 1.63× |
| 32 | 20.38 s | 14.33 s | 1.42× |

- Disabling caching added 0.77 s, 13.72 s and 24.33 s to median parallel latency at C=1,16,32. Four preemptions were reported at C=32 with caching off; all caching-on groups reported zero.
- At C=16, full L3 reduced the prefill estimate by 7.7% but increased median latency by 9.8%. It does not meet the proposed targets in this pilot. At C=32 it reduced median latency by 3.9% in the short two-wave run.
- Parallel round-1 aggregate uncached-token estimates were already about one prompt copy per debate, rather than three. The agent reporting the largest prefill varied, so agents-2/3 cache share alone was misleading.
- The C=16 BASE/parallel latency ratio remained 1.63–1.67× across seeds 0,1,2. Parallel accuracy changes were 0, +6.25 and -1.56 pp. This does not prove non-inferiority or erase earlier C=4 warnings.
- All 192 first-round recorded request tuples matched between BASE and parallel at C=1, but only 53 response texts and 177 parsed answers matched. Fixed seeds alone did not ensure identical answers. Recorded round-2 construction, hashes, parsing and votes were validated.

Read `pilot_6847083_extension_report.md` for full tables, paired bootstrap intervals, accuracy checks, request audits and server diagnostic counters. Raw requests/responses and before/after Prometheus snapshots are included. The redundant derived `_seed0.jsonl` is omitted from the archive; the complete multi-seed JSONL is authoritative. Run the supplied extension analysis script from the repository root to regenerate the report without pooling seeds.

A separate 20-story, three-seed C=1 check was launched afterward as step 6847083.5. The shared SSH connection dropped during final retrieval. Its completion and final results have NOT been verified and are not included in these totals. Its driver has a 20:10 Eastern deadline, and the parent allocation ends at 20:13. The original 430-run pilot and 80-repeat accuracy check remain preserved separately.

The sample sizes, approximate workflow, short load windows, unrecorded rendered token IDs/per-call finish reasons, and first-use compilation remain limitations. No preregistered threshold was changed or claimed formally established.
