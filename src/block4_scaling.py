"""Block 4 scaling study: how the edge-string diagnostic behaves as the chain
grows, and the two distinct ways a NISQ preparation fails.

Three objects, three cost classes -- only the genuinely exponential ones are
removed:

  reference (exact ground state) -- `free_fermion.ground`, a 2L x 2L BdG matrix,
      O(L^3), exact to L ~ hundreds. This removes the 2^L ED reference entirely.

  ideal VQE state -- a 2^L statevector with sparse-Pauli expectations
      (`Statevector.expectation_value` on the SparsePauliOp H/P/O_edge). This
      never forms the 2^L x 2^L = 4^L dense Hamiltonian, so it is exact and
      ~500x faster than `.to_matrix()`; a 2^L statevector is trivial to L ~ 22
      (16 MB at L=20) and is the mild, unavoidable object. (Beyond that it MPS-
      compresses to chi ~ 2^reps; see the chi-probe note.)

  noisy VQE state -- MPS-trajectory sampling of O_edge: each shot is one
      stochastic-Kraus trajectory (a pure state, 2^L, chi <= 2^reps), and
      averaging N_traj of them is an unbiased estimator of Tr(O rho) that
      converges as 1/sqrt(N_traj). This removes the 4^L density matrix -- the
      real memory wall (~17 GB at L=15). The noise is either a toy uniform
      per-cx depolarizing channel (--p-cx) or a real IBM device's recorded
      calibration (--backend FakeCairoV2 etc.): `device_noise_model` transplants
      the device's genuine per-qubit 1q errors and a representative real 2q error
      channel onto the native linear chain (the real chips are heavy-hex, so
      from_backend alone would leave our cx pairs noiseless).

Validated by `--selftest`: the ideal expectation matches dense `.to_matrix()` to
~1e-15, and the trajectory estimator matches the exact density matrix to ~1
sigma at L <= 8.

The physics the figure shows (cross-checked against block3_core's ED optimizer;
grid extended to L=16 on the Leipzig SC cluster). The two failure modes turn out
to be DECOUPLED, and the large-L wall is noise alone:
  * Expressibility is cheap and L-INDEPENDENT. At FIXED depth the noiseless edge
    is essentially binary -- ~0.94 if the depth is adequate, ~0 (exactly) if it
    is not -- with a depth THRESHOLD that does NOT grow with L: shallow r=2,3 fail
    outright for L>=6, but a CONSTANT r*=4 already reproduces the edge string all
    the way to L=16 (r*(L)=[2,4,4,4,4,4,4] for L=4..16). Physically the edge
    Majoranas are localized at the two ends, so building them costs ~constant
    depth however long the chain between them. (Panel A. A few dips at high depth
    -- r=5@L=14, r=6/7@L=16 -- are optimizer stalls at large parameter counts,
    not physics: a smaller r succeeds at the same L.)
  * NOISE is the whole large-L story. Because r* is fixed, the CNOT count grows
    only linearly, n_cnot = r*(L-1) = 4(L-1) = 6..60 for L=4..16, yet the NOISY
    edge decays exponentially along the (1-p)^{n_cnot} envelope. Under the toy
    p=0.05 it falls 0.68 -> 0.07 over L=4..16 (effectively dead by L~14). Under a
    real device (--backend, Cairo 2q err ~7.5e-3, ~6x gentler) the same 60 CNOTs
    give ~0.6 at L=16 -- the diagnostic survives much further. (Panel B.) The
    fundamental NISQ wall here is decoherence over a linearly growing gate count,
    not a growing depth requirement.

Run:
  python src/block4_scaling.py --selftest
  python src/block4_scaling.py --Lmax 12                         # toy noise, local
  python src/block4_scaling.py --Lmax 12 --backend FakeCairoV2   # real device noise
  BACKEND=FakeCairoV2 sbatch scripts/lsweep.slurm               # larger L on HPC
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
from qiskit_aer.noise import NoiseModel

from block3_core import T, DELTA, vqe_ansatz, qubit_hamiltonian, edge_string, parity
from block4 import depolarizing_noise_model, _transpiled
import free_fermion as ff
from utils import setup_style, save_fig, COLORS, clean_axes


P_CX = 0.05                 # per-cx depolarizing strength (matches the Week 9 decks)
MU = 0.5                    # gapped topological point (|mu|<2t). NOT the sweet spot mu=0:
                            # there t=delta makes the edge Majoranas exact zero modes, the
                            # BdG state is parity-degenerate and <O_edge> is ill-defined.
REPS_FAMILY = (2, 3, 4, 5, 6)
EDGE_OK = 0.5               # noiseless edge above this counts as "adequately expressed";
                            # the edge is binary (~0 or ~0.94) so the threshold is robust.
LAM = 1.0                  # parity penalty: at mu=0.5 the parity gap is ~1e-4, so a firm
                           # penalty is needed to pin the even sector (ED-free selection).


# ── fast exact ideal expectations (2^L statevector, no 4^L dense matrix) ───────

def _sv(ansatz, theta):
    return Statevector(ansatz.assign_parameters(theta))


def _expect(sv, op):
    return float(np.real(sv.expectation_value(op)))


def optimize_fixed_reps(L, reps, mu, t=T, delta=DELTA, lam=LAM, seed=7,
                        maxiter=800, n_starts=8, e_ref=None, conv_tol=0.1):
    """Best reps-r VQE state at (mu, L), ED-free. Returns (theta, edge, energy, parity).

    Cost = <H> + lam*(1-<P>)^2 on the 2^L statevector (sparse-Pauli, no dense H),
    minimized with L-BFGS-B (reliable on the 10s-of-parameters landscape where
    COBYLA gets stuck at high depth). Selection is ED-free: among the restarts we
    keep the lowest-energy optimum in the even sector (<P> >= 0.5) -- the correct
    variational target, the lowest-energy even-parity state the depth-r ansatz can
    make (falling back to lowest cost if none reach the even sector).

    `e_ref` (the exact free-fermion ground energy -- itself ED-free) is used as a
    convergence oracle: once an even-sector optimum comes within `conv_tol` of it
    we stop restarting. Easy cells converge on the first start; genuinely hard or
    inexpressible cells (r too small) exhaust n_starts and honestly report the
    best the ansatz managed.
    """
    ansatz = vqe_ansatz(L, reps)
    H, P, O = qubit_hamiltonian(L, t, mu, delta), parity(L), edge_string(L)
    rng = np.random.default_rng(seed)

    def cost(theta):
        sv = _sv(ansatz, theta)
        return _expect(sv, H) + lam * (1.0 - _expect(sv, P)) ** 2

    best_even = None       # (energy, theta, parity, edge)
    best_any = None
    for _ in range(n_starts):
        x0 = rng.uniform(-np.pi, np.pi, ansatz.num_parameters)
        r = minimize(cost, x0, method='L-BFGS-B', options={'maxiter': maxiter})
        sv = _sv(ansatz, r.x)
        e, p, edge = _expect(sv, H), _expect(sv, P), abs(_expect(sv, O))
        cand = (e, r.x, p, edge)
        if best_any is None or e < best_any[0]:
            best_any = cand
        if p >= 0.5 and (best_even is None or e < best_even[0]):
            best_even = cand
        if (e_ref is not None and best_even is not None
                and best_even[0] - e_ref < conv_tol):
            break                                    # converged to the exact GS energy
    e, theta, p, edge = best_even if best_even is not None else best_any
    return theta, edge, e, p


def ff_reference(L, mu, t=T, delta=DELTA):
    """Exact ground-state |<O_edge>| and energy from the free-fermion BdG solver."""
    g = ff.ground(L, t, delta, mu)
    return abs(ff.edge_string(g['cov'])), g['energy']


# ── matrix-free noisy edge string (MPS trajectories) ──────────────────────────

def noisy_edge_mps(ansatz, theta, L, noise_model, n_traj=16000, seed=100):
    """Trajectory-averaged |<O_edge>| under `noise_model`, with a std-error bar.

    One run of `n_traj` stochastic-Kraus trajectories; `save_expectation_value_
    variance` returns [mean, var] with var the single-trajectory variance of
    O_edge (~1 for a Pauli). The standard error on the mean is sqrt(var/n_traj),
    matching the empirical 1/sqrt(N) convergence to the exact density matrix.
    (Re-running with a different seed_simulator does NOT decorrelate this Aer
    path, so the honest way to shrink the bar is to raise n_traj.) Cost = n_traj
    pure-state (2^L, chi<=2^reps) sims -- never the 4^L density matrix.
    """
    sim = AerSimulator(method='matrix_product_state', noise_model=noise_model)
    qc = _transpiled(ansatz, theta)
    qc.save_expectation_value_variance(edge_string(L), range(L))
    mean, var = sim.run(qc, shots=n_traj, seed_simulator=seed).result().data(0)[
        'expectation_value_variance']
    stderr = float(np.sqrt(max(var, 0.0) / n_traj))
    return abs(float(mean)), stderr


# ── device-calibrated noise (real hardware parameters) ─────────────────────────

def _resolve_device(name):
    """Instantiate a real IBM device snapshot by name (real recorded calibration)."""
    from qiskit_ibm_runtime.fake_provider import __dict__ as fp
    if name not in fp:
        raise ValueError(f"unknown device '{name}'. Examples: FakeCairoV2 (27q, "
                         f"CX-native), FakeWashingtonV2 (127q).")
    return fp[name]()


def device_noise_model(backend, L):
    """NoiseModel with the device's REAL per-gate error channels, mapped onto the
    linear chain (qubits 0..L-1).

    `NoiseModel.from_backend` carries the genuine recorded calibration -- per-qubit
    sx errors (thermal T1/T2 + gate infidelity) and per-EDGE two-qubit errors. But
    the real devices are heavy-hex, so our cx(i,i+1) are not calibrated edges and
    would otherwise get NO 2q noise. So we take the real per-qubit 1q channels for
    qubits 0..L-1 as-is, and transplant a representative (median-error) real 2q
    channel onto every cx of the chain -- real error magnitudes, applied to the
    native linear geometry. Returns (nm, twoq_error_rate).
    """
    base = NoiseModel.from_backend(backend)
    lqe = base._local_quantum_errors
    nm = NoiseModel(basis_gates=['rz', 'sx', 'cx'])

    # real per-qubit single-qubit (sx) errors for the chain's qubits
    sx_err = lqe.get('sx', {})
    for q in range(L):
        e = sx_err.get((q,))
        if e is not None:
            nm.add_quantum_error(e, 'sx', [q])

    # real two-qubit channel: the device's native 2q gate (cx on Cairo-era chips),
    # representative = the edge whose reported error is closest to the median.
    twoq = next((g for g in ('cx', 'ecr', 'cz') if lqe.get(g)), None)
    if twoq is None:
        raise RuntimeError(f'{backend.name}: no 2q error channel found')
    tgt = backend.target[twoq]
    edges = [k for k in lqe[twoq] if tgt.get(k) and tgt[k].error is not None]
    rates = np.array([tgt[k].error for k in edges])
    med = edges[int(np.argmin(np.abs(rates - np.median(rates))))]
    rep = lqe[twoq][med]
    for q in range(L - 1):
        nm.add_quantum_error(rep, 'cx', [q, q + 1])
    return nm, float(tgt[med].error)


# ── the scan ──────────────────────────────────────────────────────────────────

_THREAD_VARS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                'NUMEXPR_NUM_THREADS')


def _optimize_cell(args):
    """Worker: one (L, reps) noiseless VQE optimization. Top-level so it pickles;
    returns everything the parent needs to assemble the table and the noisy runs."""
    (L, reps, mu, t, delta, lam, seed, maxiter, n_starts, e_ref) = args
    theta, edge, energy, par = optimize_fixed_reps(
        L, reps, mu, t, delta, lam, seed, maxiter, n_starts, e_ref=e_ref)
    return (L, reps, theta, edge, energy, par)


def _run_cells_parallel(tasks, workers, on_result=None):
    """Run the (L, reps) optimizations across a spawned process pool.

    The grid is embarrassingly parallel. Each worker is pinned to a single BLAS
    thread (env set before the pool is created, inherited by the spawned
    children) so `workers` processes x 1 thread never oversubscribe the node --
    the right way to use many cores here, since one optimization is serial and
    its statevectors are too small for BLAS threading to scale. Results stream
    back via as_completed (order-independent; the parent re-sorts); `on_result`
    is called on each as it lands, for live progress."""
    saved = {k: os.environ.get(k) for k in _THREAD_VARS}
    for k in _THREAD_VARS:
        os.environ[k] = '1'
    try:
        out = []
        with ProcessPoolExecutor(max_workers=workers,
                                 mp_context=mp.get_context('spawn')) as ex:
            futures = [ex.submit(_optimize_cell, a) for a in tasks]
            for fut in as_completed(futures):
                res = fut.result()
                if on_result is not None:
                    on_result(res)
                out.append(res)
        return out
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def scan(L_list, reps_family=REPS_FAMILY, mu=MU, t=T, delta=DELTA, p_cx=P_CX,
         lam=LAM, seed=7, maxiter=800, n_starts=8, n_traj=16000, edge_ok=EDGE_OK,
         workers=1, backend=None):
    """Full scan feeding both panels.

    For every (L, reps): the ED-free noiseless edge string (a table). From it,
    r*(L) = the smallest depth whose noiseless edge clears `edge_ok`. At that
    r*(L): the noisy trajectory edge (+ error) and the CNOT count.

    The (L, reps) optimizations are the expensive, independent part; `workers>1`
    runs them across a process pool (see `_run_cells_parallel`). The fast noisy
    trajectory phase then runs serially in the main process, where Aer keeps all
    threads.
    """
    reps_sorted = sorted(reps_family)
    ff_ref = {L: ff_reference(L, mu, t, delta) for L in L_list}    # (edge, energy)
    ff_energy = {L: ff_ref[L][1] for L in L_list}

    tasks = [(L, reps, mu, t, delta, lam, seed, maxiter, n_starts, ff_energy[L])
             for L in L_list for reps in reps_sorted]

    # --- noiseless grid (parallel or serial), reporting each cell as it lands ---
    n_cells = len(tasks)
    done = [0]

    def _report(res):
        L, reps, _theta, edge, energy, par = res
        done[0] += 1
        print(f"  [{done[0]:>2}/{n_cells}] L={L:>3} r={reps}  edge={edge:.3f}  "
              f"dE={energy - ff_energy[L]:+.3f}  P={par:+.3f}", flush=True)

    if workers and workers > 1:
        print(f"  [grid] {n_cells} cells over {workers} workers", flush=True)
        results = _run_cells_parallel(tasks, workers, on_result=_report)
    else:
        results = []
        for a in tasks:
            res = _optimize_cell(a)
            _report(res)
            results.append(res)

    cell = {(L, reps): (theta, edge, energy, par)
            for (L, reps, theta, edge, energy, par) in results}
    edge_tab = {reps: np.array([cell[(L, reps)][1] for L in L_list])
                for reps in reps_sorted}

    # --- noise wall at the minimal adequate depth (serial, threaded) ---
    # Toy uniform depolarizing (p_cx) or real device-calibrated noise (backend).
    dev = _resolve_device(backend) if backend else None
    if dev is not None and max(L_list) > dev.num_qubits:
        raise ValueError(f'{backend} has {dev.num_qubits} qubits < Lmax={max(L_list)}')
    p_env = p_cx
    print(f"  [noise] {len(L_list)} trajectory runs at r*(L)", flush=True)
    r_star, noisy, err, n_cnot = [], [], [], []
    for i, L in enumerate(L_list, 1):
        adequate = [r for r in reps_sorted if cell[(L, r)][1] >= edge_ok]
        rs = min(adequate) if adequate else max(reps_sorted)
        theta = cell[(L, rs)][0]
        ansatz = vqe_ansatz(L, rs)
        if dev is not None:
            nm, p_env = device_noise_model(dev, L)     # real per-qubit + median 2q rate
        else:
            nm = depolarizing_noise_model(p_cx)
        ne, ee = noisy_edge_mps(ansatz, theta, L, nm, n_traj, seed + 100)
        nc = _transpiled(ansatz, theta).count_ops().get('cx', 0)
        r_star.append(rs); noisy.append(ne); err.append(ee); n_cnot.append(nc)
        print(f"  [{i:>2}/{len(L_list)}] L={L:>3} r*={rs}  n_cnot={nc:>3}  "
              f"ff={ff_ref[L][0]:.3f}  noisy={ne:.3f}+-{ee:.3f}", flush=True)

    noise_label = (rf'{dev.name} (real): 2q err {p_env:.1e}' if dev is not None
                   else rf'toy depol. $p_{{cx}}={p_cx:.2f}$')
    return {'L': np.array(L_list), 'reps_family': tuple(reps_family),
            'edge_tab': edge_tab,
            'ff_edge': np.array([ff_ref[L][0] for L in L_list]),
            'ff_energy': np.array([ff_energy[L] for L in L_list]),
            'r_star': np.array(r_star), 'noisy': np.array(noisy),
            'err': np.array(err), 'n_cnot': np.array(n_cnot),
            'mu': mu, 'p_cx': p_env, 'noise_label': noise_label}


CACHE = 'plots/block4_scaling_data.npz'


def _cache_path(out_tag=''):
    """npz cache path, optionally suffixed so parallel runs (e.g. different noise
    backends) do not clobber each other's data."""
    return f'plots/block4_scaling_data_{out_tag}.npz' if out_tag else CACHE


def _fig_name(out_tag=''):
    """Figure filename, suffixed to match _cache_path (see save_fig in utils)."""
    return f'block4_scaling_Lsweep_{out_tag}.pdf' if out_tag else 'block4_scaling_Lsweep.pdf'


def save_scan(data, path=CACHE):
    """Persist a scan() result so the figure can be restyled without recomputing
    (and so a long HPC scan can be replotted locally)."""
    reps = np.array(data['reps_family'])
    edge_mat = np.array([data['edge_tab'][r] for r in data['reps_family']])
    np.savez(path, L=data['L'], reps_family=reps, edge_mat=edge_mat,
             ff_edge=data['ff_edge'], ff_energy=data['ff_energy'],
             r_star=data['r_star'], noisy=data['noisy'], err=data['err'],
             n_cnot=data['n_cnot'], mu=data['mu'], p_cx=data['p_cx'],
             noise_label=data.get('noise_label', ''))
    print(f"  [cached] {path}", flush=True)


def load_scan(path=CACHE):
    """Reconstruct a scan() dict from the npz cache."""
    z = np.load(path)
    reps_family = tuple(int(r) for r in z['reps_family'])
    return {'L': z['L'], 'reps_family': reps_family,
            'edge_tab': {r: z['edge_mat'][i] for i, r in enumerate(reps_family)},
            'ff_edge': z['ff_edge'], 'ff_energy': z['ff_energy'],
            'r_star': z['r_star'], 'noisy': z['noisy'], 'err': z['err'],
            'n_cnot': z['n_cnot'], 'mu': float(z['mu']), 'p_cx': float(z['p_cx']),
            'noise_label': str(z['noise_label']) if 'noise_label' in z else ''}


def render_figure(data, t=T, out_tag=''):
    """Draw the two-panel scaling figure from a scan() (or load_scan()) dict.

    A: noiseless edge vs L, one curve per fixed depth r -- shallow depths (r=2,3)
       fail (edge -> 0) beyond L=4 while r>=4 track the free-fermion truth at a
       CONSTANT r*=4 through L=16: the depth threshold does not grow with L.
    B: at the minimal adequate depth r*(L), the free-fermion truth, the noisy
       trajectory edge (+ error bar), and the pure-noise envelope (1-p)^{r*(L-1)}
       -- the depth needed for expressibility carries the CNOTs that noise then
       washes out.
    """
    L, mu, p_cx = data['L'], data['mu'], data['p_cx']
    reps_family = data['reps_family']
    noise_label = data.get('noise_label') or rf'toy depol. $p_{{cx}}={p_cx:.2f}$'
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.0, 5.2))

    # Panel A -- expressibility threshold.
    axA.plot(L, data['ff_edge'], color='black', lw=1.8, ls='--', marker='D', ms=5,
             zorder=5, label='exact GS (free-fermion)')
    cmap = plt.cm.viridis(np.linspace(0.12, 0.85, len(reps_family)))
    for reps, col in zip(reps_family, cmap):
        axA.plot(L, data['edge_tab'][reps], color=col, lw=2.0, marker='o', ms=5,
                 label=rf'$r={reps}$')
    axA.set_xlabel(r'chain length $L$')
    axA.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$ (noiseless)')
    axA.set_xticks(L); axA.set_ylim(-0.04, 1.08)
    axA.set_title('Fixed depth: shallow circuits cannot build the edge string')
    axA.legend(fontsize=8.5, frameon=False, ncol=2, loc='center left')
    clean_axes(axA)

    # Panel B -- the noise wall at the minimal adequate depth.
    envelope = data['ff_edge'] * (1.0 - p_cx) ** data['n_cnot']
    axB.plot(L, data['ff_edge'], color='black', lw=1.8, ls='--', marker='D', ms=5,
             label='exact GS (free-fermion)')
    axB.plot(L, envelope, color=COLORS['bulk'], lw=1.6, ls=':', marker='^', ms=5,
             label=rf'2q-error envelope $(1-{p_cx:.1e})^{{r^\ast(L-1)}}$')
    axB.errorbar(L, data['noisy'], yerr=data['err'], color=COLORS['trivial'], lw=2.2,
                 marker='s', ms=6, capsize=3,
                 label=rf'noisy VQE at $r^\ast(L)$ — {noise_label}')
    for x, y, rs, nc in zip(L, data['noisy'], data['r_star'], data['n_cnot']):
        axB.annotate(rf'$r^\ast={int(rs)}$' '\n' rf'${int(nc)}$ CX', (x, y),
                     textcoords='offset points', xytext=(0, 9), ha='center',
                     fontsize=7, color=COLORS['trivial'])
    axB.set_xlabel(r'chain length $L$')
    axB.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    axB.set_xticks(L); axB.set_ylim(-0.04, 1.08)
    axB.set_title('Minimal adequate depth: noise then wins')
    axB.legend(fontsize=8.5, frameon=False, loc='upper right')
    clean_axes(axB)

    fig.suptitle(rf'Two ways a fixed-depth preparation fails as $L$ grows '
                 rf'($\mu={mu/t:.1f}t$, noise: {noise_label})', fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save_fig(fig, _fig_name(out_tag))


def plot_scaling(L_list=(4, 6, 8, 10, 12), reps_family=REPS_FAMILY, mu=MU, p_cx=P_CX,
                 lam=LAM, seed=7, maxiter=800, n_starts=8, n_traj=16000,
                 t=T, delta=DELTA, workers=1, backend=None, out_tag=''):
    """Run the scan, cache it, and render the two-panel figure."""
    data = scan(L_list, reps_family, mu, t, delta, p_cx, lam, seed, maxiter,
                n_starts, n_traj, workers=workers, backend=backend)
    save_scan(data, path=_cache_path(out_tag))
    render_figure(data, t, out_tag=out_tag)
    return data


# ── validation ────────────────────────────────────────────────────────────────

def _selftest(Ls=(4, 6, 8), p_cx=0.05, reps=3, n_traj=20000):
    """Cross-check both matrix-free primitives against the exact paths at small L."""
    from block3_core import state_vector, expval
    from block4 import circuit_level_edge

    rng = np.random.default_rng(3)
    ok = True
    print("(a) statevector sparse-Pauli expectation vs dense to_matrix  (H, O_edge)")
    print(f"{'L':>3} {'dE_H':>10} {'dEdge':>10}")
    for L in Ls:
        a = vqe_ansatz(L, reps)
        th = rng.uniform(-np.pi, np.pi, a.num_parameters)
        H, O = qubit_hamiltonian(L, T, 0.3, DELTA), edge_string(L)
        sv = _sv(a, th)
        psi = state_vector(a, th)
        dH = abs(_expect(sv, H) - expval(psi, H.to_matrix()))
        dO = abs(_expect(sv, O) - expval(psi, O.to_matrix()))
        ok = ok and dH < 1e-9 and dO < 1e-9
        print(f"{L:>3} {dH:>10.2e} {dO:>10.2e}")

    print("\n(b) MPS-trajectory noisy edge vs exact density matrix "
          f"(N_traj={n_traj}, expect diff ~ 1/sqrt(N) ~ {1/np.sqrt(n_traj):.4f})")
    print(f"{'L':>3} {'rho_edge':>10} {'traj':>10} {'err':>8} {'|diff|':>8}")
    nm = depolarizing_noise_model(p_cx)
    for L in Ls:
        a = vqe_ansatz(L, reps)
        th = rng.uniform(-np.pi, np.pi, a.num_parameters)
        edge_dm = abs(circuit_level_edge(a, th, L, nm)[0])
        traj, err = noisy_edge_mps(a, th, L, nm, n_traj=n_traj)
        diff = abs(traj - edge_dm)
        ok = ok and diff < 5 * max(err, 1e-4)
        print(f"{L:>3} {edge_dm:>10.4f} {traj:>10.4f} {err:>8.4f} {diff:>8.4f}")

    print("\nSELF-TEST", "PASSED" if ok else "FAILED")
    return ok


def build_parser():
    p = argparse.ArgumentParser(description='Block 4 scaling study: reps-family + noise wall.')
    p.add_argument('--selftest', action='store_true', help='validate the primitives at small L')
    p.add_argument('--replot', action='store_true',
                   help='re-render the figure from the cached scan (no recompute)')
    p.add_argument('--Lmax', type=int, default=12, help='largest even L in the sweep')
    p.add_argument('--Lmin', type=int, default=4)
    p.add_argument('--reps', nargs='+', type=int, default=list(REPS_FAMILY),
                   help='fixed depths for the family (panel A)')
    p.add_argument('--mu', type=float, default=MU,
                   help='chemical potential (default 0.5t, gapped topological; '
                        'avoid mu=0 where the edge modes are exact zero modes)')
    p.add_argument('--p-cx', type=float, default=P_CX)
    p.add_argument('--lam', type=float, default=LAM)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--maxiter', type=int, default=800)
    p.add_argument('--starts', type=int, default=8)
    p.add_argument('--n-traj', type=int, default=16000,
                   help='trajectories for the noisy edge string (error bar ~ 1/sqrt(n_traj))')
    p.add_argument('--workers', type=int, default=1,
                   help='parallel processes for the (L, reps) optimization grid '
                        '(1 = serial; set to the core count on HPC)')
    p.add_argument('--backend', type=str, default=None,
                   help='real IBM device snapshot for the noise model (e.g. '
                        'FakeCairoV2, FakeWashingtonV2); default = toy depolarizing --p-cx')
    p.add_argument('--out-tag', type=str, default='',
                   help='suffix for the output pdf/npz (e.g. FakeCairoV2) so parallel '
                        'runs with different noise do not overwrite each other')
    return p


def main():
    args = build_parser().parse_args()
    if args.selftest:
        _selftest()
        return
    setup_style()
    plt.rcParams.update({'axes.grid': False, 'axes.facecolor': 'white',
                         'figure.facecolor': 'white'})
    if args.replot:
        cache = _cache_path(args.out_tag)
        print(f'replotting from cache {cache}')
        render_figure(load_scan(cache), out_tag=args.out_tag)
        print('Done.')
        return
    L_list = tuple(range(args.Lmin, args.Lmax + 1, 1))
    noise = args.backend if args.backend else f'toy p_cx={args.p_cx}'
    print(f'scan L={L_list}  reps_family={tuple(args.reps)}  mu={args.mu}  '
          f'noise={noise}  workers={args.workers}\n')
    plot_scaling(L_list=L_list, reps_family=tuple(args.reps), mu=args.mu,
                 p_cx=args.p_cx, lam=args.lam, seed=args.seed, maxiter=args.maxiter,
                 n_starts=args.starts, n_traj=args.n_traj, workers=args.workers,
                 backend=args.backend, out_tag=args.out_tag)
    print('Done.')


if __name__ == '__main__':
    main()
