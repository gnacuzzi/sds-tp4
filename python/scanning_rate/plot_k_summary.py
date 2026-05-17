"""
plot_jin_summary_vs_k.py

Reads radial_vs_N_tp4.csv from a list of per-k folders, extracts two scalars
from each curve, and plots them vs k:

  * max <J_in>(k)  — peak value of the curve
  * N*(k)          — N at which the peak occurs (argmax)

Two scalars share one figure via twin y-axes.

Edit FOLDERS and FILENAME at the top to point at your data.
"""

import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────

# One folder per k value. Same convention as plot_jin_vs_N.py.
FOLDERS = [
    ("output/radial_k10",    10),
    ("output/radial_k100",   100),
    ("output/radial_k1000",  1000),
    ("output/radial_k10000", 10000),
]

# Same filename in every folder.
FILENAME = "radial_vs_N_tp4.csv"

# Output figure.
OUTPUT_PATH = Path("images/scanning_rate/jin_summary_vs_k.png")

# Visual style.
FIGSIZE     = (9, 6)
DPI         = 300
LABEL_SIZE  = 16
TICK_SIZE   = 14
LEGEND_SIZE = 13


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_jin(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Returns (N_array, jin_mean_array), sorted by N."""
    Ns: list[int] = []
    means: list[float] = []
    with path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                Ns.append(int(row["N"]))
                means.append(float(row["jin_mean"]))
            except (KeyError, ValueError):
                continue
    order = np.argsort(Ns)
    return (
        np.array(Ns, dtype=int)[order],
        np.array(means, dtype=float)[order],
    )


def peak_and_argmax(Ns: np.ndarray, means: np.ndarray) -> tuple[float, int]:
    """Returns (max value, N at argmax). NaN-safe."""
    if Ns.size == 0:
        return float("nan"), -1
    valid = ~np.isnan(means)
    if not np.any(valid):
        return float("nan"), -1
    idx = int(np.argmax(means[valid]))
    Ns_valid = Ns[valid]
    means_valid = means[valid]
    return float(means_valid[idx]), int(Ns_valid[idx])


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ks: list[int] = []
    max_jins: list[float] = []
    N_stars: list[int] = []

    for folder, k in FOLDERS:
        path = Path(folder) / FILENAME
        if not path.is_file():
            print(f"  MISSING: {path}")
            continue

        Ns, means = load_jin(path)
        if Ns.size == 0:
            print(f"  EMPTY: {path}")
            continue

        max_jin, N_star = peak_and_argmax(Ns, means)
        if np.isnan(max_jin):
            print(f"  NO VALID DATA: {path}")
            continue

        ks.append(k)
        max_jins.append(max_jin)
        N_stars.append(N_star)
        print(f"  k = {k:>6}: max<J_in> = {max_jin:.4e}, N* = {N_star}")

    if not ks:
        print("No data plotted; check folder paths.")
        return 1

    figure, ax_left = plt.subplots(figsize=FIGSIZE)
    ax_right = ax_left.twinx()

    color_left = "#1f77b4"   # blue
    color_right = "#ff7f0e"  # orange

    ax_left.plot(
        ks, max_jins, "-o",
        color=color_left, linewidth=2.0, markersize=9,
        label=r"$\max_N \langle J_{in} \rangle$",
    )
    ax_right.plot(
        ks, N_stars, "--s",
        color=color_right, linewidth=1.6, markersize=9,
        label=r"$N^*$",
    )

    ax_left.set_xscale("log")
    ax_left.set_xlabel(r"$k$ [N/m]", fontsize=LABEL_SIZE)
    ax_left.set_ylabel(
        r"$\max_N \langle J_{in} \rangle$",
        fontsize=LABEL_SIZE, color=color_left,
    )
    ax_right.set_ylabel(
        r"$N^*$ (argmax)",
        fontsize=LABEL_SIZE, color=color_right,
    )
    ax_left.tick_params(axis="y", labelcolor=color_left, labelsize=TICK_SIZE)
    ax_right.tick_params(axis="y", labelcolor=color_right, labelsize=TICK_SIZE)
    ax_left.tick_params(axis="x", labelsize=TICK_SIZE)
    ax_left.grid(False)

    # Combined legend across both axes.
    lines_left, labels_left = ax_left.get_legend_handles_labels()
    lines_right, labels_right = ax_right.get_legend_handles_labels()
    ax_left.legend(
        lines_left + lines_right,
        labels_left + labels_right,
        fontsize=LEGEND_SIZE, loc="best",
    )

    figure.tight_layout()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_PATH, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"\nSaved {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())