"""
utils.py — shared plotting style, color palette, and figure-saving helpers.
All other modules import from here to keep visuals consistent.
"""

import os
import matplotlib as mpl
import matplotlib.pyplot as plt

# ── Paths ─────────────────────────────────────────────────────────────────────
SRC_DIR   = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR  = os.path.dirname(SRC_DIR)
PLOTS_DIR = os.path.join(ROOT_DIR, 'plots')

# ── Color palette ─────────────────────────────────────────────────────────────
COLORS = {
    'trivial':     '#d62728',   # red
    'critical':    '#2ca02c',   # green
    'topological': '#1f77b4',   # blue
    'edge':        '#e377c2',   # pink  — used for in-gap / edge modes
    'bulk':        '#7f7f7f',   # gray  — generic bulk bands
}

# ── Style ─────────────────────────────────────────────────────────────────────
def setup_style():
    """Apply a clean, publication-friendly matplotlib style."""
    mpl.rcParams.update({
        'figure.dpi':        150,
        'savefig.dpi':       300,
        'font.size':         12,
        'axes.labelsize':    13,
        'axes.titlesize':    14,
        'legend.fontsize':   11,
        'lines.linewidth':   2.0,
        'axes.grid':         True,
        'grid.alpha':        0.25,
        'grid.linestyle':    '--',
        'axes.spines.top':   False,
        'axes.spines.right': False,
    })

# ── Figure saving ─────────────────────────────────────────────────────────────
def save_fig(fig, filename):
    """
    Save *fig* to the plots/ directory.
    Supports .pdf and .png extensions.
    """
    os.makedirs(PLOTS_DIR, exist_ok=True)
    path = os.path.join(PLOTS_DIR, filename)
    fig.savefig(path, bbox_inches='tight')
    print(f"  [saved] {path}")
    plt.close(fig)
