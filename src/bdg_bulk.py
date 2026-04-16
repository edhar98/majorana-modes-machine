"""
bdg_bulk.py — momentum-space BdG for the Kitaev chain (periodic bulk).

Follows slides 4–5 of the physics-bridge deck.

BdG matrix at momentum k (eq. 13):
  h(k) = n_y(k) sigma_y + n_z(k) sigma_z

  n_z(k) = -mu - 2t cos k
  n_y(k) = -2 Delta sin k

Quasiparticle energy:
  E(k) = sqrt(n_z^2 + n_y^2)         (eq. 14)

Gap closes when |mu| = 2t             (eq. 15)
"""

import numpy as np


# ── BdG vector ────────────────────────────────────────────────────────────────

def bdg_vector(
    k: np.ndarray,
    mu: float,
    t: float = 1.0,
    delta: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (n_z(k), n_y(k)) — the two components of the BdG d-vector.

    Parameters
    ----------
    k     : array of momenta in [-pi, pi]
    mu    : chemical potential
    t     : hopping
    delta : pairing amplitude
    """
    nz = -mu - 2.0 * t * np.cos(k)
    ny = -2.0 * delta * np.sin(k)
    return nz, ny


# ── Bulk spectrum ─────────────────────────────────────────────────────────────

def bulk_energy(
    k: np.ndarray,
    mu: float,
    t: float = 1.0,
    delta: float = 1.0,
) -> np.ndarray:
    """Positive BdG quasiparticle energy E(k) = |n(k)|."""
    nz, ny = bdg_vector(k, mu, t, delta)
    return np.sqrt(nz**2 + ny**2)


def bulk_gap(
    mu: float,
    t: float = 1.0,
    delta: float = 1.0,
    nk: int = 2000,
) -> float:
    """
    Minimum quasiparticle energy over the full Brillouin zone
    (= bulk gap, zero at a phase transition).
    """
    k = np.linspace(-np.pi, np.pi, nk, endpoint=False)
    return float(np.min(bulk_energy(k, mu, t, delta)))


# ── Phase boundary (analytical) ───────────────────────────────────────────────

def critical_mu(t: float = 1.0) -> tuple[float, float]:
    """Return the two critical chemical potentials mu = ±2t."""
    return -2.0 * t, 2.0 * t
