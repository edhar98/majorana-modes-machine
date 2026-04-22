"""
block1.py — Block 1 runner: generates physics-bridge plots.

Usage:
    python block1.py                     # generate all plots
    python block1.py --plots 1 3         # only plots 1 and 3
    python block1.py --list              # list available plots
    python block1.py --L 50 --plots 4   # override chain length for plot 4
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from utils        import setup_style, save_fig, COLORS
from kitaev_chain import KitaevChain
from bdg_bulk     import bulk_energy, bulk_gap, bdg_vector, critical_mu
from winding      import winding_number, winding_scan

# ── Shared defaults ───────────────────────────────────────────────────────────
T     = 1.0
DELTA = 1.0

CASES = [
    (dict(mu=-3.0), 'trivial',     r'Trivial $\mu = -3t$'),
    (dict(mu=-2.0), 'critical',    r'Critical $\mu = -2t$'),
    (dict(mu=-1.0), 'topological', r'Topological $\mu = -t$'),
    (dict(mu=0.0),  'topological', r'Topological $\mu = 0$'),
]

PLOT_REGISTRY = {}   # filled by @plot decorator below


def plot(n, description):
    """Register a plotting function under its number and description."""
    def decorator(fn):
        PLOT_REGISTRY[n] = (fn, description)
        return fn
    return decorator


# ── Plot functions ────────────────────────────────────────────────────────────

@plot(1, "Bulk BdG dispersion E(k) vs k")
def plot_bulk_dispersion(t=T, delta=DELTA, **_):
    k_arr = np.linspace(-np.pi, np.pi, 600)
    fig, ax = plt.subplots(figsize=(7, 4.5))

    for params, phase, label in CASES:
        mu = params['mu']
        E  = bulk_energy(k_arr, mu, t, delta)
        ax.plot(k_arr / np.pi,  E, color=COLORS[phase], label=label)
        ax.plot(k_arr / np.pi, -E, color=COLORS[phase], alpha=0.35, lw=1.2)

    ax.axhline(0, color='k', lw=0.8, ls=':')
    ax.set_xlabel(r'$k\,/\,\pi$')
    ax.set_ylabel(r'$E_k$')
    ax.set_title(r'Bulk BdG dispersion  ($t = \Delta = 1$)')
    ax.legend(loc='upper center')
    ax.set_xlim(-1, 1)

    save_fig(fig, 'block1_01_bulk_dispersion.pdf')


@plot(2, "Continuous deformation of d-vector trajectory (mu sweep)")
def plot_trajectory_deformation(t=T, delta=0.5, **_):
    """
    Shows how the Hamiltonian loop deforms and crosses the origin.
    This integrates the logic from your provided snippet.
    """
    k = np.linspace(-np.pi, np.pi, 300)

    fig, ax = plt.subplots(figsize=(7, 7))

    for params, phase, label in CASES:
        mu_val = params['mu']
        nz, ny = bdg_vector(k, mu_val, t, delta)
        ls = '--' if phase == 'critical' else (':' if phase == 'trivial' else '-')
        ax.plot(nz, ny, label=label, color=COLORS[phase], ls=ls, lw=2)

    # Mark the origin (The Singularity)
    ax.scatter([0], [0], color='black', s=100, zorder=5) 
    ax.annotate("The 'Singularity' (E=0)", (0.1, 0.1), fontsize=10, fontweight='bold')
    
    ax.axhline(0, color='k', lw=0.5, alpha=0.5)
    ax.axvline(0, color='k', lw=0.5, alpha=0.5)
    
    ax.set_xlabel('$n_z(k)$')
    ax.set_ylabel('$n_y(k)$')
    ax.set_title(f"Continuous Deformation ($t={t}, \Delta={delta}$)")
    ax.legend(loc='upper right', fontsize=9)
    ax.set_aspect('equal')
    
    # Save using your existing utility
    save_fig(fig, 'block1_07_trajectory_deformation.pdf')


@plot(3, "Phase diagram: bulk gap + winding number vs mu")
def plot_phase_diagram(t=T, delta=DELTA, **_):
    mu_scan      = np.linspace(-4.5 * t, 4.5 * t, 400)
    mu_c1, mu_c2 = critical_mu(t)

    gaps = np.array([bulk_gap(mu, t, delta) for mu in mu_scan])
    nus  = winding_scan(mu_scan, t, delta)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True,
                                    gridspec_kw={'hspace': 0.08})

    ax1.plot(mu_scan / t, gaps, 'k', lw=2)
    ax1.set_ylabel(r'Bulk gap  $E_\mathrm{gap}$')
    ax1.set_title(r'Phase diagram of the Kitaev chain  ($t = \Delta = 1$)')
    ax1.set_ylim(bottom=0)

    ax2.step(mu_scan / t, nus, color='steelblue', lw=2, where='mid')
    ax2.set_xlabel(r'$\mu\,/\,t$')
    ax2.set_ylabel(r'Winding number $\nu$')
    ax2.set_yticks([0, 1])
    ax2.set_ylim(-0.3, 1.5)

    for ax in (ax1, ax2):
        ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color='steelblue',
                   label=r'topological ($|\mu| < 2t$)')
        ax.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
        ax.axvline(mu_c2 / t, color='gray', ls='--', lw=1)

    ax1.legend(loc='upper right')

    save_fig(fig, 'block1_03_phase_diagram.pdf')


@plot(4, "Finite-size spectrum: lowest quasiparticle energies vs mu (OBC)")
def plot_finite_size_spectrum(t=T, delta=DELTA, L=30, **_):
    mu_c1, mu_c2 = critical_mu(t)
    mu_fs  = np.linspace(-4.5 * t, 4.5 * t, 300)
    N_SHOW = 12

    evals_fs = np.zeros((len(mu_fs), N_SHOW))
    for i, mu in enumerate(mu_fs):
        chain        = KitaevChain(L=L, t=t, mu=mu, delta=delta)
        evals_fs[i]  = chain.positive_spectrum()[:N_SHOW]

    fig, ax = plt.subplots(figsize=(9, 4.5))

    ax.plot(mu_fs / t, evals_fs[:, 0], color=COLORS['edge'], lw=2,
            label='near-zero (edge) mode', zorder=3)
    for i in range(1, N_SHOW):
        ax.plot(mu_fs / t, evals_fs[:, i], color=COLORS['bulk'],
                lw=1.2, alpha=0.7, label='bulk bands' if i == 1 else None)

    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color='steelblue',
               label='topological')
    ax.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
    ax.axvline(mu_c2 / t, color='gray', ls='--', lw=1)
    ax.axhline(0, color='k', lw=0.7, ls=':')

    ax.set_xlabel(r'$\mu\,/\,t$')
    ax.set_ylabel(r'Quasiparticle energy $E_n$')
    ax.set_title(f'Finite-size BdG spectrum  ($L = {L}$, OBC,  $t = \\Delta = 1$)')
    ax.set_ylim(bottom=0)
    ax.legend()

    save_fig(fig, f'block1_04_finite_size_spectrum.pdf')


@plot(5, "Real-space eigenvalue snapshot: trivial vs topological")
def plot_realspace_snapshot(t=T, delta=DELTA, L=20, **_):
    snap_cases = [CASES[0], CASES[2]]
    fig, axes  = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)

    for ax, (params, phase, label) in zip(axes, snap_cases):
        mu     = params['mu']
        chain  = KitaevChain(L=L, t=t, mu=mu, delta=delta)
        evals  = chain.spectrum()
        colors_pt = [COLORS['edge'] if abs(e) < 0.05 else COLORS[phase]
                     for e in evals]
        ax.scatter(np.arange(len(evals)), evals, c=colors_pt, s=25, zorder=3)
        ax.axhline(0, color='k', lw=0.8, ls='--')
        ax.set_xlabel('Eigenvalue index')
        ax.set_title(label)

    axes[0].set_ylabel('Energy $E$')
    edge_patch = mpatches.Patch(color=COLORS['edge'], label='near-zero mode')
    fig.legend(handles=[edge_patch], loc='lower center', frameon=True)
    fig.suptitle(rf'Full BdG spectrum in real space  ($L = {L}$, OBC)', fontsize=14)
    fig.tight_layout(rect=[0, 0.06, 1, 1])

    save_fig(fig, f'block1_05_realspace_snapshot.pdf')


@plot(6, "Majorana splitting E0 vs chain length L (semilog)")
def plot_majorana_splitting(t=T, delta=DELTA, L=100, **_):
    mu_cases = [
        (dict(mu=-0.5), 'topological', r'$\mu = -0.5t$'),
        (dict(mu=-1.0), 'topological', r'$\mu = -t$'),
        (dict(mu=-1.5), 'topological', r'$\mu = -1.5t$'),
    ]
    L_arr = np.arange(4, L + 1, 2)

    fig, ax = plt.subplots(figsize=(8, 5))

    for params, _, label in mu_cases:
        mu     = params['mu']
        E0_arr = np.array([
            np.sort(np.abs(KitaevChain(L=l, t=t, mu=mu, delta=delta).spectrum()))[0]
            for l in L_arr
        ])
        theory = 2 * t * (abs(mu) / (2 * t)) ** L_arr

        line, = ax.semilogy(L_arr, E0_arr, 'o-', ms=4, label=f'numerical  {label}')
        ax.semilogy(L_arr, theory, '--', color=line.get_color(), lw=1.2, alpha=0.6,
                    label=r'$2t\,(|\mu|/2t)^L$  ' + label)

    ax.set_xlabel('Chain length $L$')
    ax.set_ylabel('Near-zero mode energy $E_0$')
    ax.set_title(r'Majorana hybridization splitting  ($t = \Delta = 1$, OBC)')
    ax.legend(fontsize=9)

    save_fig(fig, 'block1_06_majorana_splitting.pdf')



# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description='Generate Block 1 (physics bridge) plots for the Kitaev chain.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--plots', nargs='+', type=int, metavar='N',
        help='plot numbers to generate (default: all)',
    )
    parser.add_argument(
        '--list', action='store_true',
        help='list available plots and exit',
    )
    parser.add_argument('--L',     type=int,   default=30,  help='chain length (default: 30)')
    parser.add_argument('--t',     type=float, default=T,   help='hopping amplitude (default: 1.0)')
    parser.add_argument('--delta', type=float, default=DELTA, help='pairing amplitude (default: 1.0)')
    return parser


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.list:
        print("Available plots:")
        for n, (_, desc) in sorted(PLOT_REGISTRY.items()):
            print(f"  {n}  {desc}")
        return

    setup_style()

    targets = sorted(args.plots) if args.plots else sorted(PLOT_REGISTRY)
    kwargs  = dict(t=args.t, delta=args.delta, L=args.L)

    print(f"Generating plots: {targets}\n")
    for n in targets:
        if n not in PLOT_REGISTRY:
            print(f"  [skip] no plot #{n}")
            continue
        fn, desc = PLOT_REGISTRY[n]
        print(f"  [{n}] {desc}")
        fn(**kwargs)

    print("\nDone.")


if __name__ == '__main__':
    main()
