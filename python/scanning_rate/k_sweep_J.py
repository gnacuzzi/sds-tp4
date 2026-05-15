import argparse
import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────

# Internally we index k by its exponent. The actual k is 10**k_exp.
K_EXPONENTS = [1, 2, 3, 4, 5]                 # drop trailing values if not simulated
N_VALUES    = [100, 200, 300, 400, 500, 600, 700, 800, 900]
N_RUNS      = 10
ENERGY_VALIDATION_N = 500                     # representative N for Plot A

# Per-N steady-state cutoff (seconds). Reused from fu_vs_n.py and extended.
T_CUT_BY_N = {
    100: 100.0,
    200: 250.0,
    300: 800.0,
    400: 900.0,
    500: 1000.0,
    600: 1250.0,
    700: 1400.0,
    800: 1500.0,
    900: 1600.0,
    1000: 1700.0,
}

# Output directory containing all simulation files (flat layout).
OUTPUT_DIR = Path("output")

# Files written by this script.
DEFAULT_SUMMARY_PATH = Path("output/k_sweep_J_summary.csv")
DEFAULT_FIG_A_PATH   = Path("images/scanning_rate/k_sweep_energy_validation.png")
DEFAULT_FIG_B_PATH   = Path("images/scanning_rate/k_sweep_fu_vs_N.png")

# Visual style.
FIGSIZE_A    = (12, 9)        # 2x3 (or 2x2) grid for Plot A
FIGSIZE_B    = (10, 6)
DPI          = 300
TITLE_SIZE   = 18
LABEL_SIZE   = 16
TICK_SIZE    = 14
LEGEND_SIZE  = 13


# ── k-formatting helpers ──────────────────────────────────────────────────────

def k_value(k_exp: int) -> float:
    return float(10 ** k_exp)


def k_to_label(k_exp: int) -> str:
    """1 -> 'k = 10¹'."""
    superscripts = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
    return f"k = 10{str(k_exp).translate(superscripts)}"


# ── File-path builders ────────────────────────────────────────────────────────

def file_id(k_exp: int, run: int) -> int:
    if k_exp == 3:
        return run
    return (10 ** k_exp) + run


def events_path(N: int, k_exp: int, run: int) -> Path:
    return OUTPUT_DIR / f"{N}_cfc{file_id(k_exp, run)}.txt"


def energy_path(N: int, k_exp: int, run: int) -> Path:
    return OUTPUT_DIR / f"{N}_energy{file_id(k_exp, run)}.txt"


# ── File parsing ──────────────────────────────────────────────────────────────

def parse_events(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Returns (times, fu) from an events file (no header).

    Each line: t  <time>  <cumulative_collisions>  <F_u>
    """
    times: list[float] = []
    fus: list[float] = []
    with path.open() as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                times.append(float(parts[1]))
                fus.append(float(parts[-1]))
            except ValueError:
                continue
    return np.array(times, dtype=float), np.array(fus, dtype=float)


def parse_energy(path: Path) -> dict[str, np.ndarray]:
    """Reads the energy file by its header columns.

    Expected header: time kinetic pair_potential wall_potential obstacle_potential total
    """
    columns: dict[str, list[float]] = {
        "time": [],
        "kinetic": [],
        "pair_potential": [],
        "wall_potential": [],
        "obstacle_potential": [],
        "total": [],
    }
    with path.open() as handle:
        header = handle.readline().split()
        for line in handle:
            parts = line.split()
            if len(parts) != len(header):
                continue
            for key, value in zip(header, parts):
                if key in columns:
                    try:
                        columns[key].append(float(value))
                    except ValueError:
                        pass
    return {key: np.array(values, dtype=float) for key, values in columns.items()}


# ── Per-(k, N, run) F_u computation ───────────────────────────────────────────

def collect_fu_steady_state(events_p: Path, t_cut: float) -> tuple[float, float, int]:
    """Returns (mean_fu, std_fu, n_samples) for samples with t > t_cut.

    Returns (nan, nan, 0) if file missing or no samples after cutoff.
    """
    if not events_p.is_file():
        return float("nan"), float("nan"), 0
    times, fus = parse_events(events_p)
    if times.size == 0:
        return float("nan"), float("nan"), 0
    mask = times > t_cut
    sample = fus[mask]
    if sample.size == 0:
        return float("nan"), float("nan"), 0
    return float(np.mean(sample)), float(np.std(sample)), int(sample.size)


# ── Plot A: energy validation ─────────────────────────────────────────────────

def plot_energy_validation(
    output_path: Path,
    representative_N: int = ENERGY_VALIDATION_N,
) -> None:
    """One panel per k (k_exp), each showing total energy vs time at the
    representative N. Drift or growth in `total` means dt is too large for that k.
    """
    n_k = len(K_EXPONENTS)
    ncols = 2 if n_k <= 4 else 3
    nrows = (n_k + ncols - 1) // ncols
    figure, axes = plt.subplots(nrows, ncols, figsize=FIGSIZE_A, sharex=False)

    if n_k == 1:
        axes_flat = [axes]
    else:
        axes_flat = np.array(axes).flatten().tolist()

    for idx, k_exp in enumerate(K_EXPONENTS):
        axis = axes_flat[idx]
        # Use realization 0 as the representative.
        path = energy_path(representative_N, k_exp, run=0)
        if not path.is_file():
            axis.text(
                0.5, 0.5,
                f"Missing:\n{path.name}",
                ha="center", va="center", transform=axis.transAxes,
                fontsize=TICK_SIZE, color="#888"
            )
            axis.set_title(k_to_label(k_exp), fontsize=LABEL_SIZE)
            continue

        data = parse_energy(path)
        t = data["time"]
        if t.size == 0:
            axis.text(
                0.5, 0.5, "Empty file",
                ha="center", va="center", transform=axis.transAxes,
                fontsize=TICK_SIZE, color="#888",
            )
            axis.set_title(k_to_label(k_exp), fontsize=LABEL_SIZE)
            continue

        axis.plot(t, data["total"], label="total", color="#1d3557", linewidth=1.6)
        axis.plot(t, data["kinetic"], label="kinetic",
                  color="#e63946", linewidth=1.0, alpha=0.7)
        axis.plot(
            t,
            data["pair_potential"] + data["wall_potential"] + data["obstacle_potential"],
            label="potential", color="#2a9d8f", linewidth=1.0, alpha=0.7,
        )

        # Drift diagnostic: relative change of total from start.
        e0 = data["total"][0] if data["total"].size else 1.0
        drift = (data["total"][-1] - e0) / e0 if e0 != 0 else 0.0
        axis.set_title(
            f"{k_to_label(k_exp)}   (N={representative_N}, drift={drift:+.2%})",
            fontsize=LABEL_SIZE,
        )
        axis.set_xlabel("Tiempo (s)", fontsize=LABEL_SIZE - 2)
        axis.set_ylabel("Energía", fontsize=LABEL_SIZE - 2)
        axis.tick_params(axis="both", labelsize=TICK_SIZE - 2)
        axis.legend(fontsize=LEGEND_SIZE - 2, loc="best")
        axis.grid(True, alpha=0.3)

    # Hide any unused panels.
    for j in range(n_k, len(axes_flat)):
        axes_flat[j].axis("off")

    figure.suptitle(
        "Validación de energía: dt válido si total se mantiene constante",
        fontsize=TITLE_SIZE,
    )
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"[Plot A] Saved energy-validation grid to {output_path}")


# ── Plot B: <F_u>(N) per k ────────────────────────────────────────────────────

def build_fu_summary() -> list[dict]:
    """Iterates the (k_exp, N, run) matrix and collects steady-state F_u stats."""
    rows: list[dict] = []
    for k_exp in K_EXPONENTS:
        for N in N_VALUES:
            t_cut = T_CUT_BY_N.get(N, 0.0)
            for run in range(N_RUNS):
                ev_path = events_path(N, k_exp, run)
                mean_fu, std_fu, n_samples = collect_fu_steady_state(ev_path, t_cut)
                rows.append(
                    {
                        "k": k_value(k_exp),
                        "k_exp": k_exp,
                        "N": N,
                        "run": run,
                        "t_cut": t_cut,
                        "mean_fu": mean_fu,
                        "std_fu": std_fu,
                        "n_samples": n_samples,
                        "events_file": str(ev_path),
                    }
                )
                if n_samples == 0:
                    print(
                        f"  MISSING/EMPTY: k=10^{k_exp}, N={N}, run={run} "
                        f"-> {ev_path.name}"
                    )
    return rows


def aggregate_per_kN(rows: list[dict]) -> dict[int, dict[int, dict]]:
    """{k_exp: {N: {mean, std, n_runs}}} aggregating per-realization means over runs."""
    out: dict[int, dict[int, dict]] = {}
    for k_exp in K_EXPONENTS:
        out[k_exp] = {}
        for N in N_VALUES:
            cell = [
                r["mean_fu"]
                for r in rows
                if r["k_exp"] == k_exp and r["N"] == N and not np.isnan(r["mean_fu"])
            ]
            if not cell:
                out[k_exp][N] = {"mean": float("nan"), "std": float("nan"), "n_runs": 0}
                continue
            arr = np.asarray(cell, dtype=float)
            out[k_exp][N] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "n_runs": int(arr.size),
            }
    return out


def plot_fu_vs_N_per_k(
    aggregate: dict[int, dict[int, dict]], output_path: Path
) -> None:
    figure, axis = plt.subplots(figsize=FIGSIZE_B)

    # Colormap by log10(k) == k_exp.
    log_ks = np.array(K_EXPONENTS, dtype=float)
    norm = mcolors.Normalize(vmin=log_ks.min(), vmax=log_ks.max())
    cmap = cm.get_cmap("viridis")

    plotted_any = False
    for k_exp in K_EXPONENTS:
        means = np.array([aggregate[k_exp][N]["mean"] for N in N_VALUES])
        stds = np.array([aggregate[k_exp][N]["std"] for N in N_VALUES])
        if np.all(np.isnan(means)):
            print(f"  Plot B: no data for k=10^{k_exp}, skipping curve")
            continue
        color = cmap(norm(k_exp))
        axis.errorbar(
            N_VALUES, means, yerr=stds,
            fmt="-o", markersize=6, linewidth=1.6,
            color=color, ecolor=color, elinewidth=1.2, capsize=4,
        )
        plotted_any = True

    if not plotted_any:
        print("[Plot B] No data plotted; check file paths.")
        plt.close(figure)
        return

    axis.set_xlabel("N (número de partículas)", fontsize=LABEL_SIZE)
    axis.set_ylabel(r"$\langle F_u \rangle$", fontsize=LABEL_SIZE)
    axis.tick_params(axis="both", labelsize=TICK_SIZE)
    axis.set_xticks(N_VALUES)
    axis.grid(True, alpha=0.3)

    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = figure.colorbar(sm, ax=axis, pad=0.02)
    cbar.set_label(r"$\log_{10}(k)$ [N/m]", fontsize=LABEL_SIZE - 2)
    cbar.ax.tick_params(labelsize=TICK_SIZE - 2)

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"[Plot B] Saved <F_u>(N) per k to {output_path}")


# ── Summary CSV ───────────────────────────────────────────────────────────────

def write_summary(rows: list[dict], summary_path: Path) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "k", "k_exp", "N", "run", "t_cut",
                "mean_fu", "std_fu", "n_samples", "events_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {summary_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TP4 item 2.4: k-sweep on F_u (Plots A and B).",
    )
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument("--fig-energy", default=str(DEFAULT_FIG_A_PATH))
    parser.add_argument("--fig-fu", default=str(DEFAULT_FIG_B_PATH))
    parser.add_argument(
        "--energy-N", type=int, default=ENERGY_VALIDATION_N,
        help="Representative N for the energy-validation panels.",
    )
    parser.add_argument(
        "--skip-energy", action="store_true",
        help="Skip Plot A (e.g., if energy files aren't ready yet).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.skip_energy:
        plot_energy_validation(Path(args.fig_energy), representative_N=args.energy_N)
    else:
        print("[Plot A] Skipped (--skip-energy).")

    print("\nBuilding F_u summary across (k_exp, N, run) ...")
    rows = build_fu_summary()
    write_summary(rows, Path(args.summary))

    print("\nAggregating per (k_exp, N) ...")
    aggregate = aggregate_per_kN(rows)

    plot_fu_vs_N_per_k(aggregate, Path(args.fig_fu))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
