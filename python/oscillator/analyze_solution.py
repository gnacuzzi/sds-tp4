import argparse
import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DEFAULT_INPUT_DIR = Path("output")
DEFAULT_OUTPUT_DIR = Path("images/oscillator")
DEFAULT_SUMMARY_PATH = Path("output/oscillator_mse_summary.csv")
KNOWN_METHODS = {"euler", "verlet", "beeman", "gear5"}
METHOD_ORDER = ["euler", "verlet", "beeman", "gear5"]
METHOD_COLORS = {
    "euler": "#e41a1c",
    "verlet": "#377eb8",
    "beeman": "#4daf4a",
    "gear5": "#984ea3",
}

FIGSIZE = (10, 8)
DPI = 300
TITLE_SIZE = 18
LABEL_SIZE = 18
TICK_SIZE = 15
LEGEND_SIZE = 15


def infer_method(path: Path) -> str:
    name = path.stem.lower()
    if name.startswith("oscillator_"):
        return name.removeprefix("oscillator_")
    return name


def load_csv(path: Path) -> dict[str, np.ndarray]:
    columns = {
        "time": [],
        "x_numeric": [],
        "v_numeric": [],
        "x_analytic": [],
        "v_analytic": [],
    }

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for key in columns:
                columns[key].append(float(row[key]))

    return {key: np.array(values, dtype=float) for key, values in columns.items()}


def compute_metrics(data: dict[str, np.ndarray]) -> dict[str, float]:
    x_error = data["x_numeric"] - data["x_analytic"]
    v_error = data["v_numeric"] - data["v_analytic"]

    return {
        "mse_position": float(np.mean(x_error ** 2)),
        "mse_velocity": float(np.mean(v_error ** 2)),
        "max_abs_position_error": float(np.max(np.abs(x_error))),
        "max_abs_velocity_error": float(np.max(np.abs(v_error))),
    }


def plot_solution(method: str, data: dict[str, np.ndarray], metrics: dict[str, float], output_dir: Path) -> Path:
    figure, axes = plt.subplots(2, 1, figsize=FIGSIZE, sharex=True)

    axes[0].plot(data["time"], data["x_analytic"], label="Analitica", linewidth=2.0, color="#1d3557")
    axes[0].plot(data["time"], data["x_numeric"], label=f"Numerica ({method})", linewidth=1.4, color="#d62828")
    axes[0].set_ylabel("Posicion x(t)", fontsize=LABEL_SIZE)
    axes[0].tick_params(axis="both", labelsize=TICK_SIZE)
    axes[0].legend(fontsize=LEGEND_SIZE)

    axes[1].plot(data["time"], data["v_analytic"], label="Analitica", linewidth=2.0, color="#1d3557")
    axes[1].plot(data["time"], data["v_numeric"], label=f"Numerica ({method})", linewidth=1.4, color="#2a9d8f")
    axes[1].set_xlabel("Tiempo", fontsize=LABEL_SIZE)
    axes[1].set_ylabel("Velocidad v(t)", fontsize=LABEL_SIZE)
    axes[1].tick_params(axis="both", labelsize=TICK_SIZE)
    axes[1].legend(fontsize=LEGEND_SIZE)

    figure.suptitle(
        f"Oscilador amortiguado: {method}\n"
        f"ECM posicion = {metrics['mse_position']:.6e}, "
        f"ECM velocidad = {metrics['mse_velocity']:.6e}",
        fontsize=TITLE_SIZE
    )
    figure.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{method}_solution_comparison.png"
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    return output_path


def plot_combined_position(
    datasets: dict[str, dict[str, np.ndarray]],
    output_dir: Path,
    stride: int,
    solid_lines: bool,
) -> Path:
    figure, axis = plt.subplots(figsize=(11, 6))
    stride = max(stride, 1)

    first_method = next(method for method in METHOD_ORDER if method in datasets)
    reference = datasets[first_method]
    reference_slice = slice(None, None, stride)

    if solid_lines:
        axis.plot(
            reference["time"],
            reference["x_analytic"],
            color="black",
            linewidth=2.2,
            label="Analitica",
            zorder=4,
        )
    else:
        axis.scatter(
            reference["time"][reference_slice],
            reference["x_analytic"][reference_slice],
            marker="o",
            s=10,
            color="black",
            label="Analitica",
            zorder=4,
        )

    for method in METHOD_ORDER:
        if method not in datasets:
            continue

        data = datasets[method]
        if solid_lines:
            axis.plot(
                data["time"],
                data["x_numeric"],
                linewidth=1.5,
                color=METHOD_COLORS[method],
                label=method,
                alpha=0.9,
            )
        else:
            data_slice = slice(None, None, stride)
            axis.scatter(
                data["time"][data_slice],
                data["x_numeric"][data_slice],
                marker="x",
                s=46,
                linewidths=1.7,
                color=METHOD_COLORS[method],
                label=method,
                alpha=0.85,
            )

    axis.set_xlabel("Tiempo", fontsize=LABEL_SIZE)
    axis.set_ylabel("Posicion x(t)", fontsize=LABEL_SIZE)
    axis.tick_params(axis="both", labelsize=TICK_SIZE)
    axis.legend(fontsize=LEGEND_SIZE, loc="best", ncols=2)
    figure.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        "combined_position_methods_solid.png" if solid_lines else "combined_position_methods.png"
    )
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    return output_path


def write_summary(rows: list[dict[str, object]], summary_path: Path) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "method",
                "input_file",
                "samples",
                "mse_position",
                "mse_velocity",
                "max_abs_position_error",
                "max_abs_velocity_error",
                "plot_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def collect_input_files(paths: list[str]) -> list[Path]:
    if paths:
        return [Path(path) for path in paths]

    return sorted(
        path
        for path in DEFAULT_INPUT_DIR.glob("oscillator_*.csv")
        if infer_method(path) in KNOWN_METHODS
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Grafica soluciones analitica vs numerica del sistema 1 y calcula ECM."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="CSV(s) del oscilador. Si se omite, usa output/oscillator_*.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directorio donde guardar figuras",
    )
    parser.add_argument(
        "--summary",
        default=str(DEFAULT_SUMMARY_PATH),
        help="CSV resumen con ECM por metodo",
    )
    parser.add_argument(
        "--combined-position",
        action="store_true",
        help="Genera un unico grafico de posicion con analitica y todos los metodos.",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=25,
        help="Submuestreo para graficos con marcadores. Default: 25",
    )
    parser.add_argument(
        "--solid-lines",
        action="store_true",
        help="Usa curvas solidas en el grafico combinado de posicion.",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    input_files = collect_input_files(args.files)
    if not input_files:
        parser.error("No se encontraron archivos CSV para analizar.")

    output_dir = Path(args.output_dir)
    summary_path = Path(args.summary)
    summary_rows: list[dict[str, object]] = []
    datasets: dict[str, dict[str, np.ndarray]] = {}

    for input_path in input_files:
        if not input_path.is_file():
            parser.error(f"Archivo no encontrado: {input_path}")

        method = infer_method(input_path)
        data = load_csv(input_path)
        datasets[method] = data
        metrics = compute_metrics(data)
        plot_path = plot_solution(method, data, metrics, output_dir)

        summary_rows.append(
            {
                "method": method,
                "input_file": str(input_path),
                "samples": len(data["time"]),
                "mse_position": f"{metrics['mse_position']:.12e}",
                "mse_velocity": f"{metrics['mse_velocity']:.12e}",
                "max_abs_position_error": f"{metrics['max_abs_position_error']:.12e}",
                "max_abs_velocity_error": f"{metrics['max_abs_velocity_error']:.12e}",
                "plot_file": str(plot_path),
            }
        )

        print(
            f"{method}: "
            f"ECM posicion={metrics['mse_position']:.6e}, "
            f"ECM velocidad={metrics['mse_velocity']:.6e}, "
            f"figura={plot_path}"
        )

    write_summary(summary_rows, summary_path)
    print(f"Resumen guardado en {summary_path}")

    if args.combined_position:
        combined_path = plot_combined_position(datasets, output_dir, args.stride, args.solid_lines)
        print(f"Grafico combinado guardado en {combined_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
