import argparse
import csv
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))


DEFAULT_SUMMARIES = [
    (
        100,
        Path("output/dt_observable_N1000_K100/dt_energy_observable_max.csv"),
    ),
    (
        1000,
        Path("output/dt_observable_N1000_K1000/dt_energy_observable_max.csv"),
    ),
    (
        10000,
        Path("output/dt_observable_N1000_K10000/dt_energy_observable_max_with_0001.csv"),
    ),
]

FONT_LABELS = 20
FONT_TICKS = 16
FONT_LEGEND = 14
DPI = 300


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare energy dt-observable summaries for different k values."
    )
    parser.add_argument(
        "--summary",
        action="append",
        nargs=2,
        metavar=("K", "CSV"),
        help=(
            "Summary to include, as: --summary 100 path/to/summary.csv. "
            "Can be repeated. Defaults to k=100, 1000 and 10000 summaries."
        ),
    )
    parser.add_argument(
        "--output",
        default="images/dt_observable_compare_k/dt_energy_observable_max_by_k.png",
        help="Output image path.",
    )
    parser.add_argument(
        "--csv-output",
        default="output/dt_energy_observable_max_by_k.csv",
        help="Combined CSV output path.",
    )
    parser.add_argument(
        "--metric",
        default="max",
        help="Metric name to keep from the summaries. Default: max.",
    )
    parser.add_argument(
        "--title",
        default="N = 1000",
        help="Plot title. Default: N = 1000.",
    )
    return parser.parse_args()


def load_summary(path: Path, metric: str):
    rows = []

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("section") != "summary":
                continue
            if row.get("metric") != metric:
                continue

            rows.append(
                {
                    "dt": float(row["dt"]),
                    "value": float(row["value"]),
                    "std": float(row["std"]),
                    "runs": int(row["runs"]),
                }
            )

    rows.sort(key=lambda item: item["dt"])
    return rows


def write_combined_csv(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["k", "dt", "value", "std", "runs"])
        for k_value, rows in data:
            for row in rows:
                writer.writerow(
                    [
                        k_value,
                        f"{row['dt']:.12e}",
                        f"{row['value']:.12e}",
                        f"{row['std']:.12e}",
                        row["runs"],
                    ]
                )


def plot(data, output_path: Path, title: str):
    fig, ax = plt.subplots(figsize=(9, 6))
    markers = ["o", "s", "^", "D", "v"]

    for idx, (k_value, rows) in enumerate(data):
        if not rows:
            continue

        dt = np.array([row["dt"] for row in rows], dtype=float)
        value = np.array([row["value"] for row in rows], dtype=float)
        std = np.array([row["std"] for row in rows], dtype=float)

        ax.errorbar(
            dt,
            value,
            yerr=std,
            marker=markers[idx % len(markers)],
            capsize=5,
            linewidth=2,
            label=f"k = {k_value:g}",
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("dt (s)", fontsize=FONT_LABELS)
    ax.set_ylabel(r"$\langle \max_t |\Delta E / E_0| \rangle$", fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    ax.legend(fontsize=FONT_LEGEND)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=DPI)
    plt.close(fig)


def main():
    args = parse_args()

    if args.summary is None:
        summaries = DEFAULT_SUMMARIES
    else:
        summaries = [(float(k), Path(path)) for k, path in args.summary]

    data = []
    for k_value, path in summaries:
        if not path.is_file():
            print(f"Missing summary for k={k_value:g}: {path}")
            continue

        rows = load_summary(path, args.metric)
        if not rows:
            print(f"No summary rows for metric={args.metric} in {path}")
            continue

        data.append((k_value, rows))
        print(f"k={k_value:g}: loaded {len(rows)} dt values from {path}")

    if not data:
        raise SystemExit("No valid summaries found.")

    output_path = Path(args.output)
    combined_csv = Path(args.csv_output)
    write_combined_csv(data, combined_csv)
    plot(data, output_path, args.title)

    print(f"Combined CSV written to {combined_csv}")
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
