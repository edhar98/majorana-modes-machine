# AGENTS.md

This file provides guidance to coding agents working in this repository.

## Commands

All scripts must be run from `src/` with the project virtualenv active:

```bash
source /opt/python-envs/myenv/bin/activate
cd src
```

Generate plots:
```bash
python block1.py              # all Block 1 plots
python block1.py --list       # list available plots
python block1.py --plots 4 6  # specific plots
python block1.py --L 100      # override chain length
python block2.py              # all Block 2 plots
python block2.py --plots 1    # specific plot
```

Block 3 Week 5 work is currently notebook-first:
```bash
jupyter notebook src/block3_week5.ipynb
```

`block3.py` is the single scripted Block 3 runner covering Weeks 5-7:
```bash
cd src
python block3.py              # all Block 3 plots (slow: plot 7 runs the full VQE sweep)
python block3.py --list       # list available plots
python block3.py --plots 2    # circuit visualization plots only
python block3.py --plots 3 4 5 6   # Week 6 phase-sweep plots
python block3.py --plots 7    # Week 7 parity-constrained VQE mu-sweep
python block3.py --plots 8    # Week 7 ansatz-depth diagnostic
python block3.py --plots 7 --points 41   # coarser, faster VQE sweep
```

`block4.py` is the scripted Block 4 runner for Week 8 and the Week 9 circuit-level NISQ noise study. It continues from the Block 3 Hamiltonian and edge-string definitions in `block3_core.py`; do not use notebook-local Hamiltonians for slide figures:
```bash
cd src
python block4.py --list
python block4.py --plots 1    # Week 8 frozen-state readout/gate-noise sweep (superseded story)
python block4.py --plots 2    # Week 9 edge-string phase sweep vs ansatz depth under per-cx noise
python block4.py --plots 3    # Week 9 exact gate-by-gate verification + thermal T1/T2 variant
python block4.py --plots 4    # parity vs edge string under phase/depolarizing/amplitude channels
python block4.py --plots 5    # intrinsic protection vs noisy vulnerability across chain length L
python block4.py --plots 6    # depth optimum (expressibility threshold vs accumulated gate noise)
python block4.py --plots 7    # coherent (theta+dtheta) vs incoherent gate noise: edge string + purity
python block4.py --plots 8    # noisy VQE optimization: best-case vs noise-aware under unital/non-unital channels
python block4.py --plots 9    # toy uniform noise vs backend-calibrated noise
python block4.py --plots 6 --reps 1 2 3 4 5 6   # depth optimum needs r=1..6 to match the slide figure
```

`block4_scaling.py`, `block4_largeL.py`, and `block4_errors.py` are the Block-4 large-$L$ scaling and physical-error-taxonomy modules (Weeks 9-10), all reusing `block3_core.py`/`block4.py`/`free_fermion.py`:
```bash
cd src
python block4_scaling.py --selftest                        # validate the matrix-free primitives
python block4_scaling.py --Lmax 12 --backend FakeCairoV2   # fixed-depth L-sweep, real device noise
python block4_largeL.py --help                             # fixed-depth device sweep to L=100 (HPC)
python block4_errors.py --selftest                         # error-taxonomy sanity checks
python block4_errors.py                                    # regenerate disorder + robust-vs-fatal figures
python block4_errors.py --vqe-only --vqe-L 10 --vqe-backend FakeCairoV2  # VQE-circuit overlay (ideal+noisy)
```

`showcase.py` generates the intuition-first figure gallery (`plots/show_h{1..9}_*.png` plus `_thumb` variants) published to the GitHub Pages index. It reuses `block3_core.py`/`block4.py` physics; regenerate only when the underlying results change:
```bash
cd src
python showcase.py --list
python showcase.py            # all H1-H9 showcase figures
python showcase.py h2 h5      # specific figures by id
```

Compile slides and notes from the repo root. Make only rebuilds PDFs whose `.tex` sources are newer than the generated PDF:
```bash
make slides      # all outdated presentation PDFs (weeks 1-10)
make week8       # only week 8 if outdated
make week9       # only week 9 if outdated
make notes       # all outdated notes PDFs (notes/*.tex are wildcard-discovered)
make clean       # remove LaTeX auxiliary files
```

`Makefile` `WEEKS` currently lists `1..10`, including the final-synthesis deck in `presentation/week10/`. `showcase.py` has no make target — run it manually as above.

Manual slide compile still works from a week folder:
```bash
cd presentation/weekN
pdflatex slides.tex && pdflatex slides.tex  # double-pass for TOC
```

CI compiles outdated presentation slides and notes on push, then deploys generated PDFs plus an HTML index to GitHub Pages.

Block 3 notebook dependencies include `qiskit`, `qiskit-aer`, `qiskit-algorithms`, `numpy`, `scipy`, and `matplotlib`.

## Current Status (2026-07-01)

- Block 1 is implemented: BdG bulk/real-space physics, winding number, phase diagram, finite-size spectra, Majorana splitting, and comparison plots.
- Block 2 is implemented: Jordan-Wigner qubit Hamiltonian, parity-sector spectra, and parity-gap checks against BdG splitting.
- Block 3 spans Weeks 5-7 and is consolidated into a single runner `src/block3.py` backed by shared helpers in `src/block3_core.py`. Plots 1-2 are Week 5 (VQE observables + circuit diagrams), plots 3-6 are Week 6 (ED-validated edge-string sweep, finite size, local vs non-local, classical-noise robustness), and plots 7-8 are Week 7 (parity-constrained VQE `mu`-sweep with warm-start continuation/ED validation, and the ansatz-depth diagnostic). `src/block3_week5.ipynb` is retained as the interactive Week 5 notebook and historical source for the original Week 5 workflow; current Week 5 slide assets are generated by `block3.py --plots 2`. The old `src/block3_week6.py` and `src/block3_week7.py` have been removed; their logic lives in `block3.py`/`block3_core.py`.
- Week 5 slides use `presentation/week5/slides.tex`. Week 6 slides use `presentation/week6/slides.tex`. Week 7 slides use `presentation/week7/slides.tex`. Week 8 slides use `presentation/week8/slides.tex`. Ignore `presentation/week5/slides_my.tex` unless explicitly asked.
- Block 3 Week 5 plots are now runner-generated PDFs with the `block3_week5_*` signature (matching `block3_week6_*`/`block3_week7_*`), produced by `block3.py --plots 2`. The old ad-hoc PNGs (`block3_VQE_Ansatz.png`, `block3_VQE_Converage.png`, `block3_Measurement.png`, `block3_correlation.png`) and the unused `block3_02/03/04_*.pdf` diagrams were removed; the `Converage` typo and the uppercase `block3_Correlation.png` case bug in the slides are fixed.
- Block 4 starts with Week 8. `src/block4.py` is the scripted continuation after Block 3 validation. Plot 1 generates `block4_week8_noise_sweep.pdf` from the same Kitaev/Jordan-Wigner Hamiltonian and edge-string operator as `block3_core.py`, applying symmetric readout scaling, local two-qubit depolarizing channels, and shot noise. Notebook-local Hamiltonians such as `notebooks/Kitaev_Chain_Noise_Simulation.ipynb` are exploratory only and should not be used as slide-figure sources.
- Block 4 Week 9 is implemented in `src/block4.py` (plots 2-9): circuit-level gate noise via a Qiskit density-matrix `NoiseModel`, verified to ~1e-15 against an independent gate-by-gate reference (`exact_reference_edge`), the depth-optimum study, coherent-vs-incoherent error, the parity-vs-topology and length questions, noisy-VQE re-optimization, and backend-calibrated noise. Week 8's frozen-state noise (plot 1) is treated as a theoretical intro and is superseded by the circuit-level Week 9 method; the Week 9 slides carry no explicit "Week N" wording.
- `presentation/week10/slides.tex` is the final-synthesis capstone deck (16 frames, Blocks 1-4 end-to-end), built on the Block 1-4 result figures (`block1_*`, `block2_*`, `block3_week7_*`, `block4_week9_*`) plus the Week 9-10 large-$L$ scaling and physical-error-taxonomy figures (`block4_scaling_Lsweep`, `block4_largeL_overlay`, `block4_disorder_robustness`, `block4_robust_vs_fatal`). Landscape two-panel figures use a figure-on-top / text-below layout. `src/showcase.py` + `utils.py` (`setup_showcase_style`, `save_showcase`, `topo_window`, `takeaway`) separately produce the intuition-first `plots/show_h*.png` gallery published to GitHub Pages by CI.
- Large-$L$ scaling (Weeks 9-10, `src/block4_scaling.py` + `src/block4_largeL.py`): fixed-depth $r^\ast=4$, statevector-ideal + MPS-trajectory-noisy + free-fermion reference, decoupling expressibility (an $L$-independent depth threshold) from the noise wall (exponential in a linear CNOT count); real-device runs (Cairo/Brooklyn/Washington) push the noisy edge string to $L=100$ on the HPC cluster.
- Physical-error taxonomy (`src/block4_errors.py`, added 2026-07): answers which physical Kitaev-chain perturbations kill the topological phase — robust parity-even charge disorder (exact BdG to $L=32$) vs fatal parity-odd quasiparticle poisoning $g\,X_0$ (ED), plus a `vqe_overlay` that reruns both channels through the actual VQE circuit (ideal statevector + exact density-matrix noisy) against matched exact curves. `free_fermion.majorana_matrix` now accepts a per-site $\mu_j$ so local disorder enters the BdG solver directly.

### Verified conventions and caveats (project review, 2026-07-01)

A full-project correctness review found no results-invalidating error, but pinned down these load-bearing facts. Do not reintroduce the fixed mistakes:

- **Jordan-Wigner convention.** Code uses `c_j^\dagger = (\prod_{k<j} Z_k)\,\sigma_j^+` with `\sigma^\pm=(X\pm iY)/2`, so `c_j^\dagger c_j = \sigma^+\sigma^- = (I+Z_j)/2` — the *occupied* single-site state is `|0>` (`Z=+1`). This reproduces `H = -mu/2 * sum Z + (t-delta)/2 * sum XX + (t+delta)/2 * sum YY` in `jordan_wigner.py` exactly. Do **not** write `c^\dagger c = (I-Z)/2` (it flips the `mu` sign). Fixed in `notes/qubit_encoding_derivations.tex` and `presentation/week4/slides.tex`.
- **Even `L` assumed.** Parity `P = prod Z_j` equals `(-1)^N` only for even `L` (they differ by `(-1)^L`). All parity/even-sector claims assume even `L`.
- **Edge string is a Majorana bilinear.** `O_edge = X_0 Z_1 ... Z_{L-2} X_{L-1} = i b_0 a_{L-1}` exactly. It is a finite-size edge/string diagnostic, **not** a standalone bulk topological invariant.
- **Majorana splitting prefactor.** `E_0(L) ≈ 2t(1-lambda^2)(|mu|/2t)^L` with `lambda=|mu|/2t`; keep the `(1-lambda^2)` factor (bare `2t*lambda^L` is wrong by `1/(1-lambda^2)`). Fixed in `src/block1.py` (plot 6 theory line), `notes/majorana_splitting_vs_L.tex`, `notes/qubit_encoding_derivations.tex`, `presentation/week3/slides.tex`.
- **VQE restart selection is ED-assisted.** `best_state` in `block3_core.py` picks the best restart by fidelity to the ED ground state — fine for benchmarking, but it is ED-assisted post-selection (no device-only objective) and should be disclosed as such.
- **Depth optimum is genuine expressibility.** `r=1` under-expressibility (`|O|≈0`) is real, not an optimizer artifact (survives more restarts / differential evolution). Optimum = shallowest adequately-expressive depth; noise then decays as `(1-p_cx)^{r(L-1)}`.

Current local-only/untracked worktree items observed on 2026-06-11 include `.cursorindexingignore`, `.notes.txt.swp`, `.specstory/`, `diff.tex`, `diff.txt`, `notes.txt`, `tools/`, course-description/main LaTeX auxiliary outputs, a Qiskit crash-course notebook checkpoint, generated presentation PDFs/VRB files, and `presentation/week5/slides_my.tex` / `presentation/week5/slides_my.pdf`. Do not delete or revert these unless explicitly asked.

## Architecture

### Physics modules (`src/`)

The Blocks 1-2 simulation stack has a clean dependency order — import only downward:

```
jordan_wigner.py   block2.py
                        ↓
winding.py         block1.py
    ↓                   ↓
bdg_bulk.py ──────────────
    ↓
kitaev_chain.py
    ↓
utils.py
```

- **`kitaev_chain.py`** — `KitaevChain` class. Builds the (2L×2L) real-space BdG matrix and exposes `.spectrum()`, `.positive_spectrum()`, `.eigh()`, `.gap()`. Use `.positive_spectrum()` for quasiparticle energies: it takes `np.abs(evals)` to avoid near-zero sign-filter spikes and then deduplicates the resulting ±E pairs with `[::2]`. Do not use `.spectrum()[L:]` or `np.sort(np.abs(evals))[:L]` for the full positive spectrum.
- **`bdg_bulk.py`** — momentum-space BdG: `bulk_energy()`, `bulk_gap()`, `bdg_vector()`, `critical_mu()`. Critical points are at `μ = ±2t`.
- **`winding.py`** — `winding_number(mu)` integrates the BdG d-vector angle around the BZ via `np.unwrap`. Returns 0 (trivial) or 1 (topological).
- **`jordan_wigner.py`** — qubit encoding via Jordan-Wigner. `kitaev_qubit_hamiltonian()` returns the (2^L × 2^L) qubit Hamiltonian; `spectrum_by_parity()` splits eigenvalues into even/odd fermion-parity sectors; `parity_gap()` returns `|E₀⁺ − E₀⁻|`. Limited to L ≤ ~14 due to exponential Hilbert-space growth.
- **`utils.py`** — `setup_style()`, `save_fig(fig, filename)`, `clean_axes(ax)`, `COLORS` dict. All plots call these; `block1.py`/`block2.py`/`block3.py` import `clean_axes` from here (single definition). Figures save to `plots/` relative to the repo root.
- **`block3_week5.ipynb`** — original interactive Block 3 Week 5 notebook (pure YY/topological sweet-spot VQE with `EfficientSU2` `RY`/linear-CNOT, `AerEstimator`, L-BFGS-B, parity penalty `lambda=0.1`, subspace-fidelity validation, shot-based measurements). Its logic is now fully reproduced by `block3.py --plots 2` (the `block3_week5_*.pdf` figures), which is what the Week 5 slides use; the notebook is retained only as a historical/interactive artifact.
- **`block3_core.py`** — shared Block 3 logic imported by `block3.py`. Qiskit operators (`qubit_hamiltonian` little-endian `SparsePauliOp`, `edge_string`, `local_z`, `parity`), `vqe_ansatz` (`EfficientSU2` `RY`/linear CNOT), ED helpers (`ed_sectors`, `ed_even_ground_state`, `expval`, `state_vector`), Week 6 data generators (`sweep_observables`, `finite_size_sweep`, `shot_estimate`, `noisy_value`), Week 5 VQE prototype (`prepare_vqe_ground_state`, `measure_local_x_shots`, `measure_local_y_shots`, `measure_edge_string_shots`), and the Week 7 VQE machinery (`vqe_cost`, `evaluate_state`, `measure_edge_string_shots`, `solve_point`, `vqe_sweep`, `best_state`, `depth_scan`). All ED uses the same little-endian Qiskit convention via `.to_matrix()`.
- **`block3.py`** — single scripted Block 3 runner (Weeks 5-7) using the `PLOT_REGISTRY`/`@plot` pattern and a unified CLI. Imports everything physics-related from `block3_core.py` and only holds the plotting/registry/CLI layer. Plots: 1 `block3_01_vqe_observables_test.pdf` (representative VQE local-vs-edge-string observable test, used by Week 7 slides), 2 the `block3_week5_*.pdf` sweet-spot figures (ansatz, convergence, correlation bar, and the meas_local/meas_sop/meas_correlation circuits), 3 `block3_week6_phase_sweep.pdf`, 4 `block3_week6_finite_size.pdf`, 5 `block3_week6_local_vs_nonlocal.pdf`, 6 `block3_week6_noise.pdf`, 7 `block3_week7_vqe_sweep.pdf`, 8 `block3_week7_depth_fidelity.pdf`.
- **`block4.py`** — scripted Block 4 runner for NISQ noise checks. Reuses `block3_core.py` operators and ED helpers. Plot 1 (Week 8, frozen-state) emits `block4_week8_noise_sweep.pdf`. Plots 2-9 (Week 9, circuit-level) attach a Qiskit `NoiseModel` and read `Tr[O_edge rho]` from a density matrix: `circuit_level_edge` (Aer density_matrix run), `exact_reference_edge` (independent gate-by-gate `DensityMatrix.evolve` + depolarizing `SuperOp`, the verification reference), `perturb_theta`/`_purity` (coherent-error study), `noisy_optimize` (noise inside the VQE cost), and `backend_noise_model` (`NoiseModel.from_backend`). CLI adds `--mu-opt`, `--sigma-theta`, `--reps` (use `--reps 1 2 3 4 5 6` for the plot-6 depth optimum), `--noisy-*`, and `--backend-seed`. Notebook-local Hamiltonians are exploratory only.
- **`block4_scaling.py`** — Block 4 large-$L$ scaling study (Weeks 9-10). At fixed ansatz depth it separates the two failure modes: expressibility (an $L$-independent depth threshold $r^\ast=4$) and noise (exponential decay along the linearly growing CNOT count). Removes every exponential object except the mild $2^L$ statevector — exact reference via `free_fermion.ground` (BdG), ideal VQE via sparse-Pauli statevector expectations, and the noisy edge string via **MPS quantum-trajectory** sampling (`noisy_edge_mps`, $\chi\le2^{\text{reps}}$, $1/\sqrt{N}$ bars). `device_noise_model` transplants a real IBM device's recorded per-qubit 1q calibration plus a representative median 2q channel onto the native linear chain (the real chips are heavy-hex, so `from_backend` alone would leave the cx pairs noiseless). Working point $\mu=0.5t$, L-BFGS-B, ED-free even-sector selection; the $(L,\text{reps})$ grid parallelizes across a spawned process pool (`--workers`, Leipzig SC cluster). Emits `block4_scaling_Lsweep.pdf`, caches `plots/block4_scaling_data*.npz`.
- **`block4_largeL.py`** — fixed-depth ($r^\ast=4$) device sweep pushing the noisy edge string to $L=100$ on real IBM calibrations (Brooklyn 65q, Washington 127q), reusing the statevector-ideal + MPS-trajectory-noisy + free-fermion-reference primitives of `block4_scaling.py`. Caches `plots/block4_largeL_data.npz`; the committed run backs the Week 10 "Real Hardware to $L=100$" slide (`block4_largeL_overlay.pdf`).
- **`block4_errors.py`** — **physical-error taxonomy** (Prof. Rosenow's question: which physical Kitaev-chain errors destroy the topological phase, translated through Jordan-Wigner to qubit operators). Organizing principle *symmetry vs topology*: a perturbation is harmless only if local, fermion-parity preserving, and weaker than the bulk gap $\Delta$. `disorder_sweep` — parity-even charge noise $\sum_j\delta h_j Z_j$, exact BdG to $L=32$ via `free_fermion`'s per-site $\mu_j$ (ROBUST); `contrast_ed` — parity-odd quasiparticle poisoning $g\,X_0$ by full ED so parity is free to flip (FATAL). Both at the topological point $\mu_0=t$ (chosen over $0.5t$ so the exponentially small clean parity gap stays above the `eigh` floor at large $L$). `vqe_overlay` closes the loop onto the actual Block-4 circuit: both channels run through the VQE ansatz — ideal statevector plus **exact density-matrix noisy** expectation (reusing `block4`/`block4_scaling`) — overlaid on the matched exact-solver curves. Emits `block4_disorder_robustness.pdf`, `block4_robust_vs_fatal.pdf`, `block4_vqe_taxonomy.pdf`; `--selftest` for sanity checks.
- **`free_fermion.py`** — exact free-fermion/BdG reference helper for larger-$L$ scaling analysis. Builds the Majorana matrix (accepting a scalar **or per-site** chemical potential $\mu_j$, so local charge-noise disorder enters directly), computes the ground-state energy/covariance/parity gap in `O(L^3)`, evaluates the edge string from the covariance matrix, and self-tests against exact qubit diagonalization for small even `L`.
- **`showcase.py`** — intuition-first figure gallery (H1-H9) for the GitHub Pages index and the Week 10 capstone deck. Uses the same physics as `block3_core.py`/`block4.py`; each figure returns `save_showcase(fig, 'hN_...')`, writing `plots/show_hN_*.png` + `_thumb`. Showcase styling helpers (`setup_showcase_style`, `save_showcase`, `topo_window`, `takeaway`) live in `utils.py`.

### Runner scripts (`block1.py`, `block2.py`, `block3.py`)

Each runner uses a `PLOT_REGISTRY` dict (populated by `@plot(n, description)` decorators) and a shared CLI (`--plots`, `--list`, `--L`, `--t`, `--delta`). To add a new plot: decorate a function with `@plot(N, "description")` — it auto-registers. `block3.py` extends the CLI with VQE/sweep controls (`--points`, `--shots`, `--reps`, `--lam`, `--seed`, `--maxiter`, `--restarts`, `--starts`, `--reps-list`, `--mu-points`); each plot reads what it needs via `**_`.

### Plots

Named `blockX_NN_description.pdf` in `plots/`. Beamer slides reference them via `\graphicspath{{../../plots/}}` so paths are relative to the `presentation/weekN/` folder.

Current Block 1 plot numbering:
- 1: `block1_01_bulk_dispersion.pdf`
- 2: `block1_02_trajectory_deformation.pdf` (replaces the older `block1_02_winding_loops.pdf`)
- 3: `block1_03_phase_diagram.pdf`
- 4: `block1_04_finite_size_spectrum.pdf`
- 5: `block1_05_realspace_snapshot.pdf`
- 6: `block1_06_majorana_splitting.pdf`
- 7: `block1_07_bulk_dispersion_panels.pdf`
- 8: `block1_08_winding_loops_panels.pdf`
- 9: `block1_09_npabs_comparison.pdf`

Week 5 Block 3 outputs (runner-generated PDFs, `block3.py --plots 2`):
- `block3_week5_ansatz.pdf` — hardware-efficient `RY` + linear CNOT ansatz diagram.
- `block3_week5_convergence.pdf` — symmetry-broken VQE convergence at `mu=0` (L-BFGS-B, parity penalty `lambda=0.1`) vs the ED ground-state energy.
- `block3_week5_correlation.pdf` — shot-based Majorana signatures at `mu=0`: local `|<Y_0>|` (~0) vs the edge string `|<X_0 Z..Z X_{L-1}>|` (~1).
- `block3_week5_meas_local.pdf` — local `<X_0>` measurement circuit (H on `q_0`).
- `block3_week5_meas_sop.pdf` — older SOP-style measurement circuit (S†+H on `q_{L-1}`); keep only for historical context unless explicitly needed.
- `block3_week5_meas_correlation.pdf` — edge-string measurement circuit (H on `q_0` and `q_{L-1}`).
- The Week 5 slides use ansatz/convergence/meas_correlation/correlation; `notes/measuring_topology_qiskit.tex` uses ansatz/meas_local/meas_correlation.

Week 6 Block 3 outputs:
- `block3_week6_phase_sweep.pdf` — ideal/shot-estimated edge-string correlator across `mu`, plus parity-gap ED cross-check.
- `block3_week6_finite_size.pdf` — finite-size behavior of the non-local edge string.
- `block3_week6_local_vs_nonlocal.pdf` — local-observable behavior across system sizes.

Week 7 Block 3 outputs:
- `block3_week7_vqe_sweep.pdf` — VQE-prepared edge-string sweep (ideal + shot) vs ED baseline, with a per-`mu` validation panel (energy error, infidelity, parity deviation, restart markers).
- `block3_week7_depth_fidelity.pdf` — ansatz-depth diagnostic: subspace infidelity and energy error vs `reps` at representative `mu` (topological/critical/trivial).

The Week 5/7 VQE framework test (`block3.py --plots 1`) emits `block3_01_vqe_observables_test.pdf`, showing local `|<X_0>|` near zero versus edge-string `|<X_0 Z_1 Z_2 X_3>|`; it is used as the "existing VQE baseline" figure in the Week 7 slides.

Block 4 outputs (`block4.py`):
- `block4_week8_noise_sweep.pdf` (plot 1) — Week 8 frozen-state readout/depolarizing sweep.
- `block4_week9_depth_sweep.pdf` (plot 2) — edge-string phase sweep at increasing ansatz depth under per-cx noise.
- `block4_week9_verification.pdf` (plot 3) — Aer vs exact gate-by-gate agreement (~1e-15) and the thermal T1/T2 variant.
- `block4_parity_vs_noise.pdf` (plot 4) — parity vs edge string under phase/depolarizing/amplitude channels (topological state).
- `block4_length_under_noise.pdf` (plot 5) — intrinsic parity gap vs noisy vulnerability across chain length L.
- `block4_week9_depth_optimum.pdf` (plot 6) — expressibility threshold vs accumulated gate noise; optimum = shallowest adequately-expressive depth (needs `--reps 1 2 3 4 5 6`).
- `block4_week9_parameter_noise.pdf` (plot 7) — coherent (theta+dtheta, purity preserved) vs incoherent (depolarizing, purity lost).
- `block4_week9_noisy_vqe.pdf` (plot 8) — best-case fixed ideal parameters vs noisy-cost re-optimization under unital and non-unital channels.
- `block4_week9_backend_noise.pdf` (plot 9) — uniform toy depolarizing noise vs backend-calibrated `NoiseModel.from_backend` device noise.

Block 4 scaling / taxonomy outputs (`block4_scaling.py`, `block4_largeL.py`, `block4_errors.py`):
- `block4_scaling_Lsweep.pdf` — two-panel fixed-depth scaling: expressibility threshold (Panel A) and the noise wall at minimal adequate depth (Panel B).
- `block4_largeL_overlay.pdf` — all fixed-depth ($r^\ast=4$) edge-string runs on one axis: noiseless, toy depolarizing, and real IBM Cairo/Brooklyn/Washington to $L=100$.
- `block4_disorder_robustness.pdf` — ROBUST channel: edge string + parity gap vs parity-even disorder strength $W$, exact BdG to $L=32$; protected until $W\sim\Delta$.
- `block4_robust_vs_fatal.pdf` — parity-even $Z$-disorder vs parity-odd $g\,X_0$ (QP poisoning): $|\langle O_\text{edge}\rangle|$ and $\langle P\rangle$ vs strength, exact ED at $L=10$.
- `block4_vqe_taxonomy.pdf` — the same two channels run through the actual VQE circuit (exact GS / ideal-VQE / noisy-VQE density-matrix), overlaid.

Showcase gallery (`showcase.py`, `plots/show_h*.png` + `_thumb`): H1 Majorana wavefunction, H2 depth optimum, H3 transition views, H4 edge string, H5 parity vs topology, H6 coherent vs incoherent, H7 phase banner, H8 length tradeoff, H9 Majorana under noise. Consumed by the Week 10 capstone deck and the GitHub Pages index.

### Presentations (`presentation/weekN/slides.tex`)

Beamer (Madrid/seahorse theme), 16:9. Custom macros: `\cdag`, `\winding`, `\ket{}`, `\bra{}`. Color names `trivial`/`critical`/`topological`/`edgemode` match `COLORS` in `utils.py`. Code listings use `lstlisting` with the `codebg/codekw/codecomment/codestring` color set defined in the preamble.

**Block structure:**
- Block 1 (weeks 1–2, week3 partial): Physics Bridge — Kitaev H, BdG bulk, winding number, phase diagram
- Block 2 (week3 partial + week4): Finite-Size Physics + Qubit Encoding — edge modes, Majorana splitting, JW transform, parity gap
- Block 3 (weeks 5-7): Measuring Topology — transition from exact matrix math to gate-based simulation, VQE ground-state preparation, non-local string order, Majorana observable measurement gates, and numerical evidence
- Block 4 (weeks 8-9): NISQ Reality Check — week 8 frozen-state noise plan/failure metrics; week 9 circuit-level gate noise (density-matrix `NoiseModel`, machine-precision verification, depth optimum, coherent vs incoherent, parity vs topology, length)
- Final synthesis (week 10): capstone deck tracing Blocks 1-4 end-to-end via the H1-H9 showcase gallery, building to the thesis (parity is symmetry-protected not topological; the topological signal is not noise-immune at fixed L; the optimum is the shallowest adequately-expressive depth)

Week 5 `slides.tex` content:
- Objective: move from exact matrix math to gate-based simulation.
- Task 1: VQE ground-state preparation with a hardware-efficient ansatz using only `RY` gates and linear CNOT entanglement.
- Gate explanation frames: `RY` splits amplitudes in the 16-dimensional `L=4` Hilbert space; CNOT moves amplitudes between binary configurations and builds paired/topological correlations.
- Pure YY limit: for `t = Delta` and `mu = 0`, the mapped Hamiltonian reduces to `H = sum_j Y_j Y_{j+1}`.
- VQE convergence: L-BFGS-B, cost `C(theta) = <H> - lambda <P>`, parity penalty `lambda=0.1`, even parity sector selection.
- String operator: boundary Majorana correlator maps to `-X_0 Z_1 Z_2 X_3`; local single-qubit expectations vanish, so non-local order is required.
- Measurement: hardware measures in Z basis; Hadamards on `q_0` and `q_3` rotate X-basis observables for `X_0 Z_1 Z_2 X_3`.
- Week 5 numerical evidence: local `Y_0` is approximately zero, string/correlation `X_0 Z_1 Z_2 X_3` is shown as `1.0000`. Week 6 uses the same non-local edge-string idea to sweep `mu` and build a phase-diagram diagnostic.

Week 6 `slides.tex` content:
- Uses the edge-string observable, AFM-Ising comparison, ED/shot measurement protocol, phase sweep, and finite-size behavior to motivate the next preparation milestone.
- Separates the measurable edge-string diagnostic from the ED parity-gap cross-check.
- Current sweep preparation uses exact even-parity eigenstates; a real VQE sweep is explicitly left for Week 7.

Week 7 `slides.tex` content:
- Converts the representative-point VQE prototype into a full `mu` sweep.
- Uses warm-start continuation, parity-constrained optimization, and ED benchmarks for energy, parity, subspace fidelity, and edge-string error.
- Shows the VQE-prepared edge-string sweep and ansatz-depth diagnostic, then hands off to Block 4 noise studies.

Week 8 `slides.tex` content:
- Starts Block 4: NISQ reality check after the validated VQE sweep.
- Freezes the Week 7 VQE/ED-validated edge-string baseline and defines circuit-level noise channels: depolarizing, readout, amplitude damping, and phase damping.
- Separates frozen-parameter noise tests from noisy VQE optimization.
- Uses `block3_week7_vqe_sweep.pdf` as the baseline and `block4_week8_noise_sweep.pdf` as the first scripted readout/gate-noise visualization.

Week 9 `slides.tex` content:
- Circuit-level gate noise on the validated VQE: channel taxonomy, the state-vector -> density-matrix transition, and the machine-precision verification.
- The depth optimum framed as an expressibility *threshold* (r=1 fails, r>=2 saturates) times accumulated CNOT noise `(1-p_cx)^{r(L-1)}`.
- The professor's questions (parity vs topology; chain length) as their own frames. No explicit "Week N" wording. The coherent-vs-incoherent frame exists but is currently commented out (`\iffalse`); slide 6 is the Qiskit code listing.

Week 10 `slides.tex` content (`presentation/week10/`):
- Final-synthesis capstone (16 frames): motivation -> Block 1 edge modes/transition -> Block 2 JW + finite-size parity gap -> Block 3 VQE sweep -> Block 4 NISQ reality checks (noise breaks the diagnostic; optimizing != preparing; large-$L$ scaling methods + MPS/$\chi$ in opened matrix-product form; the scaling result; real hardware to $L=100$) -> physical-error taxonomy (which Kitaev errors kill topology: robust sub-gap disorder vs fatal quasiparticle poisoning; the same taxonomy on the actual VQE circuit) -> the Jordan-Wigner unification (device noise *is* physical error: $T_1$ = poisoning, $T_2$ = charge noise, but topological protection does not transfer to the qubit emulation) -> takeaways. Uses the Block 1-4 result figures directly (not the `show_h*` gallery); landscape two-panel figures use figure-on-top / text-below.

### Notes (`notes/`)

Standalone LaTeX documents. Source `.tex` files are tracked; generated `notes/*.pdf` files are ignored and produced locally with `make notes` or by CI for GitHub Pages. Currently:
- `finite_size_majorana_splitting.tex` — additional finite-size Majorana splitting notes.
- `ising_comparison.tex` — AFM Ising vs Kitaev/Jordan-Wigner qubit Hamiltonian comparison with symmetry breaking, Neel ground states, parity structure, Majorana edge degeneracy, and TikZ diagrams.
- `majorana_splitting_vs_L.tex` — derivation of `E₀(L) ~ (|μ|/2t)^L`, overlap proxy argument, conceptual clarifications on BdG spectrum interpretation
- `qubit_encoding_derivations.tex` — Jordan-Wigner derivation details
- `measuring_topology_qiskit.tex` — Block 3 notes on Qiskit state preparation, local/string observables, and shot-based measurement protocols.
- `string_order_phase_sweep.tex` — Block 3 notes on sweeping `mu`, measuring the non-local edge string, and bridging to Block 4 noise studies.
- `parity_constrained_vqe_sweep.tex` — Block 3 notes on parity-constrained VQE sweep preparation, EfficientSU2 repetitions, subspace fidelity, ideal vs shot-based VQE, and edge-string measurement from bitstrings.
- `block4_noise_diagnostic.tex` — merged Block 4/Week 8 notes: practical `src/block4.py` frozen-state edge-string noise diagnostic, plus broader theory for measurement-basis rotations, asymmetric SPAM/readout bias, relaxation/dephasing, and noisy VQE optimization explicitly marked as not implemented yet.
- `circuit_level_gate_noise.tex` — Block 4 circuit-level gate-noise study: density-matrix `NoiseModel`, machine-precision verification, the depth-optimum (expressibility threshold) result, and the coherent-vs-incoherent (theta+dtheta) study.
- `parity_topology_protection.tex` — the professor's Q1/Q2: parity is protected by `Z2` symmetry (not topology), the non-local edge string is not noise-immune at fixed `L`, and chain length acts in opposing directions (intrinsic gap improves as `e^{-L/xi}` while device vulnerability grows with `L`).
- `topology_noise_reps_scaling.tex` — standalone explanation of why topology matters despite non-immune measurements, and how `L`, `reps`, CNOT count, and measured edge-string contrast trade off.
- `noisy_vqe_and_backend_noise.tex` — Block 4 extension notes for plots 8-9: noisy-cost VQE optimization and backend-calibrated noise.
- `scaling_to_large_L.tex` — large-`L` scaling note separating the removable ED reference from the hard noisy-state simulation, with free-fermion, MPS, and trajectory options.
- `kitaev_error_taxonomy.tex` — Prof. Rosenow's "which physical Kitaev errors kill the topology" note (backs `src/block4_errors.py`): the symmetry-vs-topology principle, the error dictionary (charge noise ROBUST vs quasiparticle poisoning FATAL), the charge-noise code-level implementation across the three solvers (BdG per-site `mu_j` / ED diagonal `Z`-field / VQE `SparsePauliOp`), an operator analysis of quasiparticle poisoning (parity is the *universal* witness; the edge string only a *site-dependent* one — a left-edge event flips the bit while the string can look healthy), and the physical-error ↔ NISQ-error mapping under Jordan-Wigner (`T1` relaxation *is* poisoning, `T2` dephasing *is* charge noise; the taxonomy transfers but topological protection does not, because the transmons are not the wire).

### Notebooks

- `notebooks/interactive_spectrum.ipynb` — interactive spectrum exploration.
- `notebooks/qiskit_crash_course.ipynb` — Qiskit learning/support material.
- `src/block3_week5.ipynb` — original Week 5 Block 3 notebook (four code cells, no markdown). Superseded for figure generation by `block3.py --plots 2`; kept as a historical/interactive artifact. It relies on prior notebook state for `target_L`/`H_op`, so restart-and-run may need those reconstructed before Cell 2.

## Code conventions

- No comments in code (see `.cursorrules`).
- No mock data or placeholders.
- `matplotlib` titles and labels must use raw strings (`r"..."` or `rf"..."`) when they contain backslashes; avoid LaTeX-only commands like `\texttt{}` in `matplotlib` text (use plain text instead).
- `fig.tight_layout(rect=[0, 0, 1, 0.93])` when a `suptitle` is present — without `rect`, the suptitle gets clipped.
- Always call `clean_axes(ax)` (imported from `utils.py`) inside runner plots to override the global grid style with white background and visible spines.
