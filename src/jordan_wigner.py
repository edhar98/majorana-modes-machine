"""
jordan_wigner.py — Qubit Hamiltonian for the 1D Kitaev chain via Jordan-Wigner.

Convention:
    c_j  = (Z_0 Z_1 ... Z_{j-1}) sigma^-_j
    c†_j = (Z_0 Z_1 ... Z_{j-1}) sigma^+_j

This maps the Kitaev Hamiltonian exactly to:
    H = -mu/2 * sum_j Z_j
        + (t - delta)/2 * sum_j X_j X_{j+1}
        + (t + delta)/2 * sum_j Y_j Y_{j+1}

The fermion parity operator P = prod_j Z_j commutes with H,
splitting the Hilbert space into even (+1) and odd (-1) parity sectors.
"""

import numpy as np

# ── Single-site Paulis ────────────────────────────────────────────────────────
I2 = np.eye(2, dtype=complex)
X  = np.array([[0,  1 ], [1,  0 ]], dtype=complex)
Y  = np.array([[0, -1j], [1j, 0 ]], dtype=complex)
Z  = np.array([[1,  0 ], [0, -1 ]], dtype=complex)
Sp = np.array([[0,  1 ], [0,  0 ]], dtype=complex)   # sigma+ = (X+iY)/2
Sm = np.array([[0,  0 ], [1,  0 ]], dtype=complex)   # sigma- = (X-iY)/2


def _kron(ops):
    out = ops[0]
    for op in ops[1:]:
        out = np.kron(out, op)
    return out


def pauli_at(op, j, L):
    """Single-site op at site j, identity elsewhere."""
    return _kron([op if k == j else I2 for k in range(L)])


def two_site(opA, opB, j, L):
    """opA at j, opB at j+1, identity elsewhere (j < L-1)."""
    return _kron([opA if k == j else opB if k == j + 1 else I2 for k in range(L)])


def kitaev_qubit_hamiltonian(L: int, t: float = 1.0, mu: float = 0.0,
                              delta: float = 1.0) -> np.ndarray:
    """Return the (2^L × 2^L) qubit Hamiltonian via Jordan-Wigner (OBC).

    H = -mu/2 * sum_j Z_j
        + (t - delta)/2 * sum_j X_j X_{j+1}
        + (t + delta)/2 * sum_j Y_j Y_{j+1}
    """
    dim = 2 ** L
    H = np.zeros((dim, dim), dtype=complex)

    for j in range(L):
        H -= (mu / 2) * pauli_at(Z, j, L)

    for j in range(L - 1):
        H += ((t - delta) / 2) * two_site(X, X, j, L)
        H += ((t + delta) / 2) * two_site(Y, Y, j, L)

    return H


def parity_operator(L: int) -> np.ndarray:
    """Fermion parity P = Z_0 ⊗ Z_1 ⊗ ... ⊗ Z_{L-1}."""
    return _kron([Z] * L)


def spectrum_by_parity(L: int, t: float = 1.0, mu: float = 0.0,
                        delta: float = 1.0):
    """Diagonalize H and split eigenvalues by fermion parity sector.

    Returns
    -------
    evals_even : ndarray — eigenvalues with parity +1, sorted
    evals_odd  : ndarray — eigenvalues with parity -1, sorted
    """
    H = kitaev_qubit_hamiltonian(L, t, mu, delta)
    P = parity_operator(L)
    evals, evecs = np.linalg.eigh(H)

    parities = np.real(np.einsum('ij,ij->j', evecs.conj(), P @ evecs))
    even_mask = parities > 0

    return np.sort(evals[even_mask]), np.sort(evals[~even_mask])


def parity_gap(L: int, t: float = 1.0, mu: float = 0.0,
               delta: float = 1.0) -> float:
    """Energy difference between the lowest even- and odd-parity states.

    Zero in the thermodynamic limit of the topological phase
    (two parity sectors degenerate), nonzero in the trivial phase.
    """
    ev, od = spectrum_by_parity(L, t, mu, delta)
    return abs(ev[0] - od[0])
