"""
kitaev_chain.py — real-space BdG Hamiltonian for the 1D Kitaev chain (OBC).

Hamiltonian (eq. 1 of the deck):
  H = -mu * sum_j c†_j c_j
      - t  * sum_j (c†_j c_{j+1} + h.c.)
      + Delta * sum_j (c†_j c†_{j+1} + h.c.)

BdG basis: Psi = (c_1, ..., c_L, c†_1, ..., c†_L)^T
BdG matrix: M = [[h, d], [-d, -h]]
  h_{ij}    = -mu * delta_{ij} - t * (delta_{i,j+1} + delta_{i+1,j})
  d_{ij}    = Delta * (delta_{i,j+1} - delta_{i+1,j})   [antisymmetric]

Eigenvalues come in ±E pairs (particle-hole symmetry).
"""

import numpy as np


class KitaevChain:
    """
    Parameters
    ----------
    L     : int   — number of lattice sites
    t     : float — hopping amplitude
    mu    : float — chemical potential
    delta : float — p-wave pairing amplitude (real)
    """

    def __init__(self, L: int, t: float = 1.0, mu: float = 0.0, delta: float = 1.0):
        self.L     = L
        self.t     = t
        self.mu    = mu
        self.delta = delta

    # ── Hamiltonian construction ───────────────────────────────────────────────

    def build_hamiltonian(self) -> np.ndarray:
        """Return the (2L × 2L) real-space BdG matrix."""
        L, t, mu, delta = self.L, self.t, self.mu, self.delta

        # Single-particle hopping block h (L × L), real symmetric
        h = np.zeros((L, L))
        np.fill_diagonal(h, -mu)
        for j in range(L - 1):
            h[j, j + 1] = -t
            h[j + 1, j] = -t

        # Pairing block d (L × L), real antisymmetric
        d = np.zeros((L, L))
        for j in range(L - 1):
            d[j,     j + 1] =  delta
            d[j + 1, j    ] = -delta

        # Full BdG matrix
        return np.block([[h, d], [-d, -h]])

    # ── Diagonalisation helpers ───────────────────────────────────────────────

    def spectrum(self) -> np.ndarray:
        """Return all 2L eigenvalues sorted in ascending order."""
        evals = np.linalg.eigvalsh(self.build_hamiltonian())
        return np.sort(evals)

    def positive_spectrum(self) -> np.ndarray:
        """Return the L positive quasiparticle energies (sorted)."""
        evals = self.spectrum()
        return evals[evals >= 0]

    def eigh(self):
        """Return (eigenvalues, eigenvectors) sorted by ascending eigenvalue."""
        evals, evecs = np.linalg.eigh(self.build_hamiltonian())
        idx = np.argsort(evals)
        return evals[idx], evecs[:, idx]

    # ── Convenience ───────────────────────────────────────────────────────────

    def gap(self) -> float:
        """Smallest positive quasiparticle energy (finite-size gap)."""
        return self.positive_spectrum()[0]

    def __repr__(self):
        return (f"KitaevChain(L={self.L}, t={self.t}, "
                f"mu={self.mu}, delta={self.delta})")
