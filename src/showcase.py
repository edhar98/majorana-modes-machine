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
from bdg_bulk import bulk_gap, bulk_energy, bdg_vector, critical_mu
from winding import winding_scan
from block3_core import sweep_observables

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


# ── H9 — H1 under noise: the Majorana correlation severed by gate noise ───────

@hero('H9', 'How noise affects the H1 picture: the non-local Majorana link severed')
def fig_majorana_under_noise(t=T, delta=DELTA, L_list=(2, 3, 4, 5, 6, 7, 8, 9, 10),
                             p_list=(0.0, 0.03, 0.08, 0.15), vqe_L=4, vqe_reps=3,
                             vqe_p=(0.0, 0.03, 0.08, 0.15), **_):
    """The qubit/VQE analog of H1 under noise.

    In the qubit encoding the parity-symmetric ground state has NO local order
    (<X_j> = 0 everywhere): there are no lobes to blur. The Majorana information
    is carried *non-locally* by the end-to-end string O_edge = X_0 Z..Z X_{L-1},
    which connects the two Majoranas. Noise does not smear two lobes -- it cuts
    that string. We show the end-to-end correlation collapsing as the Majoranas
    are separated (left, exact ground state) and confirm it on a true VQE state
    under circuit-level CNOT noise (right).
    """
    from block4 import (pauli_matrix, expval_from_density, ideal_even_density,
                         single_qubit_channel, circuit_level_edge,
                         depolarizing_noise_model)
    from block3_core import vqe_ansatz, best_state, edge_string
    from qiskit_aer.noise import depolarizing_error

    def full_edge(rho, L):
        return abs(expval_from_density(rho, edge_string(L).to_matrix()))

    # ── Left: exact end-to-end correlation vs Majorana separation L ──
    Ls = np.array(L_list, dtype=int)
    curves = {}
    for p in p_list:
        vals = []
        for L in Ls:
            rho0 = ideal_even_density(0.0, L, t, delta)
            rho = rho0 if p == 0 else single_qubit_channel(rho0, depolarizing_error(p, 1), L)
            vals.append(full_edge(rho, L))
        curves[p] = np.array(vals)

    # ── Right: true VQE + circuit-level CNOT noise at fixed length ──
    rng = np.random.default_rng(7)
    ansatz = vqe_ansatz(vqe_L, vqe_reps)
    rec = best_state(0.0, vqe_L, t, delta, ansatz, 0.1, rng, 1500, 8)
    vqe_vals, vqe_ncx = [], None
    for p in vqe_p:
        edge, _, ncx = circuit_level_edge(ansatz, rec['theta'], vqe_L,
                                          depolarizing_noise_model(p))
        vqe_vals.append(abs(edge))
        vqe_ncx = ncx
    print(f"  VQE L={vqe_L} fid={rec['fidelity']:.3f}  noiseless |O_edge|={vqe_vals[0]:.3f}")

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.4, 4.9),
                                   gridspec_kw={'width_ratios': [1.5, 1]})

    reds = plt.cm.RdPu(np.linspace(0.35, 0.95, len(p_list)))
    for (p, col) in zip(p_list, reds):
        style = dict(lw=2.6, marker='o', ms=5)
        if p == 0:
            axL.plot(Ls, curves[p], color='black', lw=2.0, ls='--', marker='s', ms=5,
                     label=r'noiseless (ideal)')
        else:
            axL.plot(Ls, curves[p], color=col, label=rf'$p={p:.2f}$', **style)
    axL.set_xlabel(r'Majorana separation = chain length $L$')
    axL.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$ (end-to-end link)')
    axL.set_xticks(Ls)
    axL.set_ylim(-0.04, 1.08)
    axL.set_title('The non-local link weakens with separation')
    axL.legend(fontsize=9, frameon=False, ncol=2, loc='lower left')
    takeaway(axL, 'No local lobes to blur: noise cuts the string between the two ends.',
             loc='upper center')

    xs = np.arange(len(vqe_p))
    bar_cols = plt.cm.RdPu(np.linspace(0.35, 0.95, len(vqe_p)))
    axR.bar(xs, vqe_vals, color=bar_cols, edgecolor='#888', width=0.7)
    for x, v in zip(xs, vqe_vals):
        axR.text(x, v + 0.02, f'{v:.2f}', ha='center', va='bottom', fontsize=9)
    axR.set_xticks(xs)
    axR.set_xticklabels([rf'$p={p:.2f}$' for p in vqe_p], fontsize=9)
    axR.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    axR.set_ylim(0, 1.12)
    axR.set_title(f'True VQE state, circuit CNOT noise\n'
                  rf'($L={vqe_L}$, {vqe_ncx} CNOTs)')

    fig.suptitle(r'H1 under noise: in the qubit/VQE encoding the Majorana signal is '
                 r'non-local, so noise severs it', fontsize=12.5, y=1.0)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return save_showcase(fig, 'h9_majorana_under_noise')


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


# ── H3 — The transition in three synchronized views (static small-multiples) ──

@hero('H3', 'The phase transition: dispersion, d-vector winding, finite-size mode')
def fig_transition_views(t=T, delta=DELTA, L=30, **_):
    """One row per phase (topological / critical / trivial); three columns showing
    the gap closing, the d-vector loop slipping off the origin, and the edge mode
    lifting off zero. The static, JS-free version of the would-be animation."""
    cases = [(0.0, 'topological', r'Topological  $\mu=0$'),
             (2.0 * t, 'critical', r'Critical  $\mu=2t$'),
             (3.0 * t, 'trivial', r'Trivial  $\mu=3t$')]
    k = np.linspace(-np.pi, np.pi, 400)
    mu_c1, mu_c2 = critical_mu(t)
    mu_scan = np.linspace(-4.5 * t, 4.5 * t, 220)
    e0_scan = np.array([KitaevChain(L=L, t=t, mu=m, delta=delta).positive_spectrum()[0]
                        for m in mu_scan])

    fig, axes = plt.subplots(3, 3, figsize=(11.5, 9.0))
    for row, (mu, phase, label) in enumerate(cases):
        col = COLORS[phase]
        # Col 1: dispersion E(k).
        ax = axes[row, 0]
        E = bulk_energy(k, mu, t, delta)
        ax.plot(k / np.pi, E, color=col, lw=2)
        ax.plot(k / np.pi, -E, color=col, lw=2, alpha=0.4)
        ax.axhline(0, color='k', lw=0.7, ls=':')
        ax.set_ylabel(label, fontsize=11, color=col)
        if row == 0:
            ax.set_title(r'dispersion $E(k)$', fontsize=11)
        if row == 2:
            ax.set_xlabel(r'$k/\pi$')

        # Col 2: d-vector loop (n_z, n_y) with the origin starred.
        ax = axes[row, 1]
        nz, ny = bdg_vector(k, mu, t, delta)
        ax.plot(nz, ny, color=col, lw=2)
        ax.scatter([0], [0], marker='*', s=170, color=COLORS['trivial'], zorder=5)
        ax.axhline(0, color='gray', lw=0.6, ls=':')
        ax.axvline(0, color='gray', lw=0.6, ls=':')
        ax.set_aspect('equal', 'box')
        if row == 0:
            ax.set_title(r'd-vector loop $(n_z,n_y)$', fontsize=11)
        if row == 2:
            ax.set_xlabel(r'$n_z$')

        # Col 3: finite-size near-zero mode as a moving dot on E_0(mu).
        ax = axes[row, 2]
        topo_window(ax, mu_c1, mu_c2, t)
        ax.plot(mu_scan / t, e0_scan, color=COLORS['bulk'], lw=1.6)
        e_here = KitaevChain(L=L, t=t, mu=mu, delta=delta).positive_spectrum()[0]
        ax.scatter([mu / t], [e_here], s=70, color=col, zorder=5, edgecolor='k', lw=0.5)
        ax.set_ylim(bottom=0)
        if row == 0:
            ax.set_title(rf'edge mode $E_0(\mu)$, $L={L}$', fontsize=11)
        if row == 2:
            ax.set_xlabel(r'$\mu/t$')

    fig.suptitle(r'Crossing the transition: the gap closes, the loop slips off the '
                 r'origin, the edge mode lifts off zero', fontsize=13, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    return save_showcase(fig, 'h3_transition_views')


# ── H4 — Why the edge string is non-local: operator pictogram + decay ─────────

@hero('H4', 'The non-local edge string vs a blind local probe')
def fig_edge_string(L=8, t=T, delta=DELTA, **_):
    data = sweep_observables(L=L, t=t, delta=delta)
    mu = data['mu']
    mu_c1, mu_c2 = critical_mu(t)

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(8.6, 6.6),
                                         gridspec_kw={'height_ratios': [1, 1.5], 'hspace': 0.32})

    # Top: operator pictogram. One non-local string vs one local Z.
    sites = np.arange(L)
    ax_top.axhspan(0.78, 1.22, xmin=0.02, xmax=0.98, color=COLORS['edge'], alpha=0.18)
    for j in sites:
        op = 'X' if j in (0, L - 1) else 'Z'
        c = COLORS['edge'] if op == 'X' else COLORS['bulk']
        ax_top.scatter(j, 1.0, s=520, color='white', edgecolor=c, lw=2.2, zorder=3)
        ax_top.text(j, 1.0, op, ha='center', va='center', fontsize=12, color=c,
                    fontweight='bold', zorder=4)
    # local probe row
    ax_top.scatter(0, 0.0, s=520, color='white', edgecolor=COLORS['bulk'], lw=2.2, zorder=3)
    ax_top.text(0, 0.0, 'Z', ha='center', va='center', fontsize=12,
                color=COLORS['bulk'], fontweight='bold', zorder=4)
    for j in range(1, L):
        ax_top.scatter(j, 0.0, s=520, color='#f5f5f5', edgecolor='#ddd', lw=1.0, zorder=2)
    ax_top.text(L - 0.4, 1.0, r'$O_{\mathrm{edge}}=X_0\,Z\cdots Z\,X_{L-1}$ (non-local)',
                va='center', ha='left', fontsize=10, color='#8a2f72')
    ax_top.text(L - 0.4, 0.0, r'$|\langle Z_0\rangle|$ (local, blind)',
                va='center', ha='left', fontsize=10, color='#666')
    ax_top.set_xlim(-0.7, L + 3.2)
    ax_top.set_ylim(-0.6, 1.7)
    ax_top.axis('off')
    ax_top.set_title('One operator that pierces the whole chain', fontsize=12)

    # Bottom: the diagnostic vs the local probe across the transition.
    topo_window(ax_bot, mu_c1, mu_c2, t, label=r'topological $|\mu|<2t$')
    ax_bot.plot(mu / t, np.abs(data['string_exact']), color=COLORS['edge'], lw=2.6,
                label=r'$|\langle O_{\mathrm{edge}}\rangle|$ (non-local)')
    ax_bot.plot(mu / t, np.abs(data['local_exact']), color=COLORS['bulk'], lw=2.0, ls='--',
                label=r'$|\langle Z_0\rangle|$ (local probe)')
    ax_bot.set_xlabel(r'$\mu/t$')
    ax_bot.set_ylabel('magnitude')
    ax_bot.set_ylim(-0.04, 1.12)
    ax_bot.legend(fontsize=9.5, loc='lower right', frameon=False)
    takeaway(ax_bot, 'Only the non-local string tracks the phase; no single site sees it.',
             loc='upper center')

    fig.suptitle(r'Why the edge string is non-local  ($L=%d$)' % L, fontsize=13, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return save_showcase(fig, 'h4_edge_string')


# ── H6 — Coherent rotation vs incoherent mixing (purity) ──────────────────────

@hero('H6', 'Coherent control error rotates a pure state; incoherent noise mixes it')
def fig_coherent_vs_incoherent(L=4, t=T, delta=DELTA, mu=0.0, reps=3, **_):
    from block4 import coherent_vs_incoherent_sweep
    data = coherent_vs_incoherent_sweep(L=L, t=t, delta=delta, mu=mu, reps=reps)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    ax1.axhline(1.0, color='gray', ls=':', lw=1.2)
    ax1.plot(data['sigma'], data['coh_edge'], color=COLORS['topological'], lw=2.4,
             marker='o', ms=4, label=r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax1.plot(data['sigma'], data['coh_pur'], color=COLORS['trivial'], lw=2.4, ls='--',
             marker='s', ms=4, label=r'purity $\mathrm{Tr}\,\rho^2$')
    ax1.set_xlabel(r'control-error spread $\sigma_\theta$ (rad)')
    ax1.set_ylabel('value')
    ax1.set_title(r'Coherent: $\theta^\ast+\delta\theta$, ideal gates')
    ax1.set_ylim(-0.04, 1.12)
    ax1.legend(fontsize=9, frameon=False, loc='lower left')
    takeaway(ax1, 'state stays pure, only rotated', loc='lower right')

    ax2.axhline(1.0, color='gray', ls=':', lw=1.2)
    ax2.plot(data['p'], data['inc_edge'], color=COLORS['topological'], lw=2.4,
             marker='o', ms=4, label=r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax2.plot(data['p'], data['inc_pur'], color=COLORS['trivial'], lw=2.4, ls='--',
             marker='s', ms=4, label=r'purity $\mathrm{Tr}\,\rho^2$')
    ax2.set_xlabel(r'per-cx depolarizing strength $p_{cx}$')
    ax2.set_title(r'Incoherent: gate noise, exact $\theta^\ast$')
    ax2.legend(fontsize=9, frameon=False, loc='lower left')
    takeaway(ax2, 'purity falls -> the state mixes', loc='lower right')

    fig.suptitle(rf'Two failure modes: rotation vs mixing '
                 rf'($L={L}$, $r={reps}$, $\mu=0$)', fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    return save_showcase(fig, 'h6_coherent_vs_incoherent')


# ── H8 — The chain-length tradeoff: protection up, vulnerability up ───────────

@hero('H8', 'Chain length: intrinsic protection improves but noisy vulnerability worsens')
def fig_length_tradeoff(t=T, delta=DELTA, L_list=(2, 3, 4, 5, 6, 7, 8), gamma=0.1, **_):
    from block4 import parity_length_sweep
    data = parity_length_sweep(L_list, t, mu_topo=t, mu_triv=3 * t, delta=delta, gamma=gamma)
    L = data['L']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
    ax1.semilogy(L, data['gap_topo'] + 1e-18, color=COLORS['topological'], lw=2.4,
                 marker='o', label=r'topological $\mu=t$')
    ax1.semilogy(L, data['gap_triv'] + 1e-18, color=COLORS['trivial'], lw=2.4,
                 marker='s', ls='--', label=r'trivial $\mu=3t$')
    ax1.set_xlabel('chain length $L$')
    ax1.set_ylabel(r'parity gap $\Delta_P(L)$')
    ax1.set_title('Intrinsic protection improves with $L$')
    ax1.set_xticks(L)
    ax1.legend(fontsize=9, frameon=False)
    takeaway(ax1, 'longer chain -> exponentially better isolation', loc='lower left')

    ax2.plot(L, data['leak'], color=COLORS['trivial'], lw=2.4, marker='o',
             label=r'odd-sector leakage, $T_1$ ($\gamma=%.2f$)' % gamma)
    ax2.plot(L, data['edge_loss'], color=COLORS['bulk'], lw=2.4, marker='s', ls='--',
             label=r'edge-string loss, depol ($p=%.2f$)' % gamma)
    ax2.set_xlabel('chain length $L$')
    ax2.set_ylabel('noise-induced failure fraction')
    ax2.set_title('Noisy vulnerability worsens with $L$')
    ax2.set_xticks(L)
    ax2.legend(fontsize=9, frameon=False, loc='upper left')
    takeaway(ax2, 'more sites & gates -> more exposure', loc='lower right')

    fig.suptitle('The chain-length tradeoff: protection and vulnerability pull opposite ways',
                 fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    return save_showcase(fig, 'h8_length_tradeoff')


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
