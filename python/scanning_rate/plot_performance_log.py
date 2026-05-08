from collections import defaultdict
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


TP3_FILE = "output/performance_tp3.csv"
TP4_FILE = "output/performance.csv"
OUTPUT_FILE = "images/performance_tp3_vs_tp4_log.png"


def read_times_by_n(path):
    times_by_n = defaultdict(list)

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            n = int(row["N"])
            time = float(row["time"])

            if n <= 0 or time <= 0.0:
                raise ValueError(f"Log scale requires positive N and time values in {path}")

            times_by_n[n].append(time)

    if not times_by_n:
        raise ValueError(f"No benchmark data found in {path}")

    return times_by_n


def summarize(times_by_n):
    ns = sorted(times_by_n.keys())
    means = []
    stds = []

    for n in ns:
        samples = np.array(times_by_n[n], dtype=float)
        means.append(float(np.mean(samples)))
        stds.append(float(np.std(samples, ddof=1)) if len(samples) > 1 else 0.0)

    return np.array(ns, dtype=float), np.array(means), np.array(stds)


def log_safe_yerr(means, stds):
    lower_err = np.minimum(stds, means - 1e-12)

    return np.vstack([lower_err, stds])


tp3_data = read_times_by_n(TP3_FILE)
tp4_data = read_times_by_n(TP4_FILE)
tp3_ns, tp3_means, tp3_stds = summarize(tp3_data)
tp4_ns, tp4_means, tp4_stds = summarize(tp4_data)
all_ns = sorted(set(tp3_data.keys()) | set(tp4_data.keys()))

plt.figure(figsize=(9, 5.5))
plt.xscale("log")
plt.yscale("log")

plt.errorbar(
    tp3_ns,
    tp3_means,
    yerr=log_safe_yerr(tp3_means, tp3_stds),
    marker="o",
    linestyle="-",
    capsize=4,
    linewidth=2,
    label="TP3"
)

plt.errorbar(
    tp4_ns,
    tp4_means,
    yerr=log_safe_yerr(tp4_means, tp4_stds),
    marker="s",
    linestyle="-",
    capsize=4,
    linewidth=2,
    label="TP4"
)

plt.xlim(min(all_ns) * 0.9, max(all_ns) * 1.05)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)
plt.xlabel("Number of particles (N)", fontsize=16)
plt.ylabel("Execution time (s)", fontsize=16)
plt.legend(fontsize=13)
plt.tight_layout()

Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUT_FILE, dpi=300)
plt.close()

print(f"Saved {OUTPUT_FILE}")
