# Majorana Modes in the Machine
### Simulating Topological Phases with Quantum Circuits and AI

> Graduate seminar project — AI-Augmented Theoretical Physics

---

## Overview

This repository contains simulation code, figures, and presentation materials for a 14-week graduate seminar project on the **1D Kitaev chain** and its topological phase transition.

The goal is to bridge abstract theoretical physics and the quantum software stack — using LLMs as active research collaborators — by building a classical simulation pipeline that combines exact diagonalization, free-fermion methods, and quantum-circuit emulation.

---

## Project Blocks

| Block | Topic | Status |
|-------|-------|--------|
| 1 | **The Physics Bridge** — Kitaev chain, BdG bulk, winding number, phase diagram | ✅ |
| 2 | **Finite-Size Physics & Qubit Encoding** — Edge modes, Majorana splitting, Jordan-Wigner transform, parity sectors | ✅ |
| 3 | **Measuring Topology** — Circuit-based measurements, edge & string observables | ✅ |
| 4 | **The NISQ Reality Check** — Noise modeling, mitigation, robustness | 🚧 |

---

## Repository Structure

```
.
├── src/                        # Python simulation code
│   ├── utils.py                # Shared plot style, colors, save_fig()
│   ├── kitaev_chain.py         # KitaevChain class — real-space BdG (OBC)
│   ├── bdg_bulk.py             # Bulk BdG dispersion, gap, d-vector
│   ├── winding.py              # Topological winding number ν
│   └── block1.py               # Block 1 runner — CLI, generates all plots
│
├── plots/                      # Generated figures (PDF)
│
└── presentation/               # Weekly 20-min seminar slides (Beamer/LaTeX)
```

---

## Block 1 — The Physics Bridge

The Kitaev chain Hamiltonian:

$$H_K = -\mu \sum_j c_j^\dagger c_j - t \sum_j \left(c_j^\dagger c_{j+1} + \text{h.c.}\right) + \Delta \sum_j \left(c_j^\dagger c_{j+1}^\dagger + \text{h.c.}\right)$$

Key results implemented:

- **Real-space BdG** (open boundary conditions) — exact diagonalization via `KitaevChain`
- **Bulk dispersion** $E_k = \sqrt{(-\mu - 2t\cos k)^2 + (2\Delta \sin k)^2}$
- **Phase diagram** — bulk gap and winding number $\nu$ vs $\mu/t$
- **Winding number** — numerical BZ integral of the BdG d-vector angle

### Run

```bash
cd src
python block1.py                      # all plots
python block1.py --plots 4 --L 100   # single plot, custom chain length
python block1.py --list               # show available plots
```

---

## Block 2 — Finite-Size Physics & Qubit Encoding

Key results implemented:

- **Finite-size OBC spectrum** — near-zero edge modes in the topological phase ($|\mu| < 2t$)
- **Edge mode localization** — exponential decay of probability density from chain ends
- **Majorana hybridization splitting** — $E_0(L) \sim (|\mu|/2t)^L$ exponential decay with chain length
- **Jordan-Wigner transform** — `c_j = (∏_{k<j} Z_k) σ^-_j` mapping fermions to qubits
- **Qubit Hamiltonian** — $H = -\frac{\mu}{2}\sum Z_j + \frac{t-\Delta}{2}\sum X_jX_{j+1} + \frac{t+\Delta}{2}\sum Y_jY_{j+1}$
- **Parity gap** — $|E_0^+ - E_0^-|$ exponentially small in topological phase, validating JW mapping

### Run

```bash
cd src
python block1.py --plots 6 7 8       # finite-size plots (in block1 runner)
python block2.py                      # qubit encoding plots
python block2.py --list               # show available plots
```

## Block 3 — Measuring Topology with Quantum Circuits

Block 3 turns the qubit Hamiltonian into a circuit-measurable workflow. The central question is whether the topological phase can be detected from measurements of a prepared quantum state rather than from direct access to exact eigenvectors.

Key results implemented:

- **Week 5: Gate-based preparation** — VQE prepares a small-chain ground state with a hardware-efficient ansatz, then compares local parity-odd observables against the non-local edge string.
- **Non-local topology diagnostic** — the boundary Majorana correlator is measured as the parity-preserving Pauli string `X0 Z1 ... Z(L-2) X(L-1)`, which is large in the topological regime and suppressed in the trivial regime.
- **Week 6: Phase sweep diagnostic** — the same edge-string observable is swept across `mu` and benchmarked against parity-gap and finite-size behavior using exact diagonalization as a trusted small-system reference.
- **Week 7: VQE sweep** — the ED-prepared states are replaced by parity-constrained VQE states across the `mu` grid, with validation checks for energy, parity, subspace fidelity, and edge-string error.
- **Shot-based readout** — circuit measurements are sampled with finite shots and converted from bitstrings into string-observable estimates, matching the workflow needed before adding realistic noise.

### Run Block 3

```bash
cd src
python block3.py --list
python block3.py --plots 1          # representative VQE local-vs-edge-string test
python block3.py --plots 3 4 5 6    # Week 6 edge-string sweep diagnostics
python block3.py --plots 7          # Week 7 parity-constrained VQE mu-sweep
python block3.py --plots 8          # Week 7 ansatz-depth diagnostic
```

### Requirements

```bash
pip install numpy scipy matplotlib qiskit qiskit-aer qiskit-algorithms
```

---

## Slides

Presentation slides and notes are compiled to PDF and published via GitHub Pages. The generated site index is [majorana-modes-machine](https://edhar98.github.io/majorana-modes-machine/).

Weekly presentation slides:

| Week | Topic | PDF |
|------|-------|-----|
| 1 | The Physics Bridge — Kitaev chain, BdG, topological invariant | [week1.pdf](https://edhar98.github.io/majorana-modes-machine/week1.pdf) |
| 2 | The Physics Bridge (cont.) — winding number, phase diagram | [week2.pdf](https://edhar98.github.io/majorana-modes-machine/week2.pdf) |
| 3 | Blocks 1 & 2 — Physics Bridge + Finite-Size Physics & Edge Modes | [week3.pdf](https://edhar98.github.io/majorana-modes-machine/week3.pdf) |
| 4 | Block 2 (cont.) — Jordan-Wigner transform, qubit encoding, parity sectors | [week4.pdf](https://edhar98.github.io/majorana-modes-machine/week4.pdf) |
| 5 | Block 3 Qubit encoding, Ground State preparation | [week5.pdf](https://edhar98.github.io/majorana-modes-machine/week5.pdf) |
| 6 | Block 3 phase sweep — circuit-measurable string order | [week6.pdf](https://edhar98.github.io/majorana-modes-machine/week6.pdf) |
| 7 | Block 3 VQE sweep — parity-constrained state preparation | [week7.pdf](https://edhar98.github.io/majorana-modes-machine/week7.pdf) |
| 8 | Block 4 kickoff — noise model and failure modes | [week8.pdf](https://edhar98.github.io/majorana-modes-machine/week8.pdf) |

## Notes

Notes are kept as LaTeX sources in `notes/`. PDFs are generated by CI and linked from the main site index.

Local build:

```bash
make notes
```

On Windows `cmd`:

```bat
make notes
```

---

## Reference

- Kitaev, A. Yu. (2001). *Unpaired Majorana fermions in quantum wires.* Physics-Uspekhi, 44(10S), 131.
- Herviou, L. (2017). *Topological Phases and Majorana Fermions.* Seminar notes.

---

## License

MIT — see [LICENSE](LICENSE).
