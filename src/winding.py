"""
winding.py — Z topological invariant (winding number) for the Kitaev chain.

Follows slide 6 of the physics-bridge deck.

Definition (eq. 18–19):
  theta_k = arg(n_z(k) + i n_y(k))
  nu       = (1/2pi) * integral_BZ  d(theta_k)/dk  dk

Interpretation:
  nu = 0  →  trivial phase   (loop does not enclose origin)
  nu = 1  →  topological     (loop winds once around origin)

The invariant can only change when the bulk gap closes (|mu| = 2t).
"""

import numpy as np
from bdg_bulk import bdg_vector


def winding_number(
    mu: float,
    t: float = 1.0,
    delta: float = 1.0,
    nk: int = 10_000,
) -> int:
    """
    Numerically integrate the winding of the BdG d-vector around the BZ.

    Returns the winding number as an integer (0 or ±1 for the Kitaev chain).
    """
    k = np.linspace(-np.pi, np.pi, nk, endpoint=False)
    nz, ny = bdg_vector(k, mu, t, delta)

    theta = np.arctan2(ny, nz)
    theta_unwrapped = np.unwrap(theta)

    # Total winding = net change in angle / 2pi
    nu = (theta_unwrapped[-1] - theta_unwrapped[0]) / (2.0 * np.pi)
    return int(round(nu))


def winding_scan(
    mu_arr: np.ndarray,
    t: float = 1.0,
    delta: float = 1.0,
) -> np.ndarray:
    """Compute the winding number for an array of mu values."""
    return np.array([winding_number(mu, t, delta) for mu in mu_arr])