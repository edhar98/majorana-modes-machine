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
| 1 | **The Physics Bridge** — Kitaev chain, finite-size spectra, topological diagnostics | ✅ |
| 2 | **The Qubit Encoding** — Fermion-to-qubit mapping, ideal circuit simulation | 🔜 |
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
- **Finite-size spectrum** — near-zero edge modes in the topological phase ($|\mu| < 2t$)
- **Winding number** — numerical BZ integral of the BdG d-vector angle


### Run

```bash
cd src
python block1.py                      # all plots
python block1.py --plots 4 --L 100   # single plot, custom chain length
python block1.py --list               # show available plots
```

### Requirements

```bash
pip install numpy matplotlib
```

---

## Slides

Weekly presentation slides are compiled to PDF and published via GitHub Pages:

| Week | Topic | PDF |
|------|-------|-----|
| 1 | The Physics Bridge — Kitaev chain, BdG, topological invariant | [week1.pdf](https://edhar98.github.io/majorana-modes-machine/week1.pdf) |
| 2 | The Physics Bridge (cont.) — winding number, phase diagram | [week2.pdf](https://edhar98.github.io/majorana-modes-machine/week2.pdf) |
| 3 | Finite-Size Physics & Edge Modes — spectra, localization, splitting | [week3.pdf](https://edhar98.github.io/majorana-modes-machine/week3.pdf) |

---

## Reference

- Kitaev, A. Yu. (2001). *Unpaired Majorana fermions in quantum wires.* Physics-Uspekhi, 44(10S), 131.
- Herviou, L. (2017). *Topological Phases and Majorana Fermions.* Seminar notes.

---

## License

MIT — see [LICENSE](LICENSE).
