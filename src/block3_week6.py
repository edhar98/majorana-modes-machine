"""
block3_week6.py - Block 3 continuation: circuit observable phase sweep.
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt

from jordan_wigner import X, Z, I2, _kron, kitaev_qubit_hamiltonian, parity_gap, parity_operator
from bdg_bulk import critical_mu
from utils import setup_style, save_fig, COLORS

T = 1.0
DELTA = 1.0


def clean_axes(ax):
    ax.grid(False, which='both', axis='both')
    ax.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('black')
        spine.set_linewidth(0.8)


def pauli_string(ops):
    return _kron(ops)


def edge_string_operator(L):
    ops = [I2] * L
    ops[0] = X
    ops[-1] = X
    for j in range(1, L - 1):
        ops[j] = Z
    return pauli_string(ops)


def local_z_operator(L, site=0):
    ops = [I2] * L
    ops[site] = Z
    return pauli_string(ops)


def even_ground_state(H, P):
    evals, evecs = np.linalg.eigh(H)
    parities = np.real(np.einsum('ij,ij->j', evecs.conj(), P @ evecs))
    mask = parities > 0
    idx = np.arange(len(evals))[mask][np.argmin(evals[mask])]
    return evals[idx], evecs[:, idx]


def expectation(state, op):
    return float(np.real(np.vdot(state, op @ state)))


def shot_estimate(value, shots, rng):
    p_plus = np.clip((1.0 + value) / 2.0, 0.0, 1.0)
    plus = rng.binomial(shots, p_plus)
    return (2 * plus - shots) / shots


def sweep_observables(L=4, t=T, delta=DELTA, shots=4096, seed=7):
    mu_values = np.linspace(-3.5 * t, 3.5 * t, 81)
    string_op = edge_string_operator(L)
    local_op = local_z_operator(L, 0)
    P = parity_operator(L)
    rng = np.random.default_rng(seed)

    string_exact = []
    string_shot = []
    local_exact = []
    parity_gaps = []

    for mu in mu_values:
        H = kitaev_qubit_hamiltonian(L, t, mu, delta)
        _, psi = even_ground_state(H, P)
        s_val = expectation(psi, string_op)
        z_val = expectation(psi, local_op)
        string_exact.append(s_val)
        string_shot.append(shot_estimate(s_val, shots, rng))
        local_exact.append(z_val)
        parity_gaps.append(parity_gap(L, t, mu, delta))

    return {
        'mu': mu_values,
        'string_exact': np.array(string_exact),
        'string_shot': np.array(string_shot),
        'local_exact': np.array(local_exact),
        'parity_gap': np.array(parity_gaps),
    }


def plot_week6_phase_sweep(L=4, t=T, delta=DELTA, shots=4096):
    data = sweep_observables(L=L, t=t, delta=delta, shots=shots)
    mu_c1, mu_c2 = critical_mu(t)
    x = data['mu'] / t

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))

    ax = axes[0]
    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'], label=r'topological $|\mu|<2t$')
    ax.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
    ax.axvline(mu_c2 / t, color='gray', ls='--', lw=1)
    ax.plot(x, np.abs(data['string_exact']), color=COLORS['topological'], lw=2.4, label=r'exact $|\langle X_0 Z\cdots Z X_{L-1}\rangle|$')
    ax.scatter(x[::4], np.abs(data['string_shot'][::4]), color=COLORS['edge'], s=22, zorder=3, label=rf'{shots} shot estimator')
    ax.plot(x, np.abs(data['local_exact']), color=COLORS['bulk'], lw=1.6, ls=':', label=r'local $|\langle Z_0\rangle|$')
    ax.set_xlabel(r'$\mu/t$')
    ax.set_ylabel('Absolute expectation value')
    ax.set_title('Non-local correlator across the transition')
    ax.set_ylim(-0.05, 1.08)
    ax.legend(fontsize=8, loc='upper center')
    clean_axes(ax)

    ax = axes[1]
    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'])
    ax.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
    ax.axvline(mu_c2 / t, color='gray', ls='--', lw=1)
    ax.semilogy(x, data['parity_gap'] + 1e-14, color=COLORS['trivial'], lw=2.2)
    ax.set_xlabel(r'$\mu/t$')
    ax.set_ylabel(r'Parity gap $|E_0^+ - E_0^-|$')
    ax.set_title('Spectral cross-check from qubit Hamiltonian')
    clean_axes(ax)

    fig.suptitle(rf'Week 6: Measuring topology by sweeping $\mu$ ($L={L}$, $t=\Delta=1$)', fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save_fig(fig, 'block3_week6_phase_sweep.pdf')


def build_parser():
    p = argparse.ArgumentParser(description='Generate Week 6 Block 3 phase-sweep plots.')
    p.add_argument('--L', type=int, default=4)
    p.add_argument('--t', type=float, default=T)
    p.add_argument('--delta', type=float, default=DELTA)
    p.add_argument('--shots', type=int, default=4096)
    return p


def main():
    args = build_parser().parse_args()
    setup_style()
    plt.rcParams.update({
        'axes.grid': False,
        'axes.facecolor': 'white',
        'figure.facecolor': 'white',
    })
    plot_week6_phase_sweep(L=args.L, t=args.t, delta=args.delta, shots=args.shots)


if __name__ == '__main__':
    main()
