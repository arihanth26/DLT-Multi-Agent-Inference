#!/bin/bash
# Final-results campaign: does as much of the remaining grid as one GPU allocation allows, in
# priority order, and resumes where it stopped when resubmitted.
#
#   source <DLT>/env.sh && cd <repo>
#   sbatch slurm/campaign.sbatch                                   # H100 (as in the proposal)
#   sbatch --gres=gpu:a100:1 slurm/campaign.sbatch                 # A100 (logged revision)
#   ONLY=c1 sbatch ...      # restrict to one phase: c1 | noise | load | scd
#
# Resume: a configuration is one file results/final_<GPU>/<name>.jsonl. Complete files are
# skipped; a partial file (job hit its time limit) is moved to *.partial.<job> and rerun.
# Several jobs on the same GPU type split the work: each configuration is claimed with a lock
# directory naming the job; a lock whose job is no longer in squeue is taken over.
# Results go to a directory named after the GPU model, so H100 and A100 runs never mix.
#
#SBATCH --job-name=dlt-final
#SBATCH -q coc-ice
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --exclude=atl1-1-03-012-3-0
#SBATCH --output=logs/final_%j.out

set -uo pipefail
cd "${SLURM_SUBMIT_DIR:-.}"
: "${DLT:?source env.sh before sbatch}"
source "$DLT/dlt-venv/bin/activate"
export HF_HOME="$DLT/hf" HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1
JOB="${SLURM_JOB_ID:-local$(date +%s)}"
ONLY="${ONLY:-all}"
GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | cut -d, -f1 | tr -c 'A-Za-z0-9\n' '-' | sed 's/-*$//')
DIR="results/final_${GPU}"
mkdir -p logs "$DIR"
{
  echo "job $JOB host $(hostname) commit $(git rev-parse --short HEAD) dirty=$(git status --porcelain | wc -l)"
  nvidia-smi --query-gpu=name,uuid,memory.total,driver_version --format=csv,noheader
  python -c "import vllm; print('vllm', vllm.__version__)"
  echo "cpus ${SLURM_CPUS_PER_TASK:-?} only=$ONLY"
} | tee -a "$DIR/env_${JOB}.txt"

# ----------------------------------------------------------------------------- server
SERVER_PID=""; SERVER_APC=""
stop_server() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null && wait "$SERVER_PID" 2>/dev/null
  SERVER_PID=""; SERVER_APC=""; sleep 5
}
ensure_server() {  # $1 = on | off
  [ "$SERVER_APC" = "$1" ] && return 0
  stop_server
  local flag; [ "$1" = on ] && flag=--prefix-caching || flag=--no-prefix-caching
  local cmd; cmd=$(python -m models.serve_vllm --model llama-3.1-8b $flag --dry-run)
  local log="logs/final_server_${JOB}_apc$1.log"
  echo "== $(date +%T) starting server APC=$1"
  VLLM_SERVER_DEV_MODE=1 $cmd > "$log" 2>&1 &
  SERVER_PID=$!
  until curl -sf localhost:8000/health >/dev/null; do
    kill -0 "$SERVER_PID" 2>/dev/null || { echo "server died:"; tail -40 "$log"; exit 1; }
    sleep 5
  done
  SERVER_APC=$1
  echo "== $(date +%T) server up"
}
trap stop_server EXIT

# ----------------------------------------------------------------------------- one configuration
DONE=0; SKIPPED=0; FAILED=0
claim() {  # $1 = lock dir; succeeds if this job now owns it
  if mkdir "$1" 2>/dev/null; then echo "$JOB" > "$1/job"; return 0; fi
  local owner; owner=$(cat "$1/job" 2>/dev/null)
  [ "$owner" = "$JOB" ] && return 0
  if [ -n "$owner" ] && [ -z "$(squeue -h -j "$owner" 2>/dev/null)" ]; then
    echo "$JOB" > "$1/job"; return 0                       # stale lock: its job is gone
  fi
  return 1
}
cfg() {  # name apc n -- command...
  local name=$1 apc=$2 n=$3; shift 4
  local out="$DIR/$name.jsonl" lock="$DIR/$name.lock"
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -ge "$n" ]; then SKIPPED=$((SKIPPED + 1)); return; fi
  claim "$lock" || { echo "-- $name: claimed by another job"; return; }
  [ -f "$out" ] && mv "$out" "$out.partial.$JOB"
  ensure_server "$apc"
  echo "== $(date +%T) $name"
  if "$@" --out "$out"; then DONE=$((DONE + 1)); else echo "!! failed: $name"; FAILED=$((FAILED + 1)); fi
  rm -rf "$lock"
}
debate() {  # task mode apc n conc seed [extra...]
  local t=$1 m=$2 a=$3 n=$4 c=$5 s=$6; shift 6
  cfg "${t}_${m}_apc${a}_C${c}_s${s}${TAG:-}" "$a" "$n" -- \
    python -m pilot.debate --task "$t" --mode "$m" --apc "$a" --n "$n" --conc "$c" --seed "$s" "$@"
}
scd() {  # mode apc n conc seed
  cfg "scd_${1}_apc${2}_C${4}_s${5}" "$2" "$3" -- \
    python -m pilot.supply_chain --mode "$1" --apc "$2" --n "$3" --conc "$4" --seed "$5" --record-inputs
}
want() { [ "$ONLY" = all ] || [ "$ONLY" = "$1" ]; }

# ----------------------------------------------------------------------------- phases, by priority
# Within each block the caching-ON configurations come first, so the server restarts once.
c1_seed() {  # preregistered C=1 headline: 100 problems per task, all 7 configurations
  local s=$1
  for t in gsm8k quality; do for m in seq par l3a l3 single; do debate $t $m on 100 1 $s --record-inputs; done; done
  for t in gsm8k quality; do for m in seq par; do debate $t $m off 100 1 $s --record-inputs; done; done
}
want c1 && c1_seed 0
# Noise floor for the guardrail (revision 2): BASE repeated on the same problems and seed.
want noise && for t in gsm8k quality; do TAG=_repeat debate $t seq on 100 1 0 --record-inputs; done
want c1 && { c1_seed 1; c1_seed 2; }
if want load; then  # load sweep: 300 GSM8K, 265 QuALITY (revision 1); 6 configurations
  for c in 16 32 4; do
    for t in gsm8k quality; do
      n=$([ $t = gsm8k ] && echo 300 || echo 265)
      for m in seq par l3a l3; do debate $t $m on $n $c 0; done
      for m in seq par; do debate $t $m off $n $c 0; done
    done
  done
fi
if want scd; then  # exploratory extension
  for m in seq par l3a l3 single; do scd $m on 100 1 0; done
  for m in seq par; do scd $m off 100 1 0; done
  for m in seq par l3; do scd $m on 300 16 0; done
  scd par off 300 16 0
fi

echo "== $(date +%T) finished: $DONE run, $SKIPPED already complete, $FAILED failed (dir $DIR)"
[ "$FAILED" -eq 0 ]
