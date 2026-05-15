import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))


FONT_LABELS = 15
FONT_TICKS = 12
FONT_TITLE = 13
DPI = 300


def parse_args():
    parser = argparse.ArgumentParser(
        description="Show relative-energy time series and fitted drift slopes for each dt."
    )
    parser.add_argument("--input-dir", required=True, help="Directory with <N>_energy_dt*_run*.txt files.")
    parser.add_argument("--image-dir", required=True, help="Directory where the plot is written.")
    parser.add_argument("--output", default=None, help="Output image path.")
    parser.add_argument("--n", type=int, default=1000, help="Particle count in file names.")
    parser.add_argument("--dts", type=float, nargs="+", default=None, help="dt values to include.")
    parser.add_argument("--run-id", type=int, default=0, help="Realization shown in each panel. Default: 0.")
    parser.add_argument("--t-max", type=float, default=None, help="Maximum time included.")
    return parser.parse_args()


def dt_from_label(label):
    return float(label.replace("p", "."))


def discover_files(input_dir: Path, n_value: int):
    pattern = re.compile(rf"{n_value}_energy_dt(?P<dt>[0-9p]+)_run(?P<run>\d+)\.txt$")
    files = []

    for path in input_dir.glob(f"{n_value}_energy_dt*_run*.txt"):
        match = pattern.match(path.name)
        if match:
            files.append((dt_from_label(match.group("dt")), int(match.group("run")), path))

    return sorted(files, key=lambda item: (item[0], item[1]))


def load_relative_energy(path: Path, t_max=None):
    data = np.loadtxt(path, skiprows=1)
    if data.ndim != 2 or data.shape[1] < 6:
        raise ValueError(f"Invalid energy file: {path}")

    t = data[:, 0]
    energy = data[:, 5]
    e0 = energy[0]
    rel = (energy - e0) / e0
    mask = np.isfinite(t) & np.isfinite(rel)

    if t_max is not None:
        mask &= t <= t_max

    return t[mask], rel[mask]


def collect_selected(files, include_dts, run_id, t_max):
    include = set(include_dts) if include_dts is not None else None
    selected = {}

    for dt, current_run_id, path in files:
        if include is not None and dt not in include:
            continue
        if current_run_id != run_id:
            continue

        t, rel = load_relative_energy(path, t_max=t_max)
        if len(t) < 2:
            print(f"Skipping {path}: not enough finite samples")
            continue

        selected[dt] = (t, rel, path)

    return dict(sorted(selected.items()))


def collect_slope_stats(files, include_dts, t_max):
    include = set(include_dts) if include_dts is not None else None
    by_dt = defaultdict(list)

    for dt, _, path in files:
        if include is not None and dt not in include:
            continue

        t, rel = load_relative_energy(path, t_max=t_max)
        if len(t) < 2:
            continue

        slope, _ = np.polyfit(t, rel, deg=1)
        by_dt[dt].append(abs(float(slope)))

    stats = {}
    for dt, values in by_dt.items():
        arr = np.array(values, dtype=float)
        stats[dt] = (
            float(np.mean(arr)),
            float(np.std(arr, ddof=1 if len(arr) > 1 else 0)),
            len(arr),
        )

    return stats


def plot(selected, stats, image_path: Path, run_id):
    dts = sorted(selected)
    cols = 2
    rows = int(np.ceil(len(dts) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(11, 3.5 * rows), squeeze=False)
    axes_flat = axes.ravel()

    for ax, dt in zip(axes_flat, dts):
        t, rel, _ = selected[dt]
        slope, intercept = np.polyfit(t, rel, deg=1)
        fit = slope * t + intercept
        mean_slope, std_slope, runs = stats.get(dt, (abs(float(slope)), 0.0, 1))

        ax.plot(t, rel, color="tab:blue", linewidth=1.8, label="Evolución")
        ax.plot(t, fit, color="tab:red", linewidth=2.2, linestyle="--", label="Ajuste lineal")
        ax.axhline(0.0, color="0.35", linewidth=1.0, alpha=0.4)
        ax.set_title(
            f"dt = {dt:g} | <|pendiente|> = {mean_slope:.2e} ± {std_slope:.1e}",
            fontsize=FONT_TITLE,
        )
        ax.set_xlabel("Tiempo (s)", fontsize=FONT_LABELS)
        ax.set_ylabel(r"$(E(t)-E_0)/E_0$", fontsize=FONT_LABELS)
        ax.tick_params(labelsize=FONT_TICKS)
        ax.legend(fontsize=FONT_TICKS)

    for ax in axes_flat[len(dts):]:
        ax.axis("off")

    fig.suptitle(f"Pendiente del drift de energía, run {run_id}", fontsize=FONT_LABELS)
    fig.tight_layout()

    image_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(image_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    image_dir = Path(args.image_dir)
    image_path = Path(args.output) if args.output else image_dir / f"dt_energy_slope_fits_N{args.n}.png"

    files = discover_files(input_dir, args.n)
    if not files:
        raise SystemExit(f"No energy files found in {input_dir}")

    selected = collect_selected(files, args.dts, args.run_id, args.t_max)
    if not selected:
        raise SystemExit(f"No valid finite energy series found for run {args.run_id}.")

    stats = collect_slope_stats(files, args.dts, args.t_max)
    plot(selected, stats, image_path, args.run_id)
    print(f"Saved {image_path}")


if __name__ == "__main__":
    main()
