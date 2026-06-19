import argparse
from itertools import product

import numpy as np
import matplotlib.pyplot as plt
from qiskit.quantum_info import SparsePauliOp

from block3_core import (
    T, DELTA,
    qubit_hamiltonian, edge_string, parity,
    ed_even_ground_state, shot_estimate,
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
                  shots=args.shots, seed=args.seed)

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
