import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle
import numpy as np
import argparse

USE_NUMPY = 1

FONT_LABELS = 16
FONT_TICKS  = 14

NUM_OF_N = [50,100,200,300,400,500, 600, 700, 800]

# ==============================
# PARSER
# ==============================

parser = argparse.ArgumentParser()
parser.add_argument("n", type=int, help="N number of files")
parser.add_argument("-ns", "--noshow", action="store_false", help="If argument is passed the program will not show plots, just save them")
args = parser.parse_args()

def parse_dynamic_file(filename):
    frames = []

    with open(filename, "r") as f:
        while True:
            time_line = f.readline().strip()
            if not time_line:
                break
            
            parts = time_line.split()
            t = float(parts[1])
            cfc = int(parts[2])

            frames.append((t, cfc))

    return frames

N_vals = []
J_means = []
J_stds = []

# ==============================
# Generate separate plots for diffrent N's
# ==============================

for N in NUM_OF_N:
    plt.figure(figsize=(8, 5))

    # Generate distinct colors for each iteration Set1, tab10, Dark2
    colors = plt.cm.Set1(np.linspace(0, 1, args.n))
    J_values = []

    #Grab data from all runs of same N and plot them together
    for idx in range(args.n):
        INPUT_FILE = f"output/{N}_events{idx}.txt"
        frames = parse_dynamic_file(INPUT_FILE)

        time_long, cfcval_long = map(list, zip(*frames))

        # Keep only points where CFC changes
        time = [time_long[0]]
        cfcval = [cfcval_long[0]]

        for j in range(1, len(cfcval_long)):
            if cfcval_long[j] != cfcval_long[j - 1]:
                time.append(time_long[j])
                cfcval.append(cfcval_long[j])

        color = colors[idx]

        try:
            # Fit linear regression
            coef = np.polyfit(time, cfcval, 1)
            poly1d_fn = np.poly1d(coef)
            J_values.append(coef[0])

            # Scatter points
            plt.scatter(time, cfcval, color=color, s=7)

            # Extended regression line (full range)
            xline = np.linspace(0, 2000, 500)
            plt.plot(
                xline,
                poly1d_fn(xline),
                color=color,
                linestyle="--",
                linewidth=3
            )

        except Exception as e:
            #Add the single 0,0 scatterpoint so we get the correct legend
            J_values.append(0)
            plt.scatter(time, cfcval, color=color, s=15,
                        label=f"Run {idx} (J=0)")
            print(f"Error in N={N}, run={idx}:", e)
    
    
    J_mean = np.mean(J_values)
    J_std = np.std(J_values, ddof=1)

    N_vals.append(N)
    J_means.append(J_mean)
    J_stds.append(J_std)

    plt.grid(False)
    plt.xlabel("Tiempo (s)", fontsize=FONT_LABELS)
    plt.ylabel("Cfc(t)", fontsize=FONT_LABELS)
    plt.tick_params(labelsize=FONT_TICKS)


    plt.tight_layout()
    filename = f"images/Cfc_fit_N_{N}.png"
    plt.savefig(filename, dpi=600)
    if args.noshow:
        plt.show()


# ==============================
# Plot J vs N for all runs
# ==============================
N_vals = np.array(N_vals)
J_means = np.array(J_means)
J_stds = np.array(J_stds)
plt.figure(figsize=(8, 5))

plt.errorbar(
    N_vals,
    J_means,
    yerr=J_stds,
    fmt='o-',
    capsize=5,
    capthick=1,
)

#plt.fill_between(
#    N_vals,
#    J_means - J_stds,
#    J_means + J_stds,
#    alpha=0.15
#)

plt.xlabel("N", fontsize=FONT_LABELS)
plt.ylabel("⟨J⟩", fontsize=FONT_LABELS)
plt.tick_params(labelsize=FONT_TICKS)
plt.grid(False)

plt.tight_layout()
filename = "images/J_vs_N.png"
plt.savefig(filename, dpi=600)
if args.noshow:
    plt.show()



