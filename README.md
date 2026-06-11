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
| 3 | **Measuring Topology** — Circuit-based measurements, edge & string observables | 🔜 |
| 4 | **The NISQ Reality Check** — Noise modeling, mitigation, robustness | 🔜 |

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

## Block 3 — Measuring Topology with Qiskit

Block 3 moves from matrix-based validation to gate-based simulation. The current scripted runner is `src/block3.py`, with shared VQE and measurement helpers in `src/block3_core.py`.

Key pieces:

- **VQE state preparation** — an `EfficientSU2` ansatz with `RY` rotations and linear CNOT entanglement prepares small-chain ground states.
- **Aer Estimator** — Qiskit's simulator primitive used to evaluate VQE energy expectations, e.g. `(<psi(theta)|H|psi(theta)>)`, without running on real hardware.
- **Why "Aer"?** `qiskit-aer` is Qiskit's high-performance simulator package. The name follows Qiskit's classical-elements naming theme: Terra for the core framework, Aer for simulators, and the older Aqua package for algorithms.
- **Shot-based measurements** — `AerSimulator` samples circuits with finite shots, then bitstrings are post-processed into observables such as the edge string `X0 Z1 Z2 X3`.
- **Week 7 VQE sweep** — a parity-constrained VQE sweep over `mu` is validated against ED using energy error, parity, subspace fidelity, and edge-string error.

### Run Block 3

```bash
cd src
python block3.py --list
python block3.py --plots 1      # VQE local-vs-edge-string observable test
python block3.py --plots 7      # Week 7 VQE mu-sweep
python block3.py --plots 8      # ansatz-depth diagnostic
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
