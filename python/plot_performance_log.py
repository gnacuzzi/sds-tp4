import csv
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

# Escalas logaritmicas (ejemplo tipico: log-log)
USE_LOG_X = True
USE_LOG_Y = True

times_by_n = defaultdict(list)

with open("output/performance.csv", "r") as f:
    reader = csv.reader(f)

    next(reader)  # skip header

    for row in reader:
        n = int(row[0])
        t = float(row[1])
        times_by_n[n].append(t)

if len(times_by_n) == 0:
    raise ValueError("No se encontraron datos de benchmark en output/performance.csv")

ns = sorted(times_by_n.keys())
means = []
stds = []

for n in ns:
    samples = np.array(times_by_n[n], dtype=float)
    means.append(float(np.mean(samples)))
    if len(samples) > 1:
        stds.append(float(np.std(samples, ddof=1)))
    else:
        stds.append(0.0)


plt.figure(figsize=(8,5))
yerr = np.array(stds)

if USE_LOG_X:
    if any(n <= 0 for n in ns):
        raise ValueError("N debe ser > 0 para usar escala logaritmica en X")
    plt.xscale("log")

    # Reduce empty space on the left/right in log scale.
    plt.xlim(min(ns) * 0.9, max(ns) * 1.05)
else:
    span = max(ns) - min(ns)
    if span == 0:
        span = max(ns) * 0.1 if max(ns) != 0 else 1.0
    plt.xlim(min(ns) - 0.05 * span, max(ns) + 0.05 * span)

if USE_LOG_Y:
    if any(t <= 0 for t in means):
        raise ValueError("Los tiempos de ejecucion deben ser > 0 para usar escala logaritmica en Y")

    # Prevent negative lower error bars in log scale.
    lower_err = np.minimum(np.array(stds), np.array(means) - 1e-12)
    upper_err = np.array(stds)
    yerr = np.vstack([lower_err, upper_err])
    plt.yscale("log")

plt.errorbar(
    ns,
    means,
    yerr=yerr,
    marker="o",
    linestyle="-",
    capsize=4
)

plt.xlabel("Número de particulas (N)", fontsize=14)
plt.ylabel("Tiempo de ejecucion (s)", fontsize=14)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)

#plt.ylim(0, max(means) * 1.5)
plt.tight_layout()

plt.savefig("images/performance_plot_log.png", dpi=300)

plt.show()