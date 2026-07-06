"""Toy vs real-device noisy edge string, from the two cached HPC runs."""
import sys
sys.path.insert(0, 'src')
import numpy as np
import matplotlib.pyplot as plt
from utils import setup_style, save_fig, COLORS, clean_axes

setup_style()
plt.rcParams.update({'axes.grid': False, 'axes.facecolor': 'white',
                     'figure.facecolor': 'white'})

toy = np.load('plots/block4_scaling_data.npz', allow_pickle=True)
cai = np.load('plots/block4_scaling_data_FakeCairoV2.npz', allow_pickle=True)
L = toy['L']

fig, ax = plt.subplots(figsize=(8.4, 5.2))
ax.plot(L, toy['ff_edge'], color='black', lw=1.8, ls='--', marker='D', ms=4,
        label='exact GS (free-fermion)')
ax.axhspan(0.45, 0.55, color=COLORS['topological'], alpha=0.08)
ax.errorbar(L, cai['noisy'], yerr=cai['err'], color=COLORS['topological'], lw=2.4,
            marker='o', ms=6, capsize=3,
            label=r'real IBM Cairo ($2q$ err $7.5\times10^{-3}$)')
ax.errorbar(L, toy['noisy'], yerr=toy['err'], color=COLORS['trivial'], lw=2.4,
            marker='s', ms=6, capsize=3,
            label=r'toy depolarizing ($p_{cx}=0.05$)')
ax.annotate('survives ${\\sim}0.5$', xy=(16, cai['noisy'][-1]), xytext=(12.4, 0.66),
            color=COLORS['topological'], fontsize=10,
            arrowprops=dict(arrowstyle='->', color=COLORS['topological']))
ax.annotate('washed out', xy=(16, toy['noisy'][-1]), xytext=(12.6, 0.17),
            color=COLORS['trivial'], fontsize=10,
            arrowprops=dict(arrowstyle='->', color=COLORS['trivial']))
ax.set_xlabel(r'chain length $L$')
ax.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$ (noisy, at $r^\ast=4$)')
ax.set_xticks(L[::2])
ax.set_ylim(-0.02, 1.02)
ax.set_title(r'Real device noise vs the toy model: the edge string survives to $L=16$')
ax.legend(fontsize=9, frameon=False, loc='upper right')
clean_axes(ax)
fig.tight_layout()
save_fig(fig, 'block4_scaling_toy_vs_real.pdf')
print('saved plots/block4_scaling_toy_vs_real.pdf')
