#!/bin/bash
# Separate 20-story three-seed C=1 quality check; exploratory, not pooled with load runs.
set -euo pipefail
cd "$HOME/scratch/dlt-proj"
source "$HOME/scratch/dlt-venv/bin/activate"
export HF_HOME="$HOME/scratch/hf"
OUT=results/pilot/pilot_6847083_c1_seeds.jsonl
[ ! -e "$OUT" ] || exit 1
DEADLINE=$(date -d '2026-11-07 01:10:00 UTC' +%s)
SERVER_PID=""
cleanup() {
 if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT
cmd=$(python -m models.serve_vllm --model llama-3.1-8b --prefix-caching --dry-run)
VLLM_SERVER_DEV_MODE=1 $cmd > logs/pilot_6847083_c1_seeds_server.log 2>&1 & SERVER_PID=$!
until curl -sf --max-time 3 localhost:8000/health >/dev/null; do
 kill -0 "$SERVER_PID" || exit 1
 [ "$(date +%s)" -lt "$DEADLINE" ] || exit 1
 sleep 5
done
for seed in 0 1 2; do
 for mode in seq par; do
  remain=$(( DEADLINE-$(date +%s)-30 ))
  [ "$remain" -gt 90 ] || { echo '!! time budget exhausted'; exit 1; }
  echo "== C=1 $mode seed=$seed n=20 at $(date -Is)"
  timeout --signal=TERM "$remain" python -m pilot.debate --task quality --mode "$mode" --apc on \
   --n 20 --conc 1 --seed "$seed" --problem-seed 0 --record-inputs --model llama-3.1-8b --out "$OUT"
 done
done
echo "== C1 seeds done in ${SECONDS}s"
