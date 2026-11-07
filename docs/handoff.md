# Handoff: pilot setup on PACE-ICE

> **Superseded:** see [HANDOFF.md](../HANDOFF.md) for the current status. This file is kept for history.

For the complete current session handoff, read [CLAUDE_HANDOFF.md](../CLAUDE_HANDOFF.md).
It includes the validated experiments, artifact map, code changes, analysis caveats and
the final C=1 run that still needs retrieval. This older document retains historical text.

Status as of 2026-11-06. Written for the team (Tanishk, Arihanth, Malhar) and anyone who picks
up the pilot run.

### Live follow-up, Nov 6 evening

- Quota failure resolved: `~/scratch` was an ordinary directory on the **30 GB home**
  filesystem, not the 300 GB scratch allocation. `~/scratch/hf` now symlinks to
  `/storage/ice1/9/1/tdeo7/dlt/hf`; the model download completed. Xet was only 408 KB,
  so the earlier Xet-cache explanation below was not supported by the actual usage.
- Smoke job **6850879** completed successfully in **9m13s** on an NVIDIA H100 80GB HBM3,
  vLLM 0.31.0. All 18 configurations produced two records (36 total). Structural trace
  checks passed and APC-off cached-token counts were zero. Artifacts are in `results/pilot/`.
- Exploratory pilot **6850988** was queued, then canceled after launching the same default
  30 GSM8K / 20 QuALITY grid inside the user's existing idle H100 VS Code allocation,
  **6847083**, step **6847083.1**, at 18:35 Eastern. This allocation has four CPUs and
  80 GB host memory. Output stem: `results/pilot/pilot_6847083_initial`; log:
  `logs/pilot_existing_6847083.out`. The runner now reports a failed exit status when any
  configuration fails; source changes are uncommitted locally and on ICE.
- Step **6847083.1 completed successfully in 29m27s**. All **430 expected records** passed
  validation. Read `results/pilot/pilot_6847083_initial_report.md` for the interpreted table,
  paired bootstrap intervals, exact McNemar checks, quality warnings and limitations.
  C=1 BASE-to-parallel median latency ratios: **2.19x GSM8K**, **2.41x QuALITY**.
  Full L3 did not improve median latency in this pilot. QuALITY C=4 had a 10 pp accuracy
  warning for parallel+APC and full L3 against BASE. Separate same-seed repeats were
  launched as step **6847083.2** to investigate variability; do not pool them into the grid.
  Those repeats also completed (3m45s, 80 validated records): BASE/parallel accuracy was
  16/20 vs 11/20, then 13/20 vs 12/20. All three C=4 comparisons therefore cross the
  numerical quality-regression threshold. Do not claim quality preservation. The main
  report includes the separate repeat table. All pilot server processes have exited;
  the GPU was confirmed idle afterward. The user's VS Code allocation remains active.
- A subsequent **64-story QuALITY extension**, step **6847083.4**, completed successfully
  in **30m28s**: **1,024 validated runs / 16 groups**. It covers C=1,16,32 and three
  sampling seeds for BASE/parallel at C=16. See `results/pilot/pilot_6847083_extension_report.md`.
  BASE/parallel latency ratios at seed 0: **2.36x, 1.63x, 1.42x** as C increases. Caching-off
  adds **0.77s, 13.72s, 24.33s** to median parallel latency at those loads. Full L3 at C=16
  changes estimated prefill by **-7.7%** and median latency by **+9.8%**; at C=32 median
  latency improves by **3.9%** in this short pilot.
- `--record-inputs` now saves messages, hashes, request seeds, sampling settings and responses.
  The 16 tests pass, including payload-preservation checks for recording. Request/history,
  parser, vote and Prometheus checks passed on the extension. Parallel round-1 prefill is
  already about one prompt copy per debate; matching seeds/messages still produce different
  responses. Per-call finish reasons and rendered token IDs remain unrecorded.
- Read `docs/proposal_alignment_review.md` before full experiments: the current pilot is
  exploratory and does not meet all preregistered workflow, measurement, and validation gates.

The original handoff below is retained as historical context; the follow-up supersedes its
download, smoke-test, and GPU-availability status.

## 1. Where things stand

| Item | State |
|---|---|
| Proposal | Approved by the professor and TA. The approved PDF is the source of truth, and its preregistration is in the appendix. |
| Repository `main` | V1 scaffolding (model client, serving, data pipeline, tests). Built for an **earlier draft** of the proposal; see section 4. |
| Branch `pilot-initial-results` | Adds a runnable pilot of the approved design. **Committed locally only, not pushed.** |
| ICE environment | venv, vLLM 0.31.0, datasets, and tests (15 of 15 pass) are done. **The Llama-3.1-8B download failed on disk quota** at 10 of 14 files. |
| First results | Not run yet. Next: finish the download, then the smoke test, then the pilot. |

## 2. What the approved proposal commits us to

- **System.** Multi-agent debate from Du et al., as released: 3 agents, 2 rounds, majority vote.
  - GSM8K (short prompts).
  - QuALITY (long stories; the story comes first in every prompt).
- **Serving.** vLLM pinned to one version, default optimizations. Llama-3.1-8B-Instruct in bf16 on one H100 80 GB. Temperature 0.7, top-p 0.9, at most 512 output tokens, a seed per request. Development uses Llama-3.2-1B.
- **Levers.**
  - **L1:** parallel dispatch within a round.
  - **L2:** vLLM automatic prefix caching on or off.
  - **L3 (ours):** a prefill-only request plus one shared round-2 transcript, applied on top of L1 and L2.
- **BASE.** The released code with sequential calls and **prefix caching on**.
- **Load.** C in {1, 4, 16, 32} concurrent debates. Additional sweeps over rounds R in {2, 3, 4} and a smaller KV cache.
- **Problem counts.** 100 per task at C=1 with seeds 0, 1 and 2; 300 per task under load.
- **Decision rules.** Five preregistered rules, summarized in `pilot/README.md` and in the proposal appendix.
  - L1 speedup at C=1 of at least 1.5, with bootstrap lower bound above 1.2.
  - L1's gain at C=32 less than half its gain at C=1.
  - L2 thresholds on QuALITY and GSM8K.
  - L3 cuts prefill tokens by at least 30% and median T by at least 10% at C=16.
  - Accuracy no more than 2.0 percentage points below BASE.

### TA feedback and how we address it

| TA concern | How we address it |
|---|---|
| Keep caching configurations clearly separate from the optimized vLLM baseline | Every configuration has a fixed name (table below). BASE is defined as sequential calls with prefix caching **on**. Each configuration starts with an empty prefix cache (`/reset_prefix_cache`), and caching on or off means a separate server process. |
| Show that the shared-prefix prefill does not change agents' inputs or lower answer quality | L3 is split into two configurations. **L3a** only adds a prefill warm-up, so prompts stay byte-identical, the seeds are the same, and answers must match L1+L2. **L3** adds the shared transcript, which does change prompts; the McNemar test and the 2.0-point guardrail apply to it. |
| Confirm the H100 is available | Confirmed. See section 3. |

### Configuration names, used everywhere (code, tables, report)

| Name | Dispatch | Prefix caching | Prompts |
|---|---|---|---|
| **BASE** | sequential | on | as released |
| neither lever | sequential | off | as released |
| L1 only | parallel | off | as released |
| L1+L2 | parallel | on | as released |
| L1+L2+L3a | parallel, plus prefill warm-up | on | unchanged |
| L1+L2+L3 | L3a plus shared round-2 transcript | on | changed in round 2 |
| single agent | one call | on | round 1 only |

## 3. PACE-ICE facts we confirmed

- **Account and QoS.** Account `coc`, QoS `coc-ice`. QoS limits: maximum 50 queued jobs, no wall-time or GPU cap at the QoS level.
- **Partition.** Our jobs land in **`ice-gpu`**: 6 nodes with 8 H100s each, 48 GPUs in total. The larger `coe-gpu` partition belongs to the College of Engineering, not us.
- **GPU type name** (lowercase): `--gres=gpu:h100:1`.
- **Exclude** `atl1-1-03-012-3-0`. It is in state `inval` and reports only 7 GPUs.
- **Expect queue waits.** On Nov 6, every `ice-gpu` H100 was busy, and the scheduler estimated a start about 12 hours out. To start sooner:
  - Request fewer CPUs and less memory: 8 CPUs and 64 GB, not 16 and 128.
  - Request short wall times (2 hours or less), so the scheduler can fit the job into gaps.
  - Queue `sbatch` jobs ahead of time.
- **Do not use `--exclusive`.** It would charge all 8 GPUs on the node. One whole GPU per job is enough, since other users' jobs on the same node never share our GPU.
- **Memory.** The nodes are 8-GPU HGX boards, so the cards should be H100 80 GB (SXM). Confirm with `nvidia-smi` in the first job; the pilot logs it to `_env.txt`. vLLM at 0.90 memory utilization leaves roughly 55 GB for KV cache after the 8B weights.
- **Disk quota is the current blocker.** The Hugging Face downloader keeps a chunk cache in `$HF_HOME/xet` while assembling files, so a 16 GB model can briefly take about 32 GB.
- **Login nodes** have no GPU, so `nvidia-smi` fails there. Copying files to ICE from a Mac needs an interactive terminal and the GT VPN when off campus.

### ICE environment (Tanishk's account)

| Path | Contents |
|---|---|
| `~/scratch/dlt-proj` | Copy of the repository with the pilot branch |
| `~/scratch/dlt-venv` | Python 3.10 (anaconda3 2023.03) venv with vLLM 0.31.0 and client dependencies |
| `~/scratch/hf` | `HF_HOME`: the token, datasets, and the partial Llama-3.1-8B download |

## 4. Repository vs approved proposal

`main` follows an earlier draft. The pilot branch leaves these defaults alone on purpose. Fix
them in a separate PR that the whole team reviews, **before any preregistered run**.

| | `main` today | Approved proposal |
|---|---|---|
| Model | Qwen3-14B plus Qwen3-1.7B, two servers sharing the GPU | Llama-3.1-8B alone, Llama-3.2-1B for development |
| Lever names | L2 = coalescing, L3 = prefix caching, L4 = tiering | L2 = prefix caching, L3 = shared-prefill optimization |
| BASE | prefix caching **off** | prefix caching **on** |
| Sampling | top-p 0.8, max 1024 tokens | top-p 0.9, max 512 tokens |
| Datasets | GSM8K (200), HumanEval+, bugged solutions, SRDD | GSM8K and QuALITY (QuALITY was missing; the pilot loads it directly) |
| `max_model_len` | 8192 | about 12k needed for QuALITY round 2; the pilot uses 32768 |
| Decision rule | `docs/project_plan.md` still has the old 3-part rule | The 5 preregistered rules |
| SLURM | `gpu:H100:1`, two servers | `gpu:h100:1`, `-q coc-ice`, one server |

## 5. What the pilot branch adds

The branch has two commits on top of `main`: `7fa8afe` adds the pilot and `932e374` pins vLLM
to 0.31.0.

| File | Purpose |
|---|---|
| `models/model_config.py` | Registers `llama-3.1-8b` and `llama-3.2-1b`: port 8000, 0.90 GPU memory, 32k context. |
| `pilot/debate.py` | Debate harness built on the existing `LLMClient`. It runs the modes `seq`, `par`, `l3a`, `l3` and `single`, records a per-call trace (submit, done, first-token, prompt, cached and output tokens), and runs C debates concurrently in a closed loop. Problems are fixed by seed. QuALITY takes one question per story, so problems never share cache. |
| `pilot/summarize.py` | Configuration table and preregistered quantities: L1 speedup with bootstrap lower bound, L2 leave-one-out, L3 prefill and T change, critical-path bound (H2), the cached share of round-1 prompts (H4 premise), and accuracy and answer agreement against BASE with discordant counts. |
| `slurm/pilot.sbatch` | The whole grid in one 2-hour job. It also runs inside `salloc` with `bash`. Settings: `NG`, `NQ`, `MODEL`, `OUT`. |
| `pilot/README.md` | Exact run steps and what to look at in the summary. |
| `requirements-serving.txt` | `vllm==0.31.0` |

The pilot was tested without a GPU: all modes ran end to end against a fake model, the
round-2 prompts were inspected for each mode, the QuALITY schema was checked, and the existing
tests pass. **The real vLLM path has not been run yet.**

**Pilot grid.**
- C=1, GSM8K (30) and QuALITY (20): every configuration in the table above.
- C=4 on QuALITY: BASE, L1+L2, L3 and L1 only.
- Estimated about 75 minutes on an H100. If needed, use `NG=20 NQ=12`.

## 6. Next steps, in order

1. **Finish the model download on ICE:**
   ```bash
   pace-quota; du -sh ~/.cache ~/scratch/hf/* ~/scratch/dlt-venv
   pip cache purge; rm -rf ~/scratch/hf/xet
   HF_HUB_DISABLE_XET=1 hf download meta-llama/Llama-3.1-8B-Instruct --exclude "original/*"
   ```
   If scratch can't hold about 25 GB, put the weights in shared course or project storage.
2. **Smoke test:** `cd ~/scratch/dlt-proj && NG=2 NQ=2 sbatch --time=00:30:00 slurm/pilot.sbatch`. Check that `logs/pilot_<job>.out` ends with `== done`.
3. **Pilot:** `sbatch slurm/pilot.sbatch`. Commit `results/pilot/pilot_<job>_summary.md` and `_env.txt`.
4. **Read the pilot against the plan.**
   - Seconds per BASE debate: is the 14 s figure behind the compute budget right?
   - L1 speedup at C=1.
   - The H4 line: is the round-1 prompt cached for agents 2 and 3 under `par`?
   - L3a answer agreement with BASE.
5. **Push** `pilot-initial-results` and open a draft PR (Arihanth owns the repo).
6. **Alignment PR** for the items in section 4. Also rewrite `docs/project_plan.md` from the approved preregistration, with a dated revision log.
7. **Build the real harness.**
   - Wrap the **released** Du et al. debate code; the pilot's prompts are an approximation.
   - Add a GSM8K split of 300 problems.
   - Add a QuALITY data module to `data/`.
8. **Full runs.**
   - C=1, 100 problems, seeds 0, 1 and 2.
   - Load sweep C in {1, 4, 16, 32} with 300 problems.
   - Rounds and memory sweeps.

## 7. Open decisions

- **QuALITY under load.** Validation has 2086 questions but only **115 distinct stories**; train has 150. The 300 problems under load require one of:
  - several questions per story, which lets problems share cache; this must be disclosed;
  - drawing from train and validation together, 265 stories.

  Pick one and log it as a dated preregistration revision.
- **Fallback GPU.** If H100 queue times get too long near the deadline, the fallback is an A100 80 GB or an H200, logged as a revision. Check with `sinfo -p ice-gpu -o "%G %D %t"`.
- **Unpushed work.** Check whether Arihanth (harness, L1) or Malhar (load generator) has unpushed work before building the harness, to avoid duplicating it.

## 8. Schedule

The proposal timeline put the milestone on Oct 29 and the load sweep in week 11. As of Nov 6,
`main` has no harness yet. We are about two weeks behind the plan.

- **Remaining:** week 12 sweeps, week 13 analysis, week 14 buffer, Dec 3 report.
- **Priority:** C=1 headline results on both tasks first.
- **If time runs short,** drop work in the order the proposal gives:
  1. Stretch goals.
  2. The rounds sweep.
