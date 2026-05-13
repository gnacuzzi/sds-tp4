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


def main():
    args = parse_args()
    tp3_rows = read_rows(args.tp3_csv)
    tp4_rows = read_rows(args.tp4_csv)

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

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(right=0.74)
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
