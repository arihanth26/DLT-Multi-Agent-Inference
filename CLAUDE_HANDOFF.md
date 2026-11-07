# Handoff for Claude: PACE-ICE pilot, results, and remaining work

Prepared November 7, 2026, America/New_York. Experiments described below ran on
November 6. This document summarizes the Codex session and the current local workspace.
It supersedes historical status statements in `docs/handoff.md`, not the proposal or
preregistration. No formal performance threshold was changed.

## 1. Current state in one page

- The environment works: Llama-3.1-8B-Instruct bf16 on one H100 80 GB, vLLM 0.31.0.
  There was **one model/server at a time**, not two models sharing GPU memory.
- Download quota failure was resolved. The actual issue was that `~/scratch` was an
  ordinary directory on the 30 GB **home** filesystem. HF data was moved to real scratch.
- Locally available, validated substantive experiments: **430 original pilot runs +
  80 accuracy-repeat runs + 1,024 load-extension runs = 1,534 debate runs**. There are
  also 36 validated smoke-test runs. These are repeated problem/configuration/seed
  exposures, not 1,570 independent questions.
- All results are **exploratory**. The harness approximates the released Du et al.
  workflow; it does not yet satisfy the preregistered implementation and sample sizes.
- Parallel dispatch helped latency; its benefit diminished under load. Prefix caching
  became much more valuable under load on QuALITY. Full L3 missed its C=16 targets.
- Quality preservation is **not established**. Retain the earlier C=4 accuracy warnings.
  Larger C=16 runs are more encouraging, but fixed seeds did not ensure identical answers.
- One final, separate **20-story C=1 three-seed check** was launched as step `6847083.5`.
  SSH disconnected during retrieval. Its final status/data are **not verified or included**
  in the totals above. Recover this first; it should not require a new GPU allocation.
- Code changes and result files from this session remain uncommitted. This agent did
  not push a branch, open a PR, submit a milestone, or send messages to teammates.

## 2. Read these files, in this order

1. [proposal.pdf](proposal.pdf): approved methods on page 2; preregistration on page 4.
2. [Proposal alignment review](docs/proposal_alignment_review.md): code/proposal gaps,
   instructor-feedback interpretation, and follow-up evidence.
3. [Results overview](results/pilot/extended_results_2026-11-06.md).
4. [Original pilot report](results/pilot/pilot_6847083_initial_report.md): both tasks,
   C=1 and QuALITY C=4, paired accuracy checks and bootstrap intervals.
5. [Accuracy-repeat report](results/pilot/pilot_6847083_repeat_report.md).
6. [Load-extension report](results/pilot/pilot_6847083_extension_report.md): 64-story
   C=1/16/32 comparisons, three seeds at C=16, request audit and server counters.
7. `pilot/debate.py`, `pilot/summarize.py`, `models/client.py`,
   `models/model_config.py`, `models/serve_vllm.py`, `slurm/pilot.sbatch`.
8. [Historical handoff](docs/handoff.md) and [milestone draft](docs/milestone_report.md),
   subject to the cautions in section 11 below.

Archives:

- `results/initial_results_2026-11-06.zip`: original pilot and repeat investigation.
- `results/extended_results_2026-11-06.zip`: combined results available when final SSH
  retrieval failed; about 52 MB. Includes the original results and the 1,024-run extension.
  **It does not contain the final C=1 check or this new handoff.**
- `results/extended_results_2026-11-06/` appears to be an extracted duplicate. The
  working artifacts under `results/pilot/` are the source used for the reports here.

## 3. Approved design and instructor feedback

The approved proposal specifies three agents, two rounds and majority voting, on GSM8K
and QuALITY. Stories come first in QuALITY user prompts. Serving is pinned vLLM with
default optimizations, Llama-3.1-8B-Instruct bf16 on one H100 80 GB, temperature 0.7,
top-p 0.9, at most 512 output tokens, and a seed per request. Llama-3.2-1B is for separate
development runs on smaller GPUs. **Neither the proposal nor feedback calls for two
simultaneously served models or a GPU-memory split.**

Configuration meanings:

| Configuration | Dispatch | Automatic prefix caching | Prompt construction |
|---|---|---|---|
| BASE | Sequential | ON | Pilot approximation of released workflow |
| Neither lever | Sequential | OFF | Same construction |
| L1 only | Parallel per round | OFF | Same construction |
| L1+L2 | Parallel per round | ON | Same construction |
| L1+L2+L3a | Parallel plus warm-up | ON | Same construction given the same upstream answers |
| L1+L2+L3 | Parallel plus warm-up | ON | Shared round-2 transcript; intentionally changed inputs |
| Single agent | One call | ON | Round 1 only |

APC on/off use separate server processes. Modes within an APC setting share that server
but reset its prefix cache before each configuration. This distinction matters: the
milestone draft's wording about a separate process for every configuration is too strong.

Instructor concerns were: distinguish caching ablations from the optimized baseline;
validate effective inputs and answer quality for shared-prefix prefill; confirm H100
availability. The experiments confirmed the H100 and used the correct APC-on baseline.
L3a is a control for warming; full L3 cannot be described as preserving round-2 inputs.

Preregistered requirements still outstanding include 100 problems per task at C=1 with
seeds 0,1,2; 300 under load; C in {1,4,16,32}; rounds and KV-memory sweeps. Decision rules:

1. C=1 L1 latency ratio at least 1.5, bootstrap lower bound above 1.2.
2. C=32 add-one gain less than half its C=1 value.
3. QuALITY caching leave-one-out loss at C=16 at least twice C=1 and at least 10% of
   both-lever latency; GSM8K C=1 below 5%.
4. QuALITY L3 at C=16: at least 30% less computed prefill and 10% lower median latency.
5. More than 2.0 percentage points of accuracy loss, or significantly lower paired
   accuracy, is a quality regression rather than a quality-preserving speedup.

The proposal is authoritative. Root README, older project-plan text, serving docstrings,
shared sampling defaults and old SLURM examples still contain the earlier Qwen/two-model,
APC-off-baseline design. The pilot overrides those defaults explicitly. Align that
documentation before team-wide formal experiments.

## 4. Environment, access, quota and provenance

Local repository: `/Users/tanishk/Desktop/dlt/proj`.

| ICE path | Purpose |
|---|---|
| `/home/hice1/tdeo7/scratch/dlt-proj` | Remote repository and experiment outputs |
| `/home/hice1/tdeo7/scratch/dlt-venv` | Python 3.10 virtual environment |
| `/home/hice1/tdeo7/scratch/hf` | HF_HOME symlink |
| `/storage/ice1/9/1/tdeo7/dlt/hf` | Actual HF storage on 300 GB scratch allocation |

The quota diagnostic showed home at 26.1/30 GB and actual scratch almost empty.
`readlink -f "$HOME/scratch"` returned the home directory path. Moving only HF data to
actual scratch and symlinking the old HF path allowed the download to complete. Xet was
only 408 KB, so the earlier handoff's claim that an Xet cache caused the quota error was
not supported by the observed usage. Do not repeat setup/download unnecessarily.

Model snapshot recorded for the runs:
`0e9e39f249a16976918f6564b8830bc894c89659`.
The dependency freeze is `results/pilot/pilot_6847083_initial_packages.txt`.

Smoke hardware: H100 80GB HBM3 on `atl1-1-03-012-23-0`.
Main/repeat/extension hardware: H100 80GB HBM3 on `atl1-1-03-013-3-0`, UUID
`GPU-50c84c8a-1aba-88d3-ac48-894395fcf825`, driver 615.71.09.
Smoke requested 8 CPUs / 64 GB RAM; the reused VS Code allocation had 4 CPUs / 80 GB RAM.
Keep smoke and substantive-run timings separate.

vLLM used a 0.90 GPU-memory target and a 32,768-token context limit. Smoke logs reported
about 15 GiB of weights and 53.52 GiB available for KV cache. Runtime/graphs consume part
of the remaining target; these are not two-model allocations.

SSH destination: `tdeo7@login-ice.pace.gatech.edu`. The user authenticated in their Mac
terminal, and Codex reused a multiplexed connection at `/tmp/dlt-pace-ssh`. That connection
later broke. No current working connection is assumed. Passwords were never requested
in chat. Terminal UI access was blocked by the computer-use tool; shell SSH was used.

If fresh authentication is needed, the user can run locally:

```bash
ssh -M -S /tmp/dlt-pace-ssh -o ControlPersist=3h -fN \
  tdeo7@login-ice.pace.gatech.edu
```

Then an agent can use `ssh -S /tmp/dlt-pace-ssh -o BatchMode=yes ...`. Use a login shell
for Slurm commands: plain non-login SSH returned `squeue: command not found`, whereas
`bash -lc` worked. VPN/network and authentication must be verified afresh.

Account/QoS observed: `coc` / `coc-ice`; jobs ran in `ice-gpu`; GPU request was lowercase
`--gres=gpu:h100:1`. Cluster inventory and queue estimates in the older handoff are
historical. Query current state rather than assuming the same availability or exclusions.

## 5. Exact experiment history

| Job/step | Experiment | Verified outcome |
|---|---|---|
| `6850879` | Smoke, 2 GSM8K / 2 QuALITY per configuration | COMPLETED, 9m13s, exit 0:0; 36 records / 18 groups |
| `6850988` | Queued default pilot | Canceled before starting after an idle existing H100 was found |
| `6847083.1` | Original full pilot | COMPLETED, 29m27s, exit 0:0; 430 records / 18 groups |
| `6847083.2` | Two same-seed C=4 quality repeats | COMPLETED, 3m45s, exit 0:0; 80 additional records |
| `6847083.4` | Recorded QuALITY load extension | COMPLETED, 30m28s, exit 0:0; 1,024 records / 16 groups |
| `6847083.5` | Fresh 20-story C=1, seeds 0,1,2, BASE/parallel | Launched; final status and retrieval unverified |

Non-experiment step numbers were consumed by GPU diagnostics. Parent `6847083` was a
pre-existing VS Code allocation, not created by this agent. Its GPU was verified idle
before reuse. We ran `srun --jobid=6847083 --overlap --nodes=1 --ntasks=1
--cpus-per-task=4 --gres=gpu:h100:1 ...` inside it. A second GPU was not allocated.
The allocation's scheduled end was November 6 at 20:13:26 Eastern. It should not be
treated as active now; query accounting. Parent timeout does not establish failure of
an experiment step that completed earlier.

Original pilot: 30 GSM8K and 20 QuALITY problems, seed 0. C=1 had seven configurations
on each task; C=4 had QuALITY BASE, parallel/APC on, full L3, and parallel/APC off.
Counts: 7×30 + 7×20 + 4×20 = 430.

Extension: 64 distinct QuALITY validation stories, one question per story, problem seed 0.
Sampling seed 0 had C=1 BASE/parallel-on/parallel-off; C=16 BASE/parallel-on/L3a/L3/
parallel-off; C=32 BASE/parallel-on/L3/parallel-off. Seeds 1 and 2 added BASE/parallel-on
at C=16. Thus 12 seed-0 groups + 4 additional groups, each with 64 problems.

Per-file stems under `results/pilot/`:

- Smoke: `pilot_6850879`.
- Original: `pilot_6847083_initial`.
- Repeats: `pilot_6847083_repeat1`, `pilot_6847083_repeat2`, and `..._repeat_report.md`.
- Extension: `pilot_6847083_extension`.

Original and repeat traces have timings/token counts/final answers but **not** full
request/response text. The extension was run with `--record-inputs` and includes those
fields. Do not claim that recorded-input checks were applied retroactively to old traces.

## 6. Main results and what they mean

Original GSM8K C=1, n=30: BASE median 5.40s, parallel+APC 2.47s, ratio 2.19×,
paired bootstrap interval [1.96,2.46]. Accuracy 27/30 versus 28/30. Caching's leave-one-out
loss under parallel dispatch was about 0.4%. Full L3 was slower than L1+L2.

Recorded QuALITY extension, seed 0, n=64 per row:

| C | BASE median | Parallel+APC median | Latency ratio | BASE accuracy | Parallel accuracy |
|---|---:|---:|---:|---:|---:|
| 1 | 7.13s | 3.02s | 2.36× [2.18,2.59] | 41/64 | 45/64 |
| 16 | 13.76s | 8.42s | 1.63× [1.45,1.79] | 45/64 | 45/64 |
| 32 | 20.38s | 14.33s | 1.42× [1.29,1.61] | 47/64 | 46/64 |

Caching-off parallel medians were 3.80s, 22.14s and 38.66s at C=1,16,32, respectively.
Leave-one-out losses were 0.77s (25.5%), 13.72s (163.0%) and 24.33s (169.8%) relative
to parallel+APC. Four preemptions appeared at C=32/APC off; all caching-on groups had zero.

Full L3 versus L1+L2:

- C=16: estimated prefill −7.7%, median latency **+9.8%**, accuracy 47/64 vs 45/64.
- C=32: estimated prefill −8.3%, median latency **−3.9%**, accuracy 48/64 vs 46/64.
- C=16 L3a: prefill +0.8%, latency +1.5%, accuracy 46/64.

The current L3 implementation does not meet its proposed C=16 targets in this pilot.
Do not generalize this to every prefill scheme or rescue the claim by selecting p95
instead of the preregistered median headline. Answer lengths differ and must be reported.

C=16 BASE/parallel latency ratios across seeds 0,1,2 were 1.63×, 1.67×, 1.65×.
Their accuracy differences were 0, +6.25, −1.56 percentage points. No numerical >2 pp
loss flag occurred for parallel+APC in those three 64-story comparisons. This is not
proof of non-inferiority and does not erase the earlier C=4 warnings.

## 7. Quality warnings and input audit

QuALITY C=4 on the original 20-story sample:

| Run | BASE correct | Parallel+APC correct | Difference | Exact McNemar p |
|---|---:|---:|---:|---:|
| Original | 16/20 | 14/20 | −10 pp | 0.6250 |
| Repeat 1 | 16/20 | 11/20 | −25 pp | 0.0625 |
| Repeat 2 | 13/20 | 12/20 | −5 pp | 1.0000 |

These cross the numerical loss threshold, despite non-significant paired tests. Do not
describe them as quality-preserving speedups, pool repeated problems as independent,
pick a favorable repeat as BASE, or explain away the losses as proven batching noise.
The cause of the response variability has not been established.

In the extension, C=32/APC-off accuracy also crossed the numerical loss threshold
(45/64 vs BASE 47/64, −3.125 pp). Full tables show other configurations and agreement.

Recorded-input evidence is stronger than assuming fixed seeds imply identical outputs:

- C=1 BASE vs parallel: all 192 first-round message-hash/seed/sampling tuples matched,
  but only 53 response texts and 177 parsed first-round answers matched.
- Round-2 requests were reconstructed from each debate's own recorded round-1 outputs
  and checked against the current harness's construction rules. Hashes, sampling settings,
  seeds, parsing and majority votes passed validation on all 1,024 extension records.
- This checks the executed pilot's history handling, **not** equivalence with Du et al.'s
  released code. Full L3 intentionally changes round-2 inputs. L3a preserves construction
  conditional on the same upstream responses; live round-2 messages can differ when
  round-1 responses differ. Exact final-answer identity is not guaranteed by fixed seeds.

Aggregate round-1 prefill estimate: sum `(prompt-cached)` across all agents, plus any
warm-up, divided by one agent's prompt length. Parallel was already about **1.000 prompt
copy** at C=1/16/32. Warmed modes were about 1.002. Agent 1 was not always the largest
prefiller (at C=16 parallel: agent 1 on 48 stories, agent 2 on 6, agent 3 on 10).
Therefore agents-2/3 cached share alone can misleadingly suggest duplicate prefill.
This weakens H4's round-1 premise on this stack; it is an API estimate, not a kernel trace.

## 8. Code changes and validation performed

Current uncommitted implementation changes:

| File | Change |
|---|---|
| `pilot/debate.py` | Added optional `--record-inputs` / `record_inputs=False`. Saves copied messages, SHA256 hashes, response text, request seed and sampling settings per call. |
| `tests/test_pilot_recording.py` | Deterministic fake client checks recording leaves requests/predictions unchanged in seq/par/l3a/l3/single and keeps round-1 snapshots immutable. |
| `pilot/summarize.py` | Fixed p95 to nearest rank: `ceil(0.95*n)-1`. Old formula could put p95 below median at n=2. |
| `slurm/pilot.sbatch` | Counts failed configurations, fails on summary failure and returns nonzero if any configuration failed; no misleading final success marker. |
| `docs/handoff.md` | Added historical follow-ups; it still contains old text below them. |
| `docs/proposal_alignment_review.md` | Added methods/feedback audit and follow-up instrumentation/results. |

Tests: original 15 passed on ICE; after recording change **16 passed in 1.40s** on ICE.
Shell scripts passed `bash -n`; `git diff --check` passed. p95 was checked against two-row
and 100-row examples. Raw result validations covered counts, unique IDs within groups,
matched problem sets, call counts, token bounds, timing order and zero APC-off cached tokens.
Extension checks additionally covered hashes, seeds/settings, history construction and votes.

Source provenance: recorded ICE run base was `7fa8afe5aad46dc08649e5be8b6e6d75a4a3312d`
plus saved dirty patches. Current local branch is `pilot-initial-results`; at handoff
creation local HEAD is `1e52fb8` (milestone draft), with `0fcbfc8` (older handoff) and
`932e374` (vLLM pin) above the pilot commit. Do not label historical runs with current HEAD.
Inspect `git status` before editing; other commits/files appeared outside this agent's work.
The existing `.DS_Store` files, `proposal.pdf`, and extracted result folder were not removed.

## 9. Analysis/reproduction pitfalls

**Do not run `pilot.summarize` directly on a multi-seed extension JSONL.** Its grouping
key omits seed and paired-ID dictionaries can overwrite repeated IDs. The extension driver
filtered seed 0 for its generic `_summary.md`; the dedicated analysis groups by seed.

From repository root:

```bash
python3 results/pilot/pilot_6847083_extension_analysis.py \
  results/pilot/pilot_6847083_extension.jsonl
```

The supplied script was checked for Python 3.10 syntax. It regenerates the extension report
and asserts data consistency. It relies on current pilot prompt/parsing functions; if those
are changed, use the archived `..._extension_debate_source.py` / source patch to audit
historical data. Never rewrite old traces to make a changed validator pass.

Other important limits:

- Original pilot reports used 4,000 paired problem bootstrap resamples for interpreted
  intervals. Generic summaries use 2,000 and only print a lower bound. Results may differ
  slightly; state which analysis generated a number.
- Bootstraps at load do not model within-run queue dependence. C=32 has only two waves
  of 32 debates; startup/drain and first-use JIT effects can be substantial.
- API prefill is `prompt-cached`, warm-up requests included. Server `local_compute`
  counters are supporting evidence, not an exact kernel-level recomputation trace.
- Prometheus before/after snapshots include three short setup warm-up requests per
  configuration. Their request counts matched the expected measured calls plus three.
  Queue/prefill/decode means are per server request, not additive debate-wall-time components.
- Per-call finish reasons and rendered token IDs remain missing. Hitting 512 tokens is
  only a cap-hit proxy. Raw responses permit checking answer-format/parsing failures.
- Warm-up uses **one generated token**, not literally zero decode. L3a warms round 1
  only; full L3 warms both rounds. Some older docs incorrectly claim L3a warms every round.
- Timing ends before parsing/voting in the current harness. Align it with the proposal's
  final-answer-recorded endpoint before formal runs.
- Three short unseeded warm-up calls do not guarantee seeded/batch-shape kernels are warm.
  Inference-time JIT warnings were retained; no cold observations were trimmed afterward.
- Initial/extension reports contain manually written interpretation as well as computed
  tables. Preserve earlier reports when regenerating analyses.
- `slurm/pilot.sbatch` still has broad `pkill -f` cleanup. The newer one-off drivers use
  tracked server PIDs. Make cleanup job/process-scoped before concurrent same-node runs.

## 10. First recovery task: final C=1 seed run

Expected output stem on ICE: `results/pilot/pilot_6847083_c1_seeds`.
Driver: `results/pilot/pilot_6847083_c1_seeds.sh`.
Log: `logs/pilot_6847083_c1_seeds.out`.
Server log: `logs/pilot_6847083_c1_seeds_server.log`.
Slurm step: **6847083.5**. Expected full output: **120 records**, six groups of 20
(seq/par × seeds 0,1,2), same original 20 stories, C=1/APC on, recorded inputs.

Last successful read showed 82 records at 20:04:58 Eastern: seed 0 BASE 13/20 vs parallel
14/20; seed 1 BASE 13/20 vs parallel 15/20; seed 2 baseline had started. These were interim
log readings, not a fully retrieved/validated result. Retrieval at about 20:12 failed with
`mux_client_request_session ... Broken pipe`. Do not infer completion from the deadlines.

The driver has a hard November 6 20:10 Eastern deadline; the parent allocation ended at
20:13. These are **historical scripts with a fixed date/output path**, not fresh run recipes.
The driver and analysis helper have now been preserved locally from `/tmp`:

- `results/pilot/pilot_6847083_c1_seeds.sh`
- `results/pilot/pilot_6847083_c1_seeds_analysis.py`

After authenticating, read status/files without requesting a new GPU:

```bash
ssh -S /tmp/dlt-pace-ssh -o BatchMode=yes -o ConnectTimeout=15 \
  tdeo7@login-ice.pace.gatech.edu 'bash -l -s' <<'REMOTE'
cd "$HOME/scratch/dlt-proj" || exit 1
sacct -S 2026-11-06 -j 6847083 --format=JobID,State,Elapsed,ExitCode
tail -80 logs/pilot_6847083_c1_seeds.out
wc -l results/pilot/pilot_6847083_c1_seeds.jsonl
REMOTE
```

Download to temporary files first, so a failed connection cannot overwrite verified local
artifacts. Retrieve the JSONL, driver and both logs; verify actual group counts/IDs/seeds.
If partial, preserve it and report only completed pairs. The helper can analyze a retrieved
file, but completion of all six groups must be checked explicitly:

```bash
python3 results/pilot/pilot_6847083_c1_seeds_analysis.py /tmp/pilot_6847083_c1_seeds.jsonl
```

Then move verified data/reports into `results/pilot/`, update the overview/handoff, rebuild
checksums and the archive, and sync final reports to ICE if access works. Do not count this
run or claim the final seed's accuracy until verification. Local archive integrity was
verified; only the earlier small initial-results archive was also verified byte-for-byte
against ICE. The final extended archive was built locally after the disconnect.

## 11. Next research work and draft-report cautions

Before formal runs:

1. Wrap and pin the **released Du et al. implementation**, including documented QuALITY
   adaptation. Check with Arihanth (harness/L1) and Malhar (load generator) about existing
   work before duplicating it. This agent sent no teammate messages.
2. Capture tokenized/rendered inputs and per-call finish reasons. Run fixed-upstream replay
   checks for the warm-up control; separately test full L3's accuracy. Investigate observed
   same-seed variability without assuming the backend cause has been proved.
3. Specify warm-up, timing endpoints, seed aggregation, BASE-vs-BASE variability analysis
   and quality reporting before collecting formal data. Keep preregistered thresholds intact;
   log any design revision with date/reason and disclose pilots already observed.
4. Resolve QuALITY sampling: validation has 115 distinct stories, train 150. Combining
   them gives only 265, **still fewer than 300**. Reusing questions per story can create
   cross-problem cache hits; any policy must be explicit and consistently controlled.
5. Align stale root documentation/configuration, then do the full sample-size runs. Rounds
   and reduced-KV sweeps have not been performed. Prioritize headline results before stretches.

`docs/milestone_report.md` was present in current HEAD when this handoff was written.
Its author/submission status was not verified by this agent. Review especially:

- "Submitted Nov 7" is not evidence that this agent submitted anything.
- Modes share a server per APC setting; they do not each get a separate process.
- H1/H3 numbers point in the predicted direction, but no formal preregistered acceptance
  has been established with these sample sizes and approximate prompts.
- "About once" round-1 prefill is based on API/counter estimates, not a kernel trace.
- Reducing the entire compute budget from 50 to 25 H100-hours is an extrapolation, not a
  validated estimate for the complete matrix, retries, context/load, rounds and memory sweeps.
- Old queue/storage statements need current checks. The HF quota blocker was resolved.

The deadline in the proposal is December 3. Preserve negative and quality-warning results;
the project is a controlled measurement study, not a requirement to make L3 look beneficial.

## 12. What remains deliberately unclaimed

No verified final C=1 seed-2 result; no validated released-code baseline; no full 100/300
problem evaluation; no proof of 2 pp non-inferiority; no bitwise/token-level reproducibility
guarantee; no complete queue/prefill/decode/barrier wall-clock decomposition; no rounds or
KV-memory sweep; no verified current GPU allocation; no push/PR/submission by this agent.

Use saved raw evidence and current repository/account state to resolve these, rather than
the older conversational promises or historical handoff wording.
