import glob
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from python.scanning_rate.radial_profiles import compute_profiles, read_dynamic_file


# =========================
# CONFIG
# =========================
dS = 0.2
TARGET_S = 2.0
OUTPUT_DIR = "images"
TICK_FONT_SIZE = 15

# lista de N que querés analizar
Ns = [50, 100, 200, 300, 400, 500, 600, 700, 800]


def collect_bin_values(n, target_s):
    files = sorted(glob.glob(f"output/{n}_dynamic*.txt"))
    if len(files) == 0:
        print(f"No se encontraron archivos para N={n}")
        return None

    rho_runs = []
    v_runs = []
    j_runs = []
    target_idx = None

    for file in files:
        snapshots = read_dynamic_file(file)
        S, rho, v, _ = compute_profiles(snapshots)

        if target_idx is None:
            target_idx = int(np.argmin(np.abs(S - target_s)))

        rho_i = rho[target_idx]
        v_i = v[target_idx]

        rho_runs.append(rho_i)
        v_runs.append(v_i)
        j_runs.append(rho_i * abs(v_i))

    rho_runs = np.array(rho_runs)
    v_runs = np.array(v_runs)
    j_runs = np.array(j_runs)

    rho_mean = np.mean(rho_runs)
    v_mean = np.mean(v_runs)
    j_mean = rho_mean * abs(v_mean)
    ddof = 1 if len(rho_runs) > 1 else 0

    return {
        "S": S[target_idx],
        "rho_mean": rho_mean,
        "rho_std": np.std(rho_runs, ddof=ddof),
        "v_mean": v_mean,
        "v_abs_std": np.std(np.abs(v_runs), ddof=ddof),
        "j_mean": j_mean,
        "j_std": np.std(j_runs, ddof=ddof),
    }


def setup_axis(ax, ylabel):
    ax.set_xlabel("Número de particulas (N)", fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.tick_params(labelsize=TICK_FONT_SIZE)


def save_single_vs_n(values, errors, filename, ylabel, color):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        Ns,
        values,
        yerr=errors,
        marker="o",
        capsize=5,
        color=color,
    )
    setup_axis(ax, ylabel)
    fig.tight_layout()
    fig.savefig(filename, dpi=300)
    plt.close(fig)


def save_multiscale_vs_n(rho_vals, rho_errs, v_vals, v_errs, j_vals, j_errs):
    fig, ax_rho = plt.subplots(figsize=(9, 5))

    ax_v = ax_rho.twinx()
    ax_j = ax_rho.twinx()
    ax_j.spines["right"].set_position(("axes", 1.14))

    rho_plot = ax_rho.errorbar(
        Ns,
        rho_vals,
        yerr=rho_errs,
        marker="o",
        capsize=5,
        color="tab:blue",
        label=r"$\langle \rho_f^{\mathrm{in}}\rangle(S\approx 2)$",
    )
    v_plot = ax_v.errorbar(
        Ns,
        v_vals,
        yerr=v_errs,
        marker="o",
        capsize=5,
        color="tab:orange",
        label=r"$\left|\langle v_f^{\mathrm{in}}\rangle(S\approx 2)\right|$",
    )
    j_plot = ax_j.errorbar(
        Ns,
        j_vals,
        yerr=j_errs,
        marker="o",
        capsize=5,
        color="tab:green",
        label=r"$J_{\mathrm{in}}(S\approx 2)$",
    )

    ax_rho.set_xlabel("Número de particulas (N)", fontsize=14)
    ax_rho.set_ylabel(
        r"$\langle \rho_f^{\mathrm{in}}\rangle(S\approx 2)$",
        color="tab:blue",
        fontsize=14,
    )
    ax_v.set_ylabel(
        r"$\left|\langle v_f^{\mathrm{in}}\rangle(S\approx 2)\right|$",
        color="tab:orange",
        fontsize=14,
    )
    ax_j.set_ylabel(
        r"$J_{\mathrm{in}}(S\approx 2)$",
        color="tab:green",
        fontsize=14,
    )

    ax_rho.tick_params(axis="y", labelcolor="tab:blue", labelsize=TICK_FONT_SIZE)
    ax_v.tick_params(axis="y", labelcolor="tab:orange", labelsize=TICK_FONT_SIZE)
    ax_j.tick_params(axis="y", labelcolor="tab:green", labelsize=TICK_FONT_SIZE)
    ax_rho.tick_params(axis="x", labelsize=TICK_FONT_SIZE)

    ax_rho.legend(
        [rho_plot, v_plot, j_plot],
        [
            r"$\langle \rho_f^{\mathrm{in}}\rangle(S\approx 2)$",
            r"$\left|\langle v_f^{\mathrm{in}}\rangle(S\approx 2)\right|$",
            r"$J_{\mathrm{in}}(S\approx 2)$",
        ],
        fontsize=10,
        loc="upper left",
    )

    fig.tight_layout()
    fig.savefig(
        f"{OUTPUT_DIR}/radial_vs_N_multiscale.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    rho_vals = []
    rho_errs = []
    v_vals = []
    v_errs = []
    j_vals = []
    j_errs = []

    for n in Ns:
        print(f"Procesando N = {n}")
        values = collect_bin_values(n, TARGET_S)

        if values is None:
            continue

        rho_vals.append(values["rho_mean"])
        rho_errs.append(values["rho_std"])
        v_vals.append(abs(values["v_mean"]))
        v_errs.append(values["v_abs_std"])
        j_vals.append(values["j_mean"])
        j_errs.append(values["j_std"])

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        Ns,
        rho_vals,
        yerr=rho_errs,
        marker="o",
        capsize=5,
        label=r"$\langle \rho_f^{\mathrm{in}}\rangle(S\approx 2)$",
    )
    ax.errorbar(
        Ns,
        v_vals,
        yerr=v_errs,
        marker="o",
        capsize=5,
        label=r"$\left|\langle v_f^{\mathrm{in}}\rangle(S\approx 2)\right|$",
    )
    ax.errorbar(
        Ns,
        j_vals,
        yerr=j_errs,
        marker="o",
        capsize=5,
        label=r"$J_{\mathrm{in}}(S\approx 2)$",
    )

    setup_axis(ax, "Valor")
    ax.legend(fontsize=12)
    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/radial_vs_N.png", dpi=300)
    plt.close(fig)

    save_single_vs_n(
        rho_vals,
        rho_errs,
        f"{OUTPUT_DIR}/radial_vs_N_rho.png",
        r"$\langle \rho_f^{\mathrm{in}}\rangle(S\approx 2)$",
        "tab:blue",
    )
    save_single_vs_n(
        v_vals,
        v_errs,
        f"{OUTPUT_DIR}/radial_vs_N_velocity.png",
        r"$\left|\langle v_f^{\mathrm{in}}\rangle(S\approx 2)\right|$",
        "tab:orange",
    )
    save_single_vs_n(
        j_vals,
        j_errs,
        f"{OUTPUT_DIR}/radial_vs_N_Jin.png",
        r"$J_{\mathrm{in}}(S\approx 2)$",
        "tab:green",
    )
    save_multiscale_vs_n(rho_vals, rho_errs, v_vals, v_errs, j_vals, j_errs)


if __name__ == "__main__":
    main()
