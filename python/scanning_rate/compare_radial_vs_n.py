import argparse
import csv
from pathlib import Path
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from python.plot_format import apply_scientific_y


TP3_CSV = Path("output/radial_vs_N_tp3.csv")
TP4_CSV = Path("output/radial_vs_N_tp4.csv")
OUTPUT_PATH = Path("images/radial_vs_N/radial_vs_N_tp3_tp4_multiscale.png")

FONT_LABELS = 16
FONT_TICKS = 13
FONT_LEGEND = 10
DPI = 300


def parse_args():
    parser = argparse.ArgumentParser(description="Compare radial-vs-N observables between TP3 and TP4.")
    parser.add_argument("--tp3-csv", default=str(TP3_CSV), help="TP3 radial_vs_N CSV.")
    parser.add_argument("--tp4-csv", default=str(TP4_CSV), help="TP4 radial_vs_N CSV.")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output image path.")
    parser.add_argument(
        "--metric",
        choices=["all", "rho", "velocity", "jin"],
        default="all",
        help="Observable to plot. Default: all.",
    )

    return parser.parse_args()


def read_rows(path):
    rows = []

    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            rows.append({
                "dataset": row["dataset"],
                "N": int(row["N"]),
                "rho_mean": float(row["rho_mean"]),
                "rho_std": float(row["rho_std"]),
                "v_abs_mean": float(row["v_abs_mean"]),
                "v_abs_std": float(row["v_abs_std"]),
                "jin_mean": float(row["jin_mean"]),
                "jin_std": float(row["jin_std"]),
            })

    return sorted(rows, key=lambda row: row["N"])


def values(rows, key):
    return np.array([row[key] for row in rows], dtype=float)


def plot_metric(ax, rows, mean_key, std_key, label, color, marker, linestyle):
    ns = values(rows, "N")
    means = values(rows, mean_key)
    stds = values(rows, std_key)

    return ax.errorbar(
        ns,
        means,
        yerr=stds,
        marker=marker,
        linestyle=linestyle,
        linewidth=2,
        capsize=4,
        color=color,
        label=label,
    )


def plot_single_metric(tp3_rows, tp4_rows, metric, output_path):
    metrics = {
        "rho": (
            "rho_mean",
            "rho_std",
            r"$\langle \rho_f^{\mathrm{in}}\rangle$",
            "tab:blue",
        ),
        "velocity": (
            "v_abs_mean",
            "v_abs_std",
            r"$|\langle v_f^{\mathrm{in}}\rangle|$",
            "tab:orange",
        ),
        "jin": (
            "jin_mean",
            "jin_std",
            r"$J_{\mathrm{in}}$",
            "tab:green",
        ),
    }
    mean_key, std_key, ylabel, color = metrics[metric]

    fig, ax = plt.subplots(figsize=(8, 5))
    plot_metric(ax, tp3_rows, mean_key, std_key, "TP3", "tab:orange", "o", "--")
    plot_metric(ax, tp4_rows, mean_key, std_key, "TP4", "tab:blue", "s", "-")

    ax.set_xlabel("Número de partículas (N)", fontsize=FONT_LABELS)
    ax.set_ylabel(ylabel, fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    apply_scientific_y(ax, fontsize=FONT_TICKS)
    ax.legend(fontsize=FONT_LEGEND, loc="best")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main():
    args = parse_args()
    tp3_rows = read_rows(args.tp3_csv)
    tp4_rows = read_rows(args.tp4_csv)
    output_path = Path(args.output)

    if args.metric != "all":
        plot_single_metric(tp3_rows, tp4_rows, args.metric, output_path)
        print(f"Saved {output_path}")
        return

    fig, ax_rho = plt.subplots(figsize=(11.5, 6.0))
    ax_v = ax_rho.twinx()
    ax_j = ax_rho.twinx()
    ax_j.spines["right"].set_position(("axes", 1.25))

    handles = []
    handles.append(
        plot_metric(
            ax_rho,
            tp3_rows,
            "rho_mean",
            "rho_std",
            r"TP3 $\langle \rho_f^{\mathrm{in}}\rangle$",
            "tab:blue",
            "o",
            "-",
        )
    )
    handles.append(
        plot_metric(
            ax_rho,
            tp4_rows,
            "rho_mean",
            "rho_std",
            r"TP4 $\langle \rho_f^{\mathrm{in}}\rangle$",
            "tab:blue",
            "s",
            "--",
        )
    )
    handles.append(
        plot_metric(
            ax_v,
            tp3_rows,
            "v_abs_mean",
            "v_abs_std",
            r"TP3 $|\langle v_f^{\mathrm{in}}\rangle|$",
            "tab:orange",
            "o",
            "-",
        )
    )
    handles.append(
        plot_metric(
            ax_v,
            tp4_rows,
            "v_abs_mean",
            "v_abs_std",
            r"TP4 $|\langle v_f^{\mathrm{in}}\rangle|$",
            "tab:orange",
            "s",
            "--",
        )
    )
    handles.append(
        plot_metric(
            ax_j,
            tp3_rows,
            "jin_mean",
            "jin_std",
            r"TP3 $J_{\mathrm{in}}$",
            "tab:green",
            "o",
            "-",
        )
    )
    handles.append(
        plot_metric(
            ax_j,
            tp4_rows,
            "jin_mean",
            "jin_std",
            r"TP4 $J_{\mathrm{in}}$",
            "tab:green",
            "s",
            "--",
        )
    )

    ax_rho.set_xlabel("Número de partículas (N)", fontsize=FONT_LABELS)
    ax_rho.set_ylabel(r"$\langle \rho_f^{\mathrm{in}}\rangle$", color="tab:blue", fontsize=FONT_LABELS, labelpad=8)
    ax_v.set_ylabel(r"$|\langle v_f^{\mathrm{in}}\rangle|$", color="tab:orange", fontsize=FONT_LABELS, labelpad=8)
    ax_j.set_ylabel(r"$J_{\mathrm{in}}$", color="tab:green", fontsize=FONT_LABELS, labelpad=14)

    ax_rho.tick_params(axis="x", labelsize=FONT_TICKS)
    ax_rho.tick_params(axis="y", labelcolor="tab:blue", labelsize=FONT_TICKS)
    ax_v.tick_params(axis="y", labelcolor="tab:orange", labelsize=FONT_TICKS)
    ax_j.tick_params(axis="y", labelcolor="tab:green", labelsize=FONT_TICKS)
    apply_scientific_y(ax_rho, ax_v, ax_j, fontsize=FONT_TICKS)

    legend_handles = [handle.lines[0] for handle in handles]
    legend_labels = [handle.get_label() for handle in handles]
    ax_rho.legend(legend_handles, legend_labels, fontsize=FONT_LEGEND, loc="upper left")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(right=0.74)
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
