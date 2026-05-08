import argparse
import glob
import os
import re
from pathlib import Path
from typing import Optional

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_IMAGE_DIR = Path("images")
DEFAULT_SUMMARY = Path("output/scanning_rate_j_summary.csv")
DEFAULT_NS = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

FONT_LABELS = 18
FONT_TICKS = 15
FONT_LEGEND = 13
DPI = 300


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute scanning rate J from Cfc(t) event files."
    )
    parser.add_argument(
        "runs",
        nargs="?",
        type=int,
        default=10,
        help="Number of realizations per N. Default: 10",
    )
    parser.add_argument(
        "--ns",
        nargs="+",
        type=int,
        default=None,
        help="N values to process. Default: discover from output or use 100..1000.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory containing <N>_events<run>.txt files.",
    )
    parser.add_argument(
        "--image-dir",
        default=str(DEFAULT_IMAGE_DIR),
        help="Directory where plots are written.",
    )
    parser.add_argument(
        "--summary",
        default=str(DEFAULT_SUMMARY),
        help="CSV summary path.",
    )
    parser.add_argument(
        "--t-min",
        type=float,
        default=None,
        help="Minimum time used for the linear fit.",
    )
    parser.add_argument(
        "--t-max",
        type=float,
        default=None,
        help="Maximum time used for the linear fit.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show plots interactively after saving.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Process only the first two N values.",
    )
    return parser.parse_args()


def discover_ns(output_dir: Path):
    pattern = str(output_dir / "*_events*.txt")
    ns = set()
    regex = re.compile(r"(?P<n>\d+)_events\d+\.txt$")

    for path in glob.glob(pattern):
        match = regex.search(os.path.basename(path))
        if match:
            ns.add(int(match.group("n")))

    return sorted(ns)


def parse_event_line(line: str):
    parts = line.split()
    if len(parts) < 3 or parts[0] != "t":
        raise ValueError(f"Invalid event line: {line.rstrip()}")
    return float(parts[1]), float(parts[2])


def include_time(t: float, t_min: Optional[float], t_max: Optional[float]):
    if t_min is not None and t < t_min:
        return False
    if t_max is not None and t > t_max:
        return False
    return True


def compute_slope(path: Path, t_min: Optional[float], t_max: Optional[float]):
    n = 0
    sum_t = 0.0
    sum_y = 0.0
    sum_tt = 0.0
    sum_ty = 0.0

    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            t, cfc = parse_event_line(line)
            if not include_time(t, t_min, t_max):
                continue

            n += 1
            sum_t += t
            sum_y += cfc
            sum_tt += t * t
            sum_ty += t * cfc

    denominator = n * sum_tt - sum_t * sum_t
    if n < 2 or abs(denominator) < 1e-12:
        return None

    slope = (n * sum_ty - sum_t * sum_y) / denominator
    intercept = (sum_y - slope * sum_t) / n
    return slope, intercept, n


def read_change_points(path: Path, t_min: Optional[float], t_max: Optional[float]):
    times = []
    values = []
    previous = None

    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            t, cfc = parse_event_line(line)
            if not include_time(t, t_min, t_max):
                continue

            if previous is None or cfc != previous:
                times.append(t)
                values.append(cfc)
                previous = cfc

    return np.array(times), np.array(values)


def process_run(path: Path, t_min: Optional[float], t_max: Optional[float]):
    fit = compute_slope(path, t_min, t_max)
    if fit is None:
        return None

    slope, intercept, samples = fit
    times, values = read_change_points(path, t_min, t_max)
    return {
        "slope": slope,
        "intercept": intercept,
        "samples": samples,
        "times": times,
        "values": values,
    }


def save_cfc_plot(n_value: int, run_results, image_dir: Path):
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(run_results), 1)))

    for idx, result in enumerate(run_results):
        times = result["times"]
        values = result["values"]
        slope = result["slope"]
        intercept = result["intercept"]

        if len(times) > 0:
            ax.scatter(times, values, color=colors[idx % len(colors)], s=10)
            x_min = float(np.min(times))
            x_max = float(np.max(times))
        else:
            x_min = 0.0
            x_max = 1.0

        xline = np.linspace(x_min, x_max, 200)
        ax.plot(
            xline,
            slope * xline + intercept,
            color=colors[idx % len(colors)],
            linewidth=2,
            linestyle="--",
            label=f"run {result['run_id']}: J={slope:.4g}",
        )

    ax.set_xlabel("Tiempo (s)", fontsize=FONT_LABELS)
    ax.set_ylabel("Cfc(t)", fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    ax.legend(fontsize=FONT_LEGEND, loc="best")
    fig.tight_layout()

    image_dir.mkdir(parents=True, exist_ok=True)
    path = image_dir / f"Cfc_fit_N_{n_value}.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def save_j_vs_n_plot(rows, image_dir: Path):
    ns = np.array([row["N"] for row in rows], dtype=float)
    means = np.array([row["J_mean"] for row in rows], dtype=float)
    stds = np.array([row["J_std"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(ns, means, yerr=stds, fmt="o-", capsize=5, linewidth=2)
    ax.set_xlabel("N", fontsize=FONT_LABELS)
    ax.set_ylabel(r"$\langle J \rangle$", fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    fig.tight_layout()

    image_dir.mkdir(parents=True, exist_ok=True)
    path = image_dir / "J_vs_N.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def write_summary(rows, summary_path: Path):
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w") as handle:
        handle.write("N,J_mean,J_std,runs\n")
        for row in rows:
            handle.write(
                f"{row['N']},{row['J_mean']:.12e},{row['J_std']:.12e},{row['runs']}\n"
            )


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    image_dir = Path(args.image_dir)
    summary_path = Path(args.summary)

    ns = args.ns if args.ns is not None else discover_ns(output_dir)
    if not ns:
        ns = DEFAULT_NS
    if args.test:
        ns = ns[:2]

    rows = []
    for n_value in ns:
        run_results = []
        print(f"Processing N={n_value}")

        for run_id in range(args.runs):
            path = output_dir / f"{n_value}_events{run_id}.txt"
            if not path.is_file():
                print(f"  missing {path}, skipping")
                continue

            result = process_run(path, args.t_min, args.t_max)
            if result is None:
                print(f"  insufficient data in {path}, skipping")
                continue

            result["run_id"] = run_id
            run_results.append(result)
            print(f"  run {run_id}: J={result['slope']:.8e}, samples={result['samples']}")

        if not run_results:
            print(f"  no valid runs for N={n_value}")
            continue

        slopes = np.array([result["slope"] for result in run_results], dtype=float)
        ddof = 1 if len(slopes) > 1 else 0
        row = {
            "N": n_value,
            "J_mean": float(np.mean(slopes)),
            "J_std": float(np.std(slopes, ddof=ddof)),
            "runs": len(slopes),
        }
        rows.append(row)

        plot_path = save_cfc_plot(n_value, run_results, image_dir)
        print(f"  saved {plot_path}")

    if not rows:
        raise SystemExit("No valid event files found.")

    write_summary(rows, summary_path)
    j_plot_path = save_j_vs_n_plot(rows, image_dir)
    print(f"Summary written to {summary_path}")
    print(f"Saved {j_plot_path}")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
