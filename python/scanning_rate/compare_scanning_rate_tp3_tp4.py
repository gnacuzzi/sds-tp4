import argparse
import glob
import os
import re
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


TP3_DIR = Path("output_tp3")
TP4_DIR = Path("output")
IMAGE_DIR = Path("images")
SUMMARY_PATH = Path("output/scanning_rate_tp3_tp4_summary.csv")
TP4_EXISTING_SUMMARY = Path("output/scanning_rate_j_summary.csv")

FONT_LABELS = 18
FONT_TICKS = 15
FONT_LEGEND = 13
DPI = 300


def parse_args():
    parser = argparse.ArgumentParser(description="Compare scanning rate J(N) between TP3 and TP4.")
    parser.add_argument("--tp3-dir", default=str(TP3_DIR), help="Directory with TP3 *_events*.txt files.")
    parser.add_argument("--tp4-dir", default=str(TP4_DIR), help="Directory with TP4 *_cfc*.txt files.")
    parser.add_argument("--image-dir", default=str(IMAGE_DIR), help="Directory where the plot is saved.")
    parser.add_argument("--summary", default=str(SUMMARY_PATH), help="Output CSV summary path.")
    parser.add_argument(
        "--tp4-summary",
        default=str(TP4_EXISTING_SUMMARY),
        help="Existing TP4 J summary. Used automatically if it exists.",
    )
    parser.add_argument(
        "--force-recompute-tp4",
        action="store_true",
        help="Ignore --tp4-summary and recompute TP4 from cfc files.",
    )
    parser.add_argument("--runs", type=int, default=10, help="Number of realizations per N.")
    parser.add_argument("--tp3-ns", type=int, nargs="+", default=None, help="TP3 N values.")
    parser.add_argument("--tp4-ns", type=int, nargs="+", default=None, help="TP4 N values.")
    parser.add_argument("--t-min", type=float, default=None, help="Minimum time used in the fit.")
    parser.add_argument("--t-max", type=float, default=None, help="Maximum time used in the fit.")

    return parser.parse_args()


def discover_ns(directory: Path, kind: str):
    regex = re.compile(rf"(?P<n>\d+)_{kind}\d+\.txt$")
    ns = set()

    for path in glob.glob(str(directory / f"*_{kind}*.txt")):
        match = regex.search(os.path.basename(path))
        if match:
            ns.add(int(match.group("n")))

    return sorted(ns)


def include_time(t, t_min, t_max):
    if t_min is not None and t < t_min:
        return False
    if t_max is not None and t > t_max:
        return False
    return True


def parse_tp4_cfc_line(line):
    parts = line.split()
    if len(parts) < 3 or parts[0] != "t":
        raise ValueError(f"Invalid TP4 Cfc line: {line.rstrip()}")

    return float(parts[1]), float(parts[2])


def parse_tp3_event_line(line):
    parts = line.split()
    if len(parts) < 3:
        raise ValueError(f"Invalid TP3 event line: {line.rstrip()}")

    return float(parts[1]), float(parts[2])


def compute_slope(path: Path, parser, t_min, t_max):
    n = 0
    sum_t = 0.0
    sum_y = 0.0
    sum_tt = 0.0
    sum_ty = 0.0

    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue

            t, cfc = parser(line)
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

    return (n * sum_ty - sum_t * sum_y) / denominator


def summarize_dataset(directory: Path, ns, runs, kind, parser, t_min, t_max):
    rows = []

    for n_value in ns:
        slopes = []

        for run_id in range(runs):
            path = directory / f"{n_value}_{kind}{run_id}.txt"
            if not path.is_file():
                print(f"Missing {path}, skipping")
                continue

            slope = compute_slope(path, parser, t_min, t_max)
            if slope is None:
                print(f"Insufficient data in {path}, skipping")
                continue

            slopes.append(slope)

        if not slopes:
            continue

        slopes = np.array(slopes, dtype=float)
        ddof = 1 if len(slopes) > 1 else 0
        rows.append({
            "N": n_value,
            "J_mean": float(np.mean(slopes)),
            "J_std": float(np.std(slopes, ddof=ddof)),
            "runs": len(slopes),
        })

    return rows


def read_existing_summary(path: Path, selected_ns=None):
    if not path.is_file():
        return None

    selected = set(selected_ns) if selected_ns is not None else None
    rows = []

    with path.open() as handle:
        header = handle.readline().strip().split(",")
        columns = {name: idx for idx, name in enumerate(header)}

        required = ["N", "J_mean", "J_std", "runs"]
        if any(name not in columns for name in required):
            raise ValueError(f"Invalid summary header in {path}: {header}")

        for line in handle:
            if not line.strip():
                continue

            parts = line.strip().split(",")
            n_value = int(parts[columns["N"]])

            if selected is not None and n_value not in selected:
                continue

            rows.append({
                "N": n_value,
                "J_mean": float(parts[columns["J_mean"]]),
                "J_std": float(parts[columns["J_std"]]),
                "runs": int(parts[columns["runs"]]),
            })

    return sorted(rows, key=lambda row: row["N"])


def plot_comparison(tp3_rows, tp4_rows, image_dir: Path):
    fig, ax = plt.subplots(figsize=(8, 5))

    if tp3_rows:
        tp3_ns = np.array([row["N"] for row in tp3_rows], dtype=float)
        tp3_means = np.array([row["J_mean"] for row in tp3_rows], dtype=float)
        tp3_stds = np.array([row["J_std"] for row in tp3_rows], dtype=float)
        ax.errorbar(
            tp3_ns,
            tp3_means,
            yerr=tp3_stds,
            fmt="o-",
            capsize=5,
            linewidth=2,
            label="TP3 event-driven",
        )

    if tp4_rows:
        tp4_ns = np.array([row["N"] for row in tp4_rows], dtype=float)
        tp4_means = np.array([row["J_mean"] for row in tp4_rows], dtype=float)
        tp4_stds = np.array([row["J_std"] for row in tp4_rows], dtype=float)
        ax.errorbar(
            tp4_ns,
            tp4_means,
            yerr=tp4_stds,
            fmt="s-",
            capsize=5,
            linewidth=2,
            label="TP4 time-driven",
        )

    ax.set_xlabel("N", fontsize=FONT_LABELS)
    ax.set_ylabel(r"$\langle J \rangle$", fontsize=FONT_LABELS)
    ax.tick_params(labelsize=FONT_TICKS)
    ax.legend(fontsize=FONT_LEGEND)
    fig.tight_layout()

    image_dir.mkdir(parents=True, exist_ok=True)
    path = image_dir / "J_vs_N_tp3_tp4.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def write_summary(tp3_rows, tp4_rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w") as handle:
        handle.write("dataset,N,J_mean,J_std,runs\n")
        for dataset, rows in (("TP3", tp3_rows), ("TP4", tp4_rows)):
            for row in rows:
                handle.write(
                    f"{dataset},{row['N']},{row['J_mean']:.12e},{row['J_std']:.12e},{row['runs']}\n"
                )


def main():
    args = parse_args()
    tp3_dir = Path(args.tp3_dir)
    tp4_dir = Path(args.tp4_dir)
    image_dir = Path(args.image_dir)
    summary_path = Path(args.summary)
    tp4_summary_path = Path(args.tp4_summary)

    tp3_ns = args.tp3_ns if args.tp3_ns is not None else discover_ns(tp3_dir, "events")
    tp4_ns = args.tp4_ns if args.tp4_ns is not None else discover_ns(tp4_dir, "cfc")

    tp3_rows = summarize_dataset(
        tp3_dir,
        tp3_ns,
        args.runs,
        "events",
        parse_tp3_event_line,
        args.t_min,
        args.t_max,
    )
    tp4_rows = None
    if not args.force_recompute_tp4 and args.t_min is None and args.t_max is None:
        tp4_rows = read_existing_summary(tp4_summary_path, selected_ns=args.tp4_ns)
        if tp4_rows is not None:
            print(f"Using existing TP4 summary: {tp4_summary_path}")

    if tp4_rows is None:
        tp4_rows = summarize_dataset(
            tp4_dir,
            tp4_ns,
            args.runs,
            "cfc",
            parse_tp4_cfc_line,
            args.t_min,
            args.t_max,
        )

    if not tp3_rows and not tp4_rows:
        raise SystemExit("No valid TP3 or TP4 scanning-rate files found.")

    write_summary(tp3_rows, tp4_rows, summary_path)
    plot_path = plot_comparison(tp3_rows, tp4_rows, image_dir)

    print(f"Summary written to {summary_path}")
    print(f"Saved {plot_path}")


if __name__ == "__main__":
    main()
