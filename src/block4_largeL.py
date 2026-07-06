"""Fixed-depth (reps=4) topological edge string vs chain length L on REAL IBM
devices, pushed to larger L than the dense study reached.

Distinct from block4_scaling: NO exact-GS reference and NO toy noise -- just the
device-calibrated noisy edge string of a fixed-depth preparation, to test how far
the topological signature survives on real hardware (does the ~0.5 edge-string
plateau seen at L<=16 hold, or decay?).

theta strategy -- INCREMENTAL GROWTH (validated):
  One-shot bulk-tiling of a small-L optimum FAILS (a big jump collapses the
  string order, edge -> 0). But a small +2 tiling is a good warm start
  (edge ~0.7) that re-optimization recovers to ~0.97. So we grow the chain in +2
  steps from a small cold-optimized reference, tiling then re-optimizing at each
  step and carrying theta forward. The growth pass is inherently SERIAL (each L
  depends on the previous); the device noisy sims that follow are parallel.

Cost / practical ceiling:
  Expectations switch from the 2^L statevector (exact, fast below ~L=14, but
  ~160 ms/eval by L=16 and exploding as 2^L) to the MPS backend (chi<=2^4=16,
  ~L-independent per call) above `--mps-from`. The re-optimization is the binding
  cost: L-BFGS-B's numerical gradient is O(n_params)=O(5L) evals per step, so the
  serial growth pass is comfortable to L~30 and heavy beyond ~L=40. For genuine
  L~100 a gradient-light optimizer (SPSA) or an exact free-fermion / matchgate
  preparation is the right tool -- see the note. The noisy MPS-trajectory sim
  itself is polynomial and cheap at any L.

Devices (need >= L qubits): FakeWashingtonV2 (127q), FakeBrooklynV2 /
FakeManhattanV2 (65q, L<=65). Each runs over its supported range.

Run:
  python src/block4_largeL.py --selftest
  python src/block4_largeL.py --backends FakeBrooklynV2 FakeWashingtonV2 \
      --L 8 12 16 20 24 28 --workers 16
  sbatch scripts/largeL.slurm
"""
import argparse
import os
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from block3_core import T, DELTA, vqe_ansatz, qubit_hamiltonian, edge_string, parity
from block4 import _transpiled
from block4_scaling import (_expect, device_noise_model, _resolve_device,
                            noisy_edge_mps, _THREAD_VARS)
from utils import setup_style, save_fig, COLORS, clean_axes


REPS = 4          # fixed ansatz depth (chi <= 2^4 = 16, flat in L)
MU = 0.5          # gapped topological point (not the degenerate mu=0)
LAM = 1.0         # parity penalty
GROW_START = 8    # cold-optimize the reference here, then grow in +2 steps
MPS_FROM = 16     # use the MPS backend for expectations at L >= this (2^L too slow)

_MPS = AerSimulator(method='matrix_product_state')


# ── expectations: statevector (small L) or MPS (large L) ───────────────────────

def _expect_L(L, theta, op, use_mps, reps=REPS):
    """<op> of the ansatz state; MPS backend (chi-bounded, polynomial) when
    use_mps else the 2^L statevector (exact, fast only for small L)."""
    a = vqe_ansatz(L, reps)
    if use_mps:
        qc = _transpiled(a, theta)
        qc.save_expectation_value(op, range(op.num_qubits))
        return float(np.real(_MPS.run(qc).result().data(0)['expectation_value']))
    return _expect(Statevector(a.assign_parameters(theta)), op)


def noiseless_edge(L, theta, use_mps=True, reps=REPS):
    """Noiseless |<O_edge>| of the (grown) ansatz state -- the state-quality
    check recorded at every L. Not the exact GS."""
    return abs(_expect_L(L, theta, edge_string(L), use_mps, reps))


# ── theta by incremental growth ────────────────────────────────────────────────

def pad_bulk(theta, L, Lnew, reps=REPS, cell=2):
    """Grow an EfficientSU2(L, reps) angle vector to length Lnew by repeating a
    `cell`-site bulk unit from the middle of each rotation layer; the two edge
    regions are kept verbatim. Good only for SMALL Lnew-L (a +2 step); a large
    jump collapses the string order."""
    layers = np.asarray(theta, float).reshape(reps + 1, L)
    dL = Lnew - L
    if dL <= 0:
        return np.asarray(theta, float)
    mid = L // 2
    out = []
    for row in layers:
        unit = row[mid:mid + cell]
        fill = np.tile(unit, int(np.ceil(dL / cell)))[:dL]
        out.append(np.concatenate([row[:mid], fill, row[mid:]]))
    return np.concatenate(out)


def _optimize(L, x0, use_mps, maxiter, reps=REPS, lam=LAM, mu=MU, t=T, delta=DELTA):
    """One L-BFGS-B run of <H> + lam*(1-<P>)^2 from x0; returns (theta, edge, P)."""
    H, P, O = qubit_hamiltonian(L, t, mu, delta), parity(L), edge_string(L)

    if maxiter <= 0:
        th = np.asarray(x0, float)
        return (th, abs(_expect_L(L, th, O, use_mps, reps)),
                _expect_L(L, th, P, use_mps, reps))

    def cost(th):
        e = _expect_L(L, th, H, use_mps, reps)
        p = _expect_L(L, th, P, use_mps, reps)
        return e + lam * (1.0 - p) ** 2

    r = minimize(cost, x0, method='L-BFGS-B', options={'maxiter': maxiter})
    return (r.x, abs(_expect_L(L, r.x, O, use_mps, reps)),
            _expect_L(L, r.x, P, use_mps, reps))


def cold_optimize(L, reps=REPS, n_starts=6, maxiter=500, seed=0):
    """Cold VQE at a small reference L (statevector). Even-sector selection."""
    a = vqe_ansatz(L, reps)
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(n_starts):
        th, edge, p = _optimize(L, rng.uniform(-np.pi, np.pi, a.num_parameters),
                                use_mps=False, maxiter=maxiter, reps=reps)
        if p >= 0.5 and (best is None or edge > best[1]):
            best = (th, edge)
    if best is None:
        th = rng.uniform(-np.pi, np.pi, a.num_parameters)
        edge = abs(_expect_L(L, th, edge_string(L), False, reps))
        best = (th, edge)
    return best


def grow_thetas(L_targets, reps=REPS, start=GROW_START, step=2, mps_from=MPS_FROM,
                cold_starts=6, cold_maxiter=500, reopt_maxiter=150, seed=0):
    """Sequentially grow theta from `start` up to max(L_targets) in +`step`
    increments (tile then re-optimize each step), recording theta at every
    requested L. Returns {L: (theta, noiseless_edge)}."""
    targets = sorted(set(int(L) for L in L_targets))
    start = min(start, targets[0])
    Lmax = targets[-1]
    if step <= 0:
        raise ValueError('growth step must be positive')

    theta, edge = cold_optimize(start, reps, cold_starts, cold_maxiter, seed)
    print(f"  [grow] cold L={start}: edge={edge:.3f}", flush=True)
    store = {}
    if start in targets:
        store[start] = (theta, edge)
    L = start
    while L < Lmax:
        Ln = min(L + step, Lmax)
        use_mps = Ln >= mps_from
        warm = pad_bulk(theta, L, Ln, reps)
        theta, edge, p = _optimize(Ln, warm, use_mps, reopt_maxiter, reps=reps)
        L = Ln
        if L in targets:
            store[L] = (theta, edge)
        print(f"  [grow] L={L:>3}  edge={edge:.3f}  P={p:+.2f}"
              f"  ({'mps' if use_mps else 'sv'})", flush=True)
    return store


# ── the (device, L) noisy sweep ────────────────────────────────────────────────

def _cell(args):
    """Worker: one (backend, L) noisy trajectory sim on a precomputed theta."""
    (backend, L, theta, reps, n_traj, seed) = args
    dev = _resolve_device(backend)
    nm, p2 = device_noise_model(dev, L)
    a = vqe_ansatz(L, reps)
    noisy, err = noisy_edge_mps(a, theta, L, nm, n_traj, seed)
    return (backend, L, noisy, err, p2)


def sweep(backends, L_list, thetas, reps=REPS, n_traj=16000, seed=100, workers=1):
    """Noisy device sweep over precomputed `thetas` {L:(theta,edge)}. For each
    backend, only L <= device qubit count."""
    ideal = {L: thetas[L][1] for L in thetas}
    tasks = []
    for b in backends:
        nq = _resolve_device(b).num_qubits
        for L in sorted(thetas):
            if L <= nq:
                tasks.append((b, L, thetas[L][0], reps, n_traj, seed))
    print(f"  [sweep] {len(tasks)} (device,L) cells over {max(1,workers)} workers",
          flush=True)

    if workers and workers > 1:
        saved = {k: os.environ.get(k) for k in _THREAD_VARS}
        for k in _THREAD_VARS:
            os.environ[k] = '1'
        try:
            results = []
            with ProcessPoolExecutor(max_workers=workers,
                                     mp_context=mp.get_context('spawn')) as ex:
                for fut in as_completed([ex.submit(_cell, a) for a in tasks]):
                    results.append(fut.result())
        finally:
            for k, v in saved.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    else:
        results = [_cell(a) for a in tasks]

    out = {b: {'L': [], 'ideal': [], 'noisy': [], 'err': [], 'p2': None} for b in backends}
    for (b, L, noisy, err, p2) in sorted(results, key=lambda r: (r[0], r[1])):
        out[b]['L'].append(L); out[b]['ideal'].append(ideal[L])
        out[b]['noisy'].append(noisy); out[b]['err'].append(err); out[b]['p2'] = p2
        print(f"  {b:16s} L={L:>3}  edge_ideal={ideal[L]:.3f}  "
              f"noisy={noisy:.3f}+-{err:.3f}", flush=True)
    for b in out:
        for k in ('L', 'ideal', 'noisy', 'err'):
            out[b][k] = np.array(out[b][k])
    return out


CACHE = 'plots/block4_largeL_data.npz'
FIG = 'block4_largeL_device.pdf'


def save_sweep(data, path=CACHE):
    flat = {}
    for b, d in data.items():
        flat[f'{b}__L'] = d['L']; flat[f'{b}__ideal'] = d['ideal']
        flat[f'{b}__noisy'] = d['noisy']; flat[f'{b}__err'] = d['err']
        flat[f'{b}__p2'] = np.array(d['p2'] if d['p2'] is not None else np.nan)
    flat['backends'] = np.array(list(data.keys()))
    np.savez(path, **flat)
    print(f"  [cached] {path}", flush=True)


def load_sweep(path=CACHE):
    z = np.load(path, allow_pickle=True)
    data = {}
    for b in z['backends']:
        b = str(b)
        data[b] = {'L': z[f'{b}__L'], 'ideal': z[f'{b}__ideal'],
                   'noisy': z[f'{b}__noisy'], 'err': z[f'{b}__err'],
                   'p2': float(z[f'{b}__p2'])}
    return data


def render(data):
    setup_style()
    plt.rcParams.update({'axes.grid': False, 'axes.facecolor': 'white',
                         'figure.facecolor': 'white'})
    fig, ax = plt.subplots(figsize=(9.0, 5.4))
    anyb = next(iter(data.values()))
    ax.plot(anyb['L'], anyb['ideal'], color='black', lw=1.4, ls='--', marker='D',
            ms=3, alpha=0.7, label='noiseless (grown ansatz, MPS)')
    palette = [COLORS['topological'], COLORS['trivial'], COLORS['bulk']]
    for (b, d), col in zip(data.items(), palette):
        name = b.replace('Fake', '').replace('V2', '')
        ax.errorbar(d['L'], d['noisy'], yerr=d['err'], color=col, lw=2.2, marker='o',
                    ms=5, capsize=3, label=rf'{name} ($2q$ err {d["p2"]:.1e})')
    ax.set_xlabel(r'chain length $L$')
    ax.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$ (noisy, $r=4$)')
    ax.set_ylim(-0.02, 1.02)
    ax.set_title(r'Fixed-depth ($r=4$) topological edge string on real IBM devices')
    ax.legend(fontsize=9, frameon=False)
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, FIG)


# ── validation ──────────────────────────────────────────────────────────────

def _selftest():
    """MPS==statevector at r=4; incremental growth keeps the edge high; device
    2q channels extract from Washington/Brooklyn."""
    ok = True
    print("(a) MPS noiseless edge vs statevector (r=4)")
    rng = np.random.default_rng(1)
    for L in (6, 8):
        a = vqe_ansatz(L, REPS)
        th = rng.uniform(-np.pi, np.pi, a.num_parameters)
        d = abs(_expect_L(L, th, edge_string(L), True)
                - _expect_L(L, th, edge_string(L), False))
        ok = ok and d < 1e-6
        print(f"   L={L}  |sv-mps|={d:.1e}")

    print("(b) incremental growth mechanics (start=6 -> 10, no reopt)")
    store = grow_thetas([6, 8, 10], start=6, cold_starts=1, cold_maxiter=1,
                        reopt_maxiter=0, mps_from=8)
    for L in sorted(store):
        ok = ok and np.isfinite(store[L][1])
    print(f"   edges: " + ", ".join(f"L{L}={store[L][1]:.3f}" for L in sorted(store)))

    print("(c) device 2q channels")
    for name in ('FakeBrooklynV2', 'FakeWashingtonV2'):
        try:
            _, p2 = device_noise_model(_resolve_device(name), 12)
            print(f"   {name}: 2q_err={p2:.2e}")
        except Exception as ex:
            ok = False; print(f"   {name}: FAILED {ex}")
    print("\nSELF-TEST", "PASSED" if ok else "FAILED")
    return ok


def build_parser():
    p = argparse.ArgumentParser(description='Fixed-r=4 large-L edge string on real IBM devices.')
    p.add_argument('--selftest', action='store_true')
    p.add_argument('--replot', action='store_true')
    p.add_argument('--backends', nargs='+', default=['FakeBrooklynV2', 'FakeWashingtonV2'])
    p.add_argument('--L', nargs='+', type=int, default=[8, 12, 16, 20, 24, 28])
    p.add_argument('--reps', type=int, default=REPS)
    p.add_argument('--grow-start', type=int, default=GROW_START)
    p.add_argument('--growth-step', type=int, default=2)
    p.add_argument('--mps-from', type=int, default=MPS_FROM)
    p.add_argument('--cold-starts', type=int, default=6)
    p.add_argument('--cold-maxiter', type=int, default=500)
    p.add_argument('--reopt-maxiter', type=int, default=150)
    p.add_argument('--n-traj', type=int, default=16000)
    p.add_argument('--seed', type=int, default=100)
    p.add_argument('--workers', type=int, default=1)
    return p


def main():
    args = build_parser().parse_args()
    if args.selftest:
        _selftest(); return
    if args.replot:
        render(load_sweep()); print('Done.'); return
    print(f'growing theta for L={sorted(set(args.L))} (serial)...', flush=True)
    thetas = grow_thetas(args.L, reps=args.reps, start=args.grow_start,
                         step=args.growth_step, mps_from=args.mps_from,
                         cold_starts=args.cold_starts, cold_maxiter=args.cold_maxiter,
                         reopt_maxiter=args.reopt_maxiter, seed=args.seed)
    print()
    data = sweep(args.backends, tuple(args.L), thetas, reps=args.reps,
                 n_traj=args.n_traj, seed=args.seed, workers=args.workers)
    save_sweep(data)
    render(data)
    print('Done.')


if __name__ == '__main__':
    main()
