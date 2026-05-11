import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np


TP3_PROFILES = Path("output/radial_profiles_tp3.csv")
TP4_PROFILES = Path("output/radial_profiles_tp4.csv")
OUTPUT_DIR = Path("output")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export radial-vs-N values at one target radial shell from profile CSV files."
    )
    parser.add_argument(
        "--target-s",
        type=float,
        default=2.0,
        help="Target S used in the old TP3 script. With centered bins, S=2.0 maps to center S=2.1.",
    )
    parser.add_argument("--tp3-profiles", default=str(TP3_PROFILES), help="TP3 radial profile CSV.")
    parser.add_argument("--tp4-profiles", default=str(TP4_PROFILES), help="TP4 radial profile CSV.")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Directory for output CSV files.")

    return parser.parse_args()


def load_profiles(path):
    by_n = defaultdict(list)

    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            by_n[int(row["N"])].append(row)

    return by_n


def select_target_row(rows, target_s):
    # The current CSV stores bin centers. The old TP3 script used S=i*dS,
    # so TARGET_S=2.0 selected the [2.0, 2.2) shell, centered at 2.1.
    target_center = target_s + 0.1

    return min(rows, key=lambda row: abs(float(row["S"]) - target_center))


def export_dataset(dataset, profiles_path, target_s, output_dir):
    by_n = load_profiles(profiles_path)
    safe_target = str(target_s).replace(".", "p")
    output_path = Path(output_dir) / f"radial_vs_N_{dataset.lower()}_S{safe_target}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "dataset",
            "N",
            "target_S_old",
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

        for n_value in sorted(by_n):
            row = select_target_row(by_n[n_value], target_s)
            v_mean = float(row["v_mean"])

            writer.writerow([
                dataset,
                n_value,
                f"{target_s:.12g}",
                row["S"],
                row["rho_mean"],
                row["rho_std"],
                row["v_mean"],
                f"{abs(v_mean):.12e}",
                row["v_abs_std"],
                row["jin_mean"],
                row["jin_std"],
                row["runs"],
            ])

    return output_path


def main():
    args = parse_args()
    output_paths = [
        export_dataset("TP3", args.tp3_profiles, args.target_s, args.output_dir),
        export_dataset("TP4", args.tp4_profiles, args.target_s, args.output_dir),
    ]

    for path in output_paths:
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
