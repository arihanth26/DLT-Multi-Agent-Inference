# CLAUDE.md: project context for Claude sessions (as of Nov 25, 2026, 17:00 ET)

Read this first. It supersedes the status sections of `HANDOFF.md` and `CLAUDE_HANDOFF.md`
(both Nov 7), which remain the reference for pilot details and history.

## Project in one paragraph

Georgia Tech CSE 8803 (Deep Learning for Text Data) final project, team of three: Tanishk Deo
(serving, tracer, L3), Arihanth Jayavijayan (harness, L1, accuracy; repo owner), Malhar Jadhav
(load generator, sweeps, extension). We measure three serving levers on a real multi-agent
workflow (Du et al. multi-agent debate: 3 agents x 2 rounds + majority vote) on
Llama-3.1-8B-Instruct bf16, vLLM 0.31.0, one GPU: **L1** parallel dispatch of a round's calls,
**L2** vLLM automatic prefix caching, **L3** shared-prefix prefill (warm-up + shared round-2
transcript). BASE = sequential dispatch with caching ON. Tasks: GSM8K (short context) and
QuALITY (long context). The proposal (`proposal.pdf`) preregisters five decision rules with
fixed thresholds; do not change thresholds.

## Deadline and deliverables (Dec 3, 11:59 PM ET, Canvas; no extensions)

One teammate submits both files.
- Report PDF: 8-10 pages, NeurIPS 2026 format (excluding references and appendix), video link
  on page 1, "AI Tools Used" section in the appendix.
- Code zip: top-level README with setup and the exact commands that reproduce the main
  results, including the headline number; no checkpoints or large data in the zip.
- Video: 10 minutes, every member appears and speaks; YouTube unlisted or GT MediaSpace,
  link tested in a signed-out window.

TA milestone feedback (Nov 21), which sets the priorities: align the baseline with the
released implementation, resolve the accuracy-guardrail uncertainty, make the main results
reproducible from code, and keep experiments on the preregistered objectives.

## Current state of the code (branch `pilot-initial-results`, commit d2eaa3a or later)

| Commit | What |
|---|---|
| 850c6e8 | Tanishk's pilot (Nov 7): harness, pilot results, milestone, HANDOFF.md |
| b26be47 | Released-prompt alignment; supply-chain extension; `slurm/smoke.sbatch`, `slurm/campaign.sbatch`; pkill removed from `pilot.sbatch` |
| 0e546ec | `pilot/analyze.py` (final analysis) |
| d2eaa3a | `campaign.sbatch` accepts `VENV` and `HF_HOME` overrides |

Changes since the pilot (each is a logged deviation/revision for the report):
- **Released baseline (TA item 1):** GSM8K round-1 and round-2 prompts and problem selection
  (`random.seed(0)`, shuffle test, first n) match Du et al. `gsm/gen_gsm.py`, commit 9846749,
  character for character (`tests/test_released_prompts.py`). Round 2 now repeats the original
  question, as released. QuALITY uses the same template with "question" for "math problem" and
  repeats the question and options (not the story): a documented adaptation. Records carry
  `"prompts": "released-v1"`. The released eval script has bugs (unparseable answers counted
  correct; undefined variable); we keep our corrected parser and say so.
- **Revision 4:** T now stops after the majority vote.
- **Revision 1:** QuALITY draws validation stories first (same order as the pilot), then train
  stories, up to 265 distinct stories.
- **Supply-chain extension (exploratory, not preregistered):** `data/supply_chain/generate.py`
  (seeded scenarios, exact cost solver gives the gold answer, 5% ambiguity margin) and
  `pilot/supply_chain.py`: 3 specialists in a parallel debate (stages 1-2), then an
  AutoGen-style serial Coordinator (select a specialist, follow-up, final decision); 9 calls
  per task; the dossier (median 8.4k characters, roughly 2-3k tokens; the real token count is not
  yet measured) is the shared prefix of every call. Same modes and flags as `pilot/debate.py`.

Tests: `python -m pytest -q` gives **19 passed** (the old docs say 17; that number is stale).

## Experiments: one script runs everything

`slurm/campaign.sbatch` runs the remaining grid in priority order, resumes on resubmit and
lets several jobs of ONE account split the work (lock directories). Order:
1. C=1 headline seed 0: both tasks, 7 configs (seq/par/l3a/l3/single with APC on; seq/par
   with APC off), 100 problems, `--record-inputs`.
2. Noise floor: BASE repeated, seed 0 (`*_repeat.jsonl`).
3. C=1 headline seeds 1 and 2.
4. Load sweep C = 16, 32, 4: 6 configs, GSM8K n=300, QuALITY n=265, seed 0.
5. Supply chain: C=1 n=100 (7 configs), C=16 n=300 (4 configs).

`ONLY=c1|noise|load|scd` restricts a job to one phase. Results go to
`results/final_<GPU model>/<config>.jsonl`, so H100 and A100 results never mix.
**Rule: the final report uses one GPU folder, whichever type finishes the complete set first.
Never pool folders.** If it is A100 80 GB, the report states it as a dated revision (pilot and
milestone were on H100). Duplicates across accounts are allowed; keep the first complete file
per configuration.

Analysis: `python -m pilot.analyze results/final_<GPU> > results/final_report.md` prints the
five rule verdicts with paired bootstrap CIs, the McNemar guardrail plus noise floor, the H2 and
factorial tables, and the supply-chain table.

## Cluster facts (PACE-ICE) learned the hard way

- `~` is a 30 GB quota; put venv, pip cache and HF cache on real scratch (`pace-quota` shows
  the path). Never `pip install` without `PIP_CACHE_DIR` on scratch.
- Llama-3.1-8B-Instruct is gated: each account requests access on Hugging Face (took hours).
- Pin the model: download with `--revision 0e9e39f249a16976918f6564b8830bc894c89659`, then
  write that hash to `$HF_HOME/hub/models--meta-llama--Llama-3.1-8B-Instruct/refs/main`.
  Jobs run with `HF_HUB_OFFLINE=1`, so datasets must be cached on the login node first.
- GPUs: 6 H100 nodes x 8 (`--gres=gpu:h100:1`, default in the scripts); A100s are 4 nodes x 2,
  two of them 40 GB. For 80 GB A100s use `--gres=gpu:a100:1 --exclude=atl1-1-03-012-3-0,atl1-1-03-007-33-0,atl1-1-03-007-35-0`.
  `--constraint=A100-80GB` gets stuck with BadConstraints; don't use it.
- Malhar's fair-share is 0 (heavy EdgeKV use), so his jobs wait; that is why all three
  accounts queue the same campaign. Smaller requests start sooner:
  `--time=02:00:00 --cpus-per-task=4 --mem=48G`.
- Never `pkill` vLLM (it can kill the same user's other jobs). Only `scancel` jobs that are
  still pending (`squeue -t PENDING`), never running ones; Malhar also runs EdgeKV jobs.

## Setup for a new account (one time, ~30 min)

```bash
export DLT=/storage/ice1/X/Y/<user>/dlt        # from: pace-quota | grep Scratch
mkdir -p $DLT && cd $DLT
git clone -b pilot-initial-results https://github.com/arihanth26/DLT-Multi-Agent-Inference.git repo
export PIP_CACHE_DIR=$DLT/pip-cache HF_HOME=$DLT/hf
module load anaconda3 && python -m venv $DLT/dlt-venv && source $DLT/dlt-venv/bin/activate
cd repo && pip install -U pip && pip install -r requirements.txt -r requirements-serving.txt
python -m pytest -q                            # 19 passed
hf auth login
HF_HUB_DISABLE_XET=1 hf download meta-llama/Llama-3.1-8B-Instruct \
  --revision 0e9e39f249a16976918f6564b8830bc894c89659 --exclude "original/*"
M=$HF_HOME/hub/models--meta-llama--Llama-3.1-8B-Instruct; mkdir -p $M/refs
echo -n 0e9e39f249a16976918f6564b8830bc894c89659 > $M/refs/main
python -c "from datasets import load_dataset as L; L('openai/gsm8k','main',split='test'); L('emozilla/quality',split='validation'); L('emozilla/quality',split='train')"
for i in 1 2; do sbatch --time=02:00:00 --cpus-per-task=4 --mem=48G slurm/campaign.sbatch; done
```
New session: `export DLT=<path> HF_HOME=$DLT/hf && source $DLT/dlt-venv/bin/activate && cd $DLT/repo`.
Tanishk's existing layout: repo `~/scratch/dlt-proj`, venv `~/scratch/dlt-venv`,
`HF_HOME=~/scratch/hf` (a link to real scratch); his `~/scratch` counts against home quota.

## Status board (update as things finish)

- [x] Malhar's ICE setup; code changes above pushed; campaign jobs queued (Malhar: one H100 job
      running since Nov 25 ~17:00; more pending).
- [ ] Tanishk and Arihanth queue the same campaign from their accounts. (Tanishk: done Nov 26,
      jobs 7364564/7364565, 4 h each, repo `/storage/ice1/9/1/tdeo7/dlt/repo`.)
- [x] Recover pilot job step 6847083.5 (Tanishk, Nov 26): COMPLETED, 120 records validated;
      `results/pilot/pilot_6847083_c1_seeds_report.md`. BASE/parallel 2.41x, 2.27x, 2.24x
      (seeds 0-2, 20 stories, exploratory). Extension trace (176 MB) still needs Box/OneDrive.
- [ ] C=1 headline seeds 0-2, noise floor, load sweep, supply chain (campaign).
- [x] Measure prompt token counts (Llama tokenizer, Nov 26): supply-chain dossier median 3,473
      (3,332-3,579), full shared prompt 3,577; QuALITY round 1 (265 stories) median 6,635
      (2,380-8,538); GSM8K round 1 median 93 (61-176).
- [ ] L3a fixed-upstream replay test: tool done (`pilot/input_audit.py`, tested); run it on the
      C=1 files once they exist, with `--tokenizer meta-llama/Llama-3.1-8B-Instruct` on the
      login node. Token-ID logging is covered by its check D (re-tokenizes recorded messages).
- [ ] Gather result folders from all accounts into one place; run `pilot/analyze.py`.
- [ ] Report (NeurIPS 2026 template), README for the zip, 10-minute video. Target Dec 2;
      Dec 3 is buffer.

## How the team wants Claude to work

- Give commands one step at a time, say where each runs (ICE login node, a job, the user's
  Mac, or Claude's own sandbox) and what it does and why. Keep answers short.
- Read-only checks before anything that deletes or cancels; confirm before deleting.
- Do not change preregistered thresholds; label exploratory work as exploratory.
