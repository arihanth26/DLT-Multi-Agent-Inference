#!/bin/bash
# Exploratory same-seed repeats triggered by the initial pilot's C=4 quality warnings.
set -euo pipefail
cd "$HOME/scratch/dlt-proj"
source "$HOME/scratch/dlt-venv/bin/activate"
export HF_HOME="$HOME/scratch/hf"
SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT
cmd=$(python -m models.serve_vllm --model llama-3.1-8b --prefix-caching --dry-run)
VLLM_SERVER_DEV_MODE=1 $cmd > logs/pilot_accuracy_repeat_server_6847083.log 2>&1 &
SERVER_PID=$!
until curl -sf localhost:8000/health >/dev/null; do
  kill -0 "$SERVER_PID" || exit 1
  [ "$SECONDS" -lt 600 ] || exit 1
  sleep 5
done
for REP in 1 2; do
  OUT="results/pilot/pilot_6847083_repeat${REP}.jsonl"
  [ ! -e "$OUT" ] || { echo "Refusing to append to existing repeat $OUT"; exit 1; }
  for MODE in seq par; do
    python -m pilot.debate --task quality --mode "$MODE" --apc on --n 20 --conc 4 \
      --seed 0 --problem-seed 0 --model llama-3.1-8b --out "$OUT"
  done
  python -m pilot.summarize "$OUT" > "${OUT%.jsonl}_summary.md"
done
echo "== repeat checks done in ${SECONDS}s"
