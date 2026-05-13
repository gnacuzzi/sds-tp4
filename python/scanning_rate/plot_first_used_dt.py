"""Grafica la media ± std de Δt (primera usada → borde) vs N, una línea por k."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


TITLE_SIZE = 18
LABEL_SIZE = 16
TICK_SIZE = 14
LEGEND_SIZE = 13
FIGSIZE = (10, 6)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="output/first_used_dt.csv")
    parser.add_argument("--output", default="images/first_used_dt_vs_N.png")
    parser.add_argument("--summary-output", default="output/first_used_dt_summary.csv")
    parser.add_argument("--logy", action="store_true")
    return parser.parse_args()


def read_samples(path):
    samples = []
    with Path(path).open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get("dt_used_to_wall", "NA")
            if raw in (None, "", "NA"):
                continue
            try:
                k = float(row["k"])
                n = int(float(row["N"]))
                dt = float(raw)
            except (KeyError, ValueError):
                continue
            samples.append((k, n, dt))
    return samples


def main():
    args = parse_args()
    samples = read_samples(args.input)
    if not samples:
        raise SystemExit(f"No valid samples found in {args.input}")

    groups = defaultdict(list)
    for k, n, dt in samples:
        groups[(k, n)].append(dt)

    summary = {}
    for (k, n), vals in groups.items():
        arr = np.array(vals)
        summary[(k, n)] = {
            "n_samples": len(arr),
            "mean_dt": float(arr.mean()),
            "std_dt": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
        }

    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["k", "N", "n_samples", "mean_dt", "std_dt"])
        for (k, n), s in sorted(summary.items()):
            writer.writerow([k, n, s["n_samples"], f"{s['mean_dt']:.9f}", f"{s['std_dt']:.9f}"])

    expected_runs = max(s["n_samples"] for s in summary.values())
    incomplete = [(k, n, s["n_samples"]) for (k, n), s in summary.items()
                  if s["n_samples"] < expected_runs]
    if incomplete:
        print("WARNING: (k, N) pairs with fewer samples than the max — possibly tf too short:")
        for k, n, count in sorted(incomplete):
            print(f"  k={k:g} N={n}: {count}/{expected_runs} samples with a wall hit")

    ks = sorted({k for (k, _) in summary})
    fig, ax = plt.subplots(figsize=FIGSIZE)
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(ks)))

    for color, k in zip(colors, ks):
        pairs = sorted((n, summary[(k, n)]) for n in {nn for (kk, nn) in summary if kk == k})
        ns = [n for n, _ in pairs]
        means = [s["mean_dt"] for _, s in pairs]
        stds = [s["std_dt"] for _, s in pairs]
        ax.errorbar(
            ns, means, yerr=stds,
            marker="o", capsize=4, linewidth=1.6,
            color=color, label=f"k = {k:g}",
        )

    ax.set_xlabel("N (número de partículas)", fontsize=LABEL_SIZE)
    ax.set_ylabel(r"$\Delta t$ (primera usada $\to$ borde) [s]", fontsize=LABEL_SIZE)
    ax.set_title(
        "Tiempo de la primera partícula usada hasta alcanzar el borde exterior",
        fontsize=TITLE_SIZE,
    )
    ax.tick_params(axis="both", labelsize=TICK_SIZE)
    if args.logy:
        ax.set_yscale("log")
    ax.legend(title="constante elástica", fontsize=LEGEND_SIZE, title_fontsize=LEGEND_SIZE)
    fig.tight_layout()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    print(f"Saved plot to {out_path}")
    print(f"Saved summary to {summary_path}")


if __name__ == "__main__":
    main()
