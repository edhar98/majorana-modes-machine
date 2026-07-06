#!/usr/bin/env python
"""Slide-ready overlay of ALL fixed-depth (r=4) edge-string results on one axis:

  * noiseless ideal reference (flat ~0.9)
  * toy depolarizing p_cx=0.05           (L=4..16)   -- washes out
  * real IBM Cairo   27q, 2q err 7.5e-3  (L=4..16)   -- plateaus ~0.5
  * real IBM Brooklyn 65q, 2q err 1.0e-2 (L=6..64)   -- new large-L run
  * real IBM Washington 127q, 2q err 1.1e-2 (L=6..100)

Reads the three committed HPC caches. Legend pinned bottom-left, generous
margins so nothing overflows on the slide.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LARGEL = "plots/block4_largeL_data.npz"           # Brooklyn + Washington, L->100
TOY    = "plots/block4_scaling_data.npz"          # toy depolarizing p=0.05, L<=16
CAIRO  = "plots/block4_scaling_data_FakeCairoV2.npz"  # real Cairo, L<=16
OUT    = "plots/block4_largeL_overlay.pdf"


def main():
    lg = np.load(LARGEL, allow_pickle=True)
    toy = np.load(TOY, allow_pickle=True)
    cai = np.load(CAIRO, allow_pickle=True)

    plt.rcParams.update({"font.size": 13, "axes.linewidth": 0.9})
    fig, ax = plt.subplots(figsize=(7.6, 4.6))

    # --- noiseless reference (VQE r=4 noiseless == exact topological value) -----
    Li, ideal = lg["FakeBrooklynV2__L"], lg["FakeBrooklynV2__ideal"]
    ax.plot(Li, ideal, "--", color="black", lw=1.6, marker="D", ms=4,
            label="Noiseless (ideal $r{=}4$)", zorder=6)

    # --- old L<=16 runs ---------------------------------------------------------
    Ls = toy["L"]
    ax.errorbar(Ls, cai["noisy"], yerr=cai["err"], fmt="o-", color="#2ca02c",
                lw=1.6, ms=4.5, capsize=2, elinewidth=0.8, zorder=5,
                label="Cairo 27q, 2q err 0.75%")
    ax.errorbar(Ls, toy["noisy"], yerr=toy["err"], fmt="v:", color="#7f7f7f",
                lw=1.5, ms=4.5, capsize=2, elinewidth=0.8, zorder=4,
                label="Toy depolarizing $p{=}0.05$")

    # --- new large-L device runs ------------------------------------------------
    for b, mk, col, lab in [
        ("FakeBrooklynV2",   "s", "#1f77b4", "Brooklyn 65q, 2q err 1.0%"),
        ("FakeWashingtonV2", "^", "#d62728", "Washington 127q, 2q err 1.1%"),
    ]:
        L, noisy, err = lg[f"{b}__L"], lg[f"{b}__noisy"], lg[f"{b}__err"]
        ax.errorbar(L, noisy, yerr=err, fmt=mk + "-", color=col, lw=1.6, ms=5,
                    capsize=2, elinewidth=0.8, zorder=5, label=lab)

    ax.set_xlabel("Chain length $L$")
    ax.set_ylabel(r"$|\langle O_{\mathrm{edge}}\rangle|$")
    ax.set_ylim(0.0, 1.0)
    ax.set_xlim(0, 104)
    ax.grid(True, alpha=0.3, lw=0.6)
    ax.legend(loc="upper right", fontsize=9.5, framealpha=0.95,
              handlelength=1.7, borderpad=0.45, labelspacing=0.35)

    fig.tight_layout(pad=0.6)
    fig.savefig(OUT, bbox_inches="tight")
    print(f"[saved] {OUT}")


if __name__ == "__main__":
    main()
