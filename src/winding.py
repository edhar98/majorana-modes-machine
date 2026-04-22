import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ==========================================
# 1. Physical Parameter Settings
# ==========================================
t = 1.0      # Hopping integral
delta = 1.0  # Superconducting pairing potential

phases = [
    {'name': 'Topological', 'mu': 0.0, 'color': '#1f77b4'},
    {'name': 'Critical', 'mu': 2.0, 'color': '#2ca02c'},
    {'name': 'Trivial', 'mu': 3.0, 'color': '#d62728'}
]

k = np.linspace(-np.pi, np.pi, 2000)

# ==========================================
# 2. Image Initialization
# ==========================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle(r'Winding Loops of the 1D Kitaev Chain in Complex Plane ($t=1, \Delta=1$)', fontsize=16)

# ==========================================
# 3. Core Calculation and Plotting Loop
# ==========================================
for ax, phase in zip(axes, phases):
    mu = phase['mu']
    
    n_z = -mu - 2 * t * np.cos(k)
    n_y = -2 * delta * np.sin(k)
    
    z_k = n_z + 1j * n_y
    theta_k = np.unwrap(np.angle(z_k)) 
    
    winding_number_raw = (theta_k[-1] - theta_k[0]) / (2 * np.pi)
    winding_number = int(np.round(winding_number_raw))
    
    # Plotting (individual label removed to avoid generating a separate legend per subplot)
    ax.plot(n_z, n_y, color=phase['color'], linewidth=2.5)
    
    ax.scatter(n_z[0], n_y[0], color='black', s=50, zorder=5)
    
    idx_k0 = len(k) // 2
    ax.scatter(n_z[idx_k0], n_y[idx_k0], color='orange', s=50, marker='s', zorder=5)
    
    ax.scatter(0, 0, color='red', marker='*', s=150, zorder=10)
    
    ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.axvline(0, color='gray', linestyle='--', linewidth=0.8)
    
    ax.set_aspect('equal', 'box')
    
    ax.set_title(f"{phase['name']} Phase ($\\mu={mu}$)\nWinding Number $\\nu = {winding_number}$", fontsize=12)
    ax.set_xlabel(r'$n_z(k) = -\mu - 2t \cos k$', fontsize=12)
    
    if ax == axes[0]:
        ax.set_ylabel(r'$n_y(k) = -2\Delta \sin k$', fontsize=12)
        
    ax.grid(True, alpha=0.3)

# ==========================================
# 4. Global Legend and Layout Adjustment
# ==========================================
# Create a generalized global legend covering elements common to all subplots
custom_legend = [
    Line2D([0], [0], color='gray', linewidth=2.5, label='Trajectory'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='black', markersize=8, label=r'$k = \pm\pi$'),
    Line2D([0], [0], marker='s', color='w', markerfacecolor='orange', markersize=8, label=r'$k = 0$'),
    Line2D([0], [0], marker='*', color='w', markerfacecolor='red', markersize=15, label='Origin (0,0)')
]

# Place this single legend at the bottom center of the whole figure
fig.legend(handles=custom_legend, loc='lower center', ncol=4, bbox_to_anchor=(0.5, 0.02), fontsize=11)

# Adjust layout boundaries: top margin for suptitle, bottom margin for global legend
fig.tight_layout(rect=[0, 0.08, 1, 0.92]) 

output_filename = 'block1_02_winding_loops.pdf'
plt.savefig(output_filename, format='pdf', bbox_inches='tight')
print(f"Plot successfully saved as: {output_filename}")

plt.show()
