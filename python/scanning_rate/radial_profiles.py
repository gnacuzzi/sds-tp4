import argparse
import csv
import glob
import math
import os
from pathlib import Path
import sys

import matplotlib
import numpy as np
from matplotlib import colors

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from python.plot_format import apply_scientific_y

#todo: revisar esto:  
# El único punto conceptual que todavía dejaría anotado para el informe es este: el promedio actual es
# promedio sobre snapshots registrados, no promedio temporal ponderado por dt. Como el enunciado dice
#  “promediar para los distintos tiempos registrados”, esto me parece defendible. Si el docente esperara
#  un promedio temporal continuo, habría que usar los tiempos reales del header y ponderar cada snapshot
#  por el intervalo hasta el siguiente. Pero para lo que pide textual y para cómo vienen generando
#  outputs, el cálculo actual es coherente.

# =========================
# CONFIG
# =========================
D_S = 0.2
R_MAX = 40  # radio del sistema
CENTER = np.array([0.0, 0.0])
TICK_FONT_SIZE = 15
OUTPUT_DIR = "images"
DEFAULT_PROFILE_CSV = Path("output/radial_profiles_tp4.csv")
DEFAULT_PLOT_S_MIN = 1.8
DEFAULT_PLOT_S_MAX = 38.0
# Fijar limites del eje Y para comparar distintos N con la misma escala.
# Ejemplo: FIXED_Y_LIMS = (0.0, 1.2)
#FIXED_Y_LIMS = (0.0, 2.5) #remove comment to set limits

# =========================
# PARSER
# =========================
def read_dynamic_file(filename):
    snapshots = []

    with open(filename, "r") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        n = int(lines[i].strip())
        i += 1

        header = lines[i].split()
        t = float(header[1]) if len(header) >= 2 and header[0] == "t" else 0.0
        i += 1

        particles = []

        for _ in range(n):
            parts = lines[i].split()
            x = float(parts[1])
            y = float(parts[2])
            vx = float(parts[3])
            vy = float(parts[4])
            state = int(parts[5])

            particles.append((x, y, vx, vy, state))
            i += 1

        snapshots.append((t, particles))

    return snapshots


def dynamic_run_id(path):
    base = os.path.basename(path)
    run_token = base.split("_dynamic", 1)[1].split(".txt", 1)[0]

    return int(run_token) if run_token.isdigit() else None


def filter_dynamic_files(files, run_ids):
    if run_ids is None:
        return files

    selected = set(run_ids)

    return [path for path in files if dynamic_run_id(path) in selected]


def read_profile_from_csv(n, csv_path=DEFAULT_PROFILE_CSV):
    csv_path = Path(csv_path)

    if not csv_path.is_file():
        return None

    rows = []
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            if int(row["N"]) == n:
                rows.append(row)

    if not rows:
        return None

    rows.sort(key=lambda row: float(row["S"]))

    S = np.array([float(row["S"]) for row in rows], dtype=float)
    rho = np.array([float(row["rho_mean"]) for row in rows], dtype=float)
    v = np.array([float(row["v_mean"]) for row in rows], dtype=float)
    J = np.array([float(row["jin_mean"]) for row in rows], dtype=float)

    return S, rho, v, J


# =========================
# COMPUTE RADIAL PROFILES
# =========================
def compute_profiles(snapshots):
    num_bins = int(R_MAX / D_S)

    rho_acc = np.zeros(num_bins)
    v_acc = np.zeros(num_bins)
    count_acc = np.zeros(num_bins)

    for t, particles in snapshots:
        for (x, y, vx, vy, state) in particles:

            # solo frescas
            if state != 0:
                continue

            R = np.array([x, y])
            r = np.linalg.norm(R)

            if r == 0 or r >= R_MAX:
                continue

            # producto escalar
            dot = x * vx + y * vy

            # solo las que van hacia el centro
            if dot >= 0:
                continue

            bin_idx = int(r / D_S)
            if bin_idx >= num_bins:
                continue

            # velocidad radial
            v_radial = dot / r

            rho_acc[bin_idx] += 1
            v_acc[bin_idx] += v_radial
            count_acc[bin_idx] += 1

    # =========================
    # PROMEDIOS
    # =========================
    rho = np.zeros(num_bins)
    v = np.zeros(num_bins)

    n_snapshots = len(snapshots)

    for i in range(num_bins):
        if count_acc[i] > 0:
            v[i] = v_acc[i] / count_acc[i]

        # densidad = cantidad / (área * cantidad de snapshots)
        r_inner = i * D_S
        r_outer = (i + 1) * D_S
        area = math.pi * (r_outer**2 - r_inner**2)

        if n_snapshots > 0:
            rho[i] = rho_acc[i] / (area * n_snapshots)

    Jin = rho * np.abs(v)

    S = (np.arange(num_bins) + 0.5) * D_S

    return S, rho, v, Jin


# =========================
# MAIN (MULTIPLE RUNS)
# =========================
def process_N(n, run_ids=None, profiles_csv=DEFAULT_PROFILE_CSV):
    csv_profile = read_profile_from_csv(n, profiles_csv)
    if csv_profile is not None:
        print(f"Usando perfil radial desde {profiles_csv} para N={n}")
        return csv_profile

    pattern = f"output/{n}_dynamic*.txt"
    files = [path for path in sorted(glob.glob(pattern)) if os.path.getsize(path) > 0]
    files = filter_dynamic_files(files, run_ids)

    if len(files) == 0:
        print(f"No se encontraron archivos para N={n}")
        return None, None, None, None

    all_rho = []
    all_v = []

    for file in files:
        print(f"Procesando {file}")
        snapshots = read_dynamic_file(file)

        S, rho, v, _ = compute_profiles(snapshots)

        all_rho.append(rho)
        all_v.append(v)

    if len(all_rho) == 0:
        print(f"No hay datos validos para N={n}")
        return None, None, None, None

    # promedio entre realizaciones
    rho_mean = np.mean(all_rho, axis=0)
    v_mean = np.mean(all_v, axis=0)
    J_mean = rho_mean * np.abs(v_mean)

    return S, rho_mean, v_mean, J_mean


# =========================
# PLOT
# =========================
def setup_axis(ax, title, ylabel):
    ax.set_xlabel("S (m)", fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.tick_params(labelsize=TICK_FONT_SIZE)


def save_single_profile(S, values, n, filename, title, ylabel, color):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(S, values, color=color)

    setup_axis(ax, title, ylabel)
    apply_scientific_y(ax, fontsize=TICK_FONT_SIZE)
    fig.tight_layout()
    fig.savefig(filename, dpi=300)
    plt.close(fig)


def save_zoomed_j_profile(S, J, n):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(S, J, color="tab:green")

    x_min, x_max = 1.5, 5.0
    ax.set_xlim(x_min, x_max)

    mask = (S >= x_min) & (S <= x_max)
    if np.any(mask):
        y_zoom = J[mask]
        y_min = np.min(y_zoom)
        y_max = np.max(y_zoom)

        if y_max > y_min:
            pad = 0.08 * (y_max - y_min)
            ax.set_ylim(y_min - pad, y_max + pad)
        else:
            # Degenerate case: all values are equal in the zoomed interval.
            delta = 0.1 * (abs(y_min) + 1.0)
            ax.set_ylim(y_min - delta, y_max + delta)

    setup_axis(ax, rf"$J_{{\mathrm{{in}}}}(S)$ con zoom para N = {n}", r"$J_{\mathrm{in}}(S)$")
    apply_scientific_y(ax, fontsize=TICK_FONT_SIZE)
    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/radial_Jin_zoom_N{n}.png", dpi=300)
    plt.close(fig)


def plot_profiles(S, rho, v, J, n):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    return


def plot_profiles_multiscale(S, rho, v, J, n):
    fig, ax_rho = plt.subplots(figsize=(9, 5))

    ax_v = ax_rho.twinx()
    ax_j = ax_rho.twinx()
    ax_j.spines["right"].set_position(("axes", 1.14))

    line_rho, = ax_rho.plot(
        S,
        rho,
        color="tab:blue",
        label=r"$\langle \rho_f^{\mathrm{in}}\rangle(S)$"
    )
    line_v, = ax_v.plot(
        S,
        np.abs(v),
        color="tab:orange",
        label=r"$\left|\langle v_f^{\mathrm{in}}\rangle(S)\right|$"
    )
    line_j, = ax_j.plot(
        S,
        J,
        color="tab:green",
        label=r"$J_{\mathrm{in}}(S)$"
    )

    ax_rho.set_xlabel("S (m)", fontsize=14)
    ax_rho.set_ylabel(r"$\langle \rho_f^{\mathrm{in}}\rangle(S)$", color="tab:blue", fontsize=14)
    ax_v.set_ylabel(r"$\left|\langle v_f^{\mathrm{in}}\rangle(S)\right|$", color="tab:orange", fontsize=14)
    ax_j.set_ylabel(r"$J_{\mathrm{in}}(S)$", color="tab:green", fontsize=14)

    ax_rho.tick_params(axis="y", labelcolor="tab:blue", labelsize=TICK_FONT_SIZE)
    ax_v.tick_params(axis="y", labelcolor="tab:orange", labelsize=TICK_FONT_SIZE)
    ax_j.tick_params(axis="y", labelcolor="tab:green", labelsize=TICK_FONT_SIZE)
    ax_rho.tick_params(axis="x", labelsize=TICK_FONT_SIZE)
    apply_scientific_y(ax_rho, ax_v, ax_j, fontsize=TICK_FONT_SIZE)

    lines = [line_rho, line_v, line_j]
    ax_rho.legend(lines, [line.get_label() for line in lines], fontsize=11, loc="upper left")

    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/radial_profiles_multiscale_N{n}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def discover_ns():
    if DEFAULT_PROFILE_CSV.is_file():
        ns = set()

        with DEFAULT_PROFILE_CSV.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                ns.add(int(row["N"]))

        if ns:
            return sorted(ns)

    ns = set()

    for path in glob.glob("output/*_dynamic*.txt"):
        if os.path.getsize(path) == 0:
            continue

        base = os.path.basename(path)
        n_token = base.split("_dynamic", 1)[0]

        if n_token.isdigit():
            ns.add(int(n_token))

    return sorted(ns)


def plot_all_n_profiles(results, metric, ylabel, output_file, s_min=DEFAULT_PLOT_S_MIN, s_max=DEFAULT_PLOT_S_MAX):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ns = sorted(results.keys())
    cmap = plt.get_cmap("viridis")
    norm = colors.Normalize(vmin=min(ns), vmax=max(ns))

    for n in ns:
        S, rho, v, J = results[n]
        values = {
            "rho": rho,
            "velocity": np.abs(v),
            "jin": J,
        }[metric]

        mask = (S >= s_min) & (S <= s_max)
        if not np.any(mask):
            continue

        ax.plot(S[mask], values[mask], color=cmap(norm(n)), linewidth=2)

    ax.set_xlim(s_min, s_max)
    ax.set_xlabel("S (m)", fontsize=16)
    ax.set_ylabel(ylabel, fontsize=16)
    ax.tick_params(labelsize=14)
    apply_scientific_y(ax, fontsize=14)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label("N", fontsize=14)
    cbar.ax.tick_params(labelsize=12)

    fig.tight_layout()
    fig.savefig(output_file, dpi=300)
    plt.close(fig)


def plot_all_n(results, s_min=DEFAULT_PLOT_S_MIN, s_max=DEFAULT_PLOT_S_MAX):
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    plot_all_n_profiles(
        results,
        "rho",
        r"$\langle \rho_f^{\mathrm{in}}\rangle(S)$",
        f"{OUTPUT_DIR}/radial_rho_all_N.png",
        s_min=s_min,
        s_max=s_max,
    )
    plot_all_n_profiles(
        results,
        "velocity",
        r"$\left|\langle v_f^{\mathrm{in}}\rangle(S)\right|$",
        f"{OUTPUT_DIR}/radial_velocity_all_N.png",
        s_min=s_min,
        s_max=s_max,
    )
    plot_all_n_profiles(
        results,
        "jin",
        r"$J_{\mathrm{in}}(S)$",
        f"{OUTPUT_DIR}/radial_Jin_all_N.png",
        s_min=s_min,
        s_max=s_max,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Compute radial profiles for fresh incoming particles.")
    parser.add_argument("N", type=int, nargs="?", help="Single N to process.")
    parser.add_argument("--all", action="store_true", help="Process all available N values.")
    parser.add_argument("--ns", type=int, nargs="+", default=None, help="Specific N values to process.")
    parser.add_argument("--run-ids", type=int, nargs="+", default=None, help="Only process these run ids.")
    parser.add_argument(
        "--profiles-csv",
        default=str(DEFAULT_PROFILE_CSV),
        help="Use this radial profile CSV if it exists.",
    )
    parser.add_argument("--plot-s-min", type=float, default=DEFAULT_PLOT_S_MIN, help="Minimum S shown in all-N profile plots.")
    parser.add_argument("--plot-s-max", type=float, default=DEFAULT_PLOT_S_MAX, help="Maximum S shown in all-N profile plots.")

    return parser.parse_args()


def main():
    args = parse_args()

    if args.all:
        ns = discover_ns()
    elif args.ns is not None:
        ns = args.ns
    elif args.N is not None:
        ns = [args.N]
    else:
        raise SystemExit("Usage: python3 python/scanning_rate/radial_profiles.py N | --all | --ns N ...")

    results = {}

    for n in ns:
        S, rho, v, J = process_N(n, run_ids=args.run_ids, profiles_csv=args.profiles_csv)

        if S is None:
            continue

        results[n] = (S, rho, v, J)

    if args.all or args.ns is not None:
        if not results:
            raise SystemExit("No valid radial data found.")

        plot_all_n(results, s_min=args.plot_s_min, s_max=args.plot_s_max)


if __name__ == "__main__":
    main()
