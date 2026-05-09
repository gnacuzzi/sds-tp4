import argparse
import glob
import os
from pathlib import Path
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from python.scanning_rate.radial_profiles import compute_profiles, dynamic_run_id, read_dynamic_file


OUTPUT_DIR = "images"
DEFAULT_S_MIN = 1.5
DEFAULT_S_MAX = 5.0
TICK_FONT_SIZE = 15


def discover_ns():
    ns = set()

    for path in glob.glob("output/*_dynamic*.txt"):
        if os.path.getsize(path) == 0:
            continue

        base = os.path.basename(path)
        n_token = base.split("_dynamic", 1)[0]

        if n_token.isdigit():
            ns.add(int(n_token))

    return sorted(ns)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Average radial profiles over a selected S range and plot them as a function of N."
    )
    parser.add_argument("--ns", type=int, nargs="+", default=None, help="Specific N values to process.")
    parser.add_argument("--s-min", type=float, default=DEFAULT_S_MIN, help="Lower S bound in meters.")
    parser.add_argument("--s-max", type=float, default=DEFAULT_S_MAX, help="Upper S bound in meters.")
    parser.add_argument("--run-ids", type=int, nargs="+", default=None, help="Only process these run ids.")

    return parser.parse_args()


def collect_layer_averages(n, s_min, s_max, run_ids=None):
    files = [path for path in sorted(glob.glob(f"output/{n}_dynamic*.txt")) if os.path.getsize(path) > 0]
    if run_ids is not None:
        selected = set(run_ids)
        files = [path for path in files if dynamic_run_id(path) in selected]

    if len(files) == 0:
        print(f"No se encontraron archivos para N={n}")
        return None

    rho_runs = []
    v_runs = []
    j_runs = []
    selected_s = None

    for file in files:
        snapshots = read_dynamic_file(file)
        S, rho, v, J = compute_profiles(snapshots)
        mask = (S >= s_min) & (S <= s_max)

        if not np.any(mask):
            continue

        selected_s = S[mask]
        rho_runs.append(float(np.mean(rho[mask])))
        v_runs.append(float(np.mean(v[mask])))
        j_runs.append(float(np.mean(J[mask])))

    if len(rho_runs) == 0:
        print(f"No hay capas validas para N={n} en S=[{s_min}, {s_max}]")
        return None

    rho_runs = np.array(rho_runs)
    v_runs = np.array(v_runs)
    j_runs = np.array(j_runs)
    ddof = 1 if len(rho_runs) > 1 else 0

    return {
        "S_min": float(np.min(selected_s)),
        "S_max": float(np.max(selected_s)),
        "samples": len(rho_runs),
        "rho_mean": float(np.mean(rho_runs)),
        "rho_std": float(np.std(rho_runs, ddof=ddof)),
        "v_mean": float(np.mean(v_runs)),
        "v_abs_mean": float(abs(np.mean(v_runs))),
        "v_abs_std": float(np.std(np.abs(v_runs), ddof=ddof)),
        "j_mean": float(np.mean(j_runs)),
        "j_std": float(np.std(j_runs, ddof=ddof)),
    }


def setup_axis(ax, ylabel):
    ax.set_xlabel("Number of particles (N)", fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.tick_params(labelsize=TICK_FONT_SIZE)


def save_single_vs_n(ns, values, errors, filename, ylabel, color):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        ns,
        values,
        yerr=errors,
        marker="o",
        linestyle="-",
        capsize=5,
        color=color,
    )
    setup_axis(ax, ylabel)
    fig.tight_layout()
    fig.savefig(filename, dpi=300)
    plt.close(fig)


def save_multiscale_vs_n(ns, rho_vals, rho_errs, v_vals, v_errs, j_vals, j_errs, s_min, s_max):
    fig, ax_rho = plt.subplots(figsize=(9, 5))

    ax_v = ax_rho.twinx()
    ax_j = ax_rho.twinx()
    ax_j.spines["right"].set_position(("axes", 1.14))

    rho_label = rf"$\langle \rho_f^{{\mathrm{{in}}}}\rangle$ for S $\in [{s_min:.1f}, {s_max:.1f}]$ m"
    v_label = rf"$|\langle v_f^{{\mathrm{{in}}}}\rangle|$ for S $\in [{s_min:.1f}, {s_max:.1f}]$ m"
    j_label = rf"$J_{{\mathrm{{in}}}}$ for S $\in [{s_min:.1f}, {s_max:.1f}]$ m"

    rho_plot = ax_rho.errorbar(ns, rho_vals, yerr=rho_errs, marker="o", capsize=5, color="tab:blue")
    v_plot = ax_v.errorbar(ns, v_vals, yerr=v_errs, marker="o", capsize=5, color="tab:orange")
    j_plot = ax_j.errorbar(ns, j_vals, yerr=j_errs, marker="o", capsize=5, color="tab:green")

    ax_rho.set_xlabel("Number of particles (N)", fontsize=14)
    ax_rho.set_ylabel(r"$\langle \rho_f^{\mathrm{in}}\rangle$", color="tab:blue", fontsize=14)
    ax_v.set_ylabel(r"$|\langle v_f^{\mathrm{in}}\rangle|$", color="tab:orange", fontsize=14)
    ax_j.set_ylabel(r"$J_{\mathrm{in}}$", color="tab:green", fontsize=14)

    ax_rho.tick_params(axis="y", labelcolor="tab:blue", labelsize=TICK_FONT_SIZE)
    ax_v.tick_params(axis="y", labelcolor="tab:orange", labelsize=TICK_FONT_SIZE)
    ax_j.tick_params(axis="y", labelcolor="tab:green", labelsize=TICK_FONT_SIZE)
    ax_rho.tick_params(axis="x", labelsize=TICK_FONT_SIZE)

    ax_rho.legend(
        [rho_plot, v_plot, j_plot],
        [rho_label, v_label, j_label],
        fontsize=9,
        loc="upper left",
    )

    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/radial_vs_N_multiscale.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    args = parse_args()

    if args.s_max <= args.s_min:
        raise SystemExit("--s-max must be greater than --s-min")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    ns_to_process = args.ns if args.ns is not None else discover_ns()

    ns = []
    rho_vals = []
    rho_errs = []
    v_vals = []
    v_errs = []
    j_vals = []
    j_errs = []

    for n in ns_to_process:
        print(f"Procesando N = {n}")
        values = collect_layer_averages(n, args.s_min, args.s_max, run_ids=args.run_ids)

        if values is None:
            continue

        ns.append(n)
        rho_vals.append(values["rho_mean"])
        rho_errs.append(values["rho_std"])
        v_vals.append(values["v_abs_mean"])
        v_errs.append(values["v_abs_std"])
        j_vals.append(values["j_mean"])
        j_errs.append(values["j_std"])

    if len(ns) == 0:
        raise SystemExit("No valid radial-vs-N data found.")

    save_single_vs_n(
        ns,
        rho_vals,
        rho_errs,
        f"{OUTPUT_DIR}/radial_vs_N_rho.png",
        r"$\langle \rho_f^{\mathrm{in}}\rangle$",
        "tab:blue",
    )
    save_single_vs_n(
        ns,
        v_vals,
        v_errs,
        f"{OUTPUT_DIR}/radial_vs_N_velocity.png",
        r"$|\langle v_f^{\mathrm{in}}\rangle|$",
        "tab:orange",
    )
    save_single_vs_n(
        ns,
        j_vals,
        j_errs,
        f"{OUTPUT_DIR}/radial_vs_N_Jin.png",
        r"$J_{\mathrm{in}}$",
        "tab:green",
    )
    save_multiscale_vs_n(
        ns,
        rho_vals,
        rho_errs,
        v_vals,
        v_errs,
        j_vals,
        j_errs,
        args.s_min,
        args.s_max,
    )

    print(f"Processed N values: {ns}")


if __name__ == "__main__":
    main()
