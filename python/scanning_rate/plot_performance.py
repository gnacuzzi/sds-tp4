import csv
import matplotlib.pyplot as plt


ns = []
times = []

with open("output/performance.csv", "r") as f:
    reader = csv.reader(f)

    next(reader)  # skip header

    for row in reader:
        ns.append(int(row[0]))
        times.append(float(row[1]))


plt.figure(figsize=(8,5))

plt.plot(
    ns,
    times,
    marker="o",
    linestyle="-"
)

plt.xlabel("Number of Particles (N)", fontsize=14)
plt.ylabel("Execution Time (s)", fontsize=14)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)

#plt.ylim(0, max(times) * 1.5)
plt.tight_layout()

plt.savefig("images/performance_plot.png", dpi=300)

plt.show()