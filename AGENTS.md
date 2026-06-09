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

Compile slides and notes from the repo root. Make only rebuilds PDFs whose `.tex` sources are newer than the generated PDF:
```bash
make slides      # all outdated presentation PDFs
make week6       # only week 6 if outdated
make week7       # only week 7 if outdated
make notes       # all outdated notes PDFs
make clean       # remove LaTeX auxiliary files
```

Manual slide compile still works from a week folder:
```bash
cd presentation/weekN
pdflatex slides.tex && pdflatex slides.tex  # double-pass for TOC
```

CI compiles outdated presentation slides and notes on push, then deploys generated PDFs plus an HTML index to GitHub Pages.

Block 3 notebook dependencies include `qiskit`, `qiskit-aer`, `qiskit-algorithms`, `numpy`, `scipy`, and `matplotlib`.

## Current Status (2026-06-04)

- Block 1 is implemented: BdG bulk/real-space physics, winding number, phase diagram, finite-size spectra, Majorana splitting, and comparison plots.
- Block 2 is implemented: Jordan-Wigner qubit Hamiltonian, parity-sector spectra, and parity-gap checks against BdG splitting.
- Block 3 spans Weeks 5-7 and is now consolidated into a single runner `src/block3.py` backed by shared helpers in `src/block3_core.py`. Plots 1-2 are Week 5 (VQE observables + circuit diagrams), plots 3-6 are Week 6 (ED-validated edge-string sweep, finite size, local vs non-local, classical-noise robustness), and plots 7-8 are Week 7 (parity-constrained VQE `mu`-sweep with warm-start continuation/ED validation, and the ansatz-depth diagnostic). `src/block3_week5.ipynb` is retained as the interactive Week 5 notebook and the source of the committed Week 5 PNG slide assets. The old `src/block3_week6.py` and `src/block3_week7.py` have been removed; their logic lives in `block3.py`/`block3_core.py`.
- Week 5 slides use `presentation/week5/slides.tex`. Week 6 slides use `presentation/week6/slides.tex`. Week 7 slides use `presentation/week7/slides.tex`. Ignore `presentation/week5/slides_my.tex` unless explicitly asked.
- Block 3 Week 5 plots are now runner-generated PDFs with the `block3_week5_*` signature (matching `block3_week6_*`/`block3_week7_*`), produced by `block3.py --plots 2`. The old ad-hoc PNGs (`block3_VQE_Ansatz.png`, `block3_VQE_Converage.png`, `block3_Measurement.png`, `block3_correlation.png`) and the unused `block3_02/03/04_*.pdf` diagrams were removed; the `Converage` typo and the uppercase `block3_Correlation.png` case bug in the slides are fixed.
- Block 4 remains upcoming: no physically realistic NISQ noise-modeling runner is present yet. Week 7 first closes the preparation gap with a real VQE sweep before noise is added.

Current local-only/untracked worktree items observed on 2026-06-04 include `.cursorindexingignore`, `.notes.txt.swp`, `.specstory/`, `diff.txt`, a Qiskit crash-course notebook checkpoint, `notes/plan.pdf`, generated presentation PDFs/VRB files, and `presentation/week5/slides_my.tex` / `presentation/week5/slides_my.pdf`. Do not delete or revert these unless explicitly asked.

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

- **`kitaev_chain.py`** — `KitaevChain` class. Builds the (2L×2L) real-space BdG matrix and exposes `.spectrum()`, `.positive_spectrum()`, `.eigh()`, `.gap()`. Use `.positive_spectrum()` (not `.spectrum()[L:]`) to avoid spurious spikes from sign-filtering near-zero Majorana modes at large L.
- **`bdg_bulk.py`** — momentum-space BdG: `bulk_energy()`, `bulk_gap()`, `bdg_vector()`, `critical_mu()`. Critical points are at `μ = ±2t`.
- **`winding.py`** — `winding_number(mu)` integrates the BdG d-vector angle around the BZ via `np.unwrap`. Returns 0 (trivial) or 1 (topological).
- **`jordan_wigner.py`** — qubit encoding via Jordan-Wigner. `kitaev_qubit_hamiltonian()` returns the (2^L × 2^L) qubit Hamiltonian; `spectrum_by_parity()` splits eigenvalues into even/odd fermion-parity sectors; `parity_gap()` returns `|E₀⁺ − E₀⁻|`. Limited to L ≤ ~14 due to exponential Hilbert-space growth.
- **`utils.py`** — `setup_style()`, `save_fig(fig, filename)`, `clean_axes(ax)`, `COLORS` dict. All plots call these; `block1.py`/`block2.py`/`block3.py` import `clean_axes` from here (single definition). Figures save to `plots/` relative to the repo root.
- **`block3_week5.ipynb`** — original interactive Block 3 Week 5 notebook (pure YY/topological sweet-spot VQE with `EfficientSU2` `RY`/linear-CNOT, `AerEstimator`, L-BFGS-B, parity penalty `lambda=0.1`, subspace-fidelity validation, shot-based measurements). Its logic is now fully reproduced by `block3.py --plots 2` (the `block3_week5_*.pdf` figures), which is what the Week 5 slides use; the notebook is retained only as a historical/interactive artifact.
- **`block3_core.py`** — shared Block 3 logic imported by `block3.py`. Qiskit operators (`qubit_hamiltonian` little-endian `SparsePauliOp`, `edge_string`, `local_z`, `parity`), `vqe_ansatz` (`EfficientSU2` `RY`/linear CNOT), ED helpers (`ed_sectors`, `ed_even_ground_state`, `expval`, `state_vector`), Week 6 data generators (`sweep_observables`, `finite_size_sweep`, `shot_estimate`, `noisy_value`), Week 5 VQE prototype (`prepare_vqe_ground_state`, `measure_observables_shot_based`), and the Week 7 VQE machinery (`vqe_cost`, `evaluate_state`, `measure_edge_string_shots`, `solve_point`, `vqe_sweep`, `best_state`, `depth_scan`). All ED uses the same little-endian Qiskit convention via `.to_matrix()`.
- **`block3.py`** — single scripted Block 3 runner (Weeks 5-7) using the `PLOT_REGISTRY`/`@plot` pattern and a unified CLI. Imports everything physics-related from `block3_core.py` and only holds the plotting/registry/CLI layer. Plots: 1 `block3_01_vqe_observables_test.pdf` (used by Week 7 slides), 2 the `block3_week5_*.pdf` sweet-spot figures (ansatz, convergence, correlation bar, and the meas_local/meas_sop/meas_correlation circuits), 3 `block3_week6_phase_sweep.pdf`, 4 `block3_week6_finite_size.pdf`, 5 `block3_week6_local_vs_nonlocal.pdf`, 6 `block3_week6_noise.pdf`, 7 `block3_week7_vqe_sweep.pdf`, 8 `block3_week7_depth_fidelity.pdf`.

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
- `block3_week5_meas_sop.pdf` — SOP measurement circuit (S†+H on `q_{L-1}`).
- `block3_week5_meas_correlation.pdf` — edge-string measurement circuit (H on `q_0` and `q_{L-1}`).
- The Week 5 slides use ansatz/convergence/meas_correlation/correlation; `notes/measuring_topology_qiskit.tex` uses ansatz/meas_local/meas_sop.

Week 6 Block 3 outputs:
- `block3_week6_phase_sweep.pdf` — ideal/shot-estimated edge-string correlator across `mu`, plus parity-gap ED cross-check.
- `block3_week6_finite_size.pdf` — finite-size behavior of the non-local edge string.
- `block3_week6_local_vs_nonlocal.pdf` — local-observable behavior across system sizes.

Week 7 Block 3 outputs:
- `block3_week7_vqe_sweep.pdf` — VQE-prepared edge-string sweep (ideal + shot) vs ED baseline, with a per-`mu` validation panel (energy error, infidelity, parity deviation, restart markers).
- `block3_week7_depth_fidelity.pdf` — ansatz-depth diagnostic: subspace infidelity and energy error vs `reps` at representative `mu` (topological/critical/trivial).

The Week 5/7 VQE framework test (`block3.py --plots 1`) emits `block3_01_vqe_observables_test.pdf`, used as the "existing VQE baseline" figure in the Week 7 slides.

### Presentations (`presentation/weekN/slides.tex`)

Beamer (Madrid/seahorse theme), 16:9. Custom macros: `\cdag`, `\winding`, `\ket{}`, `\bra{}`. Color names `trivial`/`critical`/`topological`/`edgemode` match `COLORS` in `utils.py`. Code listings use `lstlisting` with the `codebg/codekw/codecomment/codestring` color set defined in the preamble.

**Block structure:**
- Block 1 (weeks 1–2, week3 partial): Physics Bridge — Kitaev H, BdG bulk, winding number, phase diagram
- Block 2 (week3 partial + week4): Finite-Size Physics + Qubit Encoding — edge modes, Majorana splitting, JW transform, parity gap
- Block 3 (weeks 5-7 active): Measuring Topology — transition from exact matrix math to gate-based simulation, VQE ground-state preparation, non-local string order, Majorana observable measurement gates, and numerical evidence
- Block 4 (upcoming): NISQ Reality Check after the VQE sweep is validated

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
- Defines the next milestone: convert the representative-point VQE prototype into a full `mu` sweep.
- Uses warm-start continuation, parity-constrained optimization, and ED benchmarks for energy, parity, subspace fidelity, and edge-string error.
- Contains no fabricated sweep results; it presents the existing three-point VQE baseline and the implementation/validation plan.

### Notes (`notes/`)

Standalone LaTeX documents. Source `.tex` files are tracked; generated `notes/*.pdf` files are ignored and produced locally with `make notes` or by CI for GitHub Pages. Currently:
- `majorana_splitting_vs_L.tex` — derivation of `E₀(L) ~ (|μ|/2t)^L`, overlap proxy argument, conceptual clarifications on BdG spectrum interpretation
- `qubit_encoding_derivations.tex` — Jordan-Wigner derivation details
- `measuring_topology_qiskit.tex` — Block 3 notes on Qiskit state preparation, local/string observables, and shot-based measurement protocols.
- `week6_phase_sweep.tex` — Week 6 notes on sweeping `mu`, measuring the non-local edge string, and bridging to Block 4 noise studies.

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

## Cursor Cloud specific instructions

This repo has no long-running services. Development is batch Python simulation from `src/` plus optional local LaTeX builds.

### Python environment

- The documented venv path `/opt/python-envs/myenv/bin/` may not exist on Cloud VMs. Use system `python3` from the repo root after the update script runs.
- There is no `requirements.txt`; the update script installs: `numpy`, `matplotlib`, `scipy`, `qiskit`, `qiskit-aer`, `qiskit-algorithms`, and `pylatexenc`.
- `pylatexenc` is required for `block3.py --plots 2` (Qiskit `draw('mpl')` circuit diagrams). Without it, VQE numerics still run but circuit PDF export fails.

### Running simulations

```bash
cd src
python3 block1.py --list
python3 block1.py --plots 1
python3 block2.py --plots 1
python3 block3.py --plots 2    # Week 5 VQE + circuit figures
python3 block3.py --plots 3    # Week 6 phase sweep (fast)
python3 block3.py --plots 7 --points 41   # Week 7 VQE mu-sweep (slow)
```

Figures save to `plots/` at the repo root. Plot 7 is the slowest Block 3 job.

### LaTeX / Make

- `pdflatex` is typically **not** installed on Cloud VMs. Slide and note PDFs are built in CI (`.github/workflows/compile_slides.yml`). For local PDF work, install TeX Live and run `make slides` / `make notes` from the repo root per the Commands section above.

### Lint / tests

- No pytest, ruff, or flake8 config. Sanity check: `python3 -m py_compile src/*.py`.
