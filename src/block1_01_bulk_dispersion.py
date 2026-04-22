import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. Physical Parameters Setup
# ==========================================
t = 1.0      # Hopping integral (set as energy unit)
delta = 1.0  # Superconducting pairing potential

# Choose three representative chemical potentials mu to show three phases
mu_values = {
    'Topological ($|\mu| < 2t$)': 0.0,
    'Critical ($|\mu| = 2t$)': 2.0,
    'Trivial ($|\mu| > 2t$)': 3.0
}

# Momentum k scans the first Brillouin zone [-pi, pi]
k = np.linspace(-np.pi, np.pi, 500)

# ==========================================
# 2. Plot Initialization
# ==========================================
# 1 row, 3 columns of subplots
fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
fig.suptitle(r'Bulk Dispersion of the 1D Kitaev Chain ($t=1, \Delta=1$)', fontsize=16)

# ==========================================
# 3. Core Calculation and Plotting Loop
# ==========================================
for ax, (phase_name, mu) in zip(axes, mu_values.items()):
    # Calculate n_z(k) and n_y(k)
    n_z = -mu - 2 * t * np.cos(k)
    n_y = -2 * delta * np.sin(k)
    
    # Calculate eigen-energies E_k
    E_k = np.sqrt(n_z**2 + n_y**2)
    
    # Plot positive and negative energy branches (BdG particle-hole symmetry)
    ax.plot(k, E_k, color='blue', linewidth=2, label=r'$+E_k$ (Particle)')
    ax.plot(k, -E_k, color='red', linewidth=2, label=r'$-E_k$ (Hole)')
    
    # Auxiliary lines: indicate zero energy level and boundaries
    ax.axhline(0, color='black', linestyle='--', linewidth=0.8)
    ax.axvline(0, color='gray', linestyle=':', linewidth=0.8)
    
    # Axis and label settings
    ax.set_title(rf'{phase_name}, $\mu={mu}$', fontsize=12)
    ax.set_xlabel(r'Momentum $k$', fontsize=12)
    
    # Show y-axis label only on the leftmost subplot
    if ax == axes[0]:
        ax.set_ylabel(r'Energy $E_k / t$', fontsize=12)
    
    # Set x-axis ticks to multiples of pi
    ax.set_xticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    ax.set_xticklabels([r'$-\pi$', r'$-\pi/2$', r'$0$', r'$\pi/2$', r'$\pi$'])
    
    ax.grid(True, alpha=0.3)
    

# ==========================================
# 4. Global Legend and Layout
# ==========================================
# Extract legend handles and labels from the first subplot
handles, labels = axes[0].get_legend_handles_labels()

# Create a global legend, placed at the very bottom center of the whole canvas, horizontally arranged (ncol=2)
fig.legend(handles, labels, loc='lower center', ncol=2, bbox_to_anchor=(0.5, 0.0), fontsize=12)

# Adjust layout boundaries:
# Top reserved for suptitle (0.92)
# Bottom reserved 12% space for the global legend (0.12) to prevent overlap
plt.tight_layout(rect=[0, 0.12, 1, 0.92]) 

plt.show()