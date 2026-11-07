#!/bin/bash
# Exploratory QuALITY load extension; every request/response is recorded.
set -uo pipefail
cd "$HOME/scratch/dlt-proj" || exit 1
source "$HOME/scratch/dlt-venv/bin/activate"
export HF_HOME="$HOME/scratch/hf"
STEM=pilot_6847083_extension
OUT="results/pilot/${STEM}.jsonl"
[ ! -e "$OUT" ] || { echo 'Output exists; refusing duplicate rows'; exit 1; }
END=$(( $(date +%s) + 2400 ))
SERVER_PID=""; STARTS=0; FAILED=0; APC=""
stop_server() {
 if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; fi
 SERVER_PID=""
}
trap stop_server EXIT
start_server() {
 stop_server
 APC="$1"; STARTS=$((STARTS+1))
 local flag=--prefix-caching
 [ "$APC" = off ] && flag=--no-prefix-caching
 local cmd; cmd=$(python -m models.serve_vllm --model llama-3.1-8b "$flag" --dry-run) || return 1
 local log="logs/${STEM}_server_${APC}_${STARTS}.log"
 echo "== server $APC: $cmd"
 VLLM_SERVER_DEV_MODE=1 $cmd > "$log" 2>&1 & SERVER_PID=$!
 local deadline=$(( $(date +%s)+300 ))
 until curl -sf --max-time 3 localhost:8000/health >/dev/null; do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then tail -40 "$log"; return 1; fi
  [ "$(date +%s)" -lt "$deadline" ] || return 1
  sleep 5
 done
}
run() {
 local mode="$1" conc="$2" seed="${3:-0}"
 local remaining=$(( END-$(date +%s)-60 ))
 if [ "$remaining" -lt 120 ]; then echo "== skipped budget: $mode $APC C=$conc seed=$seed"; return 0; fi
 local key="${mode}_${APC}_C${conc}_seed${seed}"
 echo "== begin $key at $(date -Is), budget ${remaining}s"
 curl -sf --max-time 10 localhost:8000/metrics > "results/pilot/${STEM}_${key}_before.prom" || true
 timeout --signal=TERM "$remaining" python -m pilot.debate --task quality --mode "$mode" --apc "$APC" \
   --n 64 --conc "$conc" --seed "$seed" --problem-seed 0 --model llama-3.1-8b --record-inputs --out "$OUT"
 local status=$?
 curl -sf --max-time 10 localhost:8000/metrics > "results/pilot/${STEM}_${key}_after.prom" || true
 if [ "$status" -ne 0 ]; then echo "!! failed $key status=$status"; FAILED=$((FAILED+1)); fi
}
{
 date -Is
 hostname
 git rev-parse HEAD
 nvidia-smi --query-gpu=name,uuid,memory.total,driver_version --format=csv,noheader
 python -c "import vllm; print('vllm',vllm.__version__)"
 echo 'One H100; 4 CPUs; 64 distinct validation stories; seed 0 priority grid; optional seeds 1,2; exploratory only.'
} > "results/pilot/${STEM}_env.txt"
git diff --binary > "results/pilot/${STEM}_source.patch"
cp pilot/debate.py "results/pilot/${STEM}_debate_source.py"
start_server on || exit 1
run seq 1; run par 1
for mode in seq par l3a l3; do run "$mode" 16; done
for mode in seq par l3; do run "$mode" 32; done
start_server off || exit 1
run par 1; run par 16; run par 32
# Additional paired seeds are secondary to the complete seed-0 load/cache grid.
if [ $(( END-$(date +%s) )) -gt 480 ]; then
 start_server on || exit 1
 for seed in 1 2; do run seq 16 "$seed"; run par 16 "$seed"; done
fi
stop_server
# The original summarizer pools seeds, so summarize seed 0 only.
python - "$OUT" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); rows=[json.loads(s) for s in p.read_text().splitlines()]
p.with_name(p.stem+'_seed0.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows if r['seed']==0))
PY
python -m pilot.summarize "${OUT%.jsonl}_seed0.jsonl" > "${OUT%.jsonl}_summary.md" || exit 1
if [ "$FAILED" -gt 0 ]; then echo "!! extension incomplete: $FAILED failed configurations"; exit 1; fi
echo "== extension done in ${SECONDS}s"
