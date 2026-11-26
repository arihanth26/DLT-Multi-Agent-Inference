# DLT Multi-Agent Inference

Multi-agent LLM workflows make many model calls per task, and research code usually issues
them one at a time and re-reads the same context on every call. This project measures, on one
GPU serving an open-weight model, how much three standard serving levers cut the end-to-end
latency of a real multi-agent workflow, how that changes under load, and whether answer
quality holds:

- **L1, parallel dispatch:** send the independent calls of a debate round concurrently.
- **L2, prefix caching:** vLLM automatic prefix caching reuses KV for shared prompt prefixes.
- **L3, shared-prefix prefill:** a 1-token warm-up of the shared prompt, and (full L3) one
  shared round-2 transcript for all agents instead of a different prompt per agent.

**Workload:** Du et al. (2023) multi-agent debate, 3 agents x 2 rounds + majority vote, with
the released prompts and problem order (GSM8K) and a documented adaptation for long-context
multiple choice (QuALITY). **BASE** = sequential dispatch with prefix caching **on**.
**Model and server:** Llama-3.1-8B-Instruct, bf16, snapshot `0e9e39f249a16976918f6564b8830bc894c89659`,
vLLM 0.31.0, one NVIDIA H100 80 GB (Georgia Tech PACE-ICE).
**Extension (exploratory):** a supply-chain disruption workflow that combines Du et al.'s
parallel debate with an AutoGen-style serial coordinator (`data/supply_chain/`, `pilot/supply_chain.py`).

Course project, CSE 8803 Deep Learning for Text Data, Georgia Tech, Fall 2026
(Tanishk Deo, Arihanth Jayavijayan, Malhar Jadhav). The proposal and its five preregistered
decision rules are in `proposal.pdf`; deviations are listed at the end of this file.

## Headline result

At one debate in flight (C=1), parallel dispatch (L1) cuts median end-to-end latency
from BASE by **[HEADLINE: GSM8K x.xx x, QuALITY x.xx x]** (paired bootstrap 95% CI over
problems, 100 problems x seeds 0-2). Reproduce it with the commands under
[Reproduce the results](#reproduce-the-results); the number is rule 1 in `results/final_report.md`.

## Repository layout

```
proposal.pdf                 Proposal with the preregistered decision rules
CLAUDE.md                    Current project state and team working notes
HANDOFF.md                   Pilot history (Nov 6-7) and cluster notes
models/
  model_config.py            Model registry (Llama-3.1-8B, max_model_len 32768, gpu fraction 0.90)
  serve_vllm.py              Builds the vLLM server command (--prefix-caching / --no-prefix-caching)
  client.py                  Async OpenAI-compatible client with per-call timing and token counts
data/
  gsm8k/                     GSM8K answer parsing for scoring
  supply_chain/generate.py   Seeded supply-chain scenarios + exact cost solver (gold answers)
pilot/
  debate.py                  Debate harness: modes seq, par, l3a, l3, single; closed-loop load --conc
  supply_chain.py            Supply-chain workflow (3 stages, 9 calls per task), same modes
  analyze.py                 Final analysis: five decision rules, guardrail, H2, factorial, extension
  input_audit.py             Checks what each configuration sends (L3a inputs unchanged; what L3 changes)
  figures.py                 Report figures (PDF/PNG) and a CSV of every plotted number
  summarize.py               Pilot summary (Nov 6 results)
slurm/
  campaign.sbatch            Runs every final configuration in priority order; resumable
  smoke.sbatch               15-minute end-to-end check on one GPU
  pilot.sbatch               The Nov 6 pilot grid
tests/                       Unit tests, no GPU or network needed (22 tests)
results/
  pilot/                     Pilot results (exploratory)
  final_<GPU model>/         Final results, one JSONL file per configuration
docs/                        Proposal alignment review, milestone report, project plan
```

## Setup

Python 3.10+, a CUDA GPU with 80 GB for the server, and a Hugging Face account with access to
`meta-llama/Llama-3.1-8B-Instruct` (gated; request it on the model page).

```bash
git clone -b pilot-initial-results https://github.com/arihanth26/DLT-Multi-Agent-Inference.git
cd DLT-Multi-Agent-Inference
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt -r requirements-serving.txt   # vLLM 0.31.0 and client deps
python -m pytest -q                                           # 22 passed, no GPU needed

hf auth login
HF_HUB_DISABLE_XET=1 hf download meta-llama/Llama-3.1-8B-Instruct \
    --revision 0e9e39f249a16976918f6564b8830bc894c89659 --exclude "original/*"
# Pin "main" to that snapshot so the server, which loads "main", always gets the same weights:
M=${HF_HOME:-~/.cache/huggingface}/hub/models--meta-llama--Llama-3.1-8B-Instruct
mkdir -p $M/refs && echo -n 0e9e39f249a16976918f6564b8830bc894c89659 > $M/refs/main

# Datasets (GSM8K test; QuALITY validation and train) download from the Hugging Face Hub on
# first use; cache them once if the GPU jobs run offline:
python -c "from datasets import load_dataset as L; L('openai/gsm8k','main',split='test'); L('emozilla/quality',split='validation'); L('emozilla/quality',split='train')"
```

The supply-chain scenarios need no download: `python -m data.supply_chain.generate --n 300 --seed 0`
regenerates them exactly (gold letters A/B/C/D = 79/81/66/74).

## Reproduce the results

**On a Slurm cluster (as we ran it).** From the repository root, with the venv active:

```bash
export DLT=<folder holding dlt-venv/ and hf/>   # or set VENV=<venv> and HF_HOME=<hf cache>
sbatch slurm/smoke.sbatch                        # optional, ~15 min end-to-end check
sbatch slurm/campaign.sbatch                     # resubmit until the log ends "0 run"
python -m pilot.analyze results/final_NVIDIA-H100-80GB-HBM3 --json results/final_numbers.json \
    > results/final_report.md                   # all five rule verdicts; rule 1 = headline
python -m pilot.input_audit results/final_NVIDIA-H100-80GB-HBM3 \
    --tokenizer meta-llama/Llama-3.1-8B-Instruct > results/input_audit.md   # CPU only
python -m pilot.figures results/final_NVIDIA-H100-80GB-HBM3 --out results/figures
```

`campaign.sbatch` runs, in order: the C=1 headline (2 tasks x 7 configurations x 100
problems x seeds 0-2, prompts and responses recorded), a BASE-vs-BASE noise floor, the load
sweep (C = 16, 32, 4; 6 configurations; 300 GSM8K and 265 QuALITY problems), then the
supply-chain extension. A complete configuration file is skipped and a partial one is rerun,
so resubmitting continues where a job stopped; several jobs of one account split the work.
`ONLY=c1|noise|load|scd` restricts a job to one phase. Results land in
`results/final_<GPU model>/`, so runs on different GPU types never mix.

**On any machine with a GPU (no Slurm).** Start the server, then run single configurations:

```bash
VLLM_SERVER_DEV_MODE=1 $(python -m models.serve_vllm --model llama-3.1-8b --prefix-caching --dry-run) &
until curl -sf localhost:8000/health; do sleep 5; done
python -m pilot.debate --task gsm8k --mode seq --apc on --n 100 --conc 1 --seed 0 --out results/final_X/gsm8k_seq_apcon_C1_s0.jsonl
python -m pilot.debate --task gsm8k --mode par --apc on --n 100 --conc 1 --seed 0 --out results/final_X/gsm8k_par_apcon_C1_s0.jsonl
python -m pilot.analyze results/final_X
```

`VLLM_SERVER_DEV_MODE=1` exposes `/reset_prefix_cache`, which the harness calls before each
configuration. For caching-off configurations, restart the server with `--no-prefix-caching`
and pass `--apc off`. File names follow `<task>_<mode>_apc<on|off>_C<conc>_s<seed>.jsonl`.

## Output format

One JSON line per task: `task, mode, id, T` (end-to-end seconds, clock stopped after the vote),
`cp` (critical path: sum over rounds of the slowest call), `final, gold, correct, preds`,
`apc, conc, seed, model`, and `calls`: per call its kind, agent, round, latency, prompt tokens,
cached tokens and output tokens. With `--record-inputs` each call also stores its messages,
response, request seed and a SHA-256 of the messages. Supply-chain records add the stage-3
time, the coordinator's chosen specialist and the stage-2 vote.

## Deviations from the proposal

1. **Baseline aligned with the released implementation** (TA feedback, Nov 21): GSM8K prompts
   and problem selection match Du et al. `gsm/gen_gsm.py` (commit 9846749) character for
   character (`tests/test_released_prompts.py`). QuALITY applies the same template, repeating
   the question and options but not the story in round 2. We keep our own answer parser: the
   released eval script counts unparseable answers as correct.
2. **Revision 1:** QuALITY draws validation stories first, then train stories (up to 265).
3. **Revision 2:** a BASE-vs-BASE repeat is the noise floor for the accuracy guardrail.
   Accuracy at C=1 pools seeds 0-2, paired by problem and seed.
4. **Revision 3:** L3 is split into L3a (1-token warm-up only; prompts unchanged, verified by
   `pilot/input_audit.py`) and full L3 (adds the shared round-2 transcript, which changes the
   round-2 prompt by design). vLLM has no prefill-only request, so the warm-up generates one token;
   its time and tokens count toward L3.
5. **Revision 4:** the latency clock stops after the majority vote.
6. **Supply-chain workload** added as an exploratory extension; it is not part of any
   preregistered decision rule.
7. **[If used] Hardware:** final runs on [GPU], because of H100 queue times; the pilot and
   milestone ran on H100 80 GB.

No preregistered threshold was changed.
