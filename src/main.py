"""
main.py — Block 1 runner: generates all physics-bridge plots.

Run from the src/ directory:
    python main.py

Output goes to ../plots/
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from utils        import setup_style, save_fig, COLORS
from kitaev_chain import KitaevChain
from bdg_bulk     import bulk_energy, bulk_gap, bdg_vector, critical_mu
from winding      import winding_number, winding_scan

setup_style()

# ── Shared parameters ─────────────────────────────────────────────────────────
T     = 1.0
DELTA = 1.0

# Three representative points used across several plots
CASES = [
    (dict(mu=-3.0), 'trivial',     r'Trivial $\mu = -3t$'),
    (dict(mu=-2.0), 'critical',    r'Critical $\mu = -2t$'),
    (dict(mu=-1.0), 'topological', r'Topological $\mu = -t$'),
]

k_arr    = np.linspace(-np.pi, np.pi, 600)
mu_scan  = np.linspace(-4.5 * T, 4.5 * T, 400)
mu_c1, mu_c2 = critical_mu(T)

print("Generating Block 1 plots …\n")

# ═══════════════════════════════════════════════════════════════════════════════
# Plot 1 — Bulk BdG dispersion  E(k) vs k  (reproduces deck slide 8)
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 4.5))

for params, phase, label in CASES:
    mu = params['mu']
    E  = bulk_energy(k_arr, mu, T, DELTA)
    ax.plot(k_arr / np.pi,  E, color=COLORS[phase], label=label)
    ax.plot(k_arr / np.pi, -E, color=COLORS[phase], alpha=0.35, lw=1.2)

ax.axhline(0, color='k', lw=0.8, ls=':')
ax.set_xlabel(r'$k\,/\,\pi$')
ax.set_ylabel(r'$E_k$')
ax.set_title(r'Bulk BdG dispersion  ($t = \Delta = 1$)')
ax.legend(loc='upper center')
ax.set_xlim(-1, 1)

save_fig(fig, 'block1_01_bulk_dispersion.pdf')

# ═══════════════════════════════════════════════════════════════════════════════
# Plot 2 — BdG d-vector loops in (n_z, n_y) plane  (deck slide 6)
# ═══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(12, 4))

for ax, (params, phase, label) in zip(axes, CASES):
    mu       = params['mu']
    nz, ny   = bdg_vector(k_arr, mu, T, DELTA)
    nu       = winding_number(mu, T, DELTA)

    ax.plot(nz, ny, color=COLORS[phase], lw=2)
    ax.axhline(0, color='k', lw=0.5)
    ax.axvline(0, color='k', lw=0.5)
    ax.plot(0, 0, 'k+', ms=12, mew=2, zorder=5)

    lim = max(np.max(np.abs(nz)), np.max(np.abs(ny))) * 1.25
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect('equal')
    ax.set_title(f'{label}\n$\\nu = {nu}$')
    ax.set_xlabel(r'$n_z(k)$')

axes[0].set_ylabel(r'$n_y(k)$')
fig.suptitle(r'BdG $\mathbf{n}(k)$ loop as $k$ sweeps the BZ', fontsize=14)
fig.tight_layout()

save_fig(fig, 'block1_02_winding_loops.pdf')

# ═══════════════════════════════════════════════════════════════════════════════
# Plot 3 — Phase diagram: bulk gap + winding number vs mu
# ═══════════════════════════════════════════════════════════════════════════════
gaps = np.array([bulk_gap(mu, T, DELTA) for mu in mu_scan])
nus  = winding_scan(mu_scan, T, DELTA)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True,
                                gridspec_kw={'hspace': 0.08})

# Bulk gap
ax1.plot(mu_scan / T, gaps, 'k', lw=2)
ax1.set_ylabel(r'Bulk gap  $E_\mathrm{gap}$')
ax1.set_title(r'Phase diagram of the Kitaev chain  ($t = \Delta = 1$)')
ax1.set_ylim(bottom=0)

# Winding number
ax2.step(mu_scan / T, nus, color='steelblue', lw=2, where='mid')
ax2.set_xlabel(r'$\mu\,/\,t$')
ax2.set_ylabel(r'Winding number $\nu$')
ax2.set_yticks([0, 1])
ax2.set_ylim(-0.3, 1.5)

# Shade topological region
for ax in (ax1, ax2):
    ax.axvspan(mu_c1 / T, mu_c2 / T, alpha=0.10, color='steelblue',
               label='topological ($|\\mu| < 2t$)')
    ax.axvline(mu_c1 / T, color='gray', ls='--', lw=1)
    ax.axvline(mu_c2 / T, color='gray', ls='--', lw=1)

ax1.legend(loc='upper right')

save_fig(fig, 'block1_03_phase_diagram.pdf')

# ═══════════════════════════════════════════════════════════════════════════════
# Plot 4 — Finite-size spectrum: lowest quasiparticle energies vs mu  (OBC)
# ═══════════════════════════════════════════════════════════════════════════════
L      = 30
N_SHOW = 6    # number of positive eigenvalues to track
mu_fs  = np.linspace(-4.5 * T, 4.5 * T, 300)

evals_fs = np.zeros((len(mu_fs), N_SHOW))
for i, mu in enumerate(mu_fs):
    chain = KitaevChain(L=L, t=T, mu=mu, delta=DELTA)
    pos   = chain.positive_spectrum()[:N_SHOW]
    evals_fs[i] = pos

fig, ax = plt.subplots(figsize=(9, 4.5))

# Plot edge mode (lowest level) in a distinct color
ax.plot(mu_fs / T, evals_fs[:, 0], color=COLORS['edge'], lw=2.5,
        label='near-zero (edge) mode', zorder=3)
for i in range(1, N_SHOW):
    ax.plot(mu_fs / T, evals_fs[:, i], color=COLORS['bulk'],
            lw=1.2, alpha=0.7, label='bulk bands' if i == 1 else None)

ax.axvspan(mu_c1 / T, mu_c2 / T, alpha=0.10, color='steelblue',
           label='topological')
ax.axvline(mu_c1 / T, color='gray', ls='--', lw=1)
ax.axvline(mu_c2 / T, color='gray', ls='--', lw=1)
ax.axhline(0, color='k', lw=0.7, ls=':')

ax.set_xlabel(r'$\mu\,/\,t$')
ax.set_ylabel(r'Quasiparticle energy $E_n$')
ax.set_title(f'Finite-size BdG spectrum  ($L = {L}$, OBC,  $t = \\Delta = 1$)')
ax.set_ylim(bottom=0)
ax.legend()

save_fig(fig, 'block1_04_finite_size_spectrum.pdf')

# ═══════════════════════════════════════════════════════════════════════════════
# Plot 5 — Real-space eigenvalue snapshot: trivial vs topological
# ═══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)

snap_cases = [CASES[0], CASES[2]]   # trivial and topological

for ax, (params, phase, label) in zip(axes, snap_cases):
    mu    = params['mu']
    chain = KitaevChain(L=20, t=T, mu=mu, delta=DELTA)
    evals = chain.spectrum()
    idx   = np.arange(len(evals))

    # Colour near-zero modes differently
    colors_pt = [COLORS['edge'] if abs(e) < 0.05 else COLORS[phase]
                 for e in evals]
    ax.scatter(idx, evals, c=colors_pt, s=25, zorder=3)
    ax.axhline(0, color='k', lw=0.8, ls='--')
    ax.set_xlabel('Eigenvalue index')
    ax.set_title(label)

axes[0].set_ylabel('Energy $E$')
edge_patch = mpatches.Patch(color=COLORS['edge'], label='near-zero mode')
fig.legend(handles=[edge_patch], loc='lower center', ncol=1, frameon=True)
fig.suptitle(r'Full BdG spectrum in real space  ($L = 20$, OBC)', fontsize=14)
fig.tight_layout(rect=[0, 0.06, 1, 1])

save_fig(fig, 'block1_05_realspace_snapshot.pdf')

# ─────────────────────────────────────────────────────────────────────────────
print("\nAll Block 1 plots written to ../plots/")
