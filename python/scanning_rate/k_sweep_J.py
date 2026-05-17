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

K_EXPONENTS = [1, 2, 3, 4]
N_VALUES    = [100, 200, 300, 400, 500, 600, 700, 800, 900]
N_RUNS      = 10
ENERGY_VALIDATION_N = 500

# Adaptive transient cutoff (matches k_sweep_radial.py).
T_CUT_FRACTION = 0.20
T_CUT_MIN      = 50.0

OUTPUT_DIR = Path("output")

DEFAULT_SUMMARY_PATH     = Path("output/k_sweep_J_summary.csv")
DEFAULT_FIG_B_PATH       = Path("images/scanning_rate/k_sweep_J_vs_N.png")
DEFAULT_FIG_SUMMARY_PATH = Path("images/scanning_rate/j_summary_vs_k.png")

FIGSIZE_A    = (12, 9)
FIGSIZE_B    = (10, 6)
FIGSIZE_SUM  = (9, 6)
DPI          = 300
TITLE_SIZE   = 18
LABEL_SIZE   = 16
TICK_SIZE    = 14
LEGEND_SIZE  = 13


# ── k-formatting helpers ──────────────────────────────────────────────────────

def k_value(k_exp: int) -> float:
    return float(10 ** k_exp)


def k_to_label(k_exp: int) -> str:
    superscripts = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
    return f"k = 10{str(k_exp).translate(superscripts)}"


# ── File-path builders ────────────────────────────────────────────────────────

def file_id(k_exp: int, run: int) -> int:
    if k_exp == 3:
        return run
    return (10 ** k_exp) + run


def cfc_path(N: int, k_exp: int, run: int) -> Path:
    return OUTPUT_DIR / f"{N}_cfc{file_id(k_exp, run)}.txt"



# ── File parsing ──────────────────────────────────────────────────────────────

def parse_cfc(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Returns (times, cfc) from a cfc file (no header).

    Each line: t  <time>  <C_fc>
    """
    times: list[float] = []
    cfc: list[float] = []
    with path.open() as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                times.append(float(parts[1]))
                cfc.append(float(parts[2]))
            except ValueError:
                continue
    return np.array(times, dtype=float), np.array(cfc, dtype=float)

# ── Per-(k, N, run) J computation ─────────────────────────────────────────────

def compute_J_slope(cfc_p: Path) -> tuple[float, int, float, float]:
    if not cfc_p.is_file():
        return float("nan"), 0, 0.0, 0.0

    times, cfc = parse_cfc(cfc_p)
    if times.size < 2:
        return float("nan"), 0, 0.0, 0.0

    t_max = float(times[-1])
    t_cut = max(T_CUT_MIN, T_CUT_FRACTION * t_max)

    # Drop transient.
    mask = times > t_cut
    times = times[mask]
    cfc = cfc[mask]
    if times.size < 2:
        return float("nan"), 0, t_max, t_cut

    # Keep only points where the counter actually changes.
    diffs = np.diff(cfc)
    change_mask = np.concatenate(([True], diffs != 0))
    times = times[change_mask]
    cfc = cfc[change_mask]
    if times.size < 2:
        return float("nan"), 0, t_max, t_cut

    try:
        slope, _intercept = np.polyfit(times, cfc, 1)
        return float(slope), int(times.size), t_max, t_cut
    except (np.linalg.LinAlgError, ValueError):
        return float("nan"), 0, t_max, t_cut

# ── Plot B: <J>(N) per k ──────────────────────────────────────────────────────

def build_J_summary() -> list[dict]:
    """Iterates the (k_exp, N, run) matrix and collects per-realization J."""
    rows: list[dict] = []
    for k_exp in K_EXPONENTS:
        for N in N_VALUES:
            for run in range(N_RUNS):
                cfc_p = cfc_path(N, k_exp, run)
                J, n_samples, t_max, t_cut = compute_J_slope(cfc_p)
                rows.append(
                    {
                        "k": k_value(k_exp),
                        "k_exp": k_exp,
                        "N": N,
                        "run": run,
                        "t_max": t_max,
                        "t_cut_used": t_cut,
                        "n_samples": n_samples,
                        "J": J,
                        "cfc_file": str(cfc_p),
                    }
                )
                if n_samples == 0 or np.isnan(J):
                    print(
                        f"  MISSING/EMPTY/UNFITTABLE: k=10^{k_exp}, N={N}, run={run} "
                        f"-> {cfc_p.name}"
                    )
                else:
                    print(
                        f"  k=10^{k_exp} N={N} run={run}: "
                        f"t_max={t_max:.1f}, t_cut={t_cut:.1f}, "
                        f"samples={n_samples}, J={J:.4e}"
                    )
    return rows


def aggregate_per_kN(rows: list[dict]) -> dict[int, dict[int, dict]]:
    """{k_exp: {N: {mean, std, n_runs}}} aggregating per-realization J over runs."""
    out: dict[int, dict[int, dict]] = {}
    for k_exp in K_EXPONENTS:
        out[k_exp] = {}
        for N in N_VALUES:
            cell = [
                r["J"]
                for r in rows
                if r["k_exp"] == k_exp and r["N"] == N and not np.isnan(r["J"])
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


def plot_J_vs_N_per_k(
    aggregate: dict[int, dict[int, dict]], output_path: Path
) -> None:
    figure, axis = plt.subplots(figsize=FIGSIZE_B)

    log_ks = np.array(K_EXPONENTS, dtype=float)
    norm = mcolors.Normalize(vmin=log_ks.min(), vmax=log_ks.max())
    cmap = plt.get_cmap("viridis")

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
    axis.set_ylabel(r"$\langle J \rangle$", fontsize=LABEL_SIZE)
    axis.tick_params(axis="both", labelsize=TICK_SIZE)
    axis.set_xticks(N_VALUES)
    axis.grid(False)

    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = figure.colorbar(sm, ax=axis, pad=0.02)
    cbar.set_label(r"$\log_{10}(k)$ [N/m]", fontsize=LABEL_SIZE - 2)
    cbar.ax.tick_params(labelsize=TICK_SIZE - 2)

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"[Plot B] Saved <J>(N) per k to {output_path}")


# ── Summary plot: max<J>(k) and N*(k) on twin y-axes ──────────────────────────

def plot_J_summary_vs_k(
    aggregate: dict[int, dict[int, dict]], output_path: Path
) -> None:
    """Extracts (max <J>, N*) per k from the aggregate and plots them vs k.

    Style mirrors jin_summary_vs_k.png:
      * Left axis (tab:blue, solid line + circles): max <J>
      * Right axis (tab:orange, dashed line + squares): N*
      * x-axis: k, log scale
      * Single legend in upper right
    """
    ks: list[float] = []
    max_Js: list[float] = []
    N_stars: list[int] = []

    for k_exp in K_EXPONENTS:
        means = np.array([aggregate[k_exp][N]["mean"] for N in N_VALUES], dtype=float)
        valid = ~np.isnan(means)
        if not np.any(valid):
            print(f"  Summary: no valid data for k=10^{k_exp}, skipping")
            continue
        Ns_arr = np.array(N_VALUES)[valid]
        means_v = means[valid]
        idx = int(np.argmax(means_v))
        ks.append(k_value(k_exp))
        max_Js.append(float(means_v[idx]))
        N_stars.append(int(Ns_arr[idx]))
        print(f"  k=10^{k_exp}: max<J>={means_v[idx]:.4e}, N*={Ns_arr[idx]}")

    if not ks:
        print("[Summary] No data plotted.")
        return

    figure, ax_left = plt.subplots(figsize=FIGSIZE_SUM)
    ax_right = ax_left.twinx()

    color_left = "#1f77b4"   # tab:blue, matches jin_summary_vs_k.png
    color_right = "#ff7f0e"  # tab:orange

    ax_left.plot(
        ks, max_Js, "-o",
        color=color_left, linewidth=2.0, markersize=9,
        label=r"$\max_N \langle J \rangle$",
    )
    ax_right.plot(
        ks, N_stars, "--s",
        color=color_right, linewidth=1.8, markersize=9,
        label=r"$N^*$",
    )

    ax_left.set_xscale("log")
    ax_left.set_xlabel(r"$k$ [N/m]", fontsize=LABEL_SIZE)
    ax_left.set_ylabel(
        r"$\max_N \langle J \rangle$",
        fontsize=LABEL_SIZE, color=color_left,
    )
    ax_right.set_ylabel(
        r"$N^*$ (argmax)",
        fontsize=LABEL_SIZE, color=color_right,
    )
    ax_left.tick_params(axis="y", labelcolor=color_left, labelsize=TICK_SIZE)
    ax_right.tick_params(axis="y", labelcolor=color_right, labelsize=TICK_SIZE)
    ax_left.tick_params(axis="x", labelsize=TICK_SIZE)
    ax_left.grid(False)

    # Combined legend across both axes, upper right to match reference.
    lines_left, labels_left = ax_left.get_legend_handles_labels()
    lines_right, labels_right = ax_right.get_legend_handles_labels()
    ax_left.legend(
        lines_left + lines_right,
        labels_left + labels_right,
        fontsize=LEGEND_SIZE, loc="upper right",
    )

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"[Summary] Saved max<J> & N* vs k to {output_path}")


# ── Summary CSV ───────────────────────────────────────────────────────────────

def write_summary(rows: list[dict], summary_path: Path) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "k", "k_exp", "N", "run",
                "t_max", "t_cut_used", "n_samples",
                "J", "cfc_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {summary_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TP4 item 2.4: k-sweep on J = slope of C_fc(t).",
    )
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument("--fig-J", default=str(DEFAULT_FIG_B_PATH))
    parser.add_argument(
        "--fig-summary", default=str(DEFAULT_FIG_SUMMARY_PATH),
        help="Output path for the max<J> & N* vs k summary figure.",
    )
    parser.add_argument(
        "--energy-N", type=int, default=ENERGY_VALIDATION_N,
        help="Representative N for the energy-validation panels.",
    )
    parser.add_argument(
        "--skip-energy", action="store_true",
        help="Skip Plot A (e.g., if energy files aren't ready yet).",
    )
    parser.add_argument(
        "--t-cut-fraction", type=float, default=T_CUT_FRACTION,
        help=f"Fraction of run duration to discard as transient (default {T_CUT_FRACTION}).",
    )
    parser.add_argument(
        "--t-cut-min", type=float, default=T_CUT_MIN,
        help=f"Minimum seconds to discard as transient (default {T_CUT_MIN}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    global T_CUT_FRACTION, T_CUT_MIN
    T_CUT_FRACTION = args.t_cut_fraction
    T_CUT_MIN = args.t_cut_min
    print(
        f"Transient cutoff: max({T_CUT_MIN:.1f}s, "
        f"{T_CUT_FRACTION*100:.0f}% of run duration)"
    )


    print("\nBuilding J summary across (k_exp, N, run) ...")
    rows = build_J_summary()
    write_summary(rows, Path(args.summary))

    print("\nAggregating per (k_exp, N) ...")
    aggregate = aggregate_per_kN(rows)

    plot_J_vs_N_per_k(aggregate, Path(args.fig_J))

    print("\nExtracting summary scalars (max<J>, N*) per k ...")
    plot_J_summary_vs_k(aggregate, Path(args.fig_summary))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())