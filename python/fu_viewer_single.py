import matplotlib.pyplot as plt
import numpy as np
import sys
import os

# ── Configuration ──────────────────────────────────────────────────────────────

INPUT_FILE = "output/800_events8.txt"

# Tiempo a partir del cual consideramos el estado estacionario
X_STATIONARY = 1500.0

# Figure
FIG_SIZE = (8, 5)
DPI      = 300

# Font sizes (mismo estilo que radial_profiles.py)
FONT_LABELS = 18
FONT_TICKS  = 14
FONT_LEGEND = 14

# Line / marker style
LINE_COLOR  = "#457b9d"
LINE_STYLE  = "-"
LINE_WIDTH  = 1.2
MARKER      = "o"
MARKER_SIZE = 2

# Labels
X_LABEL = r"Tiempo ($s$)"
Y_LABEL = r"$F_u$($t$)"

# Output — set to None to only display
SAVE_PATH = "images/fu_single.png"

# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_fu(path: str):
    times, fus = [], []
    with open(path) as f:
        for line in f:
            parts = line.split()
            times.append(float(parts[1]))
            fus.append(float(parts[-1]))
    return np.array(times), np.array(fus)

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else INPUT_FILE

    times, fus = parse_fu(path)

    mask = times >= X_STATIONARY
    fus_stat = fus[mask]

    if fus_stat.size > 0:
        mean_fu = float(np.mean(fus_stat))
        std_fu  = float(np.std(fus_stat))
    else:
        mean_fu = float("nan")
        std_fu  = float("nan")

    print(f"{path}")
    print(f"fu (t >= {X_STATIONARY}s):  mean = {mean_fu:.6f}  std = {std_fu:.6f}  N = {fus_stat.size}")

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    ax.plot(
        times, fus,
        color=LINE_COLOR,
        linestyle=LINE_STYLE,
        linewidth=LINE_WIDTH,
        marker=MARKER,
        markersize=MARKER_SIZE,
    )

    ax.axvline(
        X_STATIONARY,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label=rf"$t_{{\mathrm{{estacionario}}}} = {X_STATIONARY:g}\,$s",
    )

    if fus_stat.size > 0:
        ax.plot(
            [X_STATIONARY, times.max()],
            [mean_fu, mean_fu],
            color="#e63946",
            linestyle="-",
            linewidth=1.2,
            label=rf"media = {mean_fu:.4f}",
        )
        # ax.axhspan(
        #     mean_fu - std_fu,
        #     mean_fu + std_fu,
        #     color="gray",
        #     alpha=0.2,
        #     label=rf"$\pm\sigma = {std_fu:.4f}$",
        # )

    ax.set_xlabel(X_LABEL, fontsize=FONT_LABELS)
    ax.set_ylabel(Y_LABEL, fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    ax.set_ylim(0.0, 0.6)

    ax.legend(fontsize=FONT_LEGEND, loc="best")

    fig.tight_layout()

    if SAVE_PATH:
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        fig.savefig(SAVE_PATH, dpi=DPI)
        print(f"Saved to {SAVE_PATH}")

    plt.show()


if __name__ == "__main__":
    main()
