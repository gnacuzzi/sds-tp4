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


FONT_LABELS = 17
FONT_TICKS = 14
FONT_LEGEND = 12
DPI = 300


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot temporal evolution of relative total energy for several dt values."
    )
    parser.add_argument("--input-dir", required=True, help="Directory with <N>_energy_dt*_run*.txt files.")
    parser.add_argument("--image-dir", required=True, help="Directory where the plot is written.")
    parser.add_argument("--output", default=None, help="Output image path.")
    parser.add_argument("--n", type=int, default=1000, help="Particle count in file names.")
    parser.add_argument("--dts", type=float, nargs="+", default=None, help="dt values to include.")
    parser.add_argument("--run-id", type=int, default=None, help="Plot only this realization instead of mean/std.")
    parser.add_argument("--t-max", type=float, default=None, help="Maximum time shown.")
    parser.add_argument("--y-lim", type=float, nargs=2, default=None, help="Optional y limits.")
    parser.add_argument(
        "--show-std",
        action="store_true",
        help="Show mean +/- standard deviation shading when plotting several realizations.",
    )
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


def collect_series(files, include_dts, run_id, t_max):
    include = set(include_dts) if include_dts is not None else None
    by_dt = defaultdict(list)

    for dt, current_run_id, path in files:
        if include is not None and dt not in include:
            continue
        if run_id is not None and current_run_id != run_id:
            continue

        t, rel = load_relative_energy(path, t_max=t_max)
        if len(t) < 2:
            print(f"Skipping {path}: not enough finite samples")
            continue

        by_dt[dt].append((current_run_id, t, rel))

    return dict(sorted(by_dt.items()))


def plot(by_dt, image_path: Path, run_id, y_lim, show_std):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    cmap = plt.get_cmap("viridis")
    dts = sorted(by_dt)
    colors = {dt: cmap(i / max(len(dts) - 1, 1)) for i, dt in enumerate(dts)}

    for dt in dts:
        series = by_dt[dt]
        color = colors[dt]

        if run_id is not None:
            _, t, rel = series[0]
            ax.plot(t, rel, color=color, linewidth=2, label=f"dt = {dt:g}")
            continue

        min_len = min(len(t) for _, t, _ in series)
        if min_len < 2:
            continue

        t_ref = series[0][1][:min_len]
        values = np.array([rel[:min_len] for _, _, rel in series], dtype=float)
        mean = np.nanmean(values, axis=0)
        std = np.nanstd(values, axis=0, ddof=1 if len(series) > 1 else 0)

        ax.plot(t_ref, mean, color=color, linewidth=2, label=f"dt = {dt:g}")
        if show_std and len(series) > 1:
            ax.fill_between(t_ref, mean - std, mean + std, color=color, alpha=0.16, linewidth=0)

    ax.axhline(0.0, color="0.35", linewidth=1.0, alpha=0.45)
    ax.set_xlabel("Tiempo (s)", fontsize=FONT_LABELS)
    ax.set_ylabel(r"$(E(t)-E_0)/E_0$", fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    ax.legend(fontsize=FONT_LEGEND, loc="best")
    if y_lim is not None:
        ax.set_ylim(*y_lim)
    fig.tight_layout()

    image_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(image_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    image_dir = Path(args.image_dir)
    image_path = Path(args.output) if args.output else image_dir / f"dt_energy_evolution_N{args.n}.png"

    files = discover_files(input_dir, args.n)
    if not files:
        raise SystemExit(f"No energy files found in {input_dir}")

    by_dt = collect_series(files, args.dts, args.run_id, args.t_max)
    if not by_dt:
        raise SystemExit("No valid finite energy series found.")

    plot(by_dt, image_path, args.run_id, args.y_lim, args.show_std)
    print(f"Saved {image_path}")


if __name__ == "__main__":
    main()
