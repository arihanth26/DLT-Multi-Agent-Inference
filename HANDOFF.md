# Handoff: status, how to run, what's left

Last updated 2026-11-07. Branch `pilot-initial-results`. This is the doc to read first.
For finer detail on the pilot runs and their caveats, see [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md).
[docs/handoff.md](docs/handoff.md) is historical (written before the pilot ran).

## 1. Status in brief

- **The pipeline works end to end on an H100 80 GB on PACE-ICE.**
  - Serving: vLLM 0.31.0 with Llama-3.1-8B-Instruct in bf16.
  - The debate harness, all lever configurations, the closed-loop load generator, the per-call tracer and the analysis scripts.
- **1,534 pilot debates have run** (about 1.2 H100-hours). All results are **exploratory**: the prompts approximate Du et al.'s released code, and the sample sizes are below the preregistered ones.
- **Milestone:** written in [docs/milestone.tex](docs/milestone.tex) (one page). Due Nov 7.
- **Nothing preregistered has run yet.** Wrapping the released debate code blocks the formal runs.

## 2. What we are testing (approved proposal)

The proposal is in [proposal.pdf](proposal.pdf): methods on page 2, preregistration on page 4.
- **Tasks.** Multi-agent debate (3 agents, 2 rounds, majority vote) on GSM8K (short prompts) and QuALITY (long stories, with the story first in the prompt).
- **Serving.** Pinned vLLM, Llama-3.1-8B-Instruct in bf16, one H100 80 GB. Temperature 0.7, top-p 0.9, at most 512 output tokens, a seed per request.

| Name | What it is | Dispatch | Prefix caching | Prompts |
|---|---|---|---|---|
| **BASE** | Released debate | sequential | on | as released |
| neither lever | ablation | sequential | off | as released |
| L1 only | parallel dispatch | parallel per round | off | as released |
| L1+L2 | both standard levers | parallel | on | as released |
| L1+L2+L3a | warm-up control | parallel + 1-token warm-up of the round-1 prompt | on | unchanged |
| L1+L2+L3 | our optimization | parallel + warm-ups + shared round-2 transcript | on | **round 2 changed** |
| single agent | overhead reference | 1 call | on | round 1 only |

- **Lever definitions.** L1 = parallel dispatch. L2 = vLLM automatic prefix caching. L3 = our shared-prefill optimization.
- **Server processes.** Caching on and caching off each run in their own vLLM server. Every configuration starts from an empty prefix cache (`/reset_prefix_cache`).
- **Preregistered decision rules.**
  1. L1 at C=1 is at least 1.5×, with a bootstrap lower bound above 1.2.
  2. L1's gain at C=32 is less than half its gain at C=1.
  3. Caching's leave-one-out loss on QuALITY at C=16 is at least 2× its C=1 value and at least 10% of T; on GSM8K at C=1 it is below 5%.
  4. L3 cuts prefill by at least 30% and median T by at least 10% on QuALITY at C=16.
  5. Accuracy is no more than 2 pp below BASE.

### Instructor feedback and how it is handled

| Concern | Handling |
|---|---|
| Keep caching configurations distinct from the optimized baseline | BASE always has caching on. Caching-off runs are ablations only, and every configuration starts from an empty cache. |
| Validate that L3 doesn't change effective inputs or lower quality | L3 is split. **L3a** only warms the cache, and its round-1 requests matched L1+L2 exactly (192/192 hashes). **Full L3** changes round-2 prompts by design (the proposal says so), so the accuracy guardrail judges it. Still to do: a replay test with fixed upstream answers. |
| Confirm the H100 is available | Confirmed: the `ice-gpu` partition with `--gres=gpu:h100:1`. |

## 3. Results so far (exploratory)

Full tables are in [results/pilot/](results/pilot/). Start with `extended_results_2026-11-06.md`, then `pilot_6847083_initial_report.md`, `pilot_6847083_extension_report.md` and `pilot_6847083_repeat_report.md`.

| Rule | Pilot value [paired 95% bootstrap CI] | Status |
|---|---|---|
| 1. L1 at C=1 | GSM8K 2.19× [1.96, 2.46]; QuALITY 2.36× [2.18, 2.59] | on track |
| 2. Contention | QuALITY 2.36× (C=1) → 1.63× (C=16) → 1.42× (C=32); gain falls to 31% | on track |
| 3. Caching | QuALITY loss 0.77 s (C=1) → 13.7 s (C=16) → 24.3 s (C=32); GSM8K 0.4% | on track |
| 4. L3 | QuALITY C=16: prefill −7.7%, median T +9.8% | not met |
| 5. Quality | L1+L2 vs BASE: 0 / +6.3 / −1.6 pp at C=16 (seeds 0–2, n=64); −10 / −25 / −5 pp at C=4 (n=20) | unresolved |

- **Baseline profile.** BASE median per debate: 5.4 s on GSM8K and 7.1 s on QuALITY at C=1, then 13.8 s (C=16) and 20.4 s (C=32) on QuALITY. The proposal assumed 14 s.
- **H2 (critical path).** Each round waits for its longest answer, so L1 can reach at most about 2.4×, not 3×. We reach about 96% of that ceiling.
- **H4 (L3).**
  - Under parallel dispatch, vLLM 0.31 already prefills the shared round-1 prompt about once per debate. This comes from API and server counts, not a kernel trace. So L3's warm-up saves nothing.
  - The shared transcript trims prefill, but answers grow about 9% longer.
  - So far this is a negative result.
- **Sampling noise.**
  - Identical seeded requests returned identical text in only 53 of 192 cases.
  - BASE accuracy on the same 20 stories ranged from 65% to 80% across repeats.
  - The 2 pp guardrail is below this noise at our current n.

## 4. Repository map (what is new on this branch)

| Path | Purpose |
|---|---|
| `models/model_config.py` | Adds `llama-3.1-8b` and `llama-3.2-1b` (port 8000, 0.90 GPU memory, 32k context). Older Qwen entries remain. |
| `pilot/debate.py` | Debate harness. Modes `seq`, `par`, `l3a`, `l3`, `single`. Flags: `--conc`, `--seed`, `--problem-seed`, `--record-inputs` (saves messages, hashes, responses, seeds). |
| `pilot/summarize.py` | Configuration table and preregistered quantities. **Single-seed files only.** Its grouping ignores seed, so do not run it on multi-seed files. |
| `slurm/pilot.sbatch` | The full pilot grid in one job. Settings: `NG`, `NQ`, `MODEL`, `OUT`. Exits nonzero if any configuration fails. |
| `results/pilot/` | Reports, environment and package freezes, source patches, Prometheus snapshots, and small traces. |
| `results/pilot/*_analysis.py`, `*.sh` | Exact drivers and analyses for the extension and repeat runs. They are historical and have fixed paths and dates. |
| `docs/milestone.tex`, `docs/milestone_report.md` | Milestone, one page (LaTeX), and a longer markdown draft. |
| `docs/proposal_alignment_review.md` | Audit of the code against the proposal and feedback. |
| `tests/` | 17 tests, no GPU needed. |

**Not in git** (over GitHub's 100 MB limit, or duplicates):
- `results/pilot/pilot_6847083_extension.jsonl` (176 MB): the authoritative 1,024-run trace.
- `..._extension_seed0.jsonl`, `results/*.zip`, and the extracted copy `results/extended_results_2026-11-06/`.

These are on Tanishk's Mac in `~/Desktop/dlt/proj/results/` and on ICE in `~/scratch/dlt-proj/results/pilot/`. To share them, use Box or OneDrive, or copy them to the ICE storage below.

**Stale on purpose; fix in a separate PR.** The root README, `docs/project_plan.md`, default sampling, `slurm/serve_models.sbatch` and the `serve_vllm.py` docstring still describe the earlier draft: a Qwen pair, the old lever numbering and a caching-off baseline. The pilot overrides these explicitly.

## 5. Running on PACE-ICE

**Account and scheduling.**
- Account `coc`, QoS `coc-ice`, partition `ice-gpu` (6 nodes × 8 H100 80GB HBM3).
- Request `--gres=gpu:h100:1`, about 4–8 CPUs, 64 GB RAM, and 2 hours or less (short jobs start sooner).
- Don't use `--exclusive`. Queue waits have reached about 12 hours, so queue jobs early.
- Run `nvidia-smi` and `squeue` only on compute nodes or in a login shell. Over plain non-login SSH, use `bash -lc`.

**Storage.** `~/scratch` is a plain directory on the **30 GB home filesystem**, not real scratch. Keep large data on real scratch.

| Path | What |
|---|---|
| `~/scratch/dlt-proj` | Repository and outputs (Tanishk's account) |
| `~/scratch/dlt-venv` | Python 3.10 venv: vLLM 0.31.0 and client dependencies (counts against home quota) |
| `~/scratch/hf` → `/storage/ice1/9/1/tdeo7/dlt/hf` | `HF_HOME` (model and datasets) on the 300 GB scratch allocation |

Model snapshot used: `meta-llama/Llama-3.1-8B-Instruct@0e9e39f249a16976918f6564b8830bc894c89659`.

**New teammate setup.** Do this on the login node, not in a GPU job.
```bash
cd /storage/ice1/<your path>          # real scratch; find it with: pace-quota
git clone -b pilot-initial-results https://github.com/arihanth26/DLT-Multi-Agent-Inference.git dlt-proj
module load anaconda3 && python -m venv dlt-venv && source dlt-venv/bin/activate
pip install -r dlt-proj/requirements.txt -r dlt-proj/requirements-serving.txt
export HF_HOME=$PWD/hf && hf auth login            # needs approved Llama-3.1 access
hf download meta-llama/Llama-3.1-8B-Instruct --exclude "original/*"
cd dlt-proj && python -m pytest -q                 # expect 17 passed
```

**Run the full pilot grid** (about 30 minutes): `VENV=<venv path> sbatch slurm/pilot.sbatch`. For a smoke test, prefix the command with `NG=2 NQ=2`.

**Run one configuration by hand** inside a GPU allocation:
```bash
VLLM_SERVER_DEV_MODE=1 $(python -m models.serve_vllm --model llama-3.1-8b --prefix-caching --dry-run) > logs/server.log 2>&1 &
until curl -sf localhost:8000/health >/dev/null; do sleep 5; done
python -m pilot.debate --task quality --mode par --apc on --n 64 --conc 16 --seed 0 \
  --record-inputs --out results/pilot/<name>.jsonl
```
- For caching off, use `--no-prefix-caching` on the server and `--apc off` on the client.
- For the KV-memory sweep, add `--gpu-memory-fraction 0.5` (or similar) to the `serve_vllm` command.
- `VLLM_SERVER_DEV_MODE=1` is required: it enables the cache reset between configurations.

## 6. What's left, in order

Hour figures are rough extrapolations from pilot throughput, not validated estimates.

| # | Task | Owner (proposal roles) | H100 h | People h |
|---|---|---|---:|---:|
| 0 | Recover the final C=1 three-seed check (job step `6847083.5`, 20 stories, 120 records expected) from ICE. Verify it, and add it to `results/pilot/` only if complete. | Tanishk | 0 | 1 |
| 1 | Update docs and config to the approved design (README, project plan, sampling defaults, old SLURM). Scope `pkill` in `pilot.sbatch` to the job's own processes. | anyone | 0 | 3 |
| 2 | **Wrap and pin the released Du et al. debate code** with a documented QuALITY adaptation. Check first whether Arihanth or Malhar have work in progress. | Arihanth | ~1 | 10–14 |
| 3 | Log rendered token IDs and finish reasons. Run the fixed-upstream replay test for L3a, and investigate the same-seed variability. | Tanishk | ~0.5 | 4–6 |
| 4 | Write the preregistration revision log (dated) in `docs/project_plan.md`. | anyone | 0 | 2 |
| 5 | Build a QuALITY data module: 265 stories (115 validation + 150 train), one question each. Add a GSM8K split with ≥300 problems. | Malhar | 0 | 3 |
| 6 | **C=1 headline:** 100 problems/task × seeds 0–2 × 7 configs, recorded inputs. | all | ~5.5 | 2 |
| 7 | **Load sweep:** C ∈ {4, 16, 32} × 6 configs on both tasks (265 QuALITY, 300 GSM8K); GSM8K under load is still unmeasured. Include a BASE-vs-BASE repeat for the noise floor. | Malhar | ~4 | 3 |
| 8 | KV-memory sweep (QuALITY, C=16/32, reduced `--gpu-memory-fraction`). | Malhar | ~2 | 2 |
| 9 | Rounds sweep, R ∈ {3, 4}. Needs a `--rounds` flag. Drop first if short on time. | Arihanth | ~2.5 | 2 |
| 10 | Reruns buffer | — | ~7 | — |
| 11 | Analysis and figures; report, video, reproducible repository (due **Dec 3**) | all | — | 35 |

Total: about 22 H100-hours and about 65 person-hours. The optional extras are Khan et al. debate and AutoGen on HumanEval+, about 8–10 more H100-hours.

**Planned revisions (thresholds unchanged).**
1. QuALITY under load uses n=265.
2. The guardrail pools seeds 0–2 and is read against a BASE-vs-BASE noise floor.
3. L3 is split into L3a and full L3, with a one-token warm-up (vLLM has no prefill-only request).
4. T ends when the vote is recorded. The current harness stops the clock before parsing; fix that in task 2 or 3.

**Timeline.**

| Dates | Work |
|---|---|
| Nov 7–11 | Tasks 0–5 |
| Nov 12–18 | Task 6 |
| Nov 19–25 | Tasks 7–8 |
| Nov 26–Dec 2 | Analysis, reruns, task 9 if time allows |
| Dec 3 | Submission |

## 7. Pitfalls

- **Pooling repeated runs.** Do not pool repeated runs of the same problems as independent samples. Do not pick a favorable repeat as BASE. Report negative and quality-warning results.
- **Old traces.** The original and repeat traces lack request and response text. Only the extension was run with `--record-inputs`.
- **Summarizing multi-seed files.** Use the dedicated analysis script, e.g. `python3 results/pilot/pilot_6847083_extension_analysis.py results/pilot/pilot_6847083_extension.jsonl`.
- **Load runs.** Runs at C=32 with only 64 problems are two waves of 32, so startup and drain effects are large. Use the full n for formal claims.
- **Bootstrap counts differ.** Reports used 4,000 bootstrap resamples; the generic summary uses 2,000. Say which one produced a number.
- **Mixing CPU allocations.** Do not mix timings from 4-CPU and 8-CPU allocations. Record CPUs, node, GPU UUID, commit and vLLM version with every run.
