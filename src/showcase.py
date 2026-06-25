"""
showcase.py — landing-page "hero" figures for the GitHub Pages gallery.

These are intuition-first, self-explanatory restyles/new figures that build on
the same physics as the Block runners. Every output is written to a NEW
``plots/show_*.png`` (+ ``_thumb``) filename via ``save_showcase`` so that no
deck figure embedded by a slides.tex / notes.tex \\includegraphics is ever
overwritten (regression-safe by construction).

Usage:
    python showcase.py            # generate all hero figures
    python showcase.py --list     # list available figures
    python showcase.py H1 H2      # only the named figures
"""

import argparse

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from utils import (setup_showcase_style, save_showcase, topo_window, takeaway,
                   COLORS)
from kitaev_chain import KitaevChain
from bdg_bulk import bulk_gap, critical_mu
from winding import winding_scan

T = 1.0
DELTA = 1.0

REGISTRY = {}


def hero(name, description):
    def deco(fn):
        REGISTRY[name] = (fn, description)
        return fn
    return deco


# ── H1 — Where the Majorana lives: real-space zero-mode |psi|^2 ───────────────

def _zero_mode_density(L, t, mu, delta):
    """|psi(j)|^2 on the lattice for the lowest-|E| BdG eigenvector, summed over
    its particle and hole components (the 2L BdG vector folds onto L sites)."""
    evals, evecs = KitaevChain(L=L, t=t, mu=mu, delta=delta).eigh()
    idx = int(np.argmin(np.abs(evals)))
    vec = evecs[:, idx]
    amp2 = np.abs(vec) ** 2
    site_density = amp2[:L] + amp2[L:]          # particle + hole part per site
    site_density = site_density / site_density.sum()
    return site_density, float(evals[idx])


@hero('H1', 'Real-space Majorana zero-mode wavefunction (end lobes vs delocalized)')
def fig_majorana_wavefunction(L=40, t=T, delta=DELTA, **_):
    sites = np.arange(1, L + 1)
    dens_topo, e_topo = _zero_mode_density(L, t, -1.0 * t, delta)   # topological mu=-t
    dens_triv, e_triv = _zero_mode_density(L, t, -3.0 * t, delta)   # trivial      mu=-3t

    fig, (ax_t, ax_b) = plt.subplots(2, 1, figsize=(8.2, 6.2), sharex=True,
                                     gridspec_kw={'hspace': 0.18})

    # Topological: two end-localized Majorana lobes.
    ax_t.fill_between(sites, dens_topo, color=COLORS['edge'], alpha=0.85, zorder=2)
    ax_t.plot(sites, dens_topo, color=COLORS['edge'], lw=2.0, zorder=3)
    half = L // 2
    ax_t.annotate(r'$\gamma_A$ (left Majorana)', xy=(1, dens_topo[0]),
                  xytext=(3, dens_topo.max() * 0.62), fontsize=10, color='#8a2f72',
                  arrowprops=dict(arrowstyle='->', color='#8a2f72'))
    ax_t.annotate(r'$\gamma_B$ (right Majorana)', xy=(L, dens_topo[-1]),
                  xytext=(L - 18, dens_topo.max() * 0.62), fontsize=10, color='#8a2f72',
                  arrowprops=dict(arrowstyle='->', color='#8a2f72'))
    ax_t.text(half, dens_topo.max() * 0.18, 'exponentially small\noverlap in the bulk',
              ha='center', va='center', fontsize=9, color='#555')
    ax_t.set_title(rf'Topological  $\mu=-t$:  one fermion split into two end halves '
                   rf'($E_0\approx{abs(e_topo):.1e}$)', fontsize=12)
    ax_t.set_ylabel(r'$|\psi_0(j)|^2$')
    ax_t.set_ylim(bottom=0)

    # Trivial: single delocalized bulk mode.
    ax_b.fill_between(sites, dens_triv, color=COLORS['topological'], alpha=0.30, zorder=2)
    ax_b.plot(sites, dens_triv, color=COLORS['topological'], lw=2.0, zorder=3)
    ax_b.set_title(rf'Trivial  $\mu=-3t$:  lowest mode is gapped and delocalized '
                   rf'($E_0\approx{abs(e_triv):.2f}$)', fontsize=12)
    ax_b.set_xlabel(r'lattice site $j$')
    ax_b.set_ylabel(r'$|\psi_0(j)|^2$')
    ax_b.set_ylim(bottom=0)
    ax_b.set_xlim(1, L)

    takeaway(ax_b, 'A Majorana zero mode = two halves of one fermion, pinned to the wire ends.',
             loc='upper center')
    fig.suptitle(r'Where the Majorana lives  (Kitaev chain, OBC, $t=\Delta=1$)',
                 fontsize=14, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return save_showcase(fig, 'h1_majorana_wavefunction')


# ── H2 — The depth optimum (restyle of Block 4 plot 6) ────────────────────────

@hero('H2', 'Depth optimum: expressibility ceiling vs accumulated gate noise')
def fig_depth_optimum(L=4, t=T, delta=DELTA, mu=0.0, p_cx=0.05,
                      reps_list=(1, 2, 3, 4, 5, 6), **_):
    # Imported lazily so H1/H7 do not pull in qiskit.
    from block4 import depth_optimum_sweep
    data = depth_optimum_sweep(L=L, t=t, delta=delta, mu=mu,
                               reps_list=tuple(reps_list), p_cx=p_cx)
    r = data['reps']
    n_cnot = data['n_cnot']
    ideal = data['ideal']
    noisy = data['noisy']
    sat = ideal.max() if ideal.size else 1.0
    envelope = sat * (1.0 - p_cx) ** n_cnot
    opt = int(r[int(np.argmax(noisy))])

    fig, ax = plt.subplots(figsize=(8.4, 5.4))

    # Shade the two regimes around the sweet spot.
    ax.axvspan(r.min() - 0.5, opt - 0.5, color=COLORS['bulk'], alpha=0.08)
    ax.axvspan(opt + 0.5, r.max() + 0.5, color=COLORS['trivial'], alpha=0.07)
    ax.text(r.min(), 1.06, 'under-expressive', fontsize=9, color='#666', va='top')
    ax.text(r.max(), 1.06, 'noise-dominated', fontsize=9, color=COLORS['trivial'],
            ha='right', va='top')

    ax.plot(r, ideal, color='black', lw=2.0, ls='--', marker='s', ms=5,
            label=r'noiseless $|\langle O\rangle|$ (expressibility ceiling)')
    ax.plot(r, envelope, color=COLORS['bulk'], lw=1.8, ls=':', marker='^', ms=5,
            label=r'gate-noise envelope $(1-p_{cx})^{r(L-1)}$')
    ax.plot(r, noisy, color=COLORS['trivial'], lw=2.8, marker='o', ms=7,
            label=r'measured $|\langle O\rangle|$ (the product)')
    ax.plot([opt], [noisy.max()], marker='*', ms=18, color=COLORS['critical'],
            zorder=5)
    ax.annotate(rf'sweet spot $r^\ast={opt}$', xy=(opt, noisy.max()),
                xytext=(opt + 0.35, noisy.max() - 0.16), fontsize=11,
                color=COLORS['critical'],
                arrowprops=dict(arrowstyle='->', color=COLORS['critical']))

    ax.set_xlabel(r'ansatz repetitions $r$')
    ax.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax.set_xticks(r)
    ax.set_ylim(-0.04, 1.14)
    ax.set_title(rf'Optimal circuit depth ($L={L}$, $\mu=0$, $p_{{cx}}={p_cx:.2f}$)')
    ax.legend(fontsize=9.5, frameon=False, loc='center right')

    # Second x-axis: CNOT count makes "depth = noisy gates" explicit.
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks(r)
    ax2.set_xticklabels([str(int(c)) for c in n_cnot])
    ax2.set_xlabel(r'noisy CNOTs $= r\,(L-1)$', fontsize=10)

    takeaway(ax, 'Deeper helps noiselessly but hurts under noise; the shallowest adequate depth wins.',
             loc='lower right')
    fig.tight_layout()
    return save_showcase(fig, 'h2_depth_optimum')


# ── H5 — Parity is symmetry; topology is not noise-immune (restyle of plot 4) ──

@hero('H5', 'Parity (symmetry) survives dephasing; the edge string (topology) does not')
def fig_parity_protection(par_L=6, t=T, delta=DELTA, mu=T, p_max=0.3, points=31, **_):
    from block4 import parity_noise_sweep, PARITY_CHANNELS
    data = parity_noise_sweep(par_L, t, mu, delta, p_max, points)
    p = data['p']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
    for name, (_, color, label) in PARITY_CHANNELS.items():
        ax1.plot(p, data[name]['parity'], color=color, lw=2.4, marker='o', ms=3, label=label)
    ax1.axhline(1.0, color='gray', ls=':', lw=1.2)
    ax1.set_xlabel('noise strength $p$')
    ax1.set_ylabel(r'$\langle \hat{P}\rangle=\langle\prod_j Z_j\rangle$')
    ax1.set_title('Total fermion parity')
    ax1.set_ylim(-0.05, 1.1)
    ax1.legend(fontsize=8.5, loc='lower left')
    takeaway(ax1, 'a symmetry is exactly conserved', loc='lower right')

    for name, (_, color, label) in PARITY_CHANNELS.items():
        ax2.plot(p, data[name]['edge'], color=color, lw=2.4, marker='o', ms=3, label=label)
    ax2.set_xlabel('noise strength $p$')
    ax2.set_ylabel(r'$|\langle X_0 Z\cdots Z X_{L-1}\rangle|$')
    ax2.set_title('Non-local edge string')
    ax2.set_ylim(-0.05, 1.1)
    ax2.legend(fontsize=8.5, loc='upper right')
    takeaway(ax2, 'the topological signal still decays', loc='lower left')

    fig.suptitle(rf'Parity protection $\neq$ topological protection '
                 rf'($L={par_L}$, $\mu={mu/t:.0f}t$)', fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return save_showcase(fig, 'h5_parity_vs_topology')


# ── H7 — Phase-diagram banner: the project's map ──────────────────────────────

@hero('H7', 'Phase-diagram banner: bulk gap and winding number vs mu')
def fig_phase_banner(t=T, delta=DELTA, **_):
    mu_scan = np.linspace(-4.5 * t, 4.5 * t, 500)
    mu_c1, mu_c2 = critical_mu(t)
    gaps = np.array([bulk_gap(mu, t, delta) for mu in mu_scan])
    nus = winding_scan(mu_scan, t, delta)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 3.4), sharex=True,
                                   gridspec_kw={'hspace': 0.12, 'height_ratios': [2, 1]})

    topo_window(ax1, mu_c1, mu_c2, t, label=r'topological $|\mu|<2t$')
    ax1.plot(mu_scan / t, gaps, color='black', lw=2)
    ax1.set_ylabel(r'bulk gap')
    ax1.set_ylim(bottom=0)
    ax1.legend(loc='upper right', fontsize=9, frameon=False)

    topo_window(ax2, mu_c1, mu_c2, t)
    ax2.fill_between(mu_scan / t, 0, nus, step='mid', color=COLORS['topological'], alpha=0.55)
    ax2.step(mu_scan / t, nus, where='mid', color=COLORS['topological'], lw=2)
    ax2.set_ylabel(r'winding $\nu$')
    ax2.set_yticks([0, 1])
    ax2.set_ylim(-0.25, 1.4)
    ax2.set_xlabel(r'$\mu/t$')

    fig.suptitle(r'Phase diagram of the Kitaev chain: gap closes and winding flips at $\mu=\pm2t$',
                 fontsize=12.5, y=1.02)
    fig.tight_layout()
    return save_showcase(fig, 'h7_phase_banner')


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description='Generate landing-page hero figures.')
    p.add_argument('names', nargs='*', help='figure ids (default: all)')
    p.add_argument('--list', action='store_true')
    args = p.parse_args()

    if args.list:
        for n, (_, desc) in REGISTRY.items():
            print(f'  {n}  {desc}')
        return

    setup_showcase_style()
    targets = args.names or list(REGISTRY)
    print(f'Generating showcase figures: {targets}\n')
    for n in targets:
        if n not in REGISTRY:
            print(f'  [skip] no figure {n!r}')
            continue
        fn, desc = REGISTRY[n]
        print(f'  [{n}] {desc}')
        fn()
        print()
    print('Done.')


if __name__ == '__main__':
    main()
