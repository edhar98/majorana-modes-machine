"""
block2.py — Block 2 runner: qubit-encoding plots for the Kitaev chain.

Usage:
    python block2.py                     # generate all plots
    python block2.py --plots 1 2         # only plots 1 and 2
    python block2.py --list              # list available plots
    python block2.py --L 12 --plots 1   # override chain length
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt

from utils         import setup_style, save_fig, COLORS
from kitaev_chain  import KitaevChain
from bdg_bulk      import critical_mu
from jordan_wigner import parity_gap

T     = 1.0
DELTA = 1.0

PLOT_REGISTRY = {}

def plot(n, description):
    def decorator(fn):
        PLOT_REGISTRY[n] = (fn, description)
        return fn
    return decorator


def clean_axes(ax):
    ax.grid(False, which='both', axis='both')
    ax.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('black')
        spine.set_linewidth(0.8)


# ── Plot functions ────────────────────────────────────────────────────────────

@plot(1, "Parity gap (qubit) vs BdG Majorana splitting — cross-check")
def plot_parity_gap_vs_bdg(t=T, delta=DELTA, L=10, **_):
    mu_c1, mu_c2 = critical_mu(t)
    mu_scan = np.linspace(-3.5 * t, 3.5 * t, 120)

    pgap = np.array([parity_gap(L, t, mu, delta) for mu in mu_scan])
    bdg  = np.array([
        np.sort(np.abs(KitaevChain(L=L, t=t, mu=mu, delta=delta).spectrum()))[0]
        for mu in mu_scan
    ])

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=False)

    for ax, data, label, col in zip(
        axes,
        [pgap, bdg],
        [r'Qubit parity gap $|E^+_0 - E^-_0|$',
         r'BdG near-zero mode $E_0$'],
        [COLORS['topological'], COLORS['edge']],
    ):
        ax.semilogy(mu_scan / t, data + 1e-30, color=col, lw=2)
        ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color='steelblue',
                   label=r'topological ($|\mu|<2t$)')
        ax.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
        ax.axvline(mu_c2 / t, color='gray', ls='--', lw=1)
        ax.set_xlabel(r'$\mu\,/\,t$')
        ax.set_ylabel('Energy (log scale)')
        ax.set_title(label, fontsize=11)
        ax.legend(fontsize=9)
        clean_axes(ax)

    fig.suptitle(
        rf'Qubit parity gap vs BdG splitting  ($L={L}$, $t=\Delta=1$, OBC)',
        fontsize=13,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, 'block2_01_parity_gap_vs_bdg.pdf')


@plot(2, "Qubit many-body spectrum: lowest levels per parity sector vs mu")
def plot_qubit_spectrum(t=T, delta=DELTA, L=8, **_):
    mu_c1, mu_c2 = critical_mu(t)
    mu_scan = np.linspace(-3.5 * t, 3.5 * t, 100)
    N_SHOW  = 4  # lowest levels per parity sector to plot
    N_SHOW_BDG = 6

    from jordan_wigner import spectrum_by_parity

    even_levels = np.zeros((len(mu_scan), N_SHOW))
    odd_levels  = np.zeros((len(mu_scan), N_SHOW))
    bdg_levels  = np.zeros((len(mu_scan), N_SHOW_BDG))

    for i, mu in enumerate(mu_scan):
        ev, od = spectrum_by_parity(L, t, mu, delta)
        even_levels[i] = ev[:N_SHOW]
        odd_levels[i]  = od[:N_SHOW]
        
        chain = KitaevChain(L=L, t=t, mu=mu, delta=delta)
        bdg_levels[i] = chain.positive_spectrum()[:N_SHOW_BDG]

    # shift so GS is at 0
    gs = np.minimum(even_levels[:, 0], odd_levels[:, 0])
    even_levels -= gs[:, None]
    odd_levels  -= gs[:, None]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    # ── Left: BdG Spectrum ──
    ax1.plot(mu_scan / t, bdg_levels[:, 0], color=COLORS['edge'], lw=2,
             label='near-zero (edge) mode', zorder=3)
    for i in range(1, N_SHOW_BDG):
        ax1.plot(mu_scan / t, bdg_levels[:, i], color=COLORS['bulk'],
                 lw=1.2, alpha=0.7, label='bulk bands' if i == 1 else None)

    ax1.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.08, color='steelblue', label='topological')
    ax1.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
    ax1.axvline(mu_c2 / t, color='gray', ls='--', lw=1)
    ax1.axhline(0, color='k', lw=0.7, ls=':')

    ax1.set_xlabel(r'$\mu\,/\,t$')
    ax1.set_ylabel(r'Quasiparticle energy $E_n$')
    ax1.set_title(rf'Finite-size BdG spectrum ($L={L}$)', fontsize=13)
    ax1.set_ylim(bottom=-0.1)
    ax1.legend(fontsize=10)
    clean_axes(ax1)

    # ── Right: Many-Body Qubit Spectrum ──
    for i in range(N_SHOW):
        lw = 2.0 if i == 0 else 1.0
        al = 1.0 if i == 0 else 0.5
        ax2.plot(mu_scan / t, even_levels[:, i],
                 color=COLORS['topological'], lw=lw, alpha=al,
                 label='even parity' if i == 0 else None)
        ax2.plot(mu_scan / t, odd_levels[:, i],
                 color=COLORS['trivial'], lw=lw, alpha=al, ls='--',
                 label='odd parity' if i == 0 else None)

    ax2.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.08, color='steelblue')
    ax2.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
    ax2.axvline(mu_c2 / t, color='gray', ls='--', lw=1)
    ax2.axhline(0, color='k', lw=0.7, ls=':')

    ax2.set_xlabel(r'$\mu\,/\,t$')
    ax2.set_ylabel(r'Energy above GS')
    ax2.set_title(rf'Many-body qubit spectrum ($L={L}$)', fontsize=13)
    ax2.set_ylim(bottom=-0.1)
    ax2.legend(fontsize=10)
    clean_axes(ax2)

    fig.tight_layout()
    save_fig(fig, 'block2_02_qubit_spectrum.pdf')


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(
        description='Generate Block 2 (qubit encoding) plots.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--plots', nargs='+', type=int, metavar='N')
    p.add_argument('--list',  action='store_true')
    p.add_argument('--L',     type=int,   default=10)
    p.add_argument('--t',     type=float, default=T)
    p.add_argument('--delta', type=float, default=DELTA)
    return p


def main():
    args = build_parser().parse_args()

    if args.list:
        for n, (_, desc) in sorted(PLOT_REGISTRY.items()):
            print(f"  {n}  {desc}")
        return

    setup_style()
    plt.rcParams.update({
        'axes.grid': False,
        'axes.facecolor': 'white',
        'figure.facecolor': 'white',
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
