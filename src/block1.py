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
from matplotlib.lines import Line2D  # Added for custom legends in plot 8

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

# ── Utility function to forcefully clean grid and background ──────────────────
def clean_axes(ax):
    """Forcefully remove grids, reset background to white, and restore borders."""
    ax.grid(False, which='both', axis='both') # Forcefully turn off both major and minor grid lines
    ax.set_facecolor('white')                 # Force the background to pure white (removes gray backgrounds)
    for spine in ax.spines.values():
        spine.set_visible(True)               # Restore the surrounding borders (spines)
        spine.set_color('black')
        spine.set_linewidth(0.8)


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
    
    clean_axes(ax)
    save_fig(fig, 'block1_01_bulk_dispersion.pdf')


@plot(2, "Continuous deformation of d-vector trajectory (mu sweep)")
def plot_trajectory_deformation(t=T, delta=0.5, **_):
    k = np.linspace(-np.pi, np.pi, 300)
    fig, ax = plt.subplots(figsize=(7, 7))

    for params, phase, label in CASES:
        mu_val = params['mu']
        nz, ny = bdg_vector(k, mu_val, t, delta)
        ls = '--' if phase == 'critical' else (':' if phase == 'trivial' else '-')
        ax.plot(nz, ny, label=label, color=COLORS[phase], ls=ls, lw=2)

    ax.scatter([0], [0], color='black', s=100, zorder=5) 
    ax.annotate("The 'Singularity' (E=0)", (0.1, 0.1), fontsize=10, fontweight='bold')
    
    ax.axhline(0, color='k', lw=0.5, alpha=0.5)
    ax.axvline(0, color='k', lw=0.5, alpha=0.5)
    
    ax.set_xlabel('$n_z(k)$')
    ax.set_ylabel('$n_y(k)$')
    ax.set_title(f"Continuous Deformation ($t={t}, \Delta={delta}$)")
    ax.legend(loc='upper right', fontsize=9)
    ax.set_aspect('equal')
    
    clean_axes(ax)
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
        clean_axes(ax)

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
    
    clean_axes(ax)
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
        clean_axes(ax)

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
    
    clean_axes(ax)
    save_fig(fig, 'block1_06_majorana_splitting.pdf')


@plot(7, "Bulk dispersion 1x3 panels (Topological, Critical, Trivial)")
def plot_bulk_dispersion_panels(t=T, delta=DELTA, **_):
    """
    Shows the BdG spectrum E_k vs k across three representative phases.
    Adapted from the original bulk_dispersion.py script.
    """
    mu_values = {
        'Topological ($|\mu| < 2t$)': 0.0,
        'Critical ($|\mu| = 2t$)': 2.0 * t,
        'Trivial ($|\mu| > 2t$)': 3.0 * t
    }
    k = np.linspace(-np.pi, np.pi, 500)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    fig.suptitle(rf'Bulk Dispersion of the 1D Kitaev Chain ($t={t}, \Delta={delta}$)', fontsize=16)
    
    for ax, (phase_name, mu) in zip(axes, mu_values.items()):
        # Calculate n_z(k) and n_y(k) directly or via bdg_vector
        n_z, n_y = bdg_vector(k, mu, t, delta)
        E_k = np.sqrt(n_z**2 + n_y**2)
        
        ax.plot(k, E_k, color='blue', linewidth=2, label=r'$+E_k$ (Particle)')
        ax.plot(k, -E_k, color='red', linewidth=2, label=r'$-E_k$ (Hole)')
        
        ax.axhline(0, color='black', linestyle='--', linewidth=0.8)
        ax.axvline(0, color='gray', linestyle=':', linewidth=0.8)
        
        ax.set_title(rf'{phase_name}, $\mu={mu}$', fontsize=12)
        ax.set_xlabel(r'Momentum $k$', fontsize=12)
        
        if ax == axes[0]:
            ax.set_ylabel(r'Energy $E_k / t$', fontsize=12)
        
        ax.set_xticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
        ax.set_xticklabels([r'$-\pi$', r'$-\pi/2$', r'$0$', r'$\pi/2$', r'$\pi$'])
        
        clean_axes(ax)
        
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, bbox_to_anchor=(0.5, 0.0), fontsize=12)
    plt.tight_layout(rect=[0, 0.12, 1, 0.92]) 
    
    save_fig(fig, 'block1_07_bulk_dispersion_panels.pdf')


@plot(8, "Winding loops in Complex Plane 1x3 panels")
def plot_winding_loops_panels(t=T, delta=DELTA, **_):
    """
    Shows the BdG d-vector winding trajectories across three phases.
    Adapted from the original block1_02_winding_loops.py script.
    """
    phases = [
        {'name': 'Topological', 'mu': 0.0,     'color': COLORS['topological']},
        {'name': 'Critical',    'mu': 2.0 * t, 'color': COLORS['critical']},
        {'name': 'Trivial',     'mu': 3.0 * t, 'color': COLORS['trivial']}
    ]
    k = np.linspace(-np.pi, np.pi, 2000)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(rf'Winding Loops of the 1D Kitaev Chain in Complex Plane ($t={t}, \Delta={delta}$)', fontsize=16)
    
    for ax, phase in zip(axes, phases):
        mu = phase['mu']
        n_z, n_y = bdg_vector(k, mu, t, delta)
        
        z_k = n_z + 1j * n_y
        theta_k = np.unwrap(np.angle(z_k)) 
        
        winding_number_raw = (theta_k[-1] - theta_k[0]) / (2 * np.pi)
        wind_num = int(np.round(winding_number_raw))
        
        ax.plot(n_z, n_y, color=phase['color'], linewidth=2.5)
        ax.scatter(n_z[0], n_y[0], color='black', s=50, zorder=5)
        
        idx_k0 = len(k) // 2
        ax.scatter(n_z[idx_k0], n_y[idx_k0], color='orange', s=50, marker='s', zorder=5)
        ax.scatter(0, 0, color='red', marker='*', s=150, zorder=10)
        
        ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
        ax.axvline(0, color='gray', linestyle='--', linewidth=0.8)
        
        ax.set_aspect('equal', 'box')
        ax.set_title(f"{phase['name']} Phase ($\\mu={mu}$)\nWinding Number $\\nu = {wind_num}$", fontsize=12)
        ax.set_xlabel(r'$n_z(k) = -\mu - 2t \cos k$', fontsize=12)
        
        if ax == axes[0]:
            ax.set_ylabel(r'$n_y(k) = -2\Delta \sin k$', fontsize=12)
            
        clean_axes(ax)
        
    custom_legend = [
        Line2D([0], [0], color='gray', linewidth=2.5, label='Trajectory'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='black', markersize=8, label=r'$k = \pm\pi$'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='orange', markersize=8, label=r'$k = 0$'),
        Line2D([0], [0], marker='*', color='w', markerfacecolor='red', markersize=15, label='Origin (0,0)')
    ]
    
    fig.legend(handles=custom_legend, loc='lower center', ncol=4, bbox_to_anchor=(0.5, 0.02), fontsize=11)
    fig.tight_layout(rect=[0, 0.08, 1, 0.92]) 
    
    save_fig(fig, 'block1_08_winding_loops_panels.pdf')


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description='Generate Block 1 (physics bridge) plots for the Kitaev chain.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--plots', nargs='+', type=int, metavar='N', help='plot numbers to generate (default: all)')
    parser.add_argument('--list', action='store_true', help='list available plots and exit')
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
    
    # Global brute-force reset (prevents newly popped windows from retaining theme artifacts)
    plt.rcParams.update({
        'axes.grid': False,
        'axes.facecolor': 'white',
        'axes.edgecolor': 'black',
        'figure.facecolor': 'white'
    })

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