import argparse
from itertools import product

import numpy as np
import matplotlib.pyplot as plt
from qiskit import transpile
from qiskit.quantum_info import SparsePauliOp, DensityMatrix, SuperOp, Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from block3_core import (
    T, DELTA,
    qubit_hamiltonian, edge_string, parity,
    ed_even_ground_state, shot_estimate,
    vqe_ansatz, best_state,
)
from bdg_bulk import critical_mu
from utils import setup_style, save_fig, COLORS, clean_axes

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


def ideal_even_density(mu, L, t, delta):
    """Return the exact even-parity ground-state density matrix."""
    H = qubit_hamiltonian(L, t, mu, delta).to_matrix()
    P = parity(L).to_matrix()
    _, psi = ed_even_ground_state(H, P)
    return np.outer(psi, psi.conj())


def noisy_edge_sweep(L=4, t=T, delta=DELTA, points=81, shots=4096, seed=11,
                     epsilon=0.0, p_gate=0.0, span=3.5):
    """Sweep mu and compare ideal, readout-noisy, gate-noisy, and combined edge strings."""
    mu_values = np.linspace(-span * t, span * t, points)
    O = edge_string(L).to_matrix()
    rng = np.random.default_rng(seed)
    readout_scale = symmetric_readout_scale(epsilon, L)

    ideal, readout, gate, combined = [], [], [], []
    for mu in mu_values:
        rho = ideal_even_density(mu, L, t, delta)
        ideal_exact = expval_from_density(rho, O)
        rho_gate = apply_gate_noise(rho, L, p_gate)
        gate_exact = expval_from_density(rho_gate, O)

        ideal.append(abs(shot_estimate(ideal_exact, shots, rng)))
        readout.append(abs(shot_estimate(readout_scale * ideal_exact, shots, rng)))
        gate.append(abs(shot_estimate(gate_exact, shots, rng)))
        combined.append(abs(shot_estimate(readout_scale * gate_exact, shots, rng)))

    return {
        'mu': mu_values,
        'ideal': np.array(ideal),
        'readout': np.array(readout),
        'gate': np.array(gate),
        'combined': np.array(combined),
        'epsilon': epsilon,
        'p_gate': p_gate,
    }


def expval_from_density(rho, O):
    """Evaluate Tr(O rho) as a real expectation value."""
    return float(np.real(np.trace(O @ rho)))


def draw_noise_panel(ax, data, t):
    """Draw one noise-setting panel for the Week 8 edge-string figure."""
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


@plot(1, 'Week 8: frozen-state noise sweep from the Block 3 Hamiltonian')
def plot_week8_noise_sweep(L=4, t=T, delta=DELTA, points=81, shots=4096, seed=11, **_):
    """Generate the three-panel Week 8 frozen-state noise sweep plot."""
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


def verify_channel_equivalence(p2q=0.07, seed=0):
    """Check the two-qubit block4 channel equals Qiskit depolarizing_error(16/15 p2q)."""
    rng = np.random.default_rng(seed)
    A = rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))
    rho = A @ A.conj().T
    rho = rho / np.trace(rho)
    rho_b4 = two_qubit_depolarizing(rho, 2, 0, 1, p2q)
    mapped = DensityMatrix(rho).evolve(SuperOp(depolarizing_error(16.0 / 15.0 * p2q, 2))).data
    naive = DensityMatrix(rho).evolve(SuperOp(depolarizing_error(p2q, 2))).data
    return float(np.max(np.abs(rho_b4 - mapped))), float(np.max(np.abs(rho_b4 - naive)))


def circuit_level_edge(ansatz, theta, L, p_cnot):
    """Edge string from a preparation circuit carrying depolarizing noise on every cx."""
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(p_cnot, 2), ['cx'])
    sim = AerSimulator(method='density_matrix', noise_model=nm)
    qc = ansatz.assign_parameters(theta).copy()
    qc.save_density_matrix()
    tqc = transpile(qc, sim)
    rho = sim.run(tqc).result().data()['density_matrix']
    edge = float(np.real(rho.expectation_value(edge_string(L))))
    n_cnot = tqc.count_ops().get('cx', 0)
    return edge, np.asarray(rho.data), n_cnot


def week8_frozen_edge(ansatz, theta, L, p2q):
    """Edge string from the Week 8 single-round channel on the perfect prepared state."""
    psi = Statevector(ansatz.assign_parameters(theta)).data
    rho0 = np.outer(psi, psi.conj())
    rho = apply_gate_noise(rho0, L, p2q)
    O = edge_string(L).to_matrix()
    edge = float(np.real(np.trace(O @ rho)))
    return edge, rho


def trace_distance(a, b):
    """Return the trace distance 0.5 ||a-b||_1 between two density matrices."""
    return 0.5 * float(np.sum(np.abs(np.linalg.eigvalsh(a - b))))


def depth_divergence(L=4, t=T, delta=DELTA, p_cnot=0.05, reps_list=(2, 3, 4, 5),
                     lam=0.1, seed=7, maxiter=1500, n_starts=6):
    """Compare circuit-level and Week 8 frozen-state noise at the topological point mu=0."""
    rng = np.random.default_rng(seed)
    p2q = 15.0 / 16.0 * p_cnot
    rows = []
    for reps in reps_list:
        ansatz = vqe_ansatz(L, reps)
        rec = best_state(0.0, L, t, delta, ansatz, lam, rng, maxiter, n_starts)
        theta = rec['theta']
        s_circ, rho_circ, n_cnot = circuit_level_edge(ansatz, theta, L, p_cnot)
        s_w8, rho_w8 = week8_frozen_edge(ansatz, theta, L, p2q)
        rows.append({
            'reps': reps,
            'n_cnot': n_cnot,
            's_ideal': abs(float(rec['string'])),
            'fidelity': float(rec['fidelity']),
            's_circuit': abs(s_circ),
            's_week8': abs(s_w8),
            'td': trace_distance(rho_circ, rho_w8),
        })
    return p_cnot, p2q, rows


@plot(2, 'Week 9: circuit-level gate noise vs the Week 8 frozen-state model')
def plot_week9_gate_noise(L=4, t=T, delta=DELTA, p_cnot=0.05, reps_list=(2, 3, 4, 5),
                          lam=0.1, seed=7, maxiter=1500, n_starts=6, **_):
    """Verify the gate-error channel and show the Week 8 model is depth-blind."""
    d_mapped, d_naive = verify_channel_equivalence()
    print(f'  channel equivalence: depolarizing_error(16/15 p) max|diff|={d_mapped:.2e}; '
          f'naive p max|diff|={d_naive:.2e}')

    p_cnot, p2q, rows = depth_divergence(L=L, t=t, delta=delta, p_cnot=p_cnot,
                                         reps_list=tuple(reps_list), lam=lam, seed=seed,
                                         maxiter=maxiter, n_starts=n_starts)
    print(f'  per-cx p_cnot={p_cnot:.3f}, matched Week 8 p2q={p2q:.4f}')
    for r in rows:
        print(f"  reps={r['reps']}  n_cnot={r['n_cnot']:>2}  s_ideal={r['s_ideal']:.4f}  "
              f"fid={r['fidelity']:.3f}  s_circuit={r['s_circuit']:.4f}  "
              f"s_week8={r['s_week8']:.4f}  trace_dist={r['td']:.4f}")

    n = np.array([r['n_cnot'] for r in rows])
    s_ideal = np.array([r['s_ideal'] for r in rows])
    s_circ = np.array([r['s_circuit'] for r in rows])
    s_w8 = np.array([r['s_week8'] for r in rows])
    td = np.array([r['td'] for r in rows])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.2))
    ax1.plot(n, s_ideal, color='gray', ls='--', marker='o', ms=4, label=r'ideal (noiseless)')
    ax1.plot(n, s_w8, color=COLORS['trivial'], marker='s', ms=5, label=r'Week 8 frozen-state')
    ax1.plot(n, s_circ, color=COLORS['topological'], marker='^', ms=5, label=r'circuit-level (real)')
    ax1.set_xlabel(r'number of CNOTs in preparation circuit')
    ax1.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax1.set_ylim(-0.04, 1.08)
    ax1.legend(fontsize=8, frameon=False)
    clean_axes(ax1)

    ax2.plot(n, td, color='black', marker='o', ms=5)
    ax2.set_xlabel(r'number of CNOTs in preparation circuit')
    ax2.set_ylabel(r'trace distance $D(\rho_{\mathrm{circuit}}, \rho_{\mathrm{Week\ 8}})$')
    ax2.set_ylim(bottom=0.0)
    clean_axes(ax2)

    fig.suptitle(r'Circuit-level gate noise grows with depth; the frozen-state model does not',
                 fontsize=12, y=0.97)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, 'block4_week9_gate_noise.pdf')


def qiskit_gate_noise(rho, L, p_cx):
    """Apply Qiskit's two-qubit depolarizing gate error on each NN pair to a density matrix."""
    err = SuperOp(depolarizing_error(p_cx, 2))
    dm = DensityMatrix(rho)
    for site in range(L - 1):
        dm = dm.evolve(err, qargs=[site, site + 1])
    return np.asarray(dm.data)


def protection_sweep(L=4, t=T, delta=DELTA, points=81, shots=4096, seed=11,
                     p_check=0.10, p_levels=(0.05, 0.10, 0.20), span=3.5):
    """Sweep mu on the frozen ED state; compare ideal, analytic, and Qiskit-checked edge strings."""
    mu_values = np.linspace(-span * t, span * t, points)
    O = edge_string(L).to_matrix()
    rng = np.random.default_rng(seed)

    ideal = np.empty(points)
    analytic_check = np.empty(points)
    qiskit_check = np.empty(points)
    noisy = {p: np.empty(points) for p in p_levels}

    for i, mu in enumerate(mu_values):
        rho = ideal_even_density(mu, L, t, delta)
        ideal[i] = expval_from_density(rho, O)
        analytic_check[i] = expval_from_density(apply_gate_noise(rho, L, 15.0 / 16.0 * p_check), O)
        qiskit_check[i] = expval_from_density(qiskit_gate_noise(rho, L, p_check), O)
        for p in p_levels:
            s = expval_from_density(apply_gate_noise(rho, L, 15.0 / 16.0 * p), O)
            noisy[p][i] = shot_estimate(s, shots, rng)

    return {
        'mu': mu_values,
        'ideal': ideal,
        'analytic_check': analytic_check,
        'qiskit_check': qiskit_check,
        'noisy': noisy,
        'p_check': p_check,
        'p_levels': p_levels,
        'max_diff': float(np.max(np.abs(analytic_check - qiskit_check))),
    }


@plot(3, 'Week 9: gate-error verification and topological protection across the phase diagram')
def plot_week9_protection(L=4, t=T, delta=DELTA, points=81, shots=4096, seed=11, **_):
    """Verify the gate error across mu and show the topological plateau is protected."""
    data = protection_sweep(L=L, t=t, delta=delta, points=points, shots=shots, seed=seed)
    print(f"  gate-error check across mu: max|analytic - Qiskit| = {data['max_diff']:.2e}")

    x = data['mu'] / t
    mu_c1, mu_c2 = critical_mu(t)
    step = max(1, points // 27)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.4), sharey=True)

    ax1.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'])
    ax1.axvline(mu_c1 / t, color='gray', ls=':', lw=1)
    ax1.axvline(mu_c2 / t, color='gray', ls=':', lw=1)
    ax1.plot(x, np.abs(data['ideal']), color='black', lw=1.6, label=r'ideal')
    ax1.plot(x, np.abs(data['analytic_check']), color=COLORS['critical'], lw=1.8,
             label=rf"analytic channel ($p_{{cx}}={data['p_check']:.2f}$)")
    ax1.plot(x[::step], np.abs(data['qiskit_check'])[::step], color=COLORS['trivial'],
             lw=0, marker='o', mfc='none', ms=6, label=r'Qiskit gate error')
    ax1.set_title(rf"Gate-error check (max diff ${data['max_diff']:.0e}$)")
    ax1.set_xlabel(r'$\mu/t$')
    ax1.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax1.set_ylim(-0.04, 1.08)
    ax1.legend(fontsize=8, frameon=False)
    clean_axes(ax1)

    ax2.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'])
    ax2.axvline(mu_c1 / t, color='gray', ls=':', lw=1)
    ax2.axvline(mu_c2 / t, color='gray', ls=':', lw=1)
    ax2.plot(x, np.abs(data['ideal']), color='black', lw=1.6, ls='--', label=r'ideal (no noise)')
    level_colors = (COLORS['critical'], 'darkorange', COLORS['trivial'])
    for p, col in zip(data['p_levels'], level_colors):
        ax2.plot(x, np.abs(data['noisy'][p]), color=col, lw=1.4, marker='.', ms=3,
                 alpha=0.85, label=rf'$p_{{cx}}={p:.2f}$')
    ax2.set_title(r'Topological protection of the edge string')
    ax2.set_xlabel(r'$\mu/t$')
    ax2.legend(fontsize=8, frameon=False, title=r'topological $|\mu|<2t$ shaded',
               title_fontsize=8)
    clean_axes(ax2)

    fig.suptitle(r'Verified gate error and the protected topological plateau (frozen state, shots)',
                 fontsize=12, y=0.97)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, 'block4_week9_topology_protection.pdf')


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line interface for Block 4 plots."""
    p = argparse.ArgumentParser(description='Block 4 runner: NISQ noise checks after Block 3 validation.')
    p.add_argument('--plots', nargs='+', type=int, metavar='N')
    p.add_argument('--list', action='store_true')
    p.add_argument('--L', type=int, default=4)
    p.add_argument('--t', type=float, default=T)
    p.add_argument('--delta', type=float, default=DELTA)
    p.add_argument('--points', type=int, default=81)
    p.add_argument('--shots', type=int, default=4096)
    p.add_argument('--seed', type=int, default=11)
    p.add_argument('--p-cnot', type=float, default=0.05)
    p.add_argument('--reps', nargs='+', type=int, default=[2, 3, 4, 5])
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
                  shots=args.shots, seed=args.seed,
                  p_cnot=args.p_cnot, reps_list=tuple(args.reps))

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
