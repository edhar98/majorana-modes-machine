"""Which physical Kitaev-chain errors destroy the topological phase?

Prof. Rosenow's question, three steps:
  (1) physical perturbation of the Kitaev Hamiltonian,
  (2) Jordan-Wigner -> qubit operator,
  (3) does it kill the topological signature (edge string / parity) or not?

The organising principle is *symmetry vs topology*: a perturbation is
topologically harmless only if it is (a) local, (b) fermion-parity preserving,
and (c) weaker than the bulk gap. Break any of these and the phase dies.

Two exact numerical controls, both at the gapped topological point mu0 = 0.5 t:

  POSITIVE control -- ROBUST error (this file: `disorder_sweep`)
    Local chemical-potential disorder  sum_j d.mu_j n_j  ->  random Z field
    sum_j d.h_j Z_j (parity preserving). Computed *exactly to large L* with the
    free-fermion BdG solver (per-site mu). The edge string and parity gap survive
    until the disorder strength approaches the bulk gap Delta = 2t - mu0.

  NEGATIVE control -- FATAL error (this file: `contrast_ed`)
    Quasiparticle poisoning: a single fermion enters/leaves the end,
    c_0 + c_0^dagger = gamma_0 = X_0 (a parity-ODD boundary operator). Because the
    logical bit lives in two zero-energy Majoranas, an arbitrarily weak
    parity-breaking coupling g X_0 mixes the even/odd sectors: <P> collapses and
    the edge string with it. Done by exact diagonalisation (2^L) so parity is free
    to change -- something the (parity-fixed) free-fermion solver cannot see.

Run `python src/block4_errors.py --selftest`  for the sanity checks, or
`python src/block4_errors.py`                 to (re)generate both figures.
"""
import argparse
import numpy as np

import sys
sys.path.insert(0, 'src')
from free_fermion import ground, edge_string as ff_edge          # noqa: E402
from block3_core import (qubit_hamiltonian, edge_string, parity,  # noqa: E402
                         local_z)
from qiskit.quantum_info import SparsePauliOp                     # noqa: E402

T = 1.0
DELTA = 1.0
# Representative topological point mu0 = t (bulk gap Delta = 2t-mu0 = t). Chosen
# over the deck's mu0 = 0.5t so the *exponentially* small clean parity gap
# (~(mu0/2t)^L) stays above the eigh floor at the large L used below -- at
# mu0=0.5t it underflows by L~30 and the edge Majorana pairing becomes numerically
# ambiguous. The edge string is still solidly topological here (0.75).
MU0 = 1.0


def bulk_gap(mu0=MU0, t=T):
    """Clean Kitaev bulk gap min_k E_k. For |mu|<2t and t=delta this is 2t-|mu|."""
    k = np.linspace(0, np.pi, 4001)
    Ek = np.sqrt((mu0 + 2 * t * np.cos(k)) ** 2 + (2 * DELTA * np.sin(k)) ** 2)
    return float(Ek.min())


# --------------------------------------------------------------------------- #
#  POSITIVE control: disorder robustness, exact, large L (free-fermion BdG)    #
# --------------------------------------------------------------------------- #
def disorder_sweep(L_list=(16, 32), W_grid=None, n_real=300, mu0=MU0, seed=0):
    """Disorder-averaged edge string & parity gap vs local Z-field strength W.

    Per-site mu_j = mu0 + Uniform(-W, W) (parity-preserving charge noise). For
    each (L, W) we average |<O_edge>| and the parity gap min(eps) over n_real
    realisations. Returns {L: dict(W, edge, edge_std, gap)}.
    """
    if W_grid is None:
        W_grid = np.linspace(0.0, 2.5, 21)
    rng = np.random.default_rng(seed)
    out = {}
    for L in L_list:
        edge = np.zeros_like(W_grid)
        estd = np.zeros_like(W_grid)
        gap = np.zeros_like(W_grid)
        for i, W in enumerate(W_grid):
            e = np.empty(n_real)
            g = np.empty(n_real)
            for r in range(n_real):
                mu_j = mu0 + rng.uniform(-W, W, size=L)
                gr = ground(L, T, DELTA, mu_j)
                e[r] = abs(ff_edge(gr['cov']))
                g[r] = gr['parity_gap']
            edge[i], estd[i], gap[i] = e.mean(), e.std(), g.mean()
            print(f"  [disorder] L={L:>3} W={W:4.2f}  |edge|={edge[i]:.3f}"
                  f" +-{estd[i]:.3f}  gap={gap[i]:.3e}")
        out[L] = dict(W=W_grid, edge=edge, edge_std=estd, gap=gap)
    return out


# --------------------------------------------------------------------------- #
#  NEGATIVE control: robust vs fatal, same L, exact diagonalisation            #
# --------------------------------------------------------------------------- #
def _x0_operator(L):
    """gamma_0 = X_0 in the block3_core convention (qubit 0 at string pos L-1)."""
    label = ['I'] * L
    label[L - 1] = 'X'
    return SparsePauliOp(["".join(label)], [1.0])


def _low_eigs(H, k=6):
    """Lowest-k (eigenvalue, eigenvector) of a sparse Hermitian H, ascending."""
    from scipy.sparse.linalg import eigsh
    w, V = eigsh(H, k=min(k, H.shape[0] - 1), which="SA")
    order = np.argsort(w)
    return w[order], V[:, order]


def _ground_even(H, Pdiag):
    """Lowest eigenstate of H in the even-parity (<P>>0) sector (sparse).

    Parity-preserving noise cannot change the sector the logical bit is stored
    in; the physical question is whether the *edge string* survives there. (Taking
    the global ground state instead would just track which of the near-degenerate
    even/odd states a given disorder realisation pushes lowest -- a sector flip,
    not a parity violation.)  Pdiag is the (real +-1) diagonal of P.
    """
    _, V = _low_eigs(H, k=6)
    for c in range(V.shape[1]):
        v = V[:, c]
        if float(np.sum(Pdiag * (np.abs(v) ** 2))) > 0.5:
            return v
    return V[:, 0]


def contrast_ed(L=10, s_grid=None, n_real=120, mu0=MU0, seed=1):
    """Edge string & parity vs perturbation strength for a robust vs a fatal error.

    robust: H + sum_j d.h_j Z_j, d.h_j ~ U(-s,s) (parity-preserving), averaged.
    fatal:  H + s * X_0            (parity-breaking quasiparticle poisoning).
    Returns dict with s and, for each channel, edge[] and par[] (=<P>).

    Z_j (and P) are diagonal, so the disorder term is added straight onto the
    diagonal and only the lowest few eigenpairs are solved (sparse eigsh).
    """
    import scipy.sparse as sp
    if s_grid is None:
        s_grid = np.linspace(0.0, 1.5, 26)
    H0 = qubit_hamiltonian(L, T, mu0, DELTA).to_matrix(sparse=True).tocsc()
    Oed = edge_string(L).to_matrix(sparse=True)
    Pop = parity(L).to_matrix(sparse=True)
    X0 = _x0_operator(L).to_matrix(sparse=True)
    zdiag = [np.real(local_z(L, j).to_matrix(sparse=True).diagonal()) for j in range(L)]
    Pdiag = np.real(Pop.diagonal())
    dim = H0.shape[0]
    rng = np.random.default_rng(seed)

    def expect(psi, M):
        return float(np.real(np.vdot(psi, M @ psi)))

    r_edge = np.zeros_like(s_grid); r_par = np.zeros_like(s_grid)
    f_edge = np.zeros_like(s_grid); f_par = np.zeros_like(s_grid)
    for i, s in enumerate(s_grid):
        # robust: parity-preserving Z disorder (diagonal), averaged, even sector
        ee = np.empty(n_real); pp = np.empty(n_real)
        for r in range(n_real):
            dh = rng.uniform(-s, s, size=L)
            d = np.zeros(dim)
            for j in range(L):
                d += dh[j] * zdiag[j]
            H = H0 + sp.diags(d)
            psi = _ground_even(H, Pdiag)
            ee[r] = abs(expect(psi, Oed)); pp[r] = expect(psi, Pop)
        r_edge[i], r_par[i] = ee.mean(), pp.mean()
        # fatal: parity-breaking boundary field (deterministic)
        _, V = _low_eigs(H0 + s * X0, k=2)
        psi = V[:, 0]
        f_edge[i], f_par[i] = abs(expect(psi, Oed)), expect(psi, Pop)
        print(f"  [contrast] s={s:4.2f}  robust |edge|={r_edge[i]:.3f} P={r_par[i]:+.2f}"
              f"   fatal |edge|={f_edge[i]:.3f} P={f_par[i]:+.2f}")
    return dict(s=s_grid, L=L, robust_edge=r_edge, robust_par=r_par,
                fatal_edge=f_edge, fatal_par=f_par)


# --------------------------------------------------------------------------- #
#  Figures                                                                     #
# --------------------------------------------------------------------------- #
def render_disorder(data, mu0=MU0, out="plots/block4_disorder_robustness.pdf"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    Wc = bulk_gap(mu0)
    plt.rcParams.update({"font.size": 12})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.9))
    cols = {16: "#1f77b4", 32: "#d62728", 40: "#2ca02c", 20: "#9467bd", 60: "#8c564b"}
    for L, d in sorted(data.items()):
        c = cols.get(L, "gray")
        a1.plot(d["W"], d["edge"], "-o", color=c, ms=4, lw=1.6, label=f"$L={L}$")
        a1.fill_between(d["W"], d["edge"] - d["edge_std"], d["edge"] + d["edge_std"],
                        color=c, alpha=0.15)
        a2.semilogy(d["W"], np.maximum(d["gap"], 1e-12), "-o", color=c, ms=4, lw=1.6,
                    label=f"$L={L}$")
    for ax in (a1, a2):
        ax.axvline(Wc, ls="--", color="black", lw=1.1)
        ax.set_xlabel(r"disorder strength $W$  ($\mu_j=\mu_0+U[-W,W]$)")
    a1.annotate(r"bulk gap $\Delta$", xy=(Wc, 0.15), xytext=(Wc + 0.15, 0.3),
                fontsize=9)
    a1.set_ylabel(r"$|\langle O_{\mathrm{edge}}\rangle|$")
    a1.set_ylim(0, 1.0); a1.legend(loc="lower left", fontsize=10)
    a2.set_ylabel(r"parity gap $\delta E=\min_k\varepsilon_k$")
    a2.legend(loc="upper left", fontsize=10)
    a1.set_title("Edge string: robust to sub-gap disorder", fontsize=11)
    a2.set_title(r"Parity gap: protected until $W\!\sim\!\Delta$", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print(f"[saved] {out}")


def render_contrast(d, out="plots/block4_robust_vs_fatal.pdf"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 12})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.9))
    rob, fat = "#1f77b4", "#d62728"
    a1.plot(d["s"], d["robust_edge"], "-o", color=rob, ms=4, lw=1.7,
            label=r"robust: $\sum_j\delta h_j Z_j$ (parity-even)")
    a1.plot(d["s"], d["fatal_edge"], "-s", color=fat, ms=4, lw=1.7,
            label=r"fatal: $g\,X_0$ (QP poisoning, parity-odd)")
    a2.plot(d["s"], d["robust_par"], "-o", color=rob, ms=4, lw=1.7, label="robust")
    a2.plot(d["s"], d["fatal_par"], "-s", color=fat, ms=4, lw=1.7, label="fatal")
    a1.set_ylabel(r"$|\langle O_{\mathrm{edge}}\rangle|$"); a1.set_ylim(0, 1.0)
    a2.set_ylabel(r"$\langle P\rangle$"); a2.set_ylim(-1.05, 1.05)
    a2.axhline(0, color="gray", lw=0.6)
    for ax in (a1, a2):
        ax.set_xlabel(r"perturbation strength")
    a1.legend(loc="lower left", fontsize=9)
    a1.set_title(f"Edge string ($L={d['L']}$, exact)", fontsize=11)
    a2.set_title("Fermion parity", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print(f"[saved] {out}")


# --------------------------------------------------------------------------- #
def _selftest():
    print("--- selftest ---")
    ok = True
    # (a) clean edge string at mu0=t is the topological value 0.75, and resolvable
    g = ground(32, T, DELTA, MU0)
    e0 = abs(ff_edge(g["cov"]))
    print(f"(a) clean L=32 edge string = {e0:.4f} (topological), gap={g['parity_gap']:.1e}")
    ok &= 0.6 < e0 < 0.9 and g["parity_gap"] > 1e-12
    # (b) parity-preserving Z disorder keeps the edge string; parity-breaking X0 flips P
    d = contrast_ed(L=8, s_grid=np.array([0.0, 0.3, 0.8]), n_real=40)
    print(f"(b) robust edge @s=0.3: {d['robust_edge'][1]:.3f} (should stay high)")
    print(f"    fatal  <P>  @s=0.8: {d['fatal_par'][2]:+.3f} (should fall from +1)")
    ok &= d["robust_edge"][1] > 0.6
    ok &= d["fatal_par"][2] < 0.9
    # (c) bulk gap sanity
    print(f"(c) bulk gap at mu0={MU0}: {bulk_gap():.3f}  (expect 2t-mu0={2*T-MU0:.1f})")
    ok &= abs(bulk_gap() - (2 * T - MU0)) < 1e-2
    print("\nSELF-TEST", "PASSED" if ok else "FAILED")
    return ok


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--n-real", type=int, default=300)
    p.add_argument("--ed-L", type=int, default=10)
    p.add_argument("--ed-real", type=int, default=120)
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.selftest:
        raise SystemExit(0 if _selftest() else 1)
    print("=== disorder robustness (free-fermion, exact) ===")
    dd = disorder_sweep(L_list=(16, 32), n_real=args.n_real)
    render_disorder(dd)
    print("=== robust vs fatal (exact diagonalisation) ===")
    cc = contrast_ed(L=args.ed_L, n_real=args.ed_real)
    render_contrast(cc)
    print("Done.")
