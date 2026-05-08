import matplotlib.pyplot as plt
import numpy as np
import sys
import os

# ── Configuration ──────────────────────────────────────────────────────────────

N_VALUE = 300

INPUT_FILES = [
    f"output/{N_VALUE}_cfc0.txt",
    f"output/{N_VALUE}_cfc1.txt",
    f"output/{N_VALUE}_cfc2.txt",
    f"output/{N_VALUE}_cfc3.txt",
    f"output/{N_VALUE}_cfc4.txt",
    f"output/{N_VALUE}_cfc5.txt",
    f"output/{N_VALUE}_cfc6.txt",
    f"output/{N_VALUE}_cfc7.txt",
    f"output/{N_VALUE}_cfc8.txt",
    f"output/{N_VALUE}_cfc9.txt",
]

# Figure
FIG_SIZE   = (10, 6)   # (width, height) in inches
DPI        = 300

# Font sizes
FONT_TITLE  = 16
FONT_LABELS = 14
FONT_TICKS  = 12
FONT_LEGEND = 12

# Colors — one per file; cycles if more files than colors
COLORS = ["#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261"]

# Line / marker style
LINE_STYLE  = "-"
LINE_WIDTH  = 1.5
MARKER      = "o"
MARKER_SIZE = 3

# Axes limits — set to None for auto
X_MIN, X_MAX = None, None
Y_MIN, Y_MAX = None, None

# Tick intervals — set to None for auto
X_TICK_INTERVAL = None   # e.g. 0.5
Y_TICK_INTERVAL = None   # e.g. 0.1

# Labels
TITLE   = "Fracción de partículas usadas en función del tiempo"
X_LABEL = "Tiempo (s)"
Y_LABEL = r"$F_u(t)$"

# Cut-off: discard the first T_CUT seconds of each file
# T_CUT = 200.0 para 100
# T_CUT = 200.0 para 200
T_CUT = 500.0
# T_CUT = 500.0 para 400
# T_CUT = 700.0 para 500

# Output — set to None to only display
SAVE_PATH = "images/fu_plot.png"

# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_fu(path: str):
    times, fus = [], []
    with open(path) as f:
        for line in f:
            parts = line.split()
            times.append(float(parts[1]))
            fus.append(float(parts[-1]))
    return times, fus


def make_label(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    files = sys.argv[1:] if len(sys.argv) > 1 else INPUT_FILES

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    all_fus = []
    time_offset = 0.0
    for i, path in enumerate(files):
        color = COLORS[i % len(COLORS)]
        times, fus = parse_fu(path)

        cut_times = [t for t in times if t > T_CUT]
        cut_fus   = [f for t, f in zip(times, fus) if t > T_CUT]

        t0 = cut_times[0] if cut_times else 0.0
        shifted = [t - t0 + time_offset for t in cut_times]

        all_fus.extend(cut_fus)

        ax.plot(
            shifted, cut_fus,
            label=make_label(path),
            color=color,
            linestyle=LINE_STYLE,
            linewidth=LINE_WIDTH,
            marker=MARKER,
            markersize=MARKER_SIZE,
        )
        if shifted:
            time_offset = shifted[-1]

    fu_arr = np.array(all_fus)
    mean_fu = np.mean(fu_arr)
    std_fu  = np.std(fu_arr)
    print(f"fu (t > {T_CUT}s):  mean = {mean_fu:.6f}  std = {std_fu:.6f}  N = {len(fu_arr)}")

    ax.axhline(mean_fu, color="black", linestyle="--", linewidth=1.2, label=f"media = {mean_fu:.4f}")
    ax.axhspan(mean_fu - std_fu, mean_fu + std_fu, color="gray", alpha=0.15, label=f"±σ = {std_fu:.4f}")

    ax.set_title(TITLE, fontsize=FONT_TITLE)
    ax.set_xlabel(X_LABEL, fontsize=FONT_LABELS)
    ax.set_ylabel(Y_LABEL, fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)

    if X_MIN is not None or X_MAX is not None:
        ax.set_xlim(X_MIN, X_MAX)
    if Y_MIN is not None or Y_MAX is not None:
        ax.set_ylim(Y_MIN, Y_MAX)

    if X_TICK_INTERVAL is not None:
        xlo, xhi = ax.get_xlim()
        ax.set_xticks(np.arange(xlo, xhi + X_TICK_INTERVAL, X_TICK_INTERVAL))
    if Y_TICK_INTERVAL is not None:
        ylo, yhi = ax.get_ylim()
        ax.set_yticks(np.arange(ylo, yhi + Y_TICK_INTERVAL, Y_TICK_INTERVAL))

    # if len(files) > 1:
    #     ax.legend(fontsize=FONT_LEGEND)

    fig.tight_layout()

    if SAVE_PATH:
        fig.savefig(SAVE_PATH, dpi=DPI)
        print(f"Saved to {SAVE_PATH}")

    plt.show()


if __name__ == "__main__":
    main()
