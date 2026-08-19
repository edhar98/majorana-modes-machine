#!/usr/bin/env python
"""Build the GitHub Pages output for the seminar project."""

from __future__ import annotations

import argparse
import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Week:
    number: int
    block: str
    title: str
    summary: str



@dataclass(frozen=True)
class Note:
    stem: str
    title: str
    group: str


@dataclass(frozen=True)
class Report:
    directory: str
    part: int
    author: str
    title: str


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



# Notes are grouped by project Block and listed chronologically within each Block
# (tuple order == display order within a group; see NOTE_ORDER / render_notes).
BLOCK_GROUPS = (
    "Block 1: Kitaev chain and Majorana physics",
    "Block 2: Jordan-Wigner qubit encoding",
    "Block 3: VQE preparation and measurement",
    "Block 4: NISQ noise and scaling",
    "Additional notes",
)

NOTES = (
    # Block 1 -- Kitaev chain and Majorana physics
    Note("finite_size_majorana_splitting", "Finite-size Majorana splitting", BLOCK_GROUPS[0]),
    Note("majorana_splitting_vs_L", "Majorana splitting versus L", BLOCK_GROUPS[0]),
    # Block 2 -- Jordan-Wigner qubit encoding
    Note("qubit_encoding_derivations", "Jordan-Wigner derivations", BLOCK_GROUPS[1]),
    Note("ising_comparison", "Ising comparison", BLOCK_GROUPS[1]),
    # Block 3 -- VQE preparation and measurement
    Note("measuring_topology_qiskit", "Measuring topology in Qiskit", BLOCK_GROUPS[2]),
    Note("string_order_phase_sweep", "String-order phase sweep", BLOCK_GROUPS[2]),
    Note("parity_constrained_vqe_sweep", "Parity-constrained VQE sweep", BLOCK_GROUPS[2]),
    # Block 4 -- NISQ noise and scaling
    Note("block4_noise_diagnostic", "Block 4 noise diagnostic", BLOCK_GROUPS[3]),
    Note("circuit_level_gate_noise", "Circuit-level gate noise", BLOCK_GROUPS[3]),
    Note("parity_topology_protection", "Parity versus topology", BLOCK_GROUPS[3]),
    Note("noisy_vqe_and_backend_noise", "Noisy VQE and backend noise", BLOCK_GROUPS[3]),
    Note("topology_noise_reps_scaling", "Topology, noise, and reps scaling", BLOCK_GROUPS[3]),
    Note("scaling_to_large_L", "Scaling to large L", BLOCK_GROUPS[3]),
    Note("kitaev_error_taxonomy", "Kitaev error taxonomy", BLOCK_GROUPS[3]),
)


REPORTS = (
    Report("Guilherme_Schewtschik", 1, "Guilherme Schewtschik", "Kitaev Chain & Bulk Topology"),
    Report("Zhenming_Shi", 2, "Zhenming Shi", "Finite-Size Physics & Majorana Edge Modes"),
    Report("Jaskaran_Singh", 3, "Jaskaran Singh", "Qubit Encoding (Jordan-Wigner)"),
    Report("Zhengyi_Liu", 4, "Zhengyi Liu", "Measuring Topology on Circuits (VQE + String Order)"),
    Report("Dobromir_Stoev", 5, "Dobromir Stoev", "NISQ Noise on the Diagnostic"),
    Report("Edgar_Harutyunyan", 6, "Edgar Harutyunyan", "Error Taxonomy & Scaling to Large L"),
)


WEEK_METADATA = {week.number: week for week in WEEKS}
NOTE_METADATA = {note.stem: note for note in NOTES}
NOTE_ORDER = {note.stem: i for i, note in enumerate(NOTES)}  # chronological within blocks
REPORT_METADATA = {report.directory: report for report in REPORTS}


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
.week-card,
.note-group,
.report-card {
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
.week-card p,
.report-card p {
  margin-bottom: 0;
  color: var(--muted);
}
.week-card,
.note-group,
.report-card {
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
.reports {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
.report-card {
  min-height: 9rem;
  display: flex;
  flex-direction: column;
}
.report-card .links {
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
  .weeks,
  .notes,
  .reports,
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


def source_report_pdfs() -> list[Path]:
    paths = [ROOT / "reports" / report.directory / "report.pdf" for report in REPORTS]
    return [path for path in paths if path.exists()]


def copy_outputs(output: Path) -> None:
    notes_dir = output / "notes"
    reports_dir = output / "reports"
    img_dir = output / "img"
    notes_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)
    (output / ".nojekyll").touch()

    for pdf in source_slide_pdfs():
        target = output / f"{pdf.parent.name}.pdf"
        shutil.copy2(pdf, target)

    for pdf in source_note_pdfs():
        shutil.copy2(pdf, notes_dir / pdf.name)

    for pdf in source_report_pdfs():
        target_dir = reports_dir / pdf.parent.name
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf, target_dir / pdf.name)

    hero = ROOT / "img" / "majorana_zero_modes_hero.png"
    if hero.exists():
        shutil.copy2(hero, img_dir / hero.name)


def week_sort_key(path: Path) -> int:
    name = path.parent.name.removeprefix("week")
    return int(name) if name.isdigit() else 999


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
    for group in BLOCK_GROUPS:
        if group not in groups:
            continue
        # chronological within the block (NOTES tuple order); unknown stems last
        ordered = sorted(groups[group], key=lambda p: NOTE_ORDER.get(p.stem, 10_000))
        items = "\n".join(
            f'<li><a href="{esc(versioned("notes/" + path.name, version))}">{esc(note_title(path.stem))}</a></li>'
            for path in ordered
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


def render_report(pdf: Path, version: str) -> str:
    report = REPORT_METADATA[pdf.parent.name]
    href = f"reports/{report.directory}/report.pdf"
    return f"""
        <article class="report-card">
          <div class="meta">Part {report.part} / {esc(report.author)}</div>
          <h3>{esc(report.title)}</h3>
          {render_links((("Open report", href),), version)}
        </article>
    """


def render_index(version: str) -> str:
    weeks = "\n".join(render_week(pdf, version) for pdf in source_slide_pdfs())
    notes = render_notes(source_note_pdfs(), version)
    reports = "\n".join(render_report(pdf, version) for pdf in source_report_pdfs())
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
          <a class="action secondary" href="#slides">Browse slides</a>
          <a class="action secondary" href="#notes">Notes</a>
          <a class="action secondary" href="#reports">Reports</a>
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
    <section class="band" id="reports" aria-labelledby="reports-heading">
      <h2 id="reports-heading">Reports</h2>
      <div class="reports">
        {reports}
      </div>
    </section>
    <footer>
      <p>Generated from the repository slides, notes, and reports. Cache key: {esc(version)}.</p>
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
        <h1>What We Learned From Using LLMs</h1>
        <p class="lede">A review of an AI-heavy seminar workflow: what helped, what failed, what made the project reproducible, and what we would recommend to students using LLMs for research-style work.</p>
        <div class="actions" aria-label="Feedback page links">
          <a class="action" href="index.html">Back to project</a>
          <a class="action secondary" href="#workflow">Workflow</a>
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
        <p class="lede">We learned <strong>a lot</strong>. The project grew far beyond a normal 5 CP seminar task, precisely because LLMs made it cheap to keep expanding scope: physics derivations, code, plots, slides, notes, audits, and finally this web page.</p>
        <p>The paid coding assistants were clearly stronger for sustained work. We mainly used <strong>Claude (Opus&nbsp;4.8)</strong> and <strong>ChatGPT (GPT&#8209;5.5)</strong> inside <strong>Cursor</strong>, and tried <em>NotebookLM</em>, <em>Gemini</em>, and <em>DeepSeek</em> early on. NotebookLM was good for <em>concept understanding and visual learning</em>, but weaker for continuous, file-based project work.</p>
      </div>
      <aside class="quote-panel">
        <h3>Final takeaway</h3>
        <p>LLMs can multiply your productivity &mdash; but <u>only if the project is organized enough that both you and the agent can verify what is true.</u></p>
      </aside>
    </section>
    <section class="band" id="workflow" aria-labelledby="workflow-heading">
      <h2 id="workflow-heading">Workflow that worked</h2>
      <div class="reflection-grid">
        <article class="reflection-card teal">
          <h3>Start with the environment</h3>
          <p>Before any physics, set up the workspace: a <strong>clear project structure</strong>, <strong>Git/GitHub</strong>, reproducible commands, and a <em>shared instruction file</em>. Here <code>AGENTS.md</code> became the agent's persistent memory and kept style, conventions, and build commands <strong>stable across weeks</strong>.</p>
        </article>
        <article class="reflection-card accent">
          <h3>Everything is a file</h3>
          <p>A <strong>Linux, file-first</strong> workflow was decisive: code, LaTeX, notes, prompts, build scripts, and caches all became files you can <em>version, diff, and verify</em>. That is also how you control an agent's memory &mdash; and why we preferred <strong>CLI and file-based tools over web chat</strong>, where knowledge stays trapped in the window.</p>
        </article>
        <article class="reflection-card teal">
          <h3>Short, focused agents</h3>
          <p>For hard tasks, a <strong>fresh agent with clean context</strong> beat overloading one long conversation. Knowledge-style side questions belong in a <em>separate thread or an aside command</em>, so the main task &mdash; plotting, coding, a deck &mdash; does not <em>drift</em>.</p>
        </article>
        <article class="reflection-card accent">
          <h3>Advisor and audit patterns</h3>
          <p>Complex steps benefited from a main agent consulting <strong>advisor agents</strong>, running <strong>subagents in parallel</strong>, and <em>cross-model review</em>. We even had Opus&nbsp;4.8 write the prompt for a <strong>Fable&nbsp;5 audit</strong> of the whole project.</p>
        </article>
      </div>
    </section>
    <section class="band" aria-labelledby="project-highlights-heading">
      <h2 id="project-highlights-heading">Project highlights</h2>
      <div class="reflection-grid">
        <article class="reflection-card teal">
          <h3>From physics to infrastructure</h3>
          <p>The most valuable output was not text but <strong>reusable infrastructure</strong>: block runners, <code>Makefile</code> targets, LaTeX notes, slides, dependency checks, and this <strong>GitHub Pages</strong> build.</p>
        </article>
        <article class="reflection-card accent">
          <h3>Build tools, not repeated commands</h3>
          <p>Know <em>when to play ignorant and when to be specific</em>. If you cannot compile LaTeX you can ask the model every time &mdash; and <em>stay dependent</em>. If you know the command, ask it to write a <strong><code>Makefile</code> target</strong> both human and agent reuse. The second path <strong>compounds</strong>.</p>
        </article>
        <article class="reflection-card teal">
          <h3>LaTeX was a real advantage</h3>
          <p>LLMs are strong with text and <em>cheaper in tokens</em> on it. Writing notes and decks in <strong>LaTeX</strong> made everything easier to edit, review, compile, and keep consistent &mdash; and turned explanations into <strong>searchable project assets</strong> instead of lost chat windows.</p>
        </article>
      </div>
    </section>
    <section class="band reflection-split" id="tips" aria-labelledby="tips-heading">
      <div>
        <h2 id="tips-heading">Personal tips</h2>
        <p class="lede">The best results came from knowing <em>when to be specific</em> and <em>when to let the model propose options</em>.</p>
      </div>
      <ol class="tip-list">
        <li><strong>Read the generated code.</strong> Understanding it is what lets you write sharper prompts.</li>
        <li>Be <strong>specific</strong> when you already know the result; leave room for the model to be <em>creative</em> when you are genuinely exploring.</li>
        <li>Make the model <strong>cite exact files, commands, and outputs</strong> before you trust an &ldquo;it's fixed.&rdquo;</li>
        <li>Keep <strong>one canonical source of truth</strong> for the physics (shared runners), not scattered notebook-local copies that quietly diverge.</li>
      </ol>
    </section>
    <section class="band" aria-labelledby="risks-heading">
      <h2 id="risks-heading">Risks and bad habits</h2>
      <div class="reflection-grid">
        <article class="reflection-card accent">
          <h3>Productivity can become laziness</h3>
          <p>Short prompts are efficient, but they <em>erode writing discipline</em>. The model tolerates rough text while the human slowly loses <strong>precision, grammar, and polish</strong>.</p>
        </article>
        <article class="reflection-card teal">
          <h3>Learning can become too filtered</h3>
          <p>When most explanations come from an LLM window, awareness of <strong>cited, reviewed, trustworthy sources</strong> weakens. Scientific work still needs <em>external references</em>.</p>
        </article>
        <article class="reflection-card accent">
          <h3>Confidence without proof</h3>
          <p>LLMs sound certain even when a <em>sign convention, file path, dependency, or physics claim</em> is wrong. <u>Independent verification remains mandatory.</u></p>
        </article>
        <article class="reflection-card teal">
          <h3>Generated artifacts need boundaries</h3>
          <p>Agents happily spawn extra plots, caches, thumbnails, and pages. That only helps when generated output is <strong>controlled and separated</strong> from source.</p>
        </article>
      </div>
    </section>
    <section class="band reflection-split" id="future" aria-labelledby="future-heading">
      <div>
        <h2 id="future-heading">Future improvements</h2>
        <p class="lede">For a future seminar, we would make LLM use <em>more collaborative, more reproducible, and more research-oriented</em> from the start.</p>
      </div>
      <ul class="improvement-list">
        <li>A <strong>shared team plan</strong> (for example Claude Team), provided by a professor or university, would give every student the same project context through <em>persistent workspaces</em>.</li>
        <li>Topics could be <strong>more diverse and more research-oriented</strong> &mdash; ideally to the point where results become <em>publishable</em>.</li>
        <li>Every plot should carry <strong>provenance</strong>: source script, command, parameters, cache inputs, and the slides or notes that depend on it.</li>
        <li><strong>Automatic checks</strong> should verify figures, notes, slides, caches, and web assets <em>before</em> publishing.</li>
        <li>Review prompts should explicitly hunt for <strong>bugs, missing tests, invalid assumptions, and scientific weak points</strong> &mdash; while the student stays responsible for <u>correctness, taste, and final judgment</u>.</li>
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
