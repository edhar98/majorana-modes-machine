#!/bin/bash
#SBATCH --job-name=kitaev-largeL
#SBATCH --partition=paul            # Leipzig SC CPU partition
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16          # workers for the (device, L) noisy-sim grid
#SBATCH --mem=24G                   # MPS is chi<=16 even at L=100; device model on 127q is modest
#SBATCH --time=12:00:00
#SBATCH --output=logs/largeL-%j.out
#SBATCH --error=logs/largeL-%j.err
#
# Fixed-depth (r=4) topological edge string vs L on REAL IBM device snapshots.
#
# src/block4_largeL.py: no exact-GS or toy reference -- just the device-calibrated
# noisy edge string of a fixed-depth preparation. The current production path
# grows theta incrementally in +2 steps, then runs the noisy MPS trajectory cells
# in parallel. For a full L=6..100 pilot, keep REOPT_MAXITER=0 first; reoptimize
# selected suspicious points later.
#
# Devices need >= L qubits: FakeWashingtonV2 (127q, only option for L>65),
# FakeBrooklynV2/FakeManhattanV2 (65q, L<=65). Both run over their supported range.
#
# Submit:   sbatch scripts/largeL.slurm
# Override: LLIST="6 8 12 16 24 32 48 64 80 100" NTRAJ=2048 REOPT_MAXITER=1 sbatch scripts/largeL.slurm
#
set -euo pipefail

REPO="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO"
mkdir -p logs plots

PYMODULE="${PYMODULE:-Python/3.12.3-GCCcore-13.3.0}"
set +u
source /etc/profile.d/modules.sh
module purge
module load "$PYMODULE"
set -u

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"
export OPENBLAS_NUM_THREADS="$OMP_NUM_THREADS"
export MKL_NUM_THREADS="$OMP_NUM_THREADS"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$REPO/.mpl-cache}"
mkdir -p "$MPLCONFIGDIR"

# --- parameters (override via env) -------------------------------------------
BACKENDS="${BACKENDS:-FakeBrooklynV2 FakeWashingtonV2}"   # 65q (L<=65) + 127q (to L=100+)
LLIST="${LLIST:-6 8 12 16 24 32 48 64 80 100}"
REPS="${REPS:-4}"
GROW_START="${GROW_START:-6}"
GROWTH_STEP="${GROWTH_STEP:-2}"
MPS_FROM="${MPS_FROM:-16}"
COLD_STARTS="${COLD_STARTS:-2}"
COLD_MAXITER="${COLD_MAXITER:-80}"
REOPT_MAXITER="${REOPT_MAXITER:-0}"       # 0 = true tile-only after the cold start
NTRAJ="${NTRAJ:-512}"                     # pilot error bar ~ 1/sqrt(NTRAJ)
WORKERS="${WORKERS:-${SLURM_CPUS_PER_TASK:-16}}"

echo "host=$(hostname)  python=$(which python)  threads=$OMP_NUM_THREADS  workers=$WORKERS"
echo "backends=[$BACKENDS]  L=[$LLIST]  reps=$REPS grow_start=$GROW_START step=$GROWTH_STEP"
echo "mps_from=$MPS_FROM cold=($COLD_STARTS,$COLD_MAXITER) reopt_maxiter=$REOPT_MAXITER n_traj=$NTRAJ"

if [[ "${RUN_SELFTEST:-1}" == "1" ]]; then
    python -u src/block4_largeL.py --selftest
fi

# The sweep. Writes plots/block4_largeL_device.pdf and plots/block4_largeL_data.npz
# (replot locally with --replot). $BACKENDS and $LLIST intentionally unquoted.
# shellcheck disable=SC2086
python -u src/block4_largeL.py \
    --backends $BACKENDS --L $LLIST --reps "$REPS" \
    --grow-start "$GROW_START" --growth-step "$GROWTH_STEP" --mps-from "$MPS_FROM" \
    --cold-starts "$COLD_STARTS" --cold-maxiter "$COLD_MAXITER" \
    --reopt-maxiter "$REOPT_MAXITER" --n-traj "$NTRAJ" --workers "$WORKERS"

echo "done: plots/block4_largeL_device.pdf (+ plots/block4_largeL_data.npz)"
