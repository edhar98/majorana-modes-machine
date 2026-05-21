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

There is also a scripted Block 3 runner:
```bash
cd src
python block3.py              # all Block 3 plots
python block3.py --list       # list available plots
python block3.py --plots 2    # circuit visualization plots only
```

Compile slides and notes from the repo root. Make only rebuilds PDFs whose `.tex` sources are newer than the generated PDF:
```bash
make slides      # all outdated presentation PDFs
make week6       # only week 6 if outdated
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

## Current Status (2026-05-22)

- Block 1 is implemented: BdG bulk/real-space physics, winding number, phase diagram, finite-size spectra, Majorana splitting, and comparison plots.
- Block 2 is implemented: Jordan-Wigner qubit Hamiltonian, parity-sector spectra, and parity-gap checks against BdG splitting.
- Block 3 is active in Weeks 5-6. Week 5 source of truth is `src/block3_week5.ipynb`; Week 6 starts the `mu`-sweep diagnostic in `src/block3_week6.py`; `src/block3.py` is a runnable scripted prototype for Qiskit/Aer VQE and measurement plots.
- Week 5 slides use `presentation/week5/slides.tex`. Week 6 slides use `presentation/week6/slides.tex`. Ignore `presentation/week5/slides_my.tex` unless explicitly asked.
- Block 3 plots for Week 5 are PNG assets in `plots/block3_*.png`: `block3_VQE_Ansatz.png`, `block3_VQE_Converage.png`, `block3_Measurement.png`, and `block3_correlation.png`.
- `presentation/week5/slides.tex` currently references `block3_Correlation.png` with an uppercase `C`, while the actual file is `block3_correlation.png`. This matters on case-sensitive filesystems/CI.
- Block 4 remains upcoming: no NISQ noise-modeling runner is present yet. Week 6 tees this up by defining the ideal string-order sweep to compare against noisy circuits later.

Current local-only/untracked worktree items observed on 2026-05-22 include `.cursorindexingignore`, `.notes.txt.swp`, `.specstory/`, `diff.txt`, a Qiskit crash-course notebook checkpoint, `notes/plan.pdf`, generated presentation PDFs/VRB files, and `presentation/week5/slides_my.tex` / `presentation/week5/slides_my.pdf`. Do not delete or revert these unless explicitly asked.

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
- **`utils.py`** — `setup_style()`, `save_fig(fig, filename)`, `COLORS` dict. All plots call these. Figures save to `plots/` relative to the repo root.
- **`block3_week5.ipynb`** — latest Block 3 Week 5 notebook. It implements a Qiskit/Aer VQE workflow for the pure YY/topological sweet-spot example with a real `EfficientSU2` ansatz (`RY` gates, linear CNOT entanglement), `AerEstimator`, L-BFGS-B optimization, a parity penalty `lambda=0.1` to select the even parity sector, subspace-fidelity validation against exact diagonalization, and shot-based `AerSimulator` measurements.
- **`block3.py`** — scripted Block 3 runner. It builds a Qiskit `SparsePauliOp` Hamiltonian, uses an `EfficientSU2` `RY` ansatz, runs AerEstimator-based VQE against exact diagonalization, checks subspace fidelity, simulates shot-based local/string measurements, and emits `block3_01_*` through `block3_04_*` PDF plots. Current Week 5 presentation context should still be taken from `src/block3_week5.ipynb`.

### Runner scripts (`block1.py`, `block2.py`)

Each runner uses a `PLOT_REGISTRY` dict (populated by `@plot(n, description)` decorators) and a shared CLI (`--plots`, `--list`, `--L`, `--t`, `--delta`). To add a new plot: decorate a function with `@plot(N, "description")` — it auto-registers.

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

Week 5 Block 3 notebook plots are PNGs rather than the older runner-generated PDFs:
- `block3_VQE_Ansatz.png` — hardware-efficient `RY` + linear CNOT ansatz.
- `block3_VQE_Converage.png` — VQE convergence plot. The filename intentionally has the current misspelling `Converage`.
- `block3_Measurement.png` — basis-rotation measurement diagram for the non-local observable.
- `block3_correlation.png` — numerical/topological correlation evidence.

Week 6 Block 3 output:
- `block3_week6_phase_sweep.pdf` — ideal/shot-estimated edge-string correlator across `mu`, plus parity-gap cross-check.

Scripted Block 3 PDF outputs are:
- `block3_01_vqe_observables_test.pdf`
- `block3_02_vqe_ansatz.pdf`
- `block3_03_meas_local.pdf`
- `block3_04_meas_sop.pdf`

### Presentations (`presentation/weekN/slides.tex`)

Beamer (Madrid/seahorse theme), 16:9. Custom macros: `\cdag`, `\winding`, `\ket{}`, `\bra{}`. Color names `trivial`/`critical`/`topological`/`edgemode` match `COLORS` in `utils.py`. Code listings use `lstlisting` with the `codebg/codekw/codecomment/codestring` color set defined in the preamble.

**Block structure:**
- Block 1 (weeks 1–2, week3 partial): Physics Bridge — Kitaev H, BdG bulk, winding number, phase diagram
- Block 2 (week3 partial + week4): Finite-Size Physics + Qubit Encoding — edge modes, Majorana splitting, JW transform, parity gap
- Block 3 (week5 active): Measuring Topology — transition from exact matrix math to gate-based simulation, VQE ground-state preparation, non-local string order, Majorana observable measurement gates, and numerical evidence
- Block 4 (upcoming): NISQ Reality Check

Week 5 `slides.tex` content:
- Objective: move from exact matrix math to gate-based simulation.
- Task 1: VQE ground-state preparation with a hardware-efficient ansatz using only `RY` gates and linear CNOT entanglement.
- Gate explanation frames: `RY` splits amplitudes in the 16-dimensional `L=4` Hilbert space; CNOT moves amplitudes between binary configurations and builds paired/topological correlations.
- Pure YY limit: for `t = Delta` and `mu = 0`, the mapped Hamiltonian reduces to `H = sum_j Y_j Y_{j+1}`.
- VQE convergence: L-BFGS-B, cost `C(theta) = <H> - lambda <P>`, parity penalty `lambda=0.1`, even parity sector selection.
- String operator: boundary Majorana correlator maps to `-X_0 Z_1 Z_2 X_3`; local single-qubit expectations vanish, so non-local order is required.
- Measurement: hardware measures in Z basis; Hadamards on `q_0` and `q_3` rotate X-basis observables for `X_0 Z_1 Z_2 X_3`.
- Week 5 numerical evidence: local `Y_0` is approximately zero, string/correlation `X_0 Z_1 Z_2 X_3` is shown as `1.0000`. Week 6 uses the same non-local edge-string idea to sweep `mu` and build a phase-diagram diagnostic.

### Notes (`notes/`)

Standalone LaTeX documents. Source `.tex` files are tracked; generated `notes/*.pdf` files are ignored and produced locally with `make notes` or by CI for GitHub Pages. Currently:
- `majorana_splitting_vs_L.tex` — derivation of `E₀(L) ~ (|μ|/2t)^L`, overlap proxy argument, conceptual clarifications on BdG spectrum interpretation
- `qubit_encoding_derivations.tex` — Jordan-Wigner derivation details
- `measuring_topology_qiskit.tex` — Block 3 notes on Qiskit state preparation, local/string observables, and shot-based measurement protocols.
- `week6_phase_sweep.tex` — Week 6 notes on sweeping `mu`, measuring the non-local edge string, and bridging to Block 4 noise studies.

### Notebooks

- `notebooks/interactive_spectrum.ipynb` — interactive spectrum exploration.
- `notebooks/qiskit_crash_course.ipynb` — Qiskit learning/support material.
- `src/block3_week5.ipynb` — latest Week 5 Block 3 working notebook. It has four code cells and no markdown cells. It appears to rely on prior notebook state for `target_L` and `H_op`, so restart-and-run may require reconstructing those variables before Cell 2.

## Code conventions

- No comments in code (see `.cursorrules`).
- No mock data or placeholders.
- `matplotlib` titles and labels must use raw strings (`r"..."` or `rf"..."`) when they contain backslashes; avoid LaTeX-only commands like `\texttt{}` in `matplotlib` text (use plain text instead).
- `fig.tight_layout(rect=[0, 0, 1, 0.93])` when a `suptitle` is present — without `rect`, the suptitle gets clipped.
- Always call `clean_axes(ax)` inside runner plots to override the global grid style with white background and visible spines.
