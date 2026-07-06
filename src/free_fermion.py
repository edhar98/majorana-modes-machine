"""Exact free-fermion (Bogoliubov-de Gennes) solver for the Kitaev chain.

The Block-4 qubit Hamiltonian (block3_core.qubit_hamiltonian)

    H = -mu/2 sum_j Z_j
        + (t-Delta)/2 sum_j X_j X_{j+1}
        + (t+Delta)/2 sum_j Y_j Y_{j+1}

is quadratic in fermions, so its ground state, energy, parity gap and the edge
string <O_edge> follow from a 2L x 2L real antisymmetric Majorana matrix in
O(L^3) time -- no 2^L object anywhere. This replaces np.linalg.eigh on the
2^L x 2^L Hamiltonian for the *ideal* reference and scales to L ~ hundreds.

Majorana convention (0-indexed sites j = 0..L-1, Majoranas a = 0..2L-1):
    gamma_{2j}   = (prod_{k<j} Z_k) X_j = c_j + c_j^dagger
    gamma_{2j+1} = (prod_{k<j} Z_k) Y_j
Under this map the Hamiltonian is  H = (i/2) sum_{a<b} A_{ab} gamma_a gamma_b
with the real antisymmetric A built in `majorana_matrix`. The three Pauli terms
map to Majorana bilinears exactly (no constant), so E0 = -1/2 sum_k eps_k with
+eps_k the canonical-form frequencies.

Key identity (derived, verified by the self-test):
    O_edge = X_0 Z_1 ... Z_{L-2} X_{L-1} = -i gamma_1 gamma_{2L-2},
the product of the two unpaired end Majoranas; hence <O_edge> is a single
entry of the Majorana covariance matrix.

Run `python src/free_fermion.py` to execute the self-test against the exact
eigh path (block3_core) at several L, mu.
"""
import numpy as np

T = 1.0
DELTA = 1.0


def majorana_matrix(L, t=T, delta=DELTA, mu=0.0):
    """Real antisymmetric 2L x 2L matrix A with H = (i/2) sum_{a<b} A_ab g_a g_b.

    Nonzero couplings (derived from the Jordan-Wigner map of the qubit H):
      on-site   A[2j, 2j+1]   = mu_j         (from -mu_j/2 Z_j = i mu_j/2 g_{2j} g_{2j+1})
      bond b-a  A[2j+1, 2j+2] = delta - t    (from (t-delta)/2 X_j X_{j+1})
      bond a-b  A[2j,   2j+3] = t + delta     (from (t+delta)/2 Y_j Y_{j+1})
    plus antisymmetric partners.

    `mu` may be a scalar (uniform chemical potential) or a length-L array of
    per-site values mu_j -- the latter is how local chemical-potential disorder
    (charge noise, sum_j delta mu_j Z_j in the qubit picture) enters.
    """
    n = 2 * L
    mu_arr = np.broadcast_to(np.asarray(mu, dtype=float), (L,))
    A = np.zeros((n, n))
    for j in range(L):
        A[2 * j, 2 * j + 1] = mu_arr[j]
    for j in range(L - 1):
        A[2 * j + 1, 2 * j + 2] = delta - t
        A[2 * j, 2 * j + 3] = t + delta
    A = A - A.T
    return A


def _canonical(A):
    """Canonical form of real skew-symmetric A: blocks [[0, eps],[-eps, 0]], eps>=0.

    Returns (eps, O) with A = O @ blkdiag([[0,eps_k],[-eps_k,0]]) @ O.T, O real
    orthogonal and every eps_k >= 0.

    Robust route (no real-Schur block guessing, which underflows for the near-zero
    edge modes at large L): iA is Hermitian with eigenvalues +-eps_k. For a
    positive eigenvalue eps with (unit) eigenvector v, the relations A Re(v)=eps
    Im(v)*... hold so that, with a=Re(v), b=Im(v),
        A a = eps b,   A b = -eps a,   |a|=|b|=1/sqrt(2),   a.b = 0
    (the last two because v^T v = 0, v being orthogonal to its conjugate, the
    -eps partner). Hence the orthonormal pair (u1,u2) = (sqrt2 b, sqrt2 a) gives
    the block A u1 = -eps u2, A u2 = eps u1, i.e. the +eps*J_std block.
    """
    n = A.shape[0]
    w, V = np.linalg.eigh(1j * A)       # real eigenvalues, ascending: -eps ... +eps
    m = n // 2
    eps = np.empty(m)
    O = np.empty((n, n))
    for k in range(m):
        idx = n - 1 - k                 # k-th largest -> the positive eps_k
        v = V[:, idx]
        eps[k] = w[idx]
        O[:, 2 * k] = np.sqrt(2.0) * v.imag      # u1 = q
        O[:, 2 * k + 1] = np.sqrt(2.0) * v.real  # u2 = p
    return eps, O


def ground(L, t=T, delta=DELTA, mu=0.0):
    """Exact ground-state data of the Kitaev chain via BdG. O(L^3).

    Returns dict with:
      energy     ground-state energy  E0 = -1/2 sum_k eps_k
      cov        2L x 2L Majorana covariance  M_ab = i <gamma_a gamma_b>
      eps        canonical-form frequencies (sorted asc); min(eps) is the
                 single-particle gap, i.e. the parity-gap scale
      parity_gap min(eps)
    """
    A = majorana_matrix(L, t, delta, mu)
    eps, O = _canonical(A)
    n = 2 * L
    # Ground state of a canonical mode H_block = eps * (i g_a g_b) has
    # <i g_a g_b> = -1, so the block orientation is [[0,-1],[1,0]] (not +1).
    J = np.zeros((n, n))
    for k in range(n // 2):
        i = 2 * k
        J[i, i + 1] = -1.0
        J[i + 1, i] = 1.0
    cov = O @ J @ O.T                    # M_ab = i <gamma_a gamma_b>
    cov = 0.5 * (cov - cov.T)            # enforce exact antisymmetry
    return {'energy': -0.5 * float(np.sum(eps)),
            'cov': cov,
            'eps': np.sort(eps),
            'parity_gap': float(np.min(eps))}


def edge_string(cov):
    """<O_edge> = <-i gamma_1 gamma_{2L-2}> from the covariance matrix.

    With M_ab = i<g_a g_b>, <-i g_1 g_{2L-2}> = -i * (-i M[1,2L-2]) = -M[1,2L-2].
    """
    n = cov.shape[0]
    return -float(cov[1, n - 2])


def local_z(cov, site=0):
    """<Z_site> = <-i gamma_{2s} gamma_{2s+1}> = -M[2s, 2s+1]."""
    return -float(cov[2 * site, 2 * site + 1])


def _selftest():
    import sys
    sys.path.insert(0, 'src')
    from block3_core import qubit_hamiltonian, edge_string as edge_op, parity, local_z as lz_op

    def exact(L, t, delta, mu):
        """Exact ground energy, edge string, <Z0>, and even/odd parity splitting."""
        H = qubit_hamiltonian(L, t, mu, delta).to_matrix()
        P = parity(L).to_matrix()
        w, V = np.linalg.eigh(H)
        O = edge_op(L).to_matrix()
        Z0 = lz_op(L, 0).to_matrix()
        order = np.argsort(w)
        e_even = e_odd = None
        ge = ed = z0 = None
        for idx in order:                # scan up; grab lowest state of each parity
            v = V[:, idx]
            par = float(np.real(np.vdot(v, P @ v)))
            if par > 0.5 and e_even is None:
                e_even = w[idx]
                ge = w[idx]
                ed = float(np.real(np.vdot(v, O @ v)))
                z0 = float(np.real(np.vdot(v, Z0 @ v)))
            if par < -0.5 and e_odd is None:
                e_odd = w[idx]
            if e_even is not None and e_odd is not None:
                break
        gap = abs(e_odd - e_even)        # many-body parity splitting = min single-particle eps
        return ge, ed, z0, gap

    # Observables are compared at GAPPED mu only: at mu=0 the parity gap is exactly
    # zero, the eigh ground space is 2-fold degenerate, and its edge string is
    # basis-dependent -- the BdG value is the well-defined one there.
    print(f"{'L':>3} {'mu/t':>5} {'E ff':>10} {'E eigh':>10} {'dE':>9} "
          f"{'edge ff':>9} {'edge ex':>9} {'Z0 ff':>7} {'Z0 ex':>7} "
          f"{'gap ff':>9} {'gap ex':>9}")
    ok = True
    for L in (4, 6, 8):
        for mu in (0.5, 1.0, 2.5):       # topological (0.5, 1.0) and trivial (2.5), all gapped
            g = ground(L, T, DELTA, mu)
            e_ff, ed_ff, z_ff, gp_ff = g['energy'], edge_string(g['cov']), local_z(g['cov'], 0), g['parity_gap']
            e_ex, ed_ex, z_ex, gp_ex = exact(L, T, DELTA, mu)
            dE = abs(e_ff - e_ex)
            match = (dE < 1e-8 and abs(ed_ff - ed_ex) < 1e-7
                     and abs(z_ff - z_ex) < 1e-7 and abs(gp_ff - gp_ex) < 1e-6)
            ok = ok and match
            print(f"{L:>3} {mu:>5.1f} {e_ff:>10.5f} {e_ex:>10.5f} {dE:>9.1e} "
                  f"{ed_ff:>9.4f} {ed_ex:>9.4f} {z_ff:>7.3f} {z_ex:>7.3f} "
                  f"{gp_ff:>9.5f} {gp_ex:>9.5f} {'' if match else '  <-- MISMATCH'}")
    print("\nSELF-TEST", "PASSED" if ok else "FAILED",
          "(energy, edge string, <Z0>, parity gap all vs exact eigh)")
    return ok


if __name__ == '__main__':
    _selftest()
