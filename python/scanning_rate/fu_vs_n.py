import matplotlib.pyplot as plt
import numpy as np
import os

# ── Configuration ──────────────────────────────────────────────────────────────

OUTPUT_DIR = "output"
N_VALUES   = [50, 100, 200, 300, 400, 500, 600, 700, 800]
N_RUNS     = 10
T_CUT_50 = 0
T_CUT_100 = 100.0
T_CUT_200 = 250.0
T_CUT_300 = 800.0
T_CUT_400 = 900.0
T_CUT_500 = 1000.0
T_CUT_600 = 1250.0
T_CUT_700 = 1400.0
T_CUT_800 = 1500.0

# Figure
FIG_SIZE   = (10, 6)
DPI        = 300

# Font sizes
FONT_TITLE  = 18
FONT_LABELS = 16
FONT_TICKS  = 14

# Style
MARKER      = "o"
MARKER_SIZE = 7
LINE_WIDTH  = 1.5
COLOR       = "#457b9d"
ECOLOR      = "#d16860"
CAP_SIZE    = 5

# Labels
TITLE   = "Fracción de partículas usadas en función de N"
X_LABEL = "N (número de partículas)"
Y_LABEL = r"$F_u(N)$"

SAVE_PATH = "images/fu_vs_n.png"

# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_fu(path: str):
    times, fus = [], []
    with open(path) as f:
        for line in f:
            parts = line.split()
            times.append(float(parts[1]))
            fus.append(float(parts[-1]))
    return times, fus


def collect_fu_after_cut(n: int) -> np.ndarray:
    all_fus = []
    for i in range(N_RUNS):
        path = os.path.join(OUTPUT_DIR, f"{n}_events{i}.txt")
        if not os.path.isfile(path):
            print(f"  WARNING: {path} not found, skipping")
            continue
        times, fus = parse_fu(path)
        tcut = T_CUT_50
        if(n == 50):
            tcut = T_CUT_50
        elif(n == 100):
            tcut = T_CUT_100
        elif(n == 200):
            tcut = T_CUT_200
        elif(n == 300):
            tcut = T_CUT_300
        elif(n == 400):
            tcut = T_CUT_400
        elif(n == 500):
            tcut = T_CUT_500
        elif(n == 600):
            tcut = T_CUT_600
        elif(n == 700):
            tcut = T_CUT_700
        elif(n == 800):
            tcut = T_CUT_800
        cut_fus = [f for t, f in zip(times, fus) if t > tcut]
        all_fus.extend(cut_fus)
    return np.array(all_fus)

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    means, stds = [], []

    for n in N_VALUES:
        print(f"Processing N = {n} ...")
        fu_arr = collect_fu_after_cut(n)
        if len(fu_arr) == 0:
            print(f"  No data for N = {n}")
            means.append(np.nan)
            stds.append(np.nan)
            continue
        m, s = np.mean(fu_arr), np.std(fu_arr)
        means.append(m)
        stds.append(s)
        print(f"  mean = {m:.6f}  std = {s:.6f}  samples = {len(fu_arr)}")

    means = np.array(means)
    stds  = np.array(stds)

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    ax.errorbar(
        N_VALUES, means, yerr=stds,
        fmt="-" + MARKER,
        markersize=MARKER_SIZE,
        linewidth=LINE_WIDTH,
        color=COLOR,
        # ecolor=ECOLOR,
        elinewidth=1.5,
        capsize=CAP_SIZE,
        capthick=1.2,
        label="fu ± σ",
    )

    # ax.set_title(TITLE, fontsize=FONT_TITLE)
    ax.set_xlabel(X_LABEL, fontsize=FONT_LABELS)
    ax.set_ylabel(Y_LABEL, fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    ax.set_xticks(N_VALUES)
    # ax.legend(fontsize=FONT_TICKS)

    fig.tight_layout()

    if SAVE_PATH:
        fig.savefig(SAVE_PATH, dpi=DPI)
        print(f"\nSaved to {SAVE_PATH}")

    plt.show()


if __name__ == "__main__":
    main()
