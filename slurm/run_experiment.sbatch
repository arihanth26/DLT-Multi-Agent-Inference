#!/bin/bash
#SBATCH --job-name=dlt-experiment
#SBATCH --output=logs/exp_%j.out
#SBATCH --error=logs/exp_%j.err
#SBATCH --gres=gpu:A100:2
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --time=4:00:00
#SBATCH --partition=ice-gpu

# ---------------------------------------------------------------------------
# Usage:
#   sbatch slurm/run_experiment.sbatch \
#          configs/ablation_debate.yaml C0 0 results/runs/debate_C0_seed0
#
# Positional args:  CONFIG  CONFIG_NAME  SEED  RUN_DIR
#
# This script:
#   1. Starts both vLLM servers (large on GPU 0, small on GPU 1)
#   2. Waits until both are healthy
#   3. Runs the experiment
#   4. Shuts down the servers
# ---------------------------------------------------------------------------

set -euo pipefail

CONFIG=${1:-configs/ablation_debate.yaml}
CONFIG_NAME=${2:-C0}
SEED=${3:-0}
RUN_DIR=${4:-results/runs/debate_${CONFIG_NAME}_seed${SEED}}

REPO=~/scratch/projects/cse8803_project/DLT-Multi-Agent-Inference
CONDA_ENV=/home/hice1/mjadhav6/scratch/conda-envs/cse8803
export HF_HOME=/home/hice1/mjadhav6/scratch/hf_cache

echo "=== DLT experiment ==="
echo "CONFIG:       $CONFIG"
echo "CONFIG_NAME:  $CONFIG_NAME"
echo "SEED:         $SEED"
echo "RUN_DIR:      $RUN_DIR"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"
echo "NODE:         $(hostname)"
echo "GPUs:         $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"

cd "$REPO"
mkdir -p logs "$RUN_DIR"

# Activate conda env
module load anaconda3
source activate "$CONDA_ENV"

# --- Start vLLM servers ---
echo "=== Starting vLLM servers ==="

CUDA_VISIBLE_DEVICES=0 vllm serve Qwen/Qwen3-14B \
    --port 8000 \
    --gpu-memory-utilization 0.90 \
    --enable-prefix-caching \
    --max-model-len 32768 \
    > logs/vllm_large_${SLURM_JOB_ID}.log 2>&1 &
LARGE_PID=$!

CUDA_VISIBLE_DEVICES=1 vllm serve Qwen/Qwen3-1.7B \
    --port 8001 \
    --gpu-memory-utilization 0.90 \
    --no-enable-prefix-caching \
    --max-model-len 32768 \
    > logs/vllm_small_${SLURM_JOB_ID}.log 2>&1 &
SMALL_PID=$!

# Shut down servers on exit (success or failure)
trap "echo 'Shutting down vLLM servers...'; kill $LARGE_PID $SMALL_PID 2>/dev/null; wait" EXIT

# --- Wait for servers to be healthy ---
echo "=== Waiting for servers to be ready ==="

wait_for_server() {
    local port=$1
    local name=$2
    local max_wait=300  # 5 minutes
    local elapsed=0
    echo "Waiting for $name on port $port..."
    while ! curl -sf "http://localhost:$port/health" > /dev/null 2>&1; do
        sleep 10
        elapsed=$((elapsed + 10))
        if [ $elapsed -ge $max_wait ]; then
            echo "ERROR: $name did not start within ${max_wait}s"
            exit 1
        fi
        echo "  ... still waiting ($elapsed s)"
    done
    echo "OK: $name is ready"
}

wait_for_server 8000 "qwen3-14b"
wait_for_server 8001 "qwen3-1.7b"

# --- Run experiment ---
echo "=== Running experiment: $CONFIG_NAME seed=$SEED ==="

python -m harness.runner \
    --config "$CONFIG" \
    --config-name "$CONFIG_NAME" \
    --seed "$SEED" \
    --run-dir "$RUN_DIR"

echo "=== Done: results saved to $RUN_DIR ==="
