#!/bin/bash
#SBATCH --job-name=kitaev-lsweep
#SBATCH --partition=paul            # Leipzig SC CPU partition (paula/clara are GPU)
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16          # Aer MPS + BLAS threads for the trajectory batches
#SBATCH --mem=16G                   # matrix-free: MPS is 2^reps, not 4^L -- modest RAM
#SBATCH --time=24:00:00             # L=4..10 ~ 26 min; cost grows fast with L and depth
#SBATCH --output=logs/lsweep-%j.out
#SBATCH --error=logs/lsweep-%j.err
#
# Large-L scaling sweep for the Block-4 noisy edge-string diagnostic.
#
# This is the matrix-free path (src/block4_scaling.py): no 2^L ED reference and
# no 4^L density matrix, so it is CPU-bound (MPS statevector contractions +
# stochastic-Kraus trajectories) and runs on the paul CPU nodes. The old dense
# density-matrix study capped at ~L=15 (~17 GB); this reaches much larger L on
# ordinary RAM. GPU nodes buy nothing here -- the cost is many small MPS sims.
#
# Submit:   sbatch scripts/lsweep.slurm
# Override: LMAX=20 NTRAJ=32000 STARTS=8 sbatch scripts/lsweep.slurm
#
set -euo pipefail

# --- environment -------------------------------------------------------------
# Repo root = the directory this script's parent lives in (scripts/..).
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
mkdir -p logs plots

# Project virtualenv. On the cluster this path may differ from the workstation's
# /opt/python-envs/myenv; override with `VENV=/path/to/venv sbatch ...`.
VENV="${VENV:-/opt/python-envs/myenv}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Keep BLAS/OpenMP from oversubscribing beyond the allocation.
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"
export OPENBLAS_NUM_THREADS="$OMP_NUM_THREADS"
export MKL_NUM_THREADS="$OMP_NUM_THREADS"

# --- sweep parameters (override via env at submit time) -----------------------
LMIN="${LMIN:-4}"
LMAX="${LMAX:-16}"
REPS="${REPS:-2 3 4 5 6 7}"         # depth family for panel A (space-separated)
MU="${MU:-0.5}"                     # gapped topological point; NOT the degenerate mu=0
PCX="${PCX:-0.05}"
STARTS="${STARTS:-8}"
MAXITER="${MAXITER:-800}"           # L-BFGS-B iterations per start
NTRAJ="${NTRAJ:-16000}"

echo "host=$(hostname)  repo=$REPO  venv=$VENV  threads=$OMP_NUM_THREADS"
echo "L=$LMIN..$LMAX reps=[$REPS] mu=$MU p_cx=$PCX starts=$STARTS maxiter=$MAXITER n_traj=$NTRAJ"

# Sanity-check the matrix-free primitives before the (long) sweep.
python -u src/block4_scaling.py --selftest

# The sweep. Writes plots/block4_scaling_Lsweep.pdf and caches the data as
# plots/block4_scaling_data.npz (replot locally with --replot). $REPS is
# intentionally unquoted so the space-separated family expands into argv.
# shellcheck disable=SC2086
python -u src/block4_scaling.py \
    --Lmin "$LMIN" --Lmax "$LMAX" --reps $REPS --mu "$MU" --p-cx "$PCX" \
    --starts "$STARTS" --maxiter "$MAXITER" --n-traj "$NTRAJ"

echo "done: plots/block4_scaling_Lsweep.pdf (+ plots/block4_scaling_data.npz)"
