# Individual Reports — Sign-up & Topic Split

Final phase of **Majorana Modes in the Machine**. Each of the six group members
writes **one individual report**. The whole project is split into **six
non-overlapping parts** below — no two reports may cover the same material.

## Rules

- **Length:** max **4–5 pages** (excluding references).
- **Individual:** you write your own part; no shared authorship.
- **No overlap:** stay inside your part's **scope line**. At a seam with a
  neighbour, use a one-line *"see [Author, Part N]"* cross-reference instead of
  re-explaining their material.
- **How to claim a topic:** put your name in the **Owner** column of the row you
  want and **commit**. First commit wins a contested row.
- **How to build your report:** see [`AGENTS.md`](AGENTS.md). In short: copy
  `Edgar_Harutyunyan/` to `Firstname_Lastname/`, edit three macros, write in
  `sections/`, run `make`.

## The six parts

| # | Report title | Scope (your boundary) | Weeks | Owner |
|---|---|---|---|---|
| 1 | **Kitaev Chain & Bulk Topology** | The infinite/bulk story: lattice Hamiltonian, Majorana representation, real-space→momentum BdG, dispersion $E(k)$, gap closing $\lvert\mu\rvert=2t$, winding number $\nu$, phase diagram. | 1–2 | Guilherme Schewtschik |
| 2 | **Finite-Size Physics & Majorana Edge Modes** | The finite open chain / edge story: OBC spectrum, near-zero edge modes, exponential edge localisation, hybridisation splitting $E_0(L)\approx 2t(\lvert\mu\rvert/2t)^L$, the sign-filter artefact. | 2–3 | Zhenming Shi |
| 3 | **Qubit Encoding (Jordan–Wigner)** | The fermion→qubit mapping: JW term-by-term, qubit $H$ (Z/XX/YY), sweet spot $t=\Delta$, fermion-parity operator & sectors, parity-gap vs BdG cross-check, AFM-Ising comparison. | 4 | Jaskaran Singh |
| 4 | **Measuring Topology on Circuits (VQE + string order)** | The ideal (noiseless) circuit measurement: VQE prep (EfficientSU2), local vs non-local observables, edge string $X_0 Z_1\cdots Z_{L-2} X_{L-1}$, basis rotation, shot readout, $\mu$-sweep, parity-constrained VQE, ansatz depth. | 5–7 | _(unclaimed)_ |
| 5 | **NISQ Noise on the Diagnostic** | How realistic device noise degrades the measured signal: readout/depolarizing/$T_1T_2$ channels, circuit vs frozen vs parameter noise, gate-by-gate verification, depth optimum, coherent vs incoherent errors, noisy-opt $\neq$ state-prep, backend calibration. | 8–9 | _(unclaimed)_ |
| 6 | **Error Taxonomy & Scaling to Large L** | The classification principle + classical scaling: which errors kill topology (robust parity-even vs fatal parity-odd poisoning), locality + parity + sub-gap rule, device-noise = physical-error under JW ($T_1$=poisoning, $T_2$=charge noise), parity protection Q1/Q2 vs $L$, free-fermion $O(L^3)$ / MPS-trajectory / real-device large-$L$. | 9–10 | Edgar Harutyunyan |

## Content sources per part (mine these — don't re-derive)

| # | Code (`src/`) | Notes (`notes/`) |
|---|---|---|
| 1 | `bdg_bulk.py`, `winding.py`, `block1.py` figs 1,2,3,7,8 | *(no dedicated note — mine week1/2 slides)* |
| 2 | `kitaev_chain.py`, `block1.py` figs 4,5,6,9 | `finite_size_majorana_splitting`, `majorana_splitting_vs_L` |
| 3 | `jordan_wigner.py`, `block2.py` figs 1,2 | `qubit_encoding_derivations`, `ising_comparison` |
| 4 | `block3_core.py`, `block3.py` figs 1–8 | `measuring_topology_qiskit`, `string_order_phase_sweep`, `parity_constrained_vqe_sweep` |
| 5 | `block4.py` figs 1,2,3,6,7,8,9 | `block4_noise_diagnostic`, `circuit_level_gate_noise`, `noisy_vqe_and_backend_noise`, `topology_noise_reps_scaling` |
| 6 | `block4_errors.py`, `free_fermion.py`, `block4_scaling.py`, `block4_largeL.py`, `block4.py` figs 4,5 | `kitaev_error_taxonomy`, `parity_topology_protection`, `scaling_to_large_L` |

## The #5 / #6 seam (negotiable)

Parts 5 and 6 both touch Block 4 and meet at the $T_1/T_2$ ↔ physical-error
mapping. **Default split:** Part 6 owns the *conceptual/classification* framing
(error taxonomy, the Jordan–Wigner identity device-noise = physical-error, the
parity-protection principle); Part 5 owns the *quantitative device-noise* results
(channel mechanics, depth optimum, backend numbers). The Part-5 and Part-6 owners
**finalise this seam between themselves once both rows are claimed**, and update
this note if they move the line.

## Shared — owned by nobody

`src/utils.py` (plot style), `src/showcase.py` (gallery restyles spanning all
blocks — **off-limits as report figures**), and the **week-10 capstone deck**
(project summary). Each report writes its own short intro/conclusion; nobody
"owns" the overall summary.
