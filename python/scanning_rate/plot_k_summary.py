"""
plot_k_summary.py — TP4 item 2.4 (Plot D)

Reads the summary CSVs written by k_sweep_J.py and k_sweep_radial.py, extracts
characteristic scalars from each curve, and plots them vs k:

  * From <F_u>(N) per k:           max(<F_u>)(k)  and  N* (= argmax over N)
  * From <J_in|_{S~2}>(N) per k:   max value     and  N*

Two plots, twin y-axes:
  Plot D-1: from F_u summary       (max <F_u> on left, N* on right)
  Plot D-2: from radial summary    (max J_in_near on left, N* on right)

This script is read-only over the summary CSVs; re-running it after tweaking the
display is fast and doesn't touch any simulation outputs.
"""

import argparse
import csv
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────

DEFAULT_FU_SUMMARY     = Path("output/k_sweep_J_summary.csv")
DEFAULT_RADIAL_SUMMARY = Path("output/k_sweep_radial_summary.csv")

DEFAULT_FIG_FU_PATH     = Path("images/scanning_rate/k_sweep_summary_fu.png")
DEFAULT_FIG_RADIAL_PATH = Path("images/scanning_rate/k_sweep_summary_radial.png")

FIGSIZE     = (9, 6)
DPI         = 300
LABEL_SIZE  = 16
TICK_SIZE   = 14
LEGEND_SIZE = 13


# ── Summary loading ───────────────────────────────────────────────────────────

def load_summary(path: Path, value_col: str) -> dict[float, dict[int, list[float]]]:
    """{k: {N: [per-run values of value_col]}} ignoring NaNs."""
    out: dict[float, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    if not path.is_file():
        raise FileNotFoundError(f"Summary not found: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                k = float(row["k"])
                N = int(row["N"])
                v = float(row[value_col])
            except (KeyError, ValueError):
                continue
            if np.isnan(v):
                continue
            out[k][N].append(v)
    return out


def per_kN_means(per_kN: dict[float, dict[int, list[float]]]) -> dict[float, dict[int, float]]:
    return {
        k: {N: float(np.mean(values)) for N, values in inner.items() if values}
        for k, inner in per_kN.items()
    }


# ── Scalar extraction ─────────────────────────────────────────────────────────

def extract_max_and_argmax(curve: dict[int, float]) -> tuple[float, int]:
    """For one curve y(N), returns (max_y, argmax_N). Skips NaN."""
    items = [(N, y) for N, y in curve.items() if not np.isnan(y)]
    if not items:
        return float("nan"), -1
    items.sort(key=lambda t: t[0])
    Ns = np.array([t[0] for t in items])
    ys = np.array([t[1] for t in items])
    idx = int(np.argmax(ys))
    return float(ys[idx]), int(Ns[idx])


# ── Plotting ──────────────────────────────────────────────────────────────────

def plot_scalar_vs_k(
    means_per_kN: dict[float, dict[int, float]],
    ylabel_max: str,
    output_path: Path,
    title: str,
) -> None:
    ks = sorted(means_per_kN.keys())
    if not ks:
        print(f"  WARNING: no k values in summary, skipping {output_path}")
        return

    max_values: list[float] = []
    argmax_Ns: list[int] = []
    for k in ks:
        max_y, N_star = extract_max_and_argmax(means_per_kN[k])
        max_values.append(max_y)
        argmax_Ns.append(N_star)

    figure, ax_left = plt.subplots(figsize=FIGSIZE)
    ax_right = ax_left.twinx()

    color_left = "#1d3557"
    color_right = "#e63946"

    ax_left.plot(
        ks, max_values, "-o", color=color_left, linewidth=2.0, markersize=8,
        label=ylabel_max,
    )
    ax_right.plot(
        ks, argmax_Ns, "--s", color=color_right, linewidth=1.6, markersize=8,
        label=r"$N^*$ (argmax)",
    )

    ax_left.set_xscale("log")
    ax_left.set_xlabel(r"$k$ [N/m]", fontsize=LABEL_SIZE)
    ax_left.set_ylabel(ylabel_max, fontsize=LABEL_SIZE, color=color_left)
    ax_right.set_ylabel(r"$N^*$ (argmax)", fontsize=LABEL_SIZE, color=color_right)
    ax_left.tick_params(axis="y", labelcolor=color_left, labelsize=TICK_SIZE)
    ax_right.tick_params(axis="y", labelcolor=color_right, labelsize=TICK_SIZE)
    ax_left.tick_params(axis="x", labelsize=TICK_SIZE)
    ax_left.grid(True, alpha=0.3)

    # Combined legend
    lines_left, labels_left = ax_left.get_legend_handles_labels()
    lines_right, labels_right = ax_right.get_legend_handles_labels()
    ax_left.legend(
        lines_left + lines_right,
        labels_left + labels_right,
        fontsize=LEGEND_SIZE, loc="best",
    )

    ax_left.set_title(title, fontsize=LABEL_SIZE)

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"[Plot D] Saved {output_path}")
    for k, m, n in zip(ks, max_values, argmax_Ns):
        print(f"   k={k:.0e}: max={m:.6e}, N*={n}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TP4 item 2.4: Plot D — scalar-vs-k summary.")
    parser.add_argument("--fu-summary", default=str(DEFAULT_FU_SUMMARY),
                        help="CSV from k_sweep_J.py")
    parser.add_argument("--radial-summary", default=str(DEFAULT_RADIAL_SUMMARY),
                        help="CSV from k_sweep_radial.py")
    parser.add_argument("--fig-fu", default=str(DEFAULT_FIG_FU_PATH))
    parser.add_argument("--fig-radial", default=str(DEFAULT_FIG_RADIAL_PATH))
    parser.add_argument("--skip-fu", action="store_true")
    parser.add_argument("--skip-radial", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.skip_fu:
        try:
            fu_per_kN = load_summary(Path(args.fu_summary), "mean_fu")
            fu_means = per_kN_means(fu_per_kN)
            plot_scalar_vs_k(
                fu_means,
                ylabel_max=r"$\max_N \langle F_u \rangle$",
                output_path=Path(args.fig_fu),
                title=r"Resumen k-sweep: $\langle F_u \rangle$",
            )
        except FileNotFoundError as exc:
            print(f"  Skipping F_u plot: {exc}")
    else:
        print("Skipped F_u summary plot (--skip-fu).")

    if not args.skip_radial:
        try:
            radial_per_kN = load_summary(Path(args.radial_summary), "J_in_near")
            radial_means = per_kN_means(radial_per_kN)
            plot_scalar_vs_k(
                radial_means,
                ylabel_max=r"$\max_N \langle J_{in}|_{S \sim 2} \rangle$",
                output_path=Path(args.fig_radial),
                title=r"Resumen k-sweep: $\langle J_{in}|_{S \sim 2} \rangle$",
            )
        except FileNotFoundError as exc:
            print(f"  Skipping radial plot: {exc}")
    else:
        print("Skipped radial summary plot (--skip-radial).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
