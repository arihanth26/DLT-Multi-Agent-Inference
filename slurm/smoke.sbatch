#!/bin/bash
# GPU smoke test (~15 min): one vLLM server (prefix caching on), 2 problems per workload.
# Checks the full path on this account before any real run: debate on GSM8K and QuALITY, and the
# supply-chain workflow (seq, par, l3), plus the dossier's real token count.
#
#   sbatch slurm/smoke.sbatch           (from the repository root, after: source <DLT>/env.sh)
#
#SBATCH --job-name=dlt-smoke
#SBATCH -q coc-ice
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:45:00
#SBATCH --exclude=atl1-1-03-012-3-0
#SBATCH --output=logs/smoke_%j.out

set -uo pipefail
cd "${SLURM_SUBMIT_DIR:-.}"
: "${DLT:?source env.sh before sbatch}"
source "$DLT/dlt-venv/bin/activate"
export HF_HOME="$DLT/hf" HF_HUB_OFFLINE=1
JOB="${SLURM_JOB_ID:-local$(date +%s)}"
OUT=results/smoke/smoke_${JOB}
mkdir -p logs results/smoke

echo "host $(hostname) commit $(git rev-parse --short HEAD)"
nvidia-smi --query-gpu=name,uuid,memory.total --format=csv,noheader
python -c "import vllm; print('vllm', vllm.__version__)"

CMD=$(python -m models.serve_vllm --model llama-3.1-8b --prefix-caching --dry-run)
VLLM_SERVER_DEV_MODE=1 $CMD > "logs/smoke_server_${JOB}.log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null' EXIT
until curl -sf localhost:8000/health >/dev/null; do
  kill -0 $SERVER_PID 2>/dev/null || { echo "server died:"; tail -40 "logs/smoke_server_${JOB}.log"; exit 1; }
  sleep 5
done
echo "== server up after ${SECONDS}s"

python - <<'PY'
from transformers import AutoTokenizer
from data.supply_chain.generate import load_scenarios
from pilot.supply_chain import base_prompt
tok = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
n = sorted(len(tok(base_prompt(p))["input_ids"]) for p in load_scenarios(20, 0))
print(f"== SCD shared prefix tokens: min {n[0]} median {n[10]} max {n[-1]}")
PY

FAIL=0
python -m pilot.debate --task gsm8k   --mode par --apc on --n 2 --out "${OUT}_debate.jsonl" || FAIL=1
python -m pilot.debate --task quality --mode par --apc on --n 2 --out "${OUT}_debate.jsonl" || FAIL=1
for M in seq par l3; do
  python -m pilot.supply_chain --mode $M --apc on --n 2 --record-inputs --out "${OUT}_scd.jsonl" || FAIL=1
done
echo "== records: debate $(wc -l < ${OUT}_debate.jsonl), scd $(wc -l < ${OUT}_scd.jsonl) (expect 4 and 6)"
[ $FAIL -eq 0 ] && echo "== smoke OK in ${SECONDS}s" || { echo "!! smoke FAILED"; exit 1; }
