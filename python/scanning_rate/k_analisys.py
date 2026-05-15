import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle
import numpy as np
import argparse

USE_NUMPY = 1

FONT_LABELS = 16
FONT_TICKS  = 14

NUM_OF_N = [100,200,300,400,500, 600, 700, 800, 900, 1000]

# ==============================
# PARSER
# ==============================

parser = argparse.ArgumentParser()
parser.add_argument("n", type=int, help="N number of files")
parser.add_argument("-ns", "--noshow", action="store_false", help="If argument is passed the program will not show plots, just save them")
parser.add_argument("-ts", "--test",action="store_true", help="Uest for testing purposes, only prosesses the forst two Num of N" )
args = parser.parse_args()

if args.test:
    print("Running in TEST mode")
    NUM_OF_N = [100,200]

def parse_dynamic_file(filename):
    frames = []
    print(f"File opened {filename}")

    with open(filename, "r") as f:
        while True:
            time_line = f.readline().strip()
            if not time_line:
                break
            try:
                parts = time_line.split()
                t = float(parts[1])
                cfc = int(parts[2])
                frames.append((t, cfc))
            except Exception as e:
                print(f"Error opening file {filename}, {e}")

    return frames




N_vals = []
J_means = []
J_stds = []

# ==============================
# Generate separate plots for diffrent N's
# ==============================
def data_collection():

    # Collect data
    J = {}  # J[(k, N)] = list of per-realization J values
    for N in NUM_OF_N:
        for k_val in range(1, 6):
            for idx in range(args.n):
                if k_val == 3:
                    id_num = idx
                else:
                    id_num = (10**k_val) + idx

                INPUT_FILE = f"output/{N}_cfc{id_num}.txt"
                frames = parse_dynamic_file(INPUT_FILE)
                time_long, cfcval_long = map(list, zip(*frames))
                # Keep only points where CFC changes
                time = [time_long[0]]
                cfcval = [cfcval_long[0]]
                for j in range(1, len(cfcval_long)):
                    if cfcval_long[j] != cfcval_long[j - 1]:
                        time.append(time_long[j])
                        cfcval.append(cfcval_long[j])
                try:
                    # Fit linear regression
                    coef = np.polyfit(time, cfcval, 1)
                    poly1d_fn = np.poly1d(coef)

                    J.setdefault((k_val, N), []).append(coef[0])
                except Exception as e:

                    print(f"Error in N={N}, run={idx}:", e)


    print(J)
    # Compute mean and std per (k, N)
    J_mean = {key: np.mean(vals) for key, vals in J.items()}
    J_std  = {key: np.std(vals)  for key, vals in J.items()}

    # ─── Figure 1: ⟨J⟩(N), one line per k ─────────────────────
    fig1, ax1 = plt.subplots()
    for k_val in range(1, 6):
        Ns    = sorted(N for (kk, N) in J_mean.keys() if kk == k_val)
        means = [J_mean[(k_val, N)] for N in Ns]
        stds  = [J_std[(k_val, N)]  for N in Ns]
        ax1.errorbar(Ns, means, yerr=stds, label=f"k=10^{k_val}",
                     marker="o", capsize=4)
    ax1.set_xlabel("N")
    ax1.set_ylabel("⟨J⟩")
    ax1.legend()  # or colorbar
    fig1.savefig("images/J_vs_N_per_k.png", dpi=300)

    # ─── Figure 2: scalar(k) ─────────────────────────────────
    ks_plot, max_J, N_star = [], [], []
    for k_val in range(1, 6):
        Ns    = sorted(N for (kk, N) in J_mean.keys() if kk == k_val)
        means = np.array([J_mean[(k_val, N)] for N in Ns])
        idx_star = np.argmax(means)
        ks_plot.append(10**k_val)
        max_J.append(means[idx_star])
        N_star.append(Ns[idx_star])

    fig2, axL = plt.subplots()
    axR = axL.twinx()
    axL.plot(ks_plot, max_J, "-o", color="tab:blue", label="max⟨J⟩")
    axR.plot(ks_plot, N_star, "--s", color="tab:orange", label="N*")
    axL.set_xscale("log")
    axL.set_xlabel("k")
    axL.set_ylabel("max⟨J⟩",  color="tab:blue")
    axR.set_ylabel("N*",     color="tab:orange")
    fig2.savefig("images/scalar_vs_k.png", dpi=300)

data_collection()
