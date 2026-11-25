#!/bin/bash
# Initial-results pilot for the approved proposal: debate on GSM8K and QuALITY, Llama-3.1-8B on
# one H100, the L1 x L2 factorial at C=1, L3a/L3 on top of L1+L2, a C=4 load point, and a
# single-agent reference. Writes results/pilot/pilot_<job>.jsonl and a summary next to it.
#
# Batch:        sbatch slurm/pilot.sbatch
# Smoke test:   NG=2 NQ=2 sbatch --time=00:30:00 slurm/pilot.sbatch
# Inside salloc: bash slurm/pilot.sbatch          (the #SBATCH lines are then just comments)
# Dev model:    MODEL=llama-3.2-1b sbatch slurm/pilot.sbatch
#
#SBATCH --job-name=dlt-pilot
#SBATCH -q coc-ice
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --exclude=atl1-1-03-012-3-0
#SBATCH --output=logs/pilot_%j.out

set -uo pipefail
cd "${SLURM_SUBMIT_DIR:-.}"
source "${VENV:-$HOME/scratch/dlt-venv}/bin/activate"
export HF_HOME="${HF_HOME:-$HOME/scratch/hf}"

MODEL="${MODEL:-llama-3.1-8b}"
NG="${NG:-30}"          # GSM8K problems per configuration
NQ="${NQ:-20}"          # QuALITY problems per configuration
JOB="${SLURM_JOB_ID:-local$(date +%s)}"
OUT="${OUT:-results/pilot/pilot_${JOB}.jsonl}"
mkdir -p logs results/pilot

{
  echo "host $(hostname)"; echo "commit $(git rev-parse --short HEAD 2>/dev/null)"
  nvidia-smi --query-gpu=name,uuid,memory.total,driver_version --format=csv,noheader
  python -c "import vllm; print('vllm', vllm.__version__)"
  echo "model $MODEL NG=$NG NQ=$NQ"
} | tee "${OUT%.jsonl}_env.txt"

SERVER_PID=""
FAILED_CONFIGS=0
stop_server() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null && wait "$SERVER_PID" 2>/dev/null
  # only this job's own server is stopped (never pkill: it could hit other jobs of the same user)
  SERVER_PID=""; sleep 10
}
trap stop_server EXIT

start_server() {  # $1 = on | off (prefix caching)
  local flag; [ "$1" = on ] && flag=--prefix-caching || flag=--no-prefix-caching
  local cmd; cmd=$(python -m models.serve_vllm --model "$MODEL" $flag --dry-run)
  local log="logs/pilot_server_apc_${1}_${JOB}.log"
  echo "== starting server, APC=$1: $cmd"
  VLLM_SERVER_DEV_MODE=1 $cmd > "$log" 2>&1 &
  SERVER_PID=$!
  until curl -sf localhost:8000/health > /dev/null; do
    kill -0 "$SERVER_PID" 2>/dev/null || { echo "server died:"; tail -40 "$log"; exit 1; }
    sleep 5
  done
  echo "== server up after ${SECONDS}s total"
}

run() {  # task mode apc n conc
  python -m pilot.debate --task "$1" --mode "$2" --apc "$3" --n "$4" --conc "$5" \
    --model "$MODEL" --out "$OUT" || {
      echo "!! failed: $*"
      FAILED_CONFIGS=$((FAILED_CONFIGS + 1))
    }
}

# --- Prefix caching ON: BASE, L1+L2, L3a, L3, single agent; then C=4 ---
start_server on
for T in gsm8k quality; do
  N=$([ "$T" = gsm8k ] && echo "$NG" || echo "$NQ")
  for M in seq par l3a l3 single; do run "$T" "$M" on "$N" 1; done
done
for M in seq par l3; do run quality "$M" on "$NQ" 4; done
stop_server

# --- Prefix caching OFF: neither lever, L1 only; then C=4 (for L2 leave-one-out) ---
start_server off
for T in gsm8k quality; do
  N=$([ "$T" = gsm8k ] && echo "$NG" || echo "$NQ")
  for M in seq par; do run "$T" "$M" off "$N" 1; done
done
run quality par off "$NQ" 4
stop_server

python -m pilot.summarize "$OUT" | tee "${OUT%.jsonl}_summary.md" || exit 1
if [ "$FAILED_CONFIGS" -ne 0 ]; then
  echo "!! incomplete: $FAILED_CONFIGS configurations failed"
  exit 1
fi
echo "== done in ${SECONDS}s"
