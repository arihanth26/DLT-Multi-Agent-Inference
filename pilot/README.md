# pilot

First results for the approved proposal on PACE-ICE: one 2-hour H100 job that runs a small
version of the whole design, so that the harness, tracer and analysis can be checked against
real numbers before the preregistered runs.

| File | What it does |
|---|---|
| `debate.py` | Runs one configuration of the debate (3 agents, 2 rounds, majority vote) on GSM8K or QuALITY against a running vLLM server, and appends one JSON row per debate with a per-call trace. |
| `summarize.py` | Turns those rows into the preregistered quantities: L1 speedup with bootstrap lower bound, L2 leave-one-out loss, L3 prefill reduction, critical-path bound, and accuracy against BASE. |
| `../slurm/pilot.sbatch` | Runs the whole grid in one job and writes `results/pilot/pilot_<job>.jsonl`, `_env.txt` and `_summary.md`. |

## Configurations (names used in the report)

Prefix caching (L2) is a server flag. Every configuration starts with an empty prefix cache.

| Config | Dispatch | Prefix caching | Prompts |
|---|---|---|---|
| **BASE** | sequential (released order) | on | as released |
| neither lever | sequential | off | as released |
| L1 only | parallel within a round | off | as released |
| L1+L2 | parallel | on | as released |
| L1+L2+L3a | parallel, plus one prefill-only request per round before the fan-out | on | **unchanged**, so answers should match L1+L2 |
| L1+L2+L3 | L3a plus one shared round-2 transcript in fixed order, then a short agent-specific line | on | **changed in round 2**, so accuracy is the guardrail |
| single agent | one call | on | round 1 only |

L3 is split into L3a and L3 so that any speedup from warming the cache can be separated from
any change in answers caused by the shared transcript. This answers the TA's request to show
that the prefill optimization does not change the agents' inputs or lower answer quality.

## Grid and time

- **C=1, prefix caching on:** GSM8K (30 problems) and QuALITY (20 problems), each in BASE, L1+L2, L3a, L3 and single.
- **C=1, prefix caching off:** neither lever and L1 only, on both tasks.
- **C=4 on QuALITY:** BASE, L1+L2, L3 and L1 only.

Expect about 75 minutes on an H100, assuming roughly 14 s per sequential GSM8K debate. That
figure is the one the compute budget is based on, and this run checks it.

## Exactly what to run

**Once, on the login node.** Do not run this inside a GPU job.

```bash
cd ~/scratch/dlt-proj                       # the repository, copied or cloned here
module load anaconda3                       # if missing: module avail python
python -m venv ~/scratch/dlt-venv && source ~/scratch/dlt-venv/bin/activate
pip install -r requirements.txt vllm
pip freeze | grep -i '^vllm=='              # write this exact version into requirements-serving.txt
export HF_HOME=~/scratch/hf                 # also add this line to ~/.bashrc
hf auth login                               # token from an account approved for Llama 3.1
hf download meta-llama/Llama-3.1-8B-Instruct --exclude "original/*"
python -c "from datasets import load_dataset as l; l('openai/gsm8k','main'); l('emozilla/quality')"
python -m pytest -q                         # 15 tests, no GPU needed
```

**Smoke test** (about 10 minutes of GPU time, 2 problems per configuration):

```bash
NG=2 NQ=2 sbatch --time=00:30:00 slurm/pilot.sbatch
# or, inside an interactive salloc on an H100: NG=2 NQ=2 bash slurm/pilot.sbatch
```

Check `logs/pilot_<job>.out`. It should end with a summary table and `== done`.

**Pilot:**

```bash
sbatch slurm/pilot.sbatch
squeue -u $USER --start                     # estimated start
tail -f logs/pilot_<job>.out                # progress, one line per configuration
```

The outputs are `results/pilot/pilot_<job>_summary.md` (commit this) and the full
`pilot_<job>.jsonl` trace.

If the job is short on time, use `NG=20 NQ=12`. For development on a smaller GPU, use
`MODEL=llama-3.2-1b`, with `--gres` changed to that GPU.

## What to look at in the summary

1. **Seconds per BASE debate**, from the medT column. This checks the 14 s estimate behind the compute request.
2. **L1 speedup at C=1** against the 1.5 threshold, and **T/cp** for BASE, the critical-path bound (H2).
3. **H4 line.** The share of round-1 prompt served from cache for agents 2 and 3.
   - Under `seq`, the share should be high: agent 1 has already cached the prompt.
   - Under `par`, it may be about 0: three identical prompts arrive at once and each one prefills.
   - Under `l3a`, it should be high again.
   - If `par` is already high, vLLM already shares concurrent prefixes and L3's motivation weakens. That is worth knowing now.
4. **L2 leave-one-out** on QuALITY at C=1 and C=4, and on GSM8K at C=1 (expected below 5%).
5. **Rule 5 lines.**
   - L1+L2 and L3a send the same requests with the same seeds as BASE, so their final answers should mostly agree with BASE. They can differ only through batching nondeterminism, and the disagreement rate measures that noise floor.
   - L3 changes prompts. Its accuracy change is the number the guardrail is about.

## Known issues for the full runs

- **QuALITY sample size.** The validation split has 2086 questions but only 115 distinct
  stories, and train has 150. The pilot takes one question per story, so problems never share
  a cached story. The preregistered 300 problems under load would require either several
  questions per story, which lets problems share cache across tasks and must be reported, or
  drawing from train and validation together (265 stories). Decide this and log it as a dated
  preregistration revision.
- **Prompts.** They approximate the released debate code (Du et al.). The preregistered
  baseline must run the released code itself.
- **Pilot scale.** One seed, tens of problems, and C at most 4. The bootstrap bounds are
  indicative only.
