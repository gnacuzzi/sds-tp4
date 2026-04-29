import argparse
import csv
import os
import subprocess
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


METHODS = ["euler", "verlet", "beeman", "gear5"]
DEFAULT_DTS = [1e-1, 5e-2, 1e-2, 5e-3, 1e-3, 5e-4]
DEFAULT_TF = 5.0
DEFAULT_SAMPLE_EVERY = 1
DEFAULT_BINARY = Path("bin/oscillator")
DEFAULT_OUTPUT_DIR = Path("output/oscillator_dt_sweep")
DEFAULT_SUMMARY_PATH = Path("output/oscillator_dt_sweep_summary.csv")
DEFAULT_FIGURE_PATH = Path("images/oscillator/dt_vs_mse_position.png")
DEFAULT_FIGURE_VELOCITY_PATH = Path("images/oscillator/dt_vs_mse_velocity.png")

FIGSIZE = (10, 6)
DPI = 300
TITLE_SIZE = 18
LABEL_SIZE = 18
TICK_SIZE = 15
LEGEND_SIZE = 15

COLORS = {
    "euler": "#d62828",
    "verlet": "#f4a261",
    "beeman": "#2a9d8f",
    "gear5": "#1d3557",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Barre dt para el sistema 1 y grafica ECM en escala log-log."
    )
    parser.add_argument(
        "--binary",
        default=str(DEFAULT_BINARY),
        help="Ruta al ejecutable bin/oscillator",
    )
    parser.add_argument(
        "--dts",
        nargs="+",
        type=float,
        default=DEFAULT_DTS,
        help="Lista de pasos temporales a evaluar",
    )
    parser.add_argument(
        "--tf",
        type=float,
        default=DEFAULT_TF,
        help="Tiempo final de simulacion",
    )
    parser.add_argument(
        "--sample-every",
        type=int,
        default=DEFAULT_SAMPLE_EVERY,
        help="Cada cuantos pasos guardar muestras",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directorio donde guardar los CSV intermedios",
    )
    parser.add_argument(
        "--summary",
        default=str(DEFAULT_SUMMARY_PATH),
        help="CSV resumen con los ECM de cada corrida",
    )
    parser.add_argument(
        "--figure",
        default=str(DEFAULT_FIGURE_PATH),
        help="Ruta de salida para la figura ECM posicion vs dt",
    )
    parser.add_argument(
        "--velocity-figure",
        default=str(DEFAULT_FIGURE_VELOCITY_PATH),
        help="Ruta de salida para la figura ECM velocidad vs dt",
    )
    return parser.parse_args()


def parse_summary(stdout: str) -> dict[str, float]:
    summary: dict[str, float] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            summary[key.strip()] = float(value.strip())
        except ValueError:
            continue
    return summary


def run_method(
    binary: Path,
    output_dir: Path,
    method: str,
    dt: float,
    tf: float,
    sample_every: int,
) -> dict[str, object]:
    csv_path = output_dir / f"{method}_dt_{dt:.6g}.csv"
    command = [
        str(binary),
        method,
        str(csv_path),
        f"{dt:.12g}",
        f"{tf:.12g}",
        str(sample_every),
    ]

    result = subprocess.run(command, check=True, capture_output=True, text=True)
    summary = parse_summary(result.stdout)

    return {
        "method": method,
        "dt": dt,
        "tf": tf,
        "sample_every": sample_every,
        "steps": int(summary["steps"]),
        "mse_position": summary["mse_position"],
        "mse_velocity": summary["mse_velocity"],
        "max_abs_position_error": summary["max_abs_position_error"],
        "max_abs_velocity_error": summary["max_abs_velocity_error"],
        "csv_file": str(csv_path),
    }


def write_summary(rows: list[dict[str, object]], summary_path: Path) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "method",
                "dt",
                "tf",
                "sample_every",
                "steps",
                "mse_position",
                "mse_velocity",
                "max_abs_position_error",
                "max_abs_velocity_error",
                "csv_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def plot_metric(rows: list[dict[str, object]], metric: str, ylabel: str, output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=FIGSIZE)

    for method in METHODS:
        method_rows = [row for row in rows if row["method"] == method]
        method_rows.sort(key=lambda row: float(row["dt"]))

        dts = np.array([float(row["dt"]) for row in method_rows], dtype=float)
        values = np.array([float(row[metric]) for row in method_rows], dtype=float)

        axis.plot(
            dts,
            values,
            marker="o",
            linewidth=2.0,
            markersize=7,
            color=COLORS[method],
            label=method,
        )

    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("Paso temporal dt", fontsize=LABEL_SIZE)
    axis.set_ylabel(ylabel, fontsize=LABEL_SIZE)
    axis.set_title("Oscilador amortiguado: ECM vs dt", fontsize=TITLE_SIZE)
    axis.tick_params(axis="both", labelsize=TICK_SIZE)
    axis.legend(fontsize=LEGEND_SIZE)

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    args = parse_args()
    binary = Path(args.binary)
    output_dir = Path(args.output_dir)
    summary_path = Path(args.summary)
    figure_path = Path(args.figure)
    velocity_figure_path = Path(args.velocity_figure)

    if not binary.is_file():
        raise SystemExit(f"No se encontro el ejecutable: {binary}")

    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for method in METHODS:
        for dt in args.dts:
            row = run_method(binary, output_dir, method, dt, args.tf, args.sample_every)
            rows.append(row)
            print(
                f"{method:>6} dt={dt:.6g} "
                f"ECM_pos={float(row['mse_position']):.6e} "
                f"ECM_vel={float(row['mse_velocity']):.6e}"
            )

    write_summary(rows, summary_path)
    plot_metric(rows, "mse_position", "ECM de posicion", figure_path)
    plot_metric(rows, "mse_velocity", "ECM de velocidad", velocity_figure_path)

    print(f"Resumen guardado en {summary_path}")
    print(f"Figura posicion guardada en {figure_path}")
    print(f"Figura velocidad guardada en {velocity_figure_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
