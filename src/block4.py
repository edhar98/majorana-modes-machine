import argparse
from itertools import product

import numpy as np
import matplotlib.pyplot as plt
from qiskit import transpile
from qiskit.quantum_info import SparsePauliOp, DensityMatrix, SuperOp, Operator
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (NoiseModel, depolarizing_error, thermal_relaxation_error,
                              amplitude_damping_error, phase_damping_error)

from block3_core import (
    T, DELTA,
    qubit_hamiltonian, edge_string, parity,
    ed_even_ground_state, shot_estimate,
    vqe_ansatz, best_state,
)
from jordan_wigner import parity_gap
from bdg_bulk import critical_mu
from utils import setup_style, save_fig, COLORS, clean_axes

# Transpilation basis used everywhere so the circuit-level NoiseModel and the
# exact gate-by-gate reference act on the identical cx gate sequence.
BASIS_GATES = ['rz', 'sx', 'cx']

# Default thermal-relaxation parameters (ns); two-qubit gates are the long, noisy ones.
T1_NS = 80e3
T2_NS = 60e3
GATE_TIME_2Q_NS = 300.0

# Noise application modes used in this module:
#   circuit-level   (channel after every cx of the transpiled ansatz; accumulates with depth):
#       plots 2, 3, 6, 7(incoherent)
#   frozen-state    (single-qubit channel on the exact ground-state rho; circuit-independent):
#       plots 1, 4, 5
#   parameter-level (Gaussian angle perturbation on theta, ideal/noiseless gates):
#       plot 7 (coherent)

PLOT_REGISTRY: dict[int, tuple] = {}


def plot(n: int, description: str):
    """Register a plotting function under a numeric CLI plot id."""
    def decorator(fn):
        PLOT_REGISTRY[n] = (fn, description)
        return fn
    return decorator


def pauli_matrix(L, site_ops):
    """Build a dense L-qubit Pauli matrix from site-indexed operators."""
    label = ['I'] * L
    for site, op in site_ops.items():
        label[L - 1 - site] = op
    return SparsePauliOp([''.join(label)], [1.0]).to_matrix()


def expval_from_density(rho, O):
    """Evaluate Tr(O rho) as a real expectation value."""
    return float(np.real(np.trace(O @ rho)))


def ideal_even_density(mu, L, t, delta):
    """Return the exact even-parity ground-state density matrix."""
    H = qubit_hamiltonian(L, t, mu, delta).to_matrix()
    P = parity(L).to_matrix()
    _, psi = ed_even_ground_state(H, P)
    return np.outer(psi, psi.conj())


# ── Circuit-level noise models ────────────────────────────────────────────────

def depolarizing_noise_model(p_cx):
    """Per-cx two-qubit depolarizing noise: one channel after every entangling gate."""
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(p_cx, 2), ['cx'])
    return nm


def thermal_noise_model(t1=T1_NS, t2=T2_NS, gate_time=GATE_TIME_2Q_NS):
    """Per-cx thermal relaxation (T1 amplitude damping + T2 dephasing) on each qubit of the pair."""
    nm = NoiseModel()
    err1 = thermal_relaxation_error(t1, t2, gate_time)
    nm.add_all_qubit_quantum_error(err1.tensor(err1), ['cx'])
    return nm


def _transpiled(ansatz, theta):
    """Assign parameters and transpile to the shared basis at optimization level 0."""
    qc = ansatz.assign_parameters(theta).copy()
    return transpile(qc, basis_gates=BASIS_GATES, optimization_level=0)


def circuit_level_edge(ansatz, theta, L, noise_model):
    """Edge string from an Aer density-matrix run of the noisy preparation circuit."""
    sim = AerSimulator(method='density_matrix', noise_model=noise_model)
    qc = _transpiled(ansatz, theta)
    qc.save_density_matrix()
    rho = sim.run(qc).result().data()['density_matrix']
    edge = float(np.real(rho.expectation_value(edge_string(L))))
    n_cnot = qc.count_ops().get('cx', 0)
    return edge, np.asarray(rho.data), n_cnot


def exact_reference_edge(ansatz, theta, L, p_cx):
    """Independent exact gate-by-gate density-matrix evolution (no Aer simulator).

    Applies each gate unitary in turn and a two-qubit depolarizing SuperOp after
    every cx, reproducing what the Aer NoiseModel should do. Used to verify the
    circuit-level noise integration to machine precision.
    """
    qc = _transpiled(ansatz, theta)
    dep = SuperOp(depolarizing_error(p_cx, 2))
    dm = DensityMatrix.from_label('0' * L)
    for inst in qc.data:
        op = inst.operation
        qargs = [qc.find_bit(q).index for q in inst.qubits]
        dm = dm.evolve(Operator(op), qargs=qargs)
        if op.name == 'cx':
            dm = dm.evolve(dep, qargs=qargs)
    edge = float(np.real(dm.expectation_value(edge_string(L))))
    return edge, np.asarray(dm.data)


# ── Plot 1: standalone frozen-state isolation sweep (kept, not the Week 9 story) ──

def two_qubit_depolarizing(rho, L, site_a, site_b, p):
    """Apply a two-qubit depolarizing channel to selected lattice sites."""
    if p <= 0:
        return rho
    paulis = ('I', 'X', 'Y', 'Z')
    out = (1.0 - p) * rho
    for op_a, op_b in product(paulis, paulis):
        if op_a == 'I' and op_b == 'I':
            continue
        P = pauli_matrix(L, {site_a: op_a, site_b: op_b})
        out += (p / 15.0) * (P @ rho @ P)
    return out


def apply_gate_noise(rho, L, p_gate):
    """Apply nearest-neighbor two-qubit depolarizing noise across the chain."""
    noisy = rho
    for site in range(L - 1):
        noisy = two_qubit_depolarizing(noisy, L, site, site + 1, p_gate)
    return noisy


def symmetric_readout_scale(epsilon, weight):
    """Return Pauli-string attenuation from symmetric bit-flip readout."""
    return (1.0 - 2.0 * epsilon) ** weight


def noisy_edge_sweep(L=4, t=T, delta=DELTA, points=81, shots=4096, seed=11,
                     epsilon=0.0, p_gate=0.0, span=3.5):
    """Sweep mu on the frozen ED state: ideal, readout-only, gate-only, combined edge strings."""
    mu_values = np.linspace(-span * t, span * t, points)
    O = edge_string(L).to_matrix()
    rng = np.random.default_rng(seed)
    readout_scale = symmetric_readout_scale(epsilon, L)

    ideal, readout, gate, combined = [], [], [], []
    for mu in mu_values:
        rho = ideal_even_density(mu, L, t, delta)
        ideal_exact = expval_from_density(rho, O)
        gate_exact = expval_from_density(apply_gate_noise(rho, L, p_gate), O)
        ideal.append(abs(shot_estimate(ideal_exact, shots, rng)))
        readout.append(abs(shot_estimate(readout_scale * ideal_exact, shots, rng)))
        gate.append(abs(shot_estimate(gate_exact, shots, rng)))
        combined.append(abs(shot_estimate(readout_scale * gate_exact, shots, rng)))

    return {'mu': mu_values, 'ideal': np.array(ideal), 'readout': np.array(readout),
            'gate': np.array(gate), 'combined': np.array(combined),
            'epsilon': epsilon, 'p_gate': p_gate}


def draw_noise_panel(ax, data, t):
    """Draw one noise-setting panel for the frozen-state edge-string figure."""
    x = data['mu'] / t
    mu_c1, mu_c2 = critical_mu(t)
    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'])
    ax.axvline(mu_c1 / t, color='gray', ls=':', lw=1)
    ax.axvline(mu_c2 / t, color='gray', ls=':', lw=1)
    ideal_line, = ax.plot(x, data['ideal'], color='black', lw=1.6, label=r'ideal $+$ shots')
    readout_line, = ax.plot(x, data['readout'], color='orange', lw=0, marker='.', ms=3.2,
                            alpha=0.75, label=r'readout only')
    gate_line, = ax.plot(x, data['gate'], color=COLORS['topological'], lw=0, marker='.', ms=3.2,
                         alpha=0.75, label=r'two-qubit gates only')
    combined_line, = ax.plot(x, data['combined'], color=COLORS['trivial'], lw=1.8, label=r'combined')
    ax.set_title(rf'$\epsilon={data["epsilon"]:.2f}$, $p_{{2q}}={data["p_gate"]:.2f}$')
    ax.set_xlabel(r'$\mu/t$')
    ax.set_ylim(-0.04, 1.08)
    clean_axes(ax)
    return ideal_line, readout_line, gate_line, combined_line


# NOISE: two-qubit depolarizing (per nearest-neighbor pair) + symmetric readout.
# APPLIED: frozen-state (channels on the exact ground-state density matrix; readout
#          as a (1-2*eps)^L scale factor). Week 8 isolation sweep, not the
#          circuit-level Week 9 method.
@plot(1, 'Frozen-state isolation sweep: readout and depolarizing on the diagnostic')
def plot_frozen_noise_sweep(L=4, t=T, delta=DELTA, points=81, shots=4096, seed=11, **_):
    """Three-panel frozen even-parity state sweep (measurement-layer isolation only)."""
    settings = ((0.0, 0.0), (0.11, 0.07), (0.25, 0.15))
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0), sharey=True)
    handles = None
    for idx, (ax, (epsilon, p_gate)) in enumerate(zip(axes, settings)):
        data = noisy_edge_sweep(L=L, t=t, delta=delta, points=points, shots=shots,
                                seed=seed + idx, epsilon=epsilon, p_gate=p_gate)
        panel_handles = draw_noise_panel(ax, data, t)
        if handles is None:
            handles = panel_handles
    axes[0].set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    fig.legend(handles=handles, loc='lower center', ncol=4, fontsize=8,
               bbox_to_anchor=(0.5, 0.02), frameon=False)
    fig.suptitle(r'Readout and two-qubit depolarizing noise on the edge-string diagnostic',
                 fontsize=13, y=0.965)
    fig.tight_layout(rect=[0, 0.10, 1, 0.93])
    save_fig(fig, 'block4_week8_noise_sweep.pdf')


# ── Plot 2: noise integrated through the gates, by reps (the headline) ─────────

def depth_mu_sweep(L=4, t=T, delta=DELTA, mu_values=None, reps_list=(1, 2, 3, 4, 5),
                   p_cx=0.05, lam=0.1, seed=7, maxiter=1500, n_starts=6):
    """For each ansatz depth, prepare the VQE state across mu and measure ideal vs noisy edge string.

    The same per-cx depolarizing strength is used at every depth, so the only thing
    that changes between curves is the number of noisy CNOTs, r*(L-1).
    """
    rng = np.random.default_rng(seed)
    nm = depolarizing_noise_model(p_cx)
    results = {}
    for reps in reps_list:
        ansatz = vqe_ansatz(L, reps)
        ideal, noisy = [], []
        n_cnot = None
        for mu in mu_values:
            rec = best_state(mu, L, t, delta, ansatz, lam, rng, maxiter, n_starts)
            ideal.append(abs(float(rec['string'])))
            edge, _, n_cnot = circuit_level_edge(ansatz, rec['theta'], L, nm)
            noisy.append(abs(edge))
        results[reps] = {'ideal': np.array(ideal), 'noisy': np.array(noisy), 'n_cnot': n_cnot}
        print(f"  reps={reps:>2}  n_cnot={n_cnot:>2}  "
              f"max|O|ideal={results[reps]['ideal'].max():.3f}  "
              f"max|O|noisy={results[reps]['noisy'].max():.3f}")
    return results


# NOISE: depolarizing channel, per-cx.
# APPLIED: circuit-level (after every cx gate of the transpiled ansatz; accumulates with depth).
@plot(2, 'Edge-string phase sweep at increasing ansatz depth (reps) under per-cx noise')
def plot_depth_sweep(L=4, t=T, delta=DELTA, points=41, p_cx=0.05, reps_list=(1, 2, 3, 4, 5),
                     lam=0.1, seed=7, maxiter=1500, n_starts=6, span=3.5, **_):
    """Show the edge-string diagnostic flattening as the noisy circuit deepens."""
    mu_values = np.linspace(-span * t, span * t, points)
    results = depth_mu_sweep(L=L, t=t, delta=delta, mu_values=mu_values,
                             reps_list=tuple(reps_list), p_cx=p_cx, lam=lam,
                             seed=seed, maxiter=maxiter, n_starts=n_starts)
    x = mu_values / t
    mu_c1, mu_c2 = critical_mu(t)
    reps_sorted = sorted(results)
    cmap = plt.cm.viridis(np.linspace(0.15, 0.85, len(reps_sorted)))

    O = edge_string(L).to_matrix()
    ed_ideal = np.array([abs(expval_from_density(ideal_even_density(mu, L, t, delta), O))
                         for mu in mu_values])

    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'],
               label=r'topological $|\mu|<2t$')
    ax.axvline(mu_c1 / t, color='gray', ls=':', lw=1)
    ax.axvline(mu_c2 / t, color='gray', ls=':', lw=1)
    ax.plot(x, ed_ideal, color='black', lw=1.6, ls='--',
            label='ideal ground state (ED)')
    for reps, col in zip(reps_sorted, cmap):
        n_cnot = results[reps]['n_cnot']
        ax.plot(x, results[reps]['noisy'], color=col, lw=2.0, marker='.', ms=4,
                label=rf'$r={reps}$ ({n_cnot} CNOTs)')
    ax.set_xlabel(r'$\mu/t$')
    ax.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax.set_ylim(-0.04, 1.08)
    ax.set_title(rf'Gate noise accumulates with depth ($L={L}$, $p_{{cx}}={p_cx:.2f}$)')
    ax.legend(fontsize=8, ncol=2, frameon=False)
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, 'block4_week9_depth_sweep.pdf')


# ── Plot 6: the depth optimum at the sweet spot (factorization made explicit) ──

def depth_optimum_sweep(L=4, t=T, delta=DELTA, mu=0.0, reps_list=(1, 2, 3, 4, 5, 6),
                        p_cx=0.05, lam=0.1, seed=7, maxiter=1500, n_starts=6):
    """At a single mu, measure ideal and noisy edge string for each ansatz depth.

    Isolates the two competing factors at the sweet spot: the noiseless |O|(r)
    (expressibility) and the measured |O|(r) (expressibility x accumulated gate
    noise). Their interplay is the optimal-depth statement.
    """
    rng = np.random.default_rng(seed)
    nm = depolarizing_noise_model(p_cx)
    reps_arr, ideal, noisy, n_cnots = [], [], [], []
    for reps in reps_list:
        ansatz = vqe_ansatz(L, reps)
        rec = best_state(mu, L, t, delta, ansatz, lam, rng, maxiter, n_starts)
        edge, _, n_cnot = circuit_level_edge(ansatz, rec['theta'], L, nm)
        reps_arr.append(reps)
        ideal.append(abs(float(rec['string'])))
        noisy.append(abs(edge))
        n_cnots.append(n_cnot)
        print(f"  r={reps:>2}  n_cnot={n_cnot:>2}  |O|ideal={ideal[-1]:.3f}  |O|noisy={noisy[-1]:.3f}")
    return {'reps': np.array(reps_arr), 'ideal': np.array(ideal),
            'noisy': np.array(noisy), 'n_cnot': np.array(n_cnots),
            'mu': mu, 'p_cx': p_cx}


# NOISE: depolarizing channel, per-cx.
# APPLIED: circuit-level (after every cx gate of the transpiled ansatz; accumulates with depth).
@plot(6, 'Depth optimum at the sweet spot: expressibility threshold vs accumulated gate noise')
def plot_depth_optimum(L=4, t=T, delta=DELTA, mu_opt=0.0, p_cx=0.05,
                       reps_list=(1, 2, 3, 4, 5, 6), lam=0.1, seed=7,
                       maxiter=1500, n_starts=6, **_):
    """Single-mu view of the optimal depth: |O|ideal(r), |O|noisy(r), and the
    pure-noise envelope (1-p_cx)^{r(L-1)} that drives the post-threshold decay."""
    data = depth_optimum_sweep(L=L, t=t, delta=delta, mu=mu_opt, reps_list=tuple(reps_list),
                               p_cx=p_cx, lam=lam, seed=seed, maxiter=maxiter, n_starts=n_starts)
    r = data['reps']
    n_cnot = data['n_cnot']
    ideal = data['ideal']
    noisy = data['noisy']

    # Pure-gate-noise envelope: saturated expressibility times per-cx attenuation.
    sat = ideal.max() if ideal.size else 1.0
    envelope = sat * (1.0 - p_cx) ** n_cnot
    opt = int(r[int(np.argmax(noisy))])

    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    ax.plot(r, ideal, color='black', lw=2.0, ls='--', marker='s', ms=5,
            label=r'noiseless $|\langle O\rangle|_{\mathrm{ideal}}(r)$ (expressibility)')
    ax.plot(r, envelope, color=COLORS['bulk'], lw=1.8, ls=':', marker='^', ms=5,
            label=r'pure-noise envelope $(1-p_{cx})^{r(L-1)}$')
    ax.plot(r, noisy, color=COLORS['trivial'], lw=2.4, marker='o', ms=6,
            label=r'measured $|\langle O\rangle|_{\mathrm{meas}}(r)$')
    ax.axvline(opt, color='gray', ls='-', lw=1.0, alpha=0.6)
    ax.annotate(rf'optimal depth $r^\ast={opt}$', xy=(opt, noisy.max()),
                xytext=(opt + 0.3, noisy.max() + 0.04), fontsize=10, color=COLORS['trivial'])
    ax.set_xlabel(r'ansatz repetitions $r$')
    ax.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax.set_xticks(r)
    ax.set_ylim(-0.04, 1.12)
    ax.set_title(rf'Optimal depth at the sweet spot '
                 rf'($L={L}$, $\mu={mu_opt/t:.0f}$, $p_{{cx}}={p_cx:.2f}$)')
    ax.legend(fontsize=9, frameon=False, loc='lower center')
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, 'block4_week9_depth_optimum.pdf')


# ── Plot 7: coherent control error (theta + dtheta) vs incoherent gate noise ──

def _purity(rho):
    """Tr(rho^2) of a density matrix given as an array."""
    return float(np.real(np.trace(rho @ rho)))


def perturb_theta(theta, rng, sigma=0.0, bias=0.0):
    """Coherent control error on the VQE angles: Gaussian miscalibration (sigma)
    and/or a systematic over-rotation (bias). Returns theta* + dtheta."""
    theta = np.asarray(theta, dtype=float)
    out = theta + bias
    if sigma > 0:
        out = out + rng.normal(0.0, sigma, size=theta.shape)
    return out


def coherent_vs_incoherent_sweep(L=4, t=T, delta=DELTA, mu=0.0, reps=3,
                                 sigma_max=0.30, p_max=0.10, points=21, n_draws=16,
                                 lam=0.1, seed=7, maxiter=1500, n_starts=6):
    """At fixed mu/depth, contrast the two error types on the same prepared state.

    Coherent: the ideal (noiseless) circuit run with theta* + N(0, sigma) miscalibration,
    averaged over draws -- the state stays pure, only rotated off target. Incoherent:
    the exact theta* with per-cx depolarizing of strength p -- the state loses purity.
    A single VQE solve; everything else is a cheap density-matrix evaluation.
    """
    rng = np.random.default_rng(seed)
    ansatz = vqe_ansatz(L, reps)
    rec = best_state(mu, L, t, delta, ansatz, lam, rng, maxiter, n_starts)
    theta_star = rec['theta']
    clean_nm = NoiseModel()

    sigmas = np.linspace(0.0, sigma_max, points)
    coh_edge, coh_pur = [], []
    for s in sigmas:
        draws = 1 if s == 0 else n_draws
        e_acc, pur_acc = [], []
        for _ in range(draws):
            th = perturb_theta(theta_star, rng, sigma=s)
            e, rho, _ = circuit_level_edge(ansatz, th, L, clean_nm)
            e_acc.append(abs(e))
            pur_acc.append(_purity(rho))
        coh_edge.append(float(np.mean(e_acc)))
        coh_pur.append(float(np.mean(pur_acc)))

    ps = np.linspace(0.0, p_max, points)
    inc_edge, inc_pur = [], []
    for p in ps:
        e, rho, _ = circuit_level_edge(ansatz, theta_star, L, depolarizing_noise_model(p))
        inc_edge.append(abs(e))
        inc_pur.append(_purity(rho))

    print(f"  coherent (sigma=0..{sigma_max}): |O| {coh_edge[0]:.3f}->{coh_edge[-1]:.3f}, "
          f"purity {coh_pur[0]:.3f}->{coh_pur[-1]:.3f}")
    print(f"  incoherent (p=0..{p_max}):      |O| {inc_edge[0]:.3f}->{inc_edge[-1]:.3f}, "
          f"purity {inc_pur[0]:.3f}->{inc_pur[-1]:.3f}")
    return {'sigma': sigmas, 'p': ps,
            'coh_edge': np.array(coh_edge), 'coh_pur': np.array(coh_pur),
            'inc_edge': np.array(inc_edge), 'inc_pur': np.array(inc_pur),
            'mu': mu, 'reps': reps}


# NOISE: two modes contrasted on the same prepared state --
#   incoherent = depolarizing channel, per-cx (genuine decoherence);
#   coherent   = Gaussian angle perturbation on theta with IDEAL (noiseless) gates.
# APPLIED: incoherent = circuit-level (channel after every cx);
#          coherent   = parameter-level (perturb theta; no channel attached to gates).
@plot(7, 'Coherent control error (theta+dtheta) vs incoherent gate noise: edge string and purity')
def plot_parameter_noise(L=4, t=T, delta=DELTA, mu_opt=0.0, sigma_theta=0.30, p_check=0.10,
                         reps=3, points=21, lam=0.1, seed=7, maxiter=1500, n_starts=6, **_):
    """Two panels: coherent theta-noise (purity preserved) vs incoherent cx-noise (purity lost)."""
    data = coherent_vs_incoherent_sweep(L=L, t=t, delta=delta, mu=mu_opt, reps=reps,
                                        sigma_max=sigma_theta, p_max=p_check, points=points,
                                        lam=lam, seed=seed, maxiter=maxiter, n_starts=n_starts)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))
    ax1.plot(data['sigma'], data['coh_edge'], color=COLORS['topological'], lw=2.2,
             marker='o', ms=4, label=r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax1.plot(data['sigma'], data['coh_pur'], color=COLORS['trivial'], lw=2.2, ls='--',
             marker='s', ms=4, label=r'purity $\mathrm{Tr}\,\rho^2$')
    ax1.set_xlabel(r'control-error spread $\sigma_\theta$ (rad)')
    ax1.set_ylabel('value')
    ax1.set_title(r'Coherent: $\theta^\ast + \delta\theta$, ideal gates')
    ax1.set_ylim(-0.04, 1.08)
    ax1.legend(fontsize=9, frameon=False, loc='lower left')
    clean_axes(ax1)

    ax2.plot(data['p'], data['inc_edge'], color=COLORS['topological'], lw=2.2,
             marker='o', ms=4, label=r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax2.plot(data['p'], data['inc_pur'], color=COLORS['trivial'], lw=2.2, ls='--',
             marker='s', ms=4, label=r'purity $\mathrm{Tr}\,\rho^2$')
    ax2.set_xlabel(r'per-cx depolarizing strength $p_{cx}$')
    ax2.set_title(r'Incoherent: gate noise, exact $\theta^\ast$')
    ax2.set_ylim(-0.04, 1.08)
    ax2.legend(fontsize=9, frameon=False, loc='lower left')
    clean_axes(ax2)

    fig.suptitle(rf'Coherent control error rotates a pure state; incoherent noise mixes it '
                 rf'($L={L}$, $r={data["reps"]}$, $\mu=0$)', fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_fig(fig, 'block4_week9_parameter_noise.pdf')


# ── Plot 3: precise verification + thermal-relaxation variant ──────────────────

def verification_sweep(L=4, t=T, delta=DELTA, points=41, reps=3, p_cx=0.10,
                       t1=T1_NS, t2=T2_NS, gate_time=GATE_TIME_2Q_NS,
                       lam=0.1, seed=7, maxiter=1500, n_starts=6, span=3.5):
    """Across mu: exact-vs-Aer depolarizing agreement, plus depolarizing vs thermal edge strings."""
    mu_values = np.linspace(-span * t, span * t, points)
    rng = np.random.default_rng(seed)
    ansatz = vqe_ansatz(L, reps)
    nm_dep = depolarizing_noise_model(p_cx)
    nm_th = thermal_noise_model(t1, t2, gate_time)

    ideal, aer, exact, thermal, diff = [], [], [], [], []
    for mu in mu_values:
        rec = best_state(mu, L, t, delta, ansatz, lam, rng, maxiter, n_starts)
        theta = rec['theta']
        ideal.append(abs(float(rec['string'])))
        e_aer, _, _ = circuit_level_edge(ansatz, theta, L, nm_dep)
        e_exact, _ = exact_reference_edge(ansatz, theta, L, p_cx)
        e_th, _, _ = circuit_level_edge(ansatz, theta, L, nm_th)
        aer.append(abs(e_aer))
        exact.append(abs(e_exact))
        thermal.append(abs(e_th))
        diff.append(abs(e_aer - e_exact))

    return {'mu': mu_values, 'ideal': np.array(ideal), 'aer': np.array(aer),
            'exact': np.array(exact), 'thermal': np.array(thermal),
            'diff': np.array(diff), 'reps': reps, 'p_cx': p_cx,
            'max_diff': float(np.max(diff))}


# NOISE: LEFT comparison = depolarizing per-cx (Aer vs exact gate-by-gate reference);
#        RIGHT = thermal relaxation (T1/T2) per-cx.
# APPLIED: circuit-level (channel after every cx of the transpiled ansatz).
@plot(3, 'Exact gate-by-gate verification + thermal-relaxation (T1/T2) variant')
def plot_verification(L=4, t=T, delta=DELTA, points=41, reps=3, p_check=0.10,
                      t1=T1_NS, t2=T2_NS, gate_time=GATE_TIME_2Q_NS,
                      lam=0.1, seed=7, maxiter=1500, n_starts=6, **_):
    """Left: |Aer - exact| across mu (~machine precision). Right: depolarizing vs thermal noise."""
    data = verification_sweep(L=L, t=t, delta=delta, points=points, reps=reps, p_cx=p_check,
                              t1=t1, t2=t2, gate_time=gate_time, lam=lam, seed=seed,
                              maxiter=maxiter, n_starts=n_starts)
    print(f"  exact-vs-Aer gate-noise agreement across mu: max|diff| = {data['max_diff']:.2e}")

    x = data['mu'] / t
    mu_c1, mu_c2 = critical_mu(t)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.4))

    ax1.semilogy(x, data['diff'] + 1e-18, color='black', lw=1.6)
    ax1.set_xlabel(r'$\mu/t$')
    ax1.set_ylabel(r'$|\langle O\rangle_{\mathrm{Aer}} - \langle O\rangle_{\mathrm{exact}}|$')
    ax1.set_title(rf'Gate-noise integration verified ($r={reps}$, $p_{{cx}}={p_check:.2f}$)')
    ax1.set_ylim(1e-18, 1e-12)
    clean_axes(ax1)

    ax2.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'])
    ax2.axvline(mu_c1 / t, color='gray', ls=':', lw=1)
    ax2.axvline(mu_c2 / t, color='gray', ls=':', lw=1)
    ax2.plot(x, data['ideal'], color='black', lw=1.6, ls='--', label='ideal (noiseless)')
    ax2.plot(x, data['aer'], color=COLORS['topological'], lw=1.8, marker='.', ms=3,
             label=rf'depolarizing ($p_{{cx}}={p_check:.2f}$)')
    ax2.plot(x, data['thermal'], color=COLORS['trivial'], lw=1.8, marker='.', ms=3,
             label=r'thermal $T_1/T_2$')
    ax2.set_xlabel(r'$\mu/t$')
    ax2.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax2.set_ylim(-0.04, 1.08)
    ax2.set_title(r'Depolarizing vs thermal relaxation')
    ax2.legend(fontsize=8, frameon=False)
    clean_axes(ax2)

    fig.suptitle(r'Verified circuit-level gate noise and a physical $T_1/T_2$ model',
                 fontsize=12, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_fig(fig, 'block4_week9_verification.pdf')


# ── Plots 4-5: the professor's questions (parity protection, length influence) ──

def _depol1(p):
    return depolarizing_error(p, 1)


# Parity-preserving (phase) vs symmetric (depol) vs parity-violating (amplitude) channels.
PARITY_CHANNELS = {
    'phase': (phase_damping_error, COLORS['topological'], 'phase damping (parity-preserving)'),
    'depol': (_depol1, COLORS['bulk'], 'depolarizing (symmetric)'),
    'amp': (amplitude_damping_error, COLORS['trivial'], r'amplitude damping $T_1$ (parity-violating)'),
}


def single_qubit_channel(rho, error_1q, L):
    """Apply a single-qubit qiskit error channel independently to every qubit of rho."""
    sop = SuperOp(error_1q)
    dm = DensityMatrix(rho)
    for q in range(L):
        dm = dm.evolve(sop, qargs=[q])
    return np.asarray(dm.data)


def parity_noise_sweep(L, t, mu, delta, p_max, points):
    """Parity <P> and edge string vs noise strength on the topological ground state."""
    rho0 = ideal_even_density(mu, L, t, delta)
    P = parity(L).to_matrix()
    O = edge_string(L).to_matrix()
    ps = np.linspace(0.0, p_max, points)

    out = {'p': ps}
    for name, (efn, _, _) in PARITY_CHANNELS.items():
        par, edge = [], []
        for p in ps:
            rho = single_qubit_channel(rho0, efn(p), L)
            par.append(expval_from_density(rho, P))
            edge.append(abs(expval_from_density(rho, O)))
        out[name] = {'parity': np.array(par), 'edge': np.array(edge)}
    return out


# NOISE: three SINGLE-QUBIT channels -- phase damping, depolarizing, amplitude damping (T1).
# APPLIED: frozen-state (single-qubit channel on each qubit of the exact even-parity
#          ground-state density matrix; NOT through the ansatz circuit).
@plot(4, "Prof Q1: parity vs edge string under three noise channels (topological state)")
def plot_parity_protection(par_L=6, t=T, delta=DELTA, mu=T, p_max=0.3, points=31, **_):
    """Show parity is symmetry-protected (phase damping) while the edge string is not noise-immune."""
    data = parity_noise_sweep(par_L, t, mu, delta, p_max, points)
    p = data['p']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))
    for name, (_, color, label) in PARITY_CHANNELS.items():
        ax1.plot(p, data[name]['parity'], color=color, lw=2.2, marker='o', ms=3, label=label)
    ax1.axhline(1.0, color='gray', ls=':', lw=1.2)
    ax1.set_xlabel('noise strength $p$')
    ax1.set_ylabel(r'$\langle \hat{P} \rangle = \langle \prod_j Z_j \rangle$')
    ax1.set_title('Total fermion parity')
    ax1.set_ylim(-0.05, 1.08)
    ax1.legend(fontsize=8.5, loc='lower left')
    clean_axes(ax1)

    for name, (_, color, label) in PARITY_CHANNELS.items():
        ax2.plot(p, data[name]['edge'], color=color, lw=2.2, marker='o', ms=3, label=label)
    ax2.set_xlabel('noise strength $p$')
    ax2.set_ylabel(r'$|\langle X_0 Z\cdots Z X_{L-1} \rangle|$')
    ax2.set_title('Non-local edge string')
    ax2.set_ylim(-0.05, 1.08)
    ax2.legend(fontsize=8.5, loc='upper right')
    clean_axes(ax2)

    fig.suptitle(rf'Parity (symmetry) survives dephasing; the edge string (topology) does not '
                 rf'($L={par_L}$, $\mu={mu/t:.0f}t$)', fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, 'block4_parity_vs_noise.pdf')


def parity_length_sweep(L_list, t, mu_topo, mu_triv, delta, gamma):
    """Intrinsic parity gap vs L, and noisy poisoning / edge loss vs L at fixed channel strength."""
    L_list = list(L_list)
    amp = amplitude_damping_error(gamma)
    dep = depolarizing_error(gamma, 1)
    gap_topo, gap_triv, leak, edge_loss = [], [], [], []

    for L in L_list:
        gap_topo.append(parity_gap(L, t, mu_topo, delta))
        gap_triv.append(parity_gap(L, t, mu_triv, delta))

        rho0 = ideal_even_density(mu_topo, L, t, delta)
        P = parity(L).to_matrix()
        O = edge_string(L).to_matrix()

        rho_amp = single_qubit_channel(rho0, amp, L)
        leak.append((1.0 - expval_from_density(rho_amp, P)) / 2.0)

        rho_dep = single_qubit_channel(rho0, dep, L)
        ideal = abs(expval_from_density(rho0, O))
        noisy = abs(expval_from_density(rho_dep, O))
        edge_loss.append(1.0 - noisy / ideal if ideal > 1e-9 else 0.0)

    return {'L': np.array(L_list, dtype=float),
            'gap_topo': np.array(gap_topo), 'gap_triv': np.array(gap_triv),
            'leak': np.array(leak), 'edge_loss': np.array(edge_loss), 'gamma': gamma}


# NOISE: single-qubit amplitude damping (T1) + single-qubit depolarizing.
# APPLIED: frozen-state (single-qubit channel on each qubit of the exact
#          ground-state density matrix; NOT through the ansatz circuit).
@plot(5, "Prof Q2: intrinsic protection vs noisy vulnerability across chain length L")
def plot_length_influence(t=T, delta=DELTA, L_list=(2, 3, 4, 5, 6, 7, 8), gamma=0.1, **_):
    """Intrinsic gap improves with L while noise vulnerability worsens with L."""
    data = parity_length_sweep(L_list, t, mu_topo=t, mu_triv=3 * t, delta=delta, gamma=gamma)
    L = data['L']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))
    ax1.semilogy(L, data['gap_topo'] + 1e-18, color=COLORS['topological'], lw=2.2,
                 marker='o', label=r'topological $\mu=t$')
    ax1.semilogy(L, data['gap_triv'] + 1e-18, color=COLORS['trivial'], lw=2.2,
                 marker='s', ls='--', label=r'trivial $\mu=3t$')
    ax1.set_xlabel('chain length $L$')
    ax1.set_ylabel(r'parity gap $\Delta_P(L)$')
    ax1.set_title('Intrinsic protection improves with $L$')
    ax1.set_xticks(L)
    ax1.legend(fontsize=9)
    clean_axes(ax1)

    ax2.plot(L, data['leak'], color=COLORS['trivial'], lw=2.2, marker='o',
             label=r'odd-sector leakage, $T_1$ ($\gamma=%.2f$)' % gamma)
    ax2.plot(L, data['edge_loss'], color=COLORS['bulk'], lw=2.2, marker='s', ls='--',
             label=r'edge-string loss, depol ($p=%.2f$)' % gamma)
    ax2.set_xlabel('chain length $L$')
    ax2.set_ylabel('noise-induced failure fraction')
    ax2.set_title('Noisy vulnerability worsens with $L$')
    ax2.set_xticks(L)
    ax2.legend(fontsize=9, loc='upper left')
    clean_axes(ax2)

    fig.suptitle(r'Chain length: opposite effects under noise', fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, 'block4_length_under_noise.pdf')


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line interface for Block 4 plots."""
    p = argparse.ArgumentParser(description='Block 4 runner: circuit-level gate noise on the VQE diagnostic.')
    p.add_argument('--plots', nargs='+', type=int, metavar='N')
    p.add_argument('--list', action='store_true')
    p.add_argument('--L', type=int, default=4)
    p.add_argument('--t', type=float, default=T)
    p.add_argument('--delta', type=float, default=DELTA)
    p.add_argument('--points', type=int, default=41)
    p.add_argument('--shots', type=int, default=4096)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--p-cnot', type=float, default=0.05)
    p.add_argument('--reps', nargs='+', type=int, default=[1, 2, 3, 4, 5])
    p.add_argument('--mu-opt', type=float, default=0.0)
    p.add_argument('--sigma-theta', type=float, default=0.30,
                   help='max Gaussian control-error spread (rad) for the coherent-noise plot')
    p.add_argument('--verify-reps', type=int, default=3)
    p.add_argument('--p-check', type=float, default=0.10)
    p.add_argument('--t1', type=float, default=T1_NS)
    p.add_argument('--t2', type=float, default=T2_NS)
    p.add_argument('--gate-time', type=float, default=GATE_TIME_2Q_NS)
    p.add_argument('--maxiter', type=int, default=1500)
    p.add_argument('--starts', type=int, default=6)
    p.add_argument('--lam', type=float, default=0.1)
    p.add_argument('--par-L', type=int, default=6)
    p.add_argument('--mu', type=float, default=T)
    p.add_argument('--p-max', type=float, default=0.3)
    p.add_argument('--gamma', type=float, default=0.1)
    p.add_argument('--L-list', nargs='+', type=int, default=[2, 3, 4, 5, 6, 7, 8])
    return p


def main() -> None:
    """Parse CLI arguments and generate the requested registered plots."""
    args = build_parser().parse_args()

    if args.list:
        for n, (_, desc) in sorted(PLOT_REGISTRY.items()):
            print(f'  {n}  {desc}')
        return

    setup_style()
    plt.rcParams.update({
        'axes.grid': False,
        'axes.facecolor': 'white',
        'figure.facecolor': 'white',
    })

    targets = sorted(args.plots) if args.plots else sorted(PLOT_REGISTRY.keys())
    kwargs = dict(L=args.L, t=args.t, delta=args.delta, points=args.points,
                  shots=args.shots, seed=args.seed, p_cx=args.p_cnot,
                  reps_list=tuple(args.reps), reps=args.verify_reps, p_check=args.p_check,
                  t1=args.t1, t2=args.t2, gate_time=args.gate_time,
                  maxiter=args.maxiter, n_starts=args.starts, lam=args.lam,
                  par_L=args.par_L, mu=args.mu, mu_opt=args.mu_opt, p_max=args.p_max,
                  gamma=args.gamma, L_list=tuple(args.L_list), sigma_theta=args.sigma_theta)

    print(f'Generating plots: {targets}\n')
    for n in targets:
        if n not in PLOT_REGISTRY:
            print(f'  [skip] no plot #{n}')
            continue
        fn, desc = PLOT_REGISTRY[n]
        print(f'  [{n}] {desc}')
        fn(**kwargs)
        print()
    print('Done.')


if __name__ == '__main__':
    main()
