"""
plot_jin_vs_N.py

Reads radial_vs_N_tp4.csv from a list of per-k folders and overlays
<J_in>(N) curves, one per k, with error bars.

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
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────

# One folder per k value. Order matters — the colormap maps low-to-high.
FOLDERS = [
    ("output/radial_k10",    10),
    ("output/radial_k100",   100),
    ("output/radial_k1000",  1000),
    ("output/radial_k10000", 10000),
]

# Same filename in every folder.
FILENAME = "radial_vs_N_tp4.csv"

# Output figure.
OUTPUT_PATH = Path("images/scanning_rate/jin_vs_N_kSweep.png")

# Visual style.
FIGSIZE     = (10, 6)
DPI         = 300
LABEL_SIZE  = 16
TICK_SIZE   = 14


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_jin(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (N_array, jin_mean_array, jin_std_array), sorted by N."""
    Ns: list[int] = []
    means: list[float] = []
    stds: list[float] = []
    with path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                Ns.append(int(row["N"]))
                means.append(float(row["jin_mean"]))
                stds.append(float(row["jin_std"]))
            except (KeyError, ValueError):
                continue
    order = np.argsort(Ns)
    return (
        np.array(Ns, dtype=int)[order],
        np.array(means, dtype=float)[order],
        np.array(stds, dtype=float)[order],
    )


def k_label(k: int) -> str:
    """100 -> 'k = 10²'."""
    superscripts = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
    return f"k = 10{str(int(round(np.log10(k)))).translate(superscripts)}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    figure, axis = plt.subplots(figsize=FIGSIZE)

    log_ks = np.array([np.log10(k) for _, k in FOLDERS], dtype=float)
    norm = mcolors.Normalize(vmin=log_ks.min(), vmax=log_ks.max())
    cmap = plt.get_cmap("viridis")

    plotted_any = False
    for folder, k in FOLDERS:
        path = Path(folder) / FILENAME
        if not path.is_file():
            print(f"  MISSING: {path}")
            continue

        Ns, means, stds = load_jin(path)
        if Ns.size == 0:
            print(f"  EMPTY: {path}")
            continue

        color = cmap(norm(np.log10(k)))
        axis.errorbar(
            Ns, means, yerr=stds,
            fmt="-o", markersize=7, linewidth=1.8,
            color=color, ecolor=color, elinewidth=1.2, capsize=4,
            label=k_label(k),
        )
        plotted_any = True
        print(f"  {k_label(k)}: {Ns.size} N values, "
              f"J_in range [{means.min():.3e}, {means.max():.3e}]")

    if not plotted_any:
        print("No data plotted; check folder paths.")
        return 1

    axis.set_xlabel("N (número de partículas)", fontsize=LABEL_SIZE)
    axis.set_ylabel(r"$\langle J_{in} \rangle$", fontsize=LABEL_SIZE)
    axis.tick_params(axis="both", labelsize=TICK_SIZE)
    axis.grid(False)

    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = figure.colorbar(sm, ax=axis, pad=0.02)
    cbar.set_label(r"$\log_{10}(k)$ [N/m]", fontsize=LABEL_SIZE - 2)
    cbar.ax.tick_params(labelsize=TICK_SIZE - 2)

    figure.tight_layout()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_PATH, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"\nSaved {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())