"""Sweep (k, N) and capture dt_used_to_wall for the first used particle.

Runs the scanning_rate binary in benchmark mode (no file I/O) and parses its
stdout summary. Writes one row per realization to a CSV.
"""
import argparse
import csv
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


DEFAULT_KS = [100.0, 1000.0, 10000.0]
DEFAULT_NS = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

VALUE_RE = re.compile(r"^([A-Za-z_]+)=(\S+)$")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ks", type=float, nargs="+", default=DEFAULT_KS)
    parser.add_argument("--ns", type=int, nargs="+", default=DEFAULT_NS)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--tf", type=float, default=1500.0)
    parser.add_argument("--dt", type=float, default=0.001)
    parser.add_argument("--seed-base", type=int, default=12345)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--bin", default="bin/scanning_rate")
    parser.add_argument("--output", default="output/first_used_dt.csv")
    return parser.parse_args()


def parse_stdout(stdout: str) -> dict:
    fields = {}
    for line in stdout.splitlines():
        match = VALUE_RE.match(line.strip())
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


def parse_value(raw):
    if raw is None or raw == "NA":
        return None
    try:
        return float(raw)
    except ValueError:
        return raw


def run_one(task):
    binary, n, k, run_id, seed, tf, dt = task
    cmd = [
        binary,
        str(n),
        str(run_id),
        f"{tf}",
        f"{dt}",
        "0.1",
        str(seed),
        f"{k}",
        "0",
        f"{dt}",
        "0", "0", "0",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"[error] N={n} k={k} run={run_id}: {result.stderr.strip()}", file=sys.stderr)
        return None

    fields = parse_stdout(result.stdout)
    return {
        "k": k,
        "N": n,
        "run": run_id,
        "seed": seed,
        "id_first_used": parse_value(fields.get("id_first_used")),
        "t_used_first": parse_value(fields.get("t_used_first")),
        "t_wall_first": parse_value(fields.get("t_wall_first")),
        "dt_used_to_wall": parse_value(fields.get("dt_used_to_wall")),
    }


def format_cell(value):
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.9f}"
    return str(value)


def main():
    args = parse_args()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tasks = []
    for k in args.ks:
        for n in args.ns:
            for run_id in range(args.runs):
                seed = args.seed_base + int(k) * 1_000_000 + n * 1000 + run_id
                tasks.append((args.bin, n, k, run_id, seed, args.tf, args.dt))

    print(f"Total tasks: {len(tasks)} (ks={args.ks}, ns={args.ns}, runs={args.runs})")
    print(f"tf={args.tf}, dt={args.dt}, jobs={args.jobs}")

    rows = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_one, task): task for task in tasks}
        for index, fut in enumerate(as_completed(futures), 1):
            row = fut.result()
            if row is not None:
                rows.append(row)
                print(f"k={row['k']} N={row['N']} run={row['run']} dt_used_to_wall={row['dt_used_to_wall']}")
            if index % 10 == 0 or index == len(tasks):
                print(f"  done {index}/{len(tasks)}")

    rows.sort(key=lambda r: (r["k"], r["N"], r["run"]))
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["k", "N", "run", "seed", "id_first_used",
                         "t_used_first", "t_wall_first", "dt_used_to_wall"])
        for row in rows:
            writer.writerow([
                format_cell(row["k"]),
                format_cell(row["N"]),
                format_cell(row["run"]),
                format_cell(row["seed"]),
                format_cell(row["id_first_used"]),
                format_cell(row["t_used_first"]),
                format_cell(row["t_wall_first"]),
                format_cell(row["dt_used_to_wall"]),
            ])

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
