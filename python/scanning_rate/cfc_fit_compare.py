import argparse
import os
import sys
from pathlib import Path
from typing import Optional

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
from python.plot_format import apply_scientific_y


DEFAULT_NS = [100, 1000]
FONT_LABELS = 22
FONT_TICKS = 18
FONT_ANNOTATION = 16
DPI = 300


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot Cfc(t) linear fits for selected N values in one figure."
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory containing <N>_cfc<run>.txt files.",
    )
    parser.add_argument(
        "--image-dir",
        default="images",
        help="Directory where the figure is written.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output image path. Defaults to <image-dir>/Cfc_fit_compare_N100_N1000.png.",
    )
    parser.add_argument(
        "--ns",
        nargs="+",
        type=int,
        default=DEFAULT_NS,
        help="N values to compare. Default: 100 1000.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of realizations per N. Default: 10.",
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
        "--point-size",
        type=float,
        default=10.0,
        help="Scatter point size. Default: 10.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.28,
        help="Scatter alpha. Default: 0.28.",
    )
    parser.add_argument(
        "--show-j",
        action="store_true",
        help="Annotate mean J and standard deviation in the plot.",
    )
    return parser.parse_args()


def include_time(t: float, t_min: Optional[float], t_max: Optional[float]):
    if t_min is not None and t < t_min:
        return False
    if t_max is not None and t > t_max:
        return False
    return True


def parse_cfc_line(line: str):
    parts = line.split()
    if len(parts) < 3 or parts[0] != "t":
        raise ValueError(f"Invalid Cfc line: {line.rstrip()}")
    return float(parts[1]), float(parts[2])


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
            t, cfc = parse_cfc_line(line)
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
            t, cfc = parse_cfc_line(line)
            if not include_time(t, t_min, t_max):
                continue

            if previous is None or cfc != previous:
                times.append(t)
                values.append(cfc)
                previous = cfc

    return np.array(times), np.array(values)


def process_run(path: Path, run_id: int, t_min: Optional[float], t_max: Optional[float]):
    fit = compute_slope(path, t_min, t_max)
    if fit is None:
        return None

    slope, intercept, samples = fit
    times, values = read_change_points(path, t_min, t_max)
    if len(times) == 0:
        return None

    return {
        "run_id": run_id,
        "slope": slope,
        "intercept": intercept,
        "samples": samples,
        "times": times,
        "values": values,
    }


def load_results(output_dir: Path, ns, runs, t_min, t_max):
    by_n = {}

    for n_value in ns:
        results = []
        for run_id in range(runs):
            path = output_dir / f"{n_value}_cfc{run_id}.txt"
            if not path.is_file():
                print(f"Missing {path}, skipping.")
                continue

            result = process_run(path, run_id, t_min, t_max)
            if result is None:
                print(f"Invalid or insufficient data in {path}, skipping.")
                continue

            results.append(result)

        if results:
            by_n[n_value] = results

    return by_n


def plot(by_n, output_path: Path, point_size: float, alpha: float, show_j: bool):
    fig, ax = plt.subplots(figsize=(10, 6))
    markers = ["o", "^", "s", "D"]
    line_styles = ["-", "--", "-.", ":"]
    base_colors = {
        100: "tab:blue",
        500: "tab:orange",
        1000: "tab:red",
    }

    annotation_lines = []
    for n_index, (n_value, results) in enumerate(sorted(by_n.items())):
        slopes = np.array([result["slope"] for result in results], dtype=float)
        mean = float(np.mean(slopes))
        std = float(np.std(slopes, ddof=1 if len(slopes) > 1 else 0))
        annotation_lines.append(
            rf"$N={n_value}$: $\langle J\rangle={mean:.4g}\pm{std:.2g}$"
        )

        for result in results:
            marker = markers[n_index % len(markers)]
            line_color = base_colors.get(n_value, f"C{n_index}")

            ax.scatter(
                result["times"],
                result["values"],
                s=point_size,
                alpha=alpha,
                color=line_color,
                marker=marker,
                edgecolors="none",
            )

            xline = np.linspace(float(np.min(result["times"])), float(np.max(result["times"])), 200)
            ax.plot(
                xline,
                result["slope"] * xline + result["intercept"],
                color=line_color,
                linestyle=line_styles[n_index % len(line_styles)],
                linewidth=1.6,
                alpha=0.55,
            )

    for n_index, n_value in enumerate(sorted(by_n)):
        ax.plot(
            [],
            [],
            color=base_colors.get(n_value, f"C{n_index}"),
            linestyle=line_styles[n_index % len(line_styles)],
            linewidth=3,
            marker=markers[n_index % len(markers)],
            markersize=7,
            label=f"N = {n_value}",
        )

    if show_j:
        ax.text(
            0.98,
            0.04,
            "\n".join(annotation_lines),
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=FONT_ANNOTATION,
            bbox={"facecolor": "white", "edgecolor": "0.8", "alpha": 0.9},
        )

    ax.set_xlabel("Tiempo (s)", fontsize=FONT_LABELS)
    ax.set_ylabel("Cfc(t)", fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    ax.legend(fontsize=FONT_ANNOTATION, loc="upper left")
    apply_scientific_y(ax, fontsize=FONT_TICKS)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=DPI)
    plt.close(fig)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    image_dir = Path(args.image_dir)
    output_path = Path(args.output) if args.output else image_dir / "Cfc_fit_compare_N100_N1000.png"

    by_n = load_results(output_dir, args.ns, args.runs, args.t_min, args.t_max)
    if not by_n:
        raise SystemExit("No valid Cfc files found.")

    for n_value, results in sorted(by_n.items()):
        slopes = np.array([result["slope"] for result in results], dtype=float)
        print(
            f"N={n_value}: runs={len(results)}, "
            f"J_mean={np.mean(slopes):.8e}, "
            f"J_std={np.std(slopes, ddof=1 if len(slopes) > 1 else 0):.8e}"
        )

    plot(by_n, output_path, args.point_size, args.alpha, args.show_j)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
