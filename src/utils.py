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

# ── Axes cleanup ──────────────────────────────────────────────────────────────
def clean_axes(ax):
    ax.grid(False, which='both', axis='both')
    ax.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('black')
        spine.set_linewidth(0.8)


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


# ── Showcase / landing-page design system ─────────────────────────────────────
# Lightweight additions used only by the web-gallery generator (src/showcase.py).
# They reuse the COLORS physics roles above so the gallery reads as one body of
# work. None of this changes the existing deck figures, which keep calling
# setup_style()/clean_axes()/save_fig() exactly as before.

# Standard physics-role -> meaning used across every showcase figure.
PHASE_COLORS = {
    'topological': COLORS['topological'],   # topological phase / signal present / "good"
    'critical':    COLORS['critical'],      # mu = +-2t boundary, gap-closing
    'trivial':     COLORS['trivial'],       # trivial phase / decay / failure
    'edge':        COLORS['edge'],          # Majorana / in-gap / zero modes (the star)
    'bulk':        COLORS['bulk'],          # bulk bands / neutral reference
}


def setup_showcase_style():
    """Apply the showcase look: same clean base as setup_style() but tuned for
    landing-page thumbnails (forced white background so cards render identically
    in light and dark page themes)."""
    setup_style()
    mpl.rcParams.update({
        'axes.grid':         False,
        'axes.facecolor':    'white',
        'figure.facecolor':  'white',
        'savefig.facecolor': 'white',
        'savefig.dpi':       300,
        'font.size':         12.5,
        'axes.titlesize':    14,
    })


def topo_window(ax, mu_c1, mu_c2, t=1.0, label=None):
    """Shade the topological window and draw the +-2t phase boundaries.
    Single convention reused by every showcase mu-axis figure."""
    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'], label=label)
    ax.axvline(mu_c1 / t, color='gray', ls=':', lw=1)
    ax.axvline(mu_c2 / t, color='gray', ls=':', lw=1)


def takeaway(ax, text, loc='lower center'):
    """Stamp a one-line plain-language takeaway on a showcase figure so it is
    self-explanatory on the landing page."""
    xy = {'lower center': (0.5, 0.02, 'center', 'bottom'),
          'upper center': (0.5, 0.97, 'center', 'top'),
          'lower left':   (0.03, 0.04, 'left', 'bottom'),
          'lower right':  (0.97, 0.04, 'right', 'bottom')}[loc]
    ax.text(xy[0], xy[1], text, transform=ax.transAxes, ha=xy[2], va=xy[3],
            fontsize=10.5, style='italic', color='#333',
            bbox=dict(boxstyle='round,pad=0.4', fc='white', ec='#bbb', alpha=0.85))


def save_showcase(fig, name):
    """Save a showcase figure as a full PNG plus a downscaled thumbnail, both
    onto a white background. Writes NEW 'show_*' filenames so no deck figure is
    ever overwritten. Returns (full_path, thumb_path)."""
    os.makedirs(PLOTS_DIR, exist_ok=True)
    full = os.path.join(PLOTS_DIR, f'show_{name}.png')
    thumb = os.path.join(PLOTS_DIR, f'show_{name}_thumb.png')
    fig.savefig(full, bbox_inches='tight', dpi=300, facecolor='white')
    fig.savefig(thumb, bbox_inches='tight', dpi=90, facecolor='white')
    print(f"  [saved] {full}")
    print(f"  [saved] {thumb}")
    plt.close(fig)
    return full, thumb
