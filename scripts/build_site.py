#!/usr/bin/env python
"""Build the GitHub Pages output for the seminar project."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Week:
    number: int
    block: str
    title: str
    summary: str


@dataclass(frozen=True)
class Figure:
    filename: str
    title: str
    text: str
    alt: str
    links: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Note:
    stem: str
    title: str
    group: str


WEEKS = (
    Week(1, "Block 1", "Physics bridge", "Kitaev chain, BdG Hamiltonian, and the first topological invariant."),
    Week(2, "Block 1", "Bulk topology", "Winding number, phase diagram, and the gap closing at mu = +/- 2t."),
    Week(3, "Blocks 1-2", "Finite-size edge physics", "Majorana edge modes, splitting, and the bridge into qubits."),
    Week(4, "Block 2", "Jordan-Wigner encoding", "Qubit Hamiltonian, parity sectors, and exact qubit spectra."),
    Week(5, "Block 3", "VQE preparation", "Hardware-efficient RY/CNOT ansatz and first edge-string measurements."),
    Week(6, "Block 3", "String-order sweep", "Circuit-measurable edge string across the topological transition."),
    Week(7, "Block 3", "Parity-constrained VQE", "Warm-start mu sweep, ED validation, and depth diagnostics."),
    Week(8, "Block 4", "Noise kickoff", "Frozen-state readout and gate-noise diagnostics after the VQE baseline."),
    Week(9, "Block 4", "Circuit-level NISQ study", "Density-matrix noise, verification, depth optimum, parity, and length."),
    Week(10, "Synthesis", "Final capstone", "End-to-end thesis from Majorana physics to noisy quantum circuits."),
)


FIGURES: tuple[Figure, ...] = ()


NOTES = (
    Note("qubit_encoding_derivations", "Jordan-Wigner derivations", "Encoding and exact physics"),
    Note("finite_size_majorana_splitting", "Finite-size Majorana splitting", "Encoding and exact physics"),
    Note("majorana_splitting_vs_L", "Majorana splitting versus L", "Encoding and exact physics"),
    Note("ising_comparison", "Ising comparison", "Encoding and exact physics"),
    Note("measuring_topology_qiskit", "Measuring topology in Qiskit", "VQE and measurement"),
    Note("week6_phase_sweep", "Week 6 phase sweep", "VQE and measurement"),
    Note("week7_vqe_sweep", "Week 7 VQE sweep", "VQE and measurement"),
    Note("block4_noise_diagnostic", "Block 4 noise diagnostic", "Noise and scaling"),
    Note("week9_note", "Week 9 gate-noise study", "Noise and scaling"),
    Note("noisy_vqe_and_backend_noise", "Noisy VQE and backend noise", "Noise and scaling"),
    Note("parity_topology_protection", "Parity versus topology", "Noise and scaling"),
    Note("topology_noise_reps_scaling", "Topology, noise, and reps scaling", "Noise and scaling"),
    Note("scaling_to_large_L", "Scaling to large L", "Noise and scaling"),
    Note("kitaev_error_taxonomy", "Kitaev error taxonomy", "Noise and scaling"),
)


WEEK_METADATA = {week.number: week for week in WEEKS}
FIGURE_METADATA = {figure.filename: figure for figure in FIGURES}
NOTE_METADATA = {note.stem: note for note in NOTES}


CSS = """
:root {
  color-scheme: light;
  --ink: #121417;
  --muted: #626a72;
  --line: #dfe3e7;
  --paper: #ffffff;
  --wash: #f6f4f0;
  --accent: #d7358a;
  --accent-2: #167f7a;
  --accent-gradient: linear-gradient(135deg, var(--accent), var(--accent-2));
}
* {
  box-sizing: border-box;
}
html {
  scroll-behavior: smooth;
}
body {
  margin: 0;
  background: var(--wash);
  color: var(--ink);
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.5;
  letter-spacing: 0;
}
a {
  color: inherit;
}
a:hover {
  text-decoration-thickness: 2px;
}
.hero {
  position: relative;
  min-height: 68vh;
  padding: 1.25rem;
  display: flex;
  align-items: end;
  overflow: hidden;
  background-color: #ffffff;
  border-bottom: 1px solid var(--line);
}
.hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: var(--hero-image);
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
}
.hero-inner {
  position: relative;
  z-index: 1;
  width: min(1120px, 100%);
  margin: 0 auto;
  padding: 2rem 0;
}
.hero-copy {
  max-width: 780px;
  margin: 0 auto;
  padding: 1.25rem 1.5rem 1.35rem;
  background: rgba(255, 255, 255, 0.9);
  border-left: 8px solid transparent;
  border-image: var(--accent-gradient) 1;
}
.eyebrow {
  margin: 0 0 0.35rem;
  color: var(--accent-2);
  background: linear-gradient(90deg, var(--accent-2), var(--accent));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  font-size: 0.88rem;
  font-weight: 800;
  text-transform: uppercase;
}
h1,
h2,
h3,
p {
  margin-top: 0;
}
h1 {
  margin-bottom: 0.75rem;
  font-size: 3rem;
  line-height: 1.04;
}
h2 {
  margin-bottom: 0.75rem;
  font-size: 1.75rem;
  line-height: 1.15;
}
h3 {
  margin-bottom: 0.35rem;
  font-size: 1rem;
  line-height: 1.25;
}
.lede {
  max-width: 720px;
  margin-bottom: 1rem;
  color: #272b31;
  font-size: 1.08rem;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1.1rem;
}
.action {
  min-height: 2.5rem;
  display: inline-flex;
  align-items: center;
  padding: 0.58rem 0.8rem;
  border: 1px solid transparent;
  background: var(--accent-gradient);
  color: #ffffff;
  font-weight: 700;
  text-decoration: none;
}
.action.secondary {
  background: #ffffff;
  border-color: #cfd5db;
  color: var(--ink);
}
main {
  width: min(1120px, calc(100% - 2rem));
  margin: 0 auto;
}
.band {
  padding: 3rem 0;
  border-bottom: 1px solid var(--line);
}
.intro-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: 1.2rem;
  align-items: start;
}
.thesis {
  display: grid;
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.thesis li {
  padding: 0.95rem 1rem;
  background: var(--paper);
  border: 1px solid var(--line);
  border-left: 6px solid var(--accent-2);
  border-radius: 8px;
}
.timeline {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
}
.stage,
.figure-card,
.week-card,
.note-group {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.stage {
  min-height: 12rem;
  padding: 1rem;
}
.stage strong {
  display: inline-block;
  margin-bottom: 0.55rem;
  color: var(--accent-2);
  font-size: 0.85rem;
  text-transform: uppercase;
}
.stage p,
.figure-card p,
.week-card p {
  margin-bottom: 0;
  color: var(--muted);
}
.gallery {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}
.figure-card {
  overflow: hidden;
}
.media {
  aspect-ratio: 16 / 10;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  border-bottom: 1px solid var(--line);
}
.media img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
.figure-body,
.week-card,
.note-group {
  padding: 1rem;
}
.meta {
  margin-bottom: 0.45rem;
  color: var(--accent-2);
  font-size: 0.82rem;
  font-weight: 800;
  text-transform: uppercase;
}
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.8rem;
}
.links a {
  display: inline-flex;
  min-height: 2rem;
  align-items: center;
  padding: 0.35rem 0.55rem;
  border: 1px solid var(--line);
  background: #f8fafc;
  color: #1f2933;
  font-size: 0.88rem;
  font-weight: 700;
  text-decoration: none;
}
.weeks {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}
.week-card {
  min-height: 10.5rem;
  display: flex;
  flex-direction: column;
}
.week-card .links {
  margin-top: auto;
  padding-top: 0.9rem;
}
.notes {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}
.note-group h3 {
  color: var(--accent-2);
}
.note-group ul {
  margin: 0;
  padding-left: 1.1rem;
}
.note-group li {
  margin: 0.35rem 0;
}
.empty {
  color: var(--muted);
}
.feedback-hero {
  min-height: 52vh;
}
.feedback-page .band {
  padding: 2.7rem 0;
}
.reflection-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}
.reflection-card {
  min-height: 13rem;
  padding: 1rem;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.reflection-card.accent {
  border-left: 6px solid var(--accent);
}
.reflection-card.teal {
  border-left: 6px solid var(--accent-2);
}
.reflection-card p,
.reflection-card li {
  color: var(--muted);
}
.reflection-card ul,
.tip-list,
.improvement-list {
  margin: 0;
  padding-left: 1.1rem;
}
.reflection-card li,
.tip-list li,
.improvement-list li {
  margin: 0.45rem 0;
}
.reflection-split {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
  gap: 1.2rem;
  align-items: start;
}
.quote-panel {
  padding: 1.2rem;
  background: #ffffff;
  border: 1px solid var(--line);
  border-left: 8px solid transparent;
  border-image: var(--accent-gradient) 1;
  border-radius: 8px;
}
.quote-panel p:last-child {
  margin-bottom: 0;
}
.back-link {
  display: inline-flex;
  min-height: 2.2rem;
  align-items: center;
  margin-bottom: 1rem;
  color: var(--accent-2);
  font-weight: 800;
  text-decoration: none;
}
footer {
  padding: 2rem 0 3rem;
  color: var(--muted);
}
@media (max-width: 900px) {
  .intro-grid,
  .timeline,
  .gallery,
  .weeks,
  .notes,
  .reflection-grid,
  .reflection-split {
    grid-template-columns: 1fr;
  }
  .hero {
    min-height: 62vh;
    padding: 0.85rem;
  }
  .hero::before {
    background-position: center top;
    background-size: 100% auto;
  }
  .hero-copy {
    padding: 1rem;
  }
  h1 {
    font-size: 2.25rem;
  }
}
""".strip()


def versioned(path: str, version: str) -> str:
    return f"{path}?v={quote(version)}"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def source_slide_pdfs() -> list[Path]:
    return sorted((ROOT / "presentation").glob("week*/slides.pdf"), key=week_sort_key)


def source_note_pdfs() -> list[Path]:
    return sorted((ROOT / "notes").glob("*.pdf"))


def source_gallery_plots() -> list[Path]:
    plots = [
        plot for plot in (ROOT / "plots").iterdir()
        if plot.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}
        and not plot.name.startswith("show_")
    ]
    return sorted(plots, key=plot_sort_key)


def copy_outputs(output: Path) -> None:
    notes_dir = output / "notes"
    img_dir = output / "img"
    plots_dir = output / "plots"
    thumbs_dir = img_dir / "plot_thumbs"
    notes_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    (output / ".nojekyll").touch()

    for pdf in source_slide_pdfs():
        target = output / f"{pdf.parent.name}.pdf"
        shutil.copy2(pdf, target)

    for pdf in source_note_pdfs():
        shutil.copy2(pdf, notes_dir / pdf.name)

    for plot in source_gallery_plots():
        shutil.copy2(plot, plots_dir / plot.name)
        create_plot_thumbnail(plot, thumbs_dir / f"{plot.stem}.png")

    hero = ROOT / "img" / "majorana_zero_modes_hero.png"
    if hero.exists():
        shutil.copy2(hero, img_dir / hero.name)


def week_sort_key(path: Path) -> int:
    name = path.parent.name.removeprefix("week")
    return int(name) if name.isdigit() else 999


def plot_sort_key(path: Path) -> tuple[int, int, str]:
    block_match = re.match(r"block(\d+)", path.stem)
    index_match = re.search(r"_(\d+)_", path.stem)
    block = int(block_match.group(1)) if block_match else 999
    index = int(index_match.group(1)) if index_match else 999
    return block, index, path.name


def create_plot_thumbnail(source: Path, target: Path) -> None:
    if source.suffix.lower() == ".pdf":
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir) / "page"
            result = subprocess.run(
                ["pdftoppm", "-png", "-singlefile", "-r", "120", str(source), str(prefix)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"pdftoppm failed for {source}: {result.stderr}")
            resize_image(prefix.with_suffix(".png"), target)
        return

    resize_image(source, target)


def resize_image(source: Path, target: Path) -> None:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((760, 480), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (760, 480), "white")
        x = (canvas.width - image.width) // 2
        y = (canvas.height - image.height) // 2
        canvas.paste(image, (x, y))
        canvas.save(target, "PNG", optimize=True)


def title_from_stem(stem: str) -> str:
    cleaned = re.sub(r"^block\d+_", "", stem)
    cleaned = re.sub(r"^week\d+_", "", cleaned)
    return cleaned.replace("_", " ").title()


def render_links(links: tuple[tuple[str, str], ...], version: str) -> str:
    if not links:
        return ""
    parts = [
        f'<a href="{esc(versioned(href, version))}">{esc(label)}</a>'
        for label, href in links
    ]
    return '<div class="links">' + "\n".join(parts) + "</div>"


def fallback_figure(plot: Path) -> Figure:
    title = title_from_stem(plot.stem)
    return Figure(
        plot.name,
        title,
        "Existing project figure generated by the block runners or analysis scripts.",
        title,
    )


def render_figure(plot: Path, version: str) -> str:
    figure = FIGURE_METADATA.get(plot.name, fallback_figure(plot))
    full = f"plots/{figure.filename}"
    src = f"img/plot_thumbs/{plot.stem}.png"
    links = (("Open plot", full),) + figure.links
    return f"""
        <article class="figure-card">
          <a class="media" href="{esc(versioned(full, version))}">
            <img src="{esc(versioned(src, version))}" alt="{esc(figure.alt)}" loading="lazy">
          </a>
          <div class="figure-body">
            <h3>{esc(figure.title)}</h3>
            <p>{esc(figure.text)}</p>
            {render_links(links, version)}
          </div>
        </article>
    """


def fallback_week(pdf: Path) -> Week:
    name = pdf.parent.name.removeprefix("week")
    number = int(name) if name.isdigit() else 999
    title = f"Week {number}" if name.isdigit() else title_from_stem(pdf.parent.name)
    return Week(number, "Presentation", title, "Presentation deck generated from the repository source.")


def render_week(pdf: Path, version: str) -> str:
    name = pdf.parent.name.removeprefix("week")
    number = int(name) if name.isdigit() else 999
    week = WEEK_METADATA.get(number, fallback_week(pdf))
    filename = f"{pdf.parent.name}.pdf"
    return f"""
        <article class="week-card">
          <div class="meta">Week {week.number} / {esc(week.block)}</div>
          <h3>{esc(week.title)}</h3>
          <p>{esc(week.summary)}</p>
          {render_links((("Open slides", filename),), version)}
        </article>
    """


def note_title(stem: str) -> str:
    note = NOTE_METADATA.get(stem)
    if note:
        return note.title
    return stem.replace("_", " ").title()


def note_group(stem: str) -> str:
    note = NOTE_METADATA.get(stem)
    if note:
        return note.group
    return "Additional notes"


def render_notes(paths: list[Path], version: str) -> str:
    if not paths:
        return '<p class="empty">No note PDFs were found in this build.</p>'

    groups: dict[str, list[Path]] = {}
    for path in paths:
        groups.setdefault(note_group(path.stem), []).append(path)

    rendered: list[str] = []
    for group in ("Encoding and exact physics", "VQE and measurement", "Noise and scaling", "Additional notes"):
        if group not in groups:
            continue
        items = "\n".join(
            f'<li><a href="{esc(versioned("notes/" + path.name, version))}">{esc(note_title(path.stem))}</a></li>'
            for path in groups[group]
        )
        rendered.append(f"""
        <section class="note-group">
          <h3>{esc(group)}</h3>
          <ul>
            {items}
          </ul>
        </section>
        """)
    return "\n".join(rendered)


def render_index(version: str) -> str:
    figures = "\n".join(render_figure(plot, version) for plot in source_gallery_plots())
    weeks = "\n".join(render_week(pdf, version) for pdf in source_slide_pdfs())
    notes = render_notes(source_note_pdfs(), version)
    hero_image = versioned("img/majorana_zero_modes_hero.png", version)
    project_url = "https://github.com/edhar98/majorana-modes-machine"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Seminar project on Majorana modes, Kitaev-chain topology, VQE preparation, and NISQ noise.">
  <title>Majorana Modes in the Machine</title>
  <style>
{CSS}
  </style>
</head>
<body>
  <header class="hero" style="--hero-image: url('{esc(hero_image)}')">
    <div class="hero-inner">
      <div class="hero-copy">
        <p class="eyebrow">Advanced Seminar / AI-Augmented Theoretical Physics</p>
        <h1>Majorana Modes in the Machine</h1>
        <p class="lede">A project page for the full arc: Kitaev-chain topology, Jordan-Wigner qubits, VQE string-order measurement, and the circuit-level noise study that decides what survives on NISQ hardware.</p>
        <div class="actions" aria-label="Primary links">
          <a class="action" href="{esc(project_url)}">GitHub project</a>
          <a class="action secondary" href="#figures">View figures</a>
          <a class="action secondary" href="#slides">Browse slides</a>
          <a class="action secondary" href="{esc(versioned("llm-feedback.html", version))}">LLM feedback</a>
        </div>
      </div>
    </div>
  </header>
  <main>
    <section class="band intro-grid" aria-labelledby="thesis-heading">
      <div>
        <h2 id="thesis-heading">What the project answers</h2>
        <p class="lede">The central question is not whether Majorana physics is beautiful in the exact model. It is whether the measurable topological signal can still be prepared, verified, and read out after realistic circuit noise enters.</p>
      </div>
      <ul class="thesis">
        <li><strong>Topology gives the target.</strong> The Kitaev chain has a sharp bulk transition and exponentially split edge modes.</li>
        <li><strong>The measured signal is non-local.</strong> The useful qubit diagnostic is an edge string, not a local order parameter.</li>
        <li><strong>Noise sets the operating point.</strong> The best circuit is the shallowest one that is already expressive enough.</li>
      </ul>
    </section>
    <section class="band" aria-labelledby="arc-heading">
      <h2 id="arc-heading">Project arc</h2>
      <div class="timeline">
        <article class="stage">
          <strong>Block 1</strong>
          <h3>Bulk topology</h3>
          <p>BdG bands, winding number, phase diagram, and Majorana edge modes.</p>
        </article>
        <article class="stage">
          <strong>Block 2</strong>
          <h3>Qubit encoding</h3>
          <p>Jordan-Wigner mapping, parity sectors, and exact qubit checks.</p>
        </article>
        <article class="stage">
          <strong>Block 3</strong>
          <h3>Measurement</h3>
          <p>VQE preparation and a circuit-measurable non-local edge string.</p>
        </article>
        <article class="stage">
          <strong>Block 4</strong>
          <h3>NISQ reality check</h3>
          <p>Density-matrix gate noise, verification, depth optimum, parity, and scaling.</p>
        </article>
      </div>
    </section>
    <section class="band" id="figures" aria-labelledby="figures-heading">
      <h2 id="figures-heading">Figure gallery</h2>
      <div class="gallery">
        {figures}
      </div>
    </section>
    <section class="band" id="slides" aria-labelledby="slides-heading">
      <h2 id="slides-heading">Presentations</h2>
      <div class="weeks">
        {weeks}
      </div>
    </section>
    <section class="band" id="notes" aria-labelledby="notes-heading">
      <h2 id="notes-heading">Notes</h2>
      <div class="notes">
        {notes}
      </div>
    </section>
    <footer>
      <p>Generated from the repository slides, notes, and existing plot artifacts. Cache key: {esc(version)}.</p>
    </footer>
  </main>
</body>
</html>
"""


def render_feedback(version: str) -> str:
    hero_image = versioned("img/majorana_zero_modes_hero.png", version)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Final reflection on using LLMs during the Majorana modes seminar project.">
  <title>LLM Project Feedback</title>
  <style>
{CSS}
  </style>
</head>
<body class="feedback-page">
  <header class="hero feedback-hero" style="--hero-image: url('{esc(hero_image)}')">
    <div class="hero-inner">
      <div class="hero-copy">
        <p class="eyebrow">Final feedback / LLM-assisted research workflow</p>
        <h1>What I Learned From Using LLMs</h1>
        <p class="lede">A personal review of how language models helped this seminar project, where they were risky, and what I would change in future physics and quantum-computing workflows.</p>
        <div class="actions" aria-label="Feedback page links">
          <a class="action" href="index.html">Back to project</a>
          <a class="action secondary" href="#tips">Personal tips</a>
          <a class="action secondary" href="#future">Future improvements</a>
        </div>
      </div>
    </div>
  </header>
  <main>
    <section class="band reflection-split" aria-labelledby="summary-heading">
      <div>
        <a class="back-link" href="index.html">Back to the seminar page</a>
        <h2 id="summary-heading">Overall experience</h2>
        <p class="lede">LLMs were most useful when I treated them as an engineering and explanation partner, not as an authority. They helped me move faster from physics ideas to code, plots, notes, slides, and a publishable web page.</p>
        <p>The strongest use case was iteration: asking for a first structure, checking it against the repository, improving the visual design, and then verifying the generated files. The weakest use case was anything that required scientific trust without independent checks.</p>
      </div>
      <aside class="quote-panel">
        <h3>Final takeaway</h3>
        <p>LLMs can speed up a project dramatically, but the human still has to own the physics, the conventions, the data provenance, and the final taste.</p>
      </aside>
    </section>
    <section class="band" aria-labelledby="worked-heading">
      <h2 id="worked-heading">What worked well</h2>
      <div class="reflection-grid">
        <article class="reflection-card teal">
          <h3>Turning rough ideas into structure</h3>
          <p>The model was helpful for breaking a broad seminar topic into blocks: Kitaev physics, Jordan-Wigner encoding, VQE measurement, and NISQ noise.</p>
        </article>
        <article class="reflection-card accent">
          <h3>Code and presentation glue</h3>
          <p>It was useful for connecting scripts, figures, notes, slides, and the GitHub Pages site, especially when the task was mechanical but error-prone.</p>
        </article>
        <article class="reflection-card teal">
          <h3>Fast visual iteration</h3>
          <p>The page design improved through several short feedback loops: changing the hero figure, moving the chain, simplifying colors, and replacing the final-deck link with the repository link.</p>
        </article>
        <article class="reflection-card accent">
          <h3>Consistency checks</h3>
          <p>The model was valuable when asked to verify what slides and notes actually imported, recover cache files, and avoid publishing stale generated artifacts.</p>
        </article>
      </div>
    </section>
    <section class="band" aria-labelledby="limits-heading">
      <h2 id="limits-heading">What did not work well</h2>
      <div class="reflection-grid">
        <article class="reflection-card accent">
          <h3>Confidence without proof</h3>
          <p>LLMs can sound certain even when a convention, sign, file path, or figure dependency is wrong. In this project, physics conventions had to be pinned down explicitly.</p>
        </article>
        <article class="reflection-card teal">
          <h3>Generated artifacts need boundaries</h3>
          <p>It is easy for a model to create extra plots, thumbnails, or pages. That is only helpful when generated output is separated from source artifacts and caches.</p>
        </article>
        <article class="reflection-card accent">
          <h3>Context can drift</h3>
          <p>Long projects need persistent instructions. Otherwise the assistant may forget which branch publishes the site, which figures are canonical, or which scripts are allowed to regenerate data.</p>
        </article>
        <article class="reflection-card teal">
          <h3>Scientific judgment is not outsourced</h3>
          <p>The model can explain and implement, but it cannot replace checking equations, validating plots, or deciding whether a result is physically meaningful.</p>
        </article>
      </div>
    </section>
    <section class="band reflection-split" id="tips" aria-labelledby="tips-heading">
      <div>
        <h2 id="tips-heading">Personal tips</h2>
        <p class="lede">The best results came from giving the model narrow tasks with visible verification criteria.</p>
      </div>
      <ol class="tip-list">
        <li>Keep a clear source of truth for conventions, commands, and generated artifacts.</li>
        <li>Ask for small changes and inspect the result before asking for the next one.</li>
        <li>Make the model cite exact files, commands, and outputs when it claims something is fixed.</li>
        <li>Do not accept physics derivations or numerical claims without an independent check.</li>
        <li>Separate source plots, cache files, thumbnails, and published web output.</li>
        <li>Commit often before large cleanup or restructuring steps.</li>
      </ol>
    </section>
    <section class="band reflection-split" id="future" aria-labelledby="future-heading">
      <div>
        <h2 id="future-heading">Future improvements</h2>
        <p class="lede">For a future project, I would use LLMs more deliberately and build stronger guardrails around them.</p>
      </div>
      <ul class="improvement-list">
        <li>Use a project memory file from the beginning, especially for physics conventions and build commands.</li>
        <li>Add automatic dependency checks for figures, notes, slides, caches, and web assets.</li>
        <li>Track provenance for every plot: source script, command, parameters, and cache inputs.</li>
        <li>Prefer reproducible scripts over notebook-only workflows when a figure enters a slide deck.</li>
        <li>Make review prompts stricter: ask for bugs, missing tests, and invalid assumptions before asking for style changes.</li>
        <li>Use the LLM for acceleration, but keep final responsibility for correctness and presentation quality.</li>
      </ul>
    </section>
    <footer>
      <p>Generated from the repository site builder. Cache key: {esc(version)}.</p>
    </footer>
  </main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static GitHub Pages site.")
    parser.add_argument("--output", default="web_output", type=Path)
    parser.add_argument("--version", default="local")
    args = parser.parse_args()

    output = args.output
    if not output.is_absolute():
        output = ROOT / output
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    copy_outputs(output)
    (output / "index.html").write_text(render_index(args.version), encoding="utf-8")
    (output / "llm-feedback.html").write_text(render_feedback(args.version), encoding="utf-8")
    print(f"Built {output / 'index.html'}")
    print(f"Built {output / 'llm-feedback.html'}")


if __name__ == "__main__":
    main()
