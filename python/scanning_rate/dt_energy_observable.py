import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from python.plot_format import apply_scientific_y


DEFAULT_INPUT_DIR = Path("output/dt_observable_N1000")
DEFAULT_IMAGE_DIR = Path("images/dt_observable_N1000")
DEFAULT_SUMMARY = Path("output/dt_observable_N1000/dt_energy_observable_summary.csv")

FONT_LABELS = 16
FONT_TICKS = 13
FONT_LEGEND = 12
DPI = 300


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute an energy-error observable versus dt from multiple energy runs."
    )
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Directory with *_energy_dt*_run*.txt files.")
    parser.add_argument("--image-dir", default=str(DEFAULT_IMAGE_DIR), help="Directory for output plots.")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="CSV summary output path.")
    parser.add_argument("--n", type=int, default=1000, help="Particle count used in the file names.")
    parser.add_argument(
        "--metric",
        choices=["mse", "mae", "max", "slope"],
        default="mse",
        help=(
            "Observable: mse = mean(relative energy error^2), "
            "mae = mean(abs(relative energy error)), "
            "max = max(abs(relative energy error)), "
            "slope = abs(linear slope of relative energy error vs time)."
        ),
    )
    parser.add_argument(
        "--also-mae",
        action="store_true",
        help="Also write a MAE plot when --metric mse is selected.",
    )
    parser.add_argument("--t-min", type=float, default=None, help="Minimum time included in the observable.")
    parser.add_argument("--t-max", type=float, default=None, help="Maximum time included in the observable.")
    parser.add_argument("--dts", type=float, nargs="+", default=None, help="Only include these dt values.")
    parser.add_argument("--exclude-dts", type=float, nargs="+", default=None, help="Exclude these dt values.")
    parser.add_argument("--no-title", action="store_true", help="Do not show the N title above the plot.")

    return parser.parse_args()


def dt_from_label(label):
    return float(label.replace("p", "."))


def discover_energy_files(input_dir: Path, n_value: int):
    pattern = re.compile(rf"{n_value}_energy_dt(?P<dt>[0-9p]+)_run(?P<run>\d+)\.txt$")
    files = []

    for path in input_dir.glob(f"{n_value}_energy_dt*_run*.txt"):
        match = pattern.match(path.name)
        if match:
            files.append((dt_from_label(match.group("dt")), int(match.group("run")), path))

    return sorted(files, key=lambda item: (item[0], item[1]))


def filter_dt_values(files, include_dts, exclude_dts):
    if include_dts is not None:
        include = set(include_dts)
        files = [item for item in files if item[0] in include]

    if exclude_dts is not None:
        exclude = set(exclude_dts)
        files = [item for item in files if item[0] not in exclude]

    return files


def load_relative_error(path: Path, t_min, t_max):
    data = np.loadtxt(path, skiprows=1)
    if data.ndim != 2 or data.shape[1] < 6:
        raise ValueError(f"Invalid energy file format: {path}")

    t = data[:, 0]
    energy = data[:, 5]
    mask = np.ones_like(t, dtype=bool)

    if t_min is not None:
        mask &= t >= t_min
    if t_max is not None:
        mask &= t <= t_max

    if np.count_nonzero(mask) < 2:
        raise ValueError(f"Not enough samples in selected time interval: {path}")

    selected_energy = energy[mask]
    e0 = energy[0]
    rel = (selected_energy - e0) / e0

    return t[mask], rel, e0, energy[-1]


def compute_metric(t, rel, metric):
    if metric == "mse":
        return float(np.mean(rel ** 2))
    if metric == "mae":
        return float(np.mean(np.abs(rel)))
    if metric == "max":
        return float(np.max(np.abs(rel)))
    if metric == "slope":
        slope, _ = np.polyfit(t, rel, deg=1)
        return float(abs(slope))
    raise ValueError(f"Unknown metric: {metric}")


def compute_rows(files, metric, t_min, t_max):
    by_dt = defaultdict(list)
    per_run_rows = []

    for dt, run_id, path in files:
        t, rel, e0, e_final = load_relative_error(path, t_min, t_max)
        observable = compute_metric(t, rel, metric)
        max_abs = float(np.max(np.abs(rel)))
        final_drift = float((e_final - e0) / e0)

        by_dt[dt].append(observable)
        per_run_rows.append({
            "dt": dt,
            "run_id": run_id,
            "samples": len(rel),
            "observable": observable,
            "max_abs_relative_error": max_abs,
            "final_relative_drift": final_drift,
            "energy_file": str(path),
        })

    summary_rows = []
    for dt in sorted(by_dt):
        values = np.array(by_dt[dt], dtype=float)
        ddof = 1 if len(values) > 1 else 0
        summary_rows.append({
            "dt": dt,
            "mean": float(np.mean(values)),
            "std": float(np.std(values, ddof=ddof)),
            "runs": len(values),
        })

    return summary_rows, per_run_rows


def write_summary(path: Path, metric, summary_rows, per_run_rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "section", "dt", "run_id", "value", "std", "runs", "samples", "max_abs_relative_error", "final_relative_drift", "energy_file"])

        for row in summary_rows:
            writer.writerow([
                metric,
                "summary",
                f"{row['dt']:.12g}",
                "",
                f"{row['mean']:.12e}",
                f"{row['std']:.12e}",
                row["runs"],
                "",
                "",
                "",
                "",
            ])

        for row in per_run_rows:
            writer.writerow([
                metric,
                "run",
                f"{row['dt']:.12g}",
                row["run_id"],
                f"{row['observable']:.12e}",
                "",
                "",
                row["samples"],
                f"{row['max_abs_relative_error']:.12e}",
                f"{row['final_relative_drift']:.12e}",
                row["energy_file"],
            ])


def plot_summary(summary_rows, metric, image_dir: Path, n_value: int, show_title: bool):
    dts = np.array([row["dt"] for row in summary_rows], dtype=float)
    means = np.array([row["mean"] for row in summary_rows], dtype=float)
    stds = np.array([row["std"] for row in summary_rows], dtype=float)

    order = np.argsort(dts)
    dts = dts[order]
    means = means[order]
    stds = stds[order]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(dts, means, yerr=stds, marker="o", linestyle="-", capsize=5, linewidth=2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("dt (s)", fontsize=FONT_LABELS)

    if metric == "mse":
        ylabel = r"$\langle \mathrm{ECM}_E \rangle$"
    elif metric == "mae":
        ylabel = r"$\langle |\Delta E/E_0| \rangle$"
    else:
        ylabel = r"$\langle \max_t |\Delta E/E_0| \rangle$"
    if metric == "slope":
        ylabel = r"$\langle |d(\Delta E/E_0)/dt| \rangle$"

    ax.set_ylabel(ylabel, fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    if show_title:
        ax.set_title(f"N = {n_value}", fontsize=FONT_LABELS)
    apply_scientific_y(ax, fontsize=FONT_TICKS)
    fig.tight_layout()

    image_dir.mkdir(parents=True, exist_ok=True)
    output_path = image_dir / f"dt_energy_observable_{metric}_N{n_value}.png"
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return output_path


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    image_dir = Path(args.image_dir)
    summary_path = Path(args.summary)
    files = discover_energy_files(input_dir, args.n)
    files = filter_dt_values(files, args.dts, args.exclude_dts)

    if not files:
        raise SystemExit(f"No energy files found in {input_dir} for N={args.n}")

    metrics = [args.metric]
    if args.metric == "mse" and args.also_mae:
        metrics.append("mae")

    for metric in metrics:
        summary_rows, per_run_rows = compute_rows(files, metric, args.t_min, args.t_max)
        metric_summary_path = summary_path
        if len(metrics) > 1:
            metric_summary_path = summary_path.with_name(f"{summary_path.stem}_{metric}{summary_path.suffix}")

        write_summary(metric_summary_path, metric, summary_rows, per_run_rows)
        plot_path = plot_summary(summary_rows, metric, image_dir, args.n, not args.no_title)

        print(f"Metric: {metric}")
        print(f"Summary written to {metric_summary_path}")
        print(f"Saved {plot_path}")


if __name__ == "__main__":
    main()
