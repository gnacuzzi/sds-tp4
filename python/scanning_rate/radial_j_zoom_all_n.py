import argparse
import glob
import os
import sys
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import colors

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from python.scanning_rate.radial_profiles import process_N


# =========================
# CONFIG
# =========================
OUTPUT_DIR = "images"
X_MIN = 1.5
X_MAX = 5.0
TICK_FONT_SIZE = 15


def parse_args():
    parser = argparse.ArgumentParser(
        description="Graficar perfiles de Jin con zoom para valores de N seleccionados."
    )
    parser.add_argument(
        "--ns",
        type=int,
        nargs="+",
        default=None,
        help="Valores especificos de N a procesar (ejemplo: --ns 50 100 200).",
    )
    parser.add_argument(
        "--run-ids",
        type=int,
        nargs="+",
        default=None,
        help="Solo procesar estos run ids.",
    )
    return parser.parse_args()


def discover_ns():
    files = glob.glob("output/*_dynamic*.txt")
    ns = set()

    for path in files:
        base = os.path.basename(path)
        if "_dynamic" not in base:
            continue

        n_token = base.split("_dynamic", 1)[0]
        if n_token.isdigit():
            ns.add(int(n_token))

    return sorted(ns)


def resolve_ns(selected_ns):
    available_ns = discover_ns()

    if len(available_ns) == 0:
        return []

    if selected_ns is None:
        return available_ns

    available_set = set(available_ns)
    missing = [n for n in selected_ns if n not in available_set]

    if len(missing) > 0:
        print(f"Advertencia: no se encontraron archivos para los N: {sorted(set(missing))}")

    return [n for n in selected_ns if n in available_set]


def main():
    args = parse_args()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ns = resolve_ns(args.ns)
    if len(ns) == 0:
        if args.ns is None:
            print("No se encontraron archivos dynamic en output/")
        else:
            print("No se encontraron archivos dynamic para los N seleccionados")
        return

    fig, ax = plt.subplots(figsize=(9, 5))

    all_y_in_zoom = []
    plotted = 0

    cmap = plt.get_cmap("viridis")
    if len(ns) > 1:
        norm = colors.Normalize(vmin=min(ns), vmax=max(ns))
    else:
        # Avoid zero-width normalization when there is only one N.
        norm = colors.Normalize(vmin=ns[0] - 0.5, vmax=ns[0] + 0.5)

    for n in ns:
        print(f"Procesando N = {n}")
        S, _, _, J = process_N(n, run_ids=args.run_ids)

        if S is None:
            continue

        mask = (S >= X_MIN) & (S <= X_MAX)
        if not np.any(mask):
            continue

        ax.plot(S[mask], J[mask], linewidth=2, color=cmap(norm(n)))
        all_y_in_zoom.append(J[mask])
        plotted += 1

    if plotted == 0:
        print("No se encontraron datos validos de J en el intervalo de zoom pedido")
        plt.close(fig)
        return

    ax.set_xlim(X_MIN, X_MAX)

    y_concat = np.concatenate(all_y_in_zoom)
    y_min = np.min(y_concat)
    y_max = np.max(y_concat)

    if y_max > y_min:
        pad = 0.08 * (y_max - y_min)
        ax.set_ylim(y_min - pad, y_max + pad)
    else:
        delta = 0.1 * (abs(y_min) + 1.0)
        ax.set_ylim(y_min - delta, y_max + delta)

    ax.set_xlabel("S (m)", fontsize=14)
    ax.set_ylabel(r"$J_{\mathrm{in}}(S)$", fontsize=14)
    ax.tick_params(labelsize=TICK_FONT_SIZE)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label("N", fontsize=14)
    cbar.ax.tick_params(labelsize=12)

    fig.tight_layout()
    out_path = f"{OUTPUT_DIR}/radial_Jin_zoom_all_N.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)

    print(f"Guardado: {out_path}")


if __name__ == "__main__":
    main()
