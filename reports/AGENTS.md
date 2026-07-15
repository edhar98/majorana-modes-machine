# AGENTS.md — writing an individual report

Instructions for any agent (or person) drafting one of the six reports under
`reports/`. Read [`README.md`](README.md) first for the topic split and to see
which part you are writing. **Stay strictly inside your part's scope line.**

## 1. Start a new report folder

There is **no shared template**. `Edgar_Harutyunyan/` is the reference folder —
copy it:

```bash
cp -r reports/Edgar_Harutyunyan reports/Firstname_Lastname
```

Then edit the three metadata macros near the top of `report.tex`:

```latex
\newcommand{\subtitle}{<your Part title, e.g. Qubit Encoding via Jordan–Wigner>}
\newcommand{\AuthorName}{Firstname Lastname}
\newcommand{\AuthorNumber}{<matriculation number>}
```

Leave `\Class`, `\Title`, `\Supervisor`, and the Leipzig header as-is (shared).

## 2. Build

From inside your report folder, on **Linux/macOS** (`makefile`, GNU make) or
**Windows** (`make.bat`, cmd) — same commands, both files are in the folder:

```bash
make               # builds report.pdf (AI text purple) AND report_clean.pdf (AI text hidden)
make report        # only report.pdf
make report_clean  # only report_clean.pdf
make clean         # remove aux/log/out/toc/bbl/blg
make cleanall      # also remove the PDFs
```

On Windows cmd, typing `make` runs the bundled `make.bat` (or just double-click it),
so no separate command is needed — keep `make.bat` when you copy the folder. Needs
`pdflatex` + `bibtex` (TeX Live or MiKTeX). The `report_clean` target re-runs with
`\hideai` defined, so `\ai{...}` prose vanishes — that is the human-only PDF.

## 3. Page budget (4–5 pages) — the `sections/` skeleton

The body lives in `sections/`, `\input` from `report.tex` in this order. Keep to
these rough sizes so the report lands at 4–5 pages:

| File | Role | Size |
|---|---|---|
| `sections/00_intro.tex` | motivation + where your part sits in the project | ~½ p |
| `sections/10_theory.tex` | the physics / derivation your part owns | ~1–1.5 p |
| `sections/20_results.tex` | methods + key figures + concrete numbers | ~2 p |
| `sections/30_ai.tex` | short AI-collaboration reflection | ~⅓ p |

## 4. AI-provenance convention (required)

This is an AI-augmented seminar, so provenance is marked in the source. **Wrap
every AI-generated passage in `\ai{...}`.** `report.pdf` renders it purple;
`report_clean.pdf` (via `\hideai`) drops it, giving the human-only text. Both PDFs
should read sensibly — i.e. don't let `\ai{}` carry a load-bearing sentence the
clean version needs.

## 5. Content sources — mine, don't re-derive

Your part's row in [`README.md`](README.md) lists the exact `notes/*.tex` and
`src` figures you own. **Adapt and cite those notes; do not re-derive from
scratch.** The `notes/` write-ups are article-class LaTeX and match this report's
document class, so equations and phrasing port over directly.

## 6. Figures

- Use figures from **your own block only** (see your Code/figs list in README).
- Regenerate fresh PDFs from the runners rather than reusing stale files:

  ```bash
  source /opt/python-envs/myenv/bin/activate
  python src/block1.py --list          # see available figures
  python src/block1.py --plots 6       # regenerate one
  ```

  Copy the produced `plots/*.pdf` into a local `figs/` folder in your report and
  `\includegraphics` from there.
- **`src/showcase.py` gallery images are off-limits** — they span all blocks and
  belong to no single report.

## 7. No-overlap contract

- Respect the scope lines in README; do not spill into a neighbour's part.
- At a seam, cross-reference in one line — *"see [Author, Part N]"* — rather than
  duplicating content.
- **Parts 5 & 6 specifically:** the $T_1/T_2$ ↔ physical-error mapping is the
  seam. Default: Part 6 owns the taxonomy / Jordan–Wigner identity / parity-
  protection *principle*; Part 5 owns the *quantitative* device-noise results.
  Whoever writes the channel mechanics cross-references the other. Finalize the
  line between the two owners and update the README note if you move it.

## 8. References

Each folder has its own `references.bib` (copied from Edgar's seed). Keep the
**shared core** entries (`kitaev2001`, `herviou2017`, `qiskit2024`, …) identical
across reports; add your part-specific entries below the marked line. `report.tex`
already calls `\bibliography{references}` with `plainnat`.
