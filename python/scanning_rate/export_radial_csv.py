import argparse
import csv
import glob
import os
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
from python.scanning_rate.radial_profiles import (
    compute_profiles,
    dynamic_run_id,
    read_dynamic_file,
)


DEFAULT_S_MIN = 1.5
DEFAULT_S_MAX = 5.0


def parse_args():
    parser = argparse.ArgumentParser(description="Export radial profile averages to CSV.")
    parser.add_argument("--tp3-dir", default="output_tp3", help="Directory with TP3 dynamic files.")
    parser.add_argument("--tp4-dir", default="output", help="Directory with TP4 dynamic files.")
    parser.add_argument("--output-dir", default="output", help="Directory for generated CSV files.")
    parser.add_argument("--run-ids", type=int, nargs="+", default=list(range(10)), help="Run ids to include.")
    parser.add_argument("--tp3-ns", type=int, nargs="+", default=None, help="TP3 N values.")
    parser.add_argument("--tp4-ns", type=int, nargs="+", default=None, help="TP4 N values.")
    parser.add_argument("--s-min", type=float, default=DEFAULT_S_MIN, help="Lower S bound for vs-N averages.")
    parser.add_argument("--s-max", type=float, default=DEFAULT_S_MAX, help="Upper S bound for vs-N averages.")

    return parser.parse_args()


def discover_ns(directory):
    ns = set()

    for path in glob.glob(str(Path(directory) / "*_dynamic*.txt")):
        if os.path.getsize(path) == 0:
            continue

        base = os.path.basename(path)
        n_token = base.split("_dynamic", 1)[0]

        if n_token.isdigit():
            ns.add(int(n_token))

    return sorted(ns)


def dynamic_files(directory, n_value, run_ids):
    files = [path for path in sorted(glob.glob(str(Path(directory) / f"{n_value}_dynamic*.txt"))) if os.path.getsize(path) > 0]

    if run_ids is None:
        return files

    selected = set(run_ids)
    return [path for path in files if dynamic_run_id(path) in selected]


def summarize_n(directory, n_value, run_ids):
    files = dynamic_files(directory, n_value, run_ids)

    if not files:
        print(f"No dynamic files found for N={n_value} in {directory}")
        return None

    rho_runs = []
    v_runs = []

    for path in files:
        print(f"Processing {path}")
        snapshots = read_dynamic_file(path)
        S, rho, v, _ = compute_profiles(snapshots)
        rho_runs.append(rho)
        v_runs.append(v)

    rho_runs = np.array(rho_runs, dtype=float)
    v_runs = np.array(v_runs, dtype=float)
    ddof = 1 if len(files) > 1 else 0

    rho_mean = np.mean(rho_runs, axis=0)
    rho_std = np.std(rho_runs, axis=0, ddof=ddof)
    v_mean = np.mean(v_runs, axis=0)
    v_abs_mean = np.abs(v_mean)
    v_abs_std = np.std(np.abs(v_runs), axis=0, ddof=ddof)
    jin_runs = rho_runs * np.abs(v_runs)
    jin_mean = rho_mean * v_abs_mean
    jin_std = np.std(jin_runs, axis=0, ddof=ddof)

    return {
        "S": S,
        "runs": len(files),
        "rho_mean": rho_mean,
        "rho_std": rho_std,
        "v_mean": v_mean,
        "v_abs_mean": v_abs_mean,
        "v_abs_std": v_abs_std,
        "jin_mean": jin_mean,
        "jin_std": jin_std,
    }


def write_profiles_csv(dataset, summaries, output_dir):
    path = Path(output_dir) / f"radial_profiles_{dataset.lower()}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "dataset",
            "N",
            "S",
            "rho_mean",
            "rho_std",
            "v_mean",
            "v_abs_mean",
            "v_abs_std",
            "jin_mean",
            "jin_std",
            "runs",
        ])

        for n_value, summary in summaries.items():
            for idx, s_value in enumerate(summary["S"]):
                writer.writerow([
                    dataset,
                    n_value,
                    f"{s_value:.12g}",
                    f"{summary['rho_mean'][idx]:.12e}",
                    f"{summary['rho_std'][idx]:.12e}",
                    f"{summary['v_mean'][idx]:.12e}",
                    f"{summary['v_abs_mean'][idx]:.12e}",
                    f"{summary['v_abs_std'][idx]:.12e}",
                    f"{summary['jin_mean'][idx]:.12e}",
                    f"{summary['jin_std'][idx]:.12e}",
                    summary["runs"],
                ])

    return path


def write_vs_n_csv(dataset, summaries, output_dir, s_min, s_max):
    path = Path(output_dir) / f"radial_vs_N_{dataset.lower()}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "dataset",
            "N",
            "S_min",
            "S_max",
            "rho_mean",
            "rho_std",
            "v_mean",
            "v_abs_mean",
            "v_abs_std",
            "jin_mean",
            "jin_std",
            "runs",
        ])

        for n_value, summary in summaries.items():
            S = summary["S"]
            mask = (S >= s_min) & (S <= s_max)
            if not np.any(mask):
                continue

            writer.writerow([
                dataset,
                n_value,
                f"{float(np.min(S[mask])):.12g}",
                f"{float(np.max(S[mask])):.12g}",
                f"{float(np.mean(summary['rho_mean'][mask])):.12e}",
                f"{float(np.mean(summary['rho_std'][mask])):.12e}",
                f"{float(np.mean(summary['v_mean'][mask])):.12e}",
                f"{float(abs(np.mean(summary['v_mean'][mask]))):.12e}",
                f"{float(np.mean(summary['v_abs_std'][mask])):.12e}",
                f"{float(np.mean(summary['jin_mean'][mask])):.12e}",
                f"{float(np.mean(summary['jin_std'][mask])):.12e}",
                summary["runs"],
            ])

    return path


def process_dataset(dataset, directory, ns, run_ids, output_dir, s_min, s_max):
    summaries = {}

    for n_value in ns:
        summary = summarize_n(directory, n_value, run_ids)
        if summary is not None:
            summaries[n_value] = summary

    if not summaries:
        return []

    return [
        write_profiles_csv(dataset, summaries, output_dir),
        write_vs_n_csv(dataset, summaries, output_dir, s_min, s_max),
    ]


def main():
    args = parse_args()

    if args.s_max <= args.s_min:
        raise SystemExit("--s-max must be greater than --s-min")

    tp3_ns = args.tp3_ns if args.tp3_ns is not None else discover_ns(args.tp3_dir)
    tp4_ns = args.tp4_ns if args.tp4_ns is not None else discover_ns(args.tp4_dir)
    output_paths = []

    output_paths.extend(
        process_dataset("TP3", args.tp3_dir, tp3_ns, args.run_ids, args.output_dir, args.s_min, args.s_max)
    )
    output_paths.extend(
        process_dataset("TP4", args.tp4_dir, tp4_ns, args.run_ids, args.output_dir, args.s_min, args.s_max)
    )

    if not output_paths:
        raise SystemExit("No radial data found.")

    for path in output_paths:
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
