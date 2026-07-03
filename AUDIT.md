# AUDIT.md — Deep-Correctness Audit (2026-07-03)

Adversarial first-principles audit of the full project (code, notes, figures, slides),
hunting for a deep conceptual/physics error. Every central claim was re-derived from the
Hamiltonian and reproduced numerically, independently of the project code paths.

## Verdict

**No deep conceptual mistake found.** The physics chain — Kitaev H → BdG → Jordan–Wigner →
parity sectors → edge-string diagnostic → VQE → noise channels — is correct end to end,
including sign conventions, factors of 2, the t±Δ split, and the symmetry-vs-topology
attribution. One genuine **data-extraction bug** exists (Finding 1); it corrupts two
spectrum figures invisibly but invalidates no quoted number or conclusion.

---

## Finding 1 — `positive_spectrum()` returns duplicated levels  [MODERATE — fix before final talk]

**Where:** `src/kitaev_chain.py:75`

```python
return np.sort(np.abs(evals))[:self.L]     # WRONG past index [0]
```

**Why wrong:** the 2L BdG eigenvalues come in ±E pairs, so `np.abs` yields each physical
quasiparticle energy **twice**. Taking the first L entries returns the lowest L/2 energies,
each duplicated — not the L physical energies.

**Proof (minimal check):** L=8, t=Δ=1, μ=1:

```
positive_spectrum(): [0.0059 0.0059 1.1744 1.1744 1.5355 1.5355 1.926 1.926]
true positive evals: [0.0059 1.1744 1.5355 1.926  2.286  2.5873 2.8132 2.9528]
```

Cross-check that pinned it: the qubit ED ground energy must equal −½ΣE_n. With
`positive_spectrum()` it is off by O(1) (−5 vs −4 at L=6, μ=0); with the deduplicated
spectrum it agrees to 1e-15 for every (L, t, μ, Δ) tested — this simultaneously proves the
JW mapping is exact and localizes the bug to this one function.

**Blast radius:**
- `src/block1.py:135` (plot 4, `block1_04_finite_size_spectrum.pdf`): claims 12 lowest
  levels, actually shows 6 distinct levels each drawn twice. The first gray "bulk band" is
  a hidden duplicate of the edge mode pinned at zero inside |μ|<2t — contradicting the
  week-3 slide bullet "bulk bands gapped in both phases" (the *true* bands are gapped; the
  plotted data contains a zero-energy curve mislabeled as bulk, invisible under the pink line).
- `src/block2.py:92` (plot 2, `block2_02_qubit_spectrum.pdf`, left panel): same issue,
  3 distinct levels shown as 6.
- **Unaffected:** every `[0]`-only use — `gap()`, block1 plots 6/9, block2 plot 1,
  `showcase.py` (H3), all parity-gap comparisons. No quoted number is wrong.
- Irony to undo: block1 **plot 9** and the week-3 appendix slide advertise this method as
  *"Correct"* vs the *"Wrong"* sign filter, and `AGENTS.md` enshrines it as a verified
  convention. The sign filter's only real flaw was at index [0] (a zero mode rounding to
  −1e-16 gets dropped); the abs-fix repaired that and silently broke indices 1…L−1.

### Corrections

1. In `src/kitaev_chain.py`, `positive_spectrum()`:

   ```python
   evals = np.linalg.eigvalsh(self.build_hamiltonian())
   return np.sort(np.abs(evals))[::2]      # one entry per ±E pair
   ```

   Update the docstring: |E| still protects the near-zero mode; `[::2]` removes the
   particle-hole double counting.
2. Regenerate `block1_04_finite_size_spectrum.pdf` (`python block1.py --plots 4`) and
   `block2_02_qubit_spectrum.pdf` (`python block2.py --plots 2`). Expect twice as many
   distinct bulk lines; edge mode unchanged.
3. Re-word block1 plot 9 / week-3 appendix (`presentation/week3/slides.tex` ~lines 448–464):
   the abs trick alone is only correct for the lowest mode; the full fix is abs **plus**
   deduplication. Update the `AGENTS.md` "verified conventions" bullet accordingly.
4. Acceptance test (add or run once):
   `-0.5*positive_spectrum().sum() == eigvalsh(kitaev_qubit_hamiltonian(...))[0]` to ~1e-12
   for a few (L, t, μ, Δ), e.g. (6,1,1.3,1), (5,1,0.7,1), (7,1,−1.5,0.6).

---

## Finding 2 — Parity-operator derivation internally inconsistent; "GS always even" fails for odd L  [MODERATE/COSMETIC]

**Where:** `notes/qubit_encoding_derivations.tex` §4.1 (≈ line 106) and §"Ground State Parity".

**Why wrong:** §4.1 derives P=∏Z from c†c=(I−Z)/2, contradicting the note's own §2.1
convention c†c=(I+Z)/2 (the one the code uses). With the code's convention,
(−1)^N = (−1)^L·∏Z, so ∏Z equals fermion parity **only for even L**. Numerically verified:
at L=5, μ=−3t the true ground state has ⟨∏Z⟩=−1, falsifying the unqualified claim "the
absolute many-body ground state has even parity."

**Blast radius:** all headline runs use even L (4, 6, 8, 10) — conclusions unaffected.
`src/block4.py` plot 5 (`--L-list 2..8`) does call `ideal_even_density` at odd L=3,5,7,
where "even ∏Z sector" is actually odd fermion parity; the leak/edge-loss curves survive
(any near-degenerate sector state demonstrates the point) but the label is wrong at those points.

### Corrections

1. In §4.1, redo the two lines with n=(I+Z)/2: (−1)^{n_j} = −Z_j, hence
   P_f = (−1)^L ∏Z_j; state that the code's P̂=∏Z equals P_f for even L (and cite the
   AGENTS.md even-L caveat).
2. Qualify "the global ground state is always the even-parity state" → "…always the
   fermion-parity-even state; in the ∏Z labeling used by the code this is the +1 sector
   for even L."
3. Either restrict block4 plot 5 to even L (`--L-list 2 4 6 8`) or add one sentence in
   `notes/parity_topology_protection.tex` noting the odd-L label subtlety.

---

## Finding 3 — Minor items  [COSMETIC]

1. **block1 plot 6** (`block1_06_majorana_splitting.pdf`): the μ=−0.5t numerical curve
   flattens at ~1e-16 for L≳26 — the `eigvalsh` double-precision floor, not physics.
   *Correction:* one caption sentence ("points below ~1e-15 are at the eigensolver noise
   floor"), or clip the curve at 1e-15.
2. **Doc sign mismatch:** `AGENTS.md` says O_edge = +i b₀a_{L−1}; the week-5 audit section
   in `notes/measuring_topology_qiskit.tex` derives O_edge = −i γ_{0,2}γ_{3,1}. Both are
   right under different b-sign conventions and only |⟨O⟩| is used. *Correction:* pick one
   convention and state it once.
3. **Week-6 "classical noise"** `(1−p)v + p·N(0,1)` (`block3_core.noisy_value`) has no
   channel interpretation. Already labeled "classical" and superseded by Block 4 — keep,
   but do not present as a physical noise model.

---

## Verified clean (re-derived and reproduced — do not "fix" these)

| Target | Result |
|---|---|
| JW mapping (signs, μ term, t±Δ) | Exact: qubit GS = −½ΣE_n to 1e-15 across (L,t,μ,Δ); [H,P]=0 exactly |
| Topological window / labels | ν=1 iff \|μ\|<2t (ν=−1 for Δ<0); labels not swapped |
| Edge string O_edge | = −i b₀a_{L−1} = −P·Y₀Y_{L−1}; saturates nonzero in-phase (0.748 at μ=t, L→10), decays exp. out-of-phase (0.0815→0.0039, L=4→10 at μ=3t); works at Δ=0.4; ±μ symmetric |
| Parity gap | Δ_P(L) = BdG E₀ to 1e-15; even-odd splitting, not bulk gap; trivial gap = \|μ\|−2t |
| Splitting formula | E₀(L)=2t(1−λ²)λ^L exact (ratio 1.0000 at L=20 for μ=−0.5,−1,−1.5); ξ⁻¹=ln(2t/\|μ\|) |
| Depth optimum (r=1 vs r≥2) | Genuine under-expressivity: direct fidelity maximization (oracle objective, 40 restarts + differential evolution) caps at exactly F=0.500 for r=1, F=1.000 at r=2 |
| Noise verification | Aer vs gate-by-gate reference agree to 5.6e-17 even at random θ; genuinely different engines (Aer C++ vs quantum_info numpy) |
| Backend noise | `fake_manila` genuinely resolves (qiskit_ibm_runtime 0.47.0 installed) — note's claims match environment |
| Parity-vs-channels table | Phase damping conserves ⟨P⟩ to 10 digits; depolarizing = (1−p)^L exactly; amplitude damping in between; edge string decays under all three |
| VQE sweep honesty | ED-fidelity-assisted restart selection is disclosed (AGENTS.md + week-7 validation panel) — benchmarking, not hidden curation |

## Load-bearing assumptions (residual, could not fully verify)

1. Even L wherever ∏Z is read as fermion parity (see Finding 2).
2. Full 81-point week-7 VQE sweep and block-4 plots 8/9 sweeps not rerun (hours of
   compute); machinery spot-checked, printed diagnostics are self-auditing.
3. Depth-optimum rule is claimed only at L=4; notes correctly refuse to extrapolate.
4. The 1e-15 noise verification validates channel *placement*, conditional on Qiskit's
   `depolarizing_error` definition being the intended physics (it is).
5. Shot curves use binomial resampling of exact expectations (`shot_estimate`) —
   statistically exact for ±1-valued observables, but not per-bitstring sampling.

## Suggested fix order

1. Finding 1 steps 1–2 (one-line code fix + regenerate two figures).
2. Finding 1 steps 3–4 (plot-9/week-3 wording, AGENTS.md bullet, acceptance test).
3. Finding 2 (note §4.1 + odd-L qualifier).
4. Finding 3 as time permits.
