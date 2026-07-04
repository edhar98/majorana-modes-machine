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
# Repo root. Under Slurm the batch script runs from a spool copy, so BASH_SOURCE
# points into /var/spool and not the repo -- prefer SLURM_SUBMIT_DIR (the dir
# `sbatch` was invoked from). Fall back to scripts/.. for a direct `bash` run.
REPO="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO"
mkdir -p logs plots

# Cluster Python: load the environment module and use the user-site qiskit stack
# (installed once on the login node with `pip install --user qiskit qiskit-aer
# qiskit-algorithms`). numpy/scipy/matplotlib already live in ~/.local for py3.12.
# The compute node inherits the same module tree as the login node. Override the
# module with `PYMODULE=Python/3.13.5-GCCcore-14.3.0 sbatch ...`.
PYMODULE="${PYMODULE:-Python/3.12.3-GCCcore-13.3.0}"
set +u                              # modules.sh references unbound vars under `set -u`
source /etc/profile.d/modules.sh
module purge
module load "$PYMODULE"
set -u

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
# Noise model: empty = toy uniform depolarizing (--p-cx); or a real IBM device
# snapshot for calibrated noise, e.g. BACKEND=FakeCairoV2 (27q) or
# FakeWashingtonV2 (127q, for L>27). The device must have >= Lmax qubits.
BACKEND="${BACKEND:-}"
# Output filename tag so a device-calibrated run does not overwrite the toy run's
# plots/block4_scaling_Lsweep.pdf and _data.npz. Defaults to the backend name
# (e.g. FakeCairoV2); empty for the toy run keeps the original filenames.
OUTTAG="${OUTTAG:-$BACKEND}"
STARTS="${STARTS:-8}"
MAXITER="${MAXITER:-800}"           # L-BFGS-B iterations per start
NTRAJ="${NTRAJ:-16000}"
# One worker per core for the (L, reps) optimization grid. Each worker pins
# itself to a single BLAS thread (block4_scaling sets this during the pool), so
# WORKERS x 1 thread fills the allocation without oversubscription; the serial
# noisy phase then reclaims all $OMP_NUM_THREADS threads for Aer.
WORKERS="${WORKERS:-${SLURM_CPUS_PER_TASK:-16}}"

echo "host=$(hostname)  repo=$REPO  python=$(which python)  threads=$OMP_NUM_THREADS  workers=$WORKERS"
echo "L=$LMIN..$LMAX reps=[$REPS] mu=$MU noise=${BACKEND:-toy p_cx=$PCX} out_tag=${OUTTAG:-<none>} starts=$STARTS maxiter=$MAXITER n_traj=$NTRAJ"

# Sanity-check the matrix-free primitives before the (long) sweep.
python -u src/block4_scaling.py --selftest

# The sweep. Writes plots/block4_scaling_Lsweep.pdf and caches the data as
# plots/block4_scaling_data.npz (replot locally with --replot). $REPS is
# intentionally unquoted so the space-separated family expands into argv;
# $BACKEND adds --backend only when set (else toy depolarizing --p-cx).
# shellcheck disable=SC2086
python -u src/block4_scaling.py \
    --Lmin "$LMIN" --Lmax "$LMAX" --reps $REPS --mu "$MU" --p-cx "$PCX" \
    --starts "$STARTS" --maxiter "$MAXITER" --n-traj "$NTRAJ" --workers "$WORKERS" \
    ${BACKEND:+--backend "$BACKEND"} ${OUTTAG:+--out-tag "$OUTTAG"}

echo "done: plots/block4_scaling_Lsweep.pdf (+ plots/block4_scaling_data.npz)"
