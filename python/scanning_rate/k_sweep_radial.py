"""
k_sweep_radial.py — TP4 item 2.4 (radial branch)

For each (k, N, realization), parses the dynamic file frame-by-frame, selects
fresh inbound particles (state==0 and x·v < 0), bins them by radial distance S
from the center, and computes per-shell <rho_f^in>(S) and <v_f^in>(S). Then
averages those over time and realizations to produce J_in(S), aggregates over
the obstacle-near shell window S in [S_NEAR_MIN, S_NEAR_MAX], and finally plots:

  Plot C: <J_in|_{S~2}>(N) curves, one per k. Colormap+colorbar by log10(k).

Writes a summary CSV (k, k_exp, N, run, J_in_near, rho_near, v_near) so
plot_k_summary.py can produce Plot D.

Expected dynamic file format (frame-based, no header):

    <N>                                             ← line 1: particle count
    t  <time>  <num_collisions>  <unknown_float>    ← line 2: time stamp
    <id>  <x>  <y>  <vx>  <vy>  <state>             ← N rows
    ...
    <N>                                              ← next frame
    t  <time>  ...
    ...

State convention: 0 = fresh, 1 = used. Adjust `FRESH_STATE` if reversed.

File-naming convention (flat, all in output/):

    output/{N}_dynamic{id}.txt
    output/{N}_events{id}.txt
    output/{N}_energy{id}.txt

where  id = 10**k_exp + run   for k_exp != 3
       id = run               for k_exp == 3  (legacy)
"""

import argparse
import csv
import os
from pathlib import Path
from typing import Iterator

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
K_EXPONENTS = [1, 2, 3, 4, 5]
N_VALUES    = [100, 200, 300, 400, 500, 600, 700, 800, 900]
N_RUNS      = 10

# Per-N steady-state cutoff for time averaging (matches fu_vs_n.py).
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

# Radial binning.
S_MIN = 1.0       # inner edge of the bin range; the obstacle has r0 = 1 m
S_MAX = 40.0      # outer edge — half of L=80 (system radius)
DS    = 0.2       # shell width per the assignment

# Obstacle-near window: shells whose centers fall inside this range get
# averaged together to produce J_in|_{S~2}. S = 2 m is the rim of contact
# (obstacle r0 = 1 + particle r = 1). Default chosen broadly; tune from the
# 2.3 zoomed J_in(S) figure.
S_NEAR_MIN = 2.0
S_NEAR_MAX = 3.0

# Particle properties (for area normalization and inbound filter).
FRESH_STATE = 0   # 0 = fresh per the assignment

# Output directory (flat layout).
OUTPUT_DIR = Path("output")

# Outputs written by this script.
DEFAULT_SUMMARY_PATH = Path("output/k_sweep_radial_summary.csv")
DEFAULT_FIG_C_PATH   = Path("images/scanning_rate/k_sweep_J_in_near_vs_N.png")

# Visual style.
FIGSIZE      = (10, 6)
DPI          = 300
TITLE_SIZE   = 18
LABEL_SIZE   = 16
TICK_SIZE    = 14


# ── k and file-path helpers ───────────────────────────────────────────────────

def k_value(k_exp: int) -> float:
    return float(10 ** k_exp)


def file_id(k_exp: int, run: int) -> int:
    """Encodes (k_exp, run) into the integer used in filenames.

    Legacy convention: k=10^3 was the first sweep and uses bare run indices 0..9.
    Other k_exp values prefix the run with 10**k_exp to avoid collisions.

    WARNING: collisions are possible if N_RUNS grows large (e.g. k_exp=1
    with run=90 collides with k_exp=2, run=0 → both produce id=100). With
    N_RUNS=10 this scheme is safe.
    """
    if k_exp == 3:
        return run
    return (10 ** k_exp) + run


def dynamic_path(N: int, k_exp: int, run: int) -> Path:
    return OUTPUT_DIR / f"{N}_dynamic{file_id(k_exp, run)}.txt"


# ── Dynamic file frame parser ────────────────────────────────────────────────

def iter_dynamic_frames(path: Path) -> Iterator[tuple[float, np.ndarray]]:
    """Yields (time, particles) per frame.

    `particles` is an (N, 6) array with columns [id, x, y, vx, vy, state].
    """
    with path.open() as handle:
        while True:
            header = handle.readline()
            if not header:
                return
            header = header.strip()
            if not header:
                continue
            try:
                n_particles = int(header)
            except ValueError:
                # Defensive: skip malformed lines.
                continue

            time_line = handle.readline().split()
            # Expected: "t <time> <num_collisions> <unknown>"
            if len(time_line) < 2:
                return
            try:
                time = float(time_line[1])
            except (ValueError, IndexError):
                return

            rows = []
            for _ in range(n_particles):
                parts = handle.readline().split()
                if len(parts) < 6:
                    break
                # id, x, y, vx, vy, state
                rows.append([float(x) for x in parts[:6]])
            if len(rows) != n_particles:
                return
            yield time, np.array(rows, dtype=float)


# ── Per-frame computation: density + radial velocity per shell ───────────────

def shell_edges() -> np.ndarray:
    return np.arange(S_MIN, S_MAX + DS, DS)


def shell_centers(edges: np.ndarray) -> np.ndarray:
    return 0.5 * (edges[:-1] + edges[1:])


def shell_areas(edges: np.ndarray) -> np.ndarray:
    """Annular areas: pi*(r_out^2 - r_in^2) for each shell."""
    return np.pi * (edges[1:] ** 2 - edges[:-1] ** 2)


def per_frame_radial_stats(
    particles: np.ndarray, edges: np.ndarray
) -> dict[str, np.ndarray]:
    """Returns per-shell counts and sum of radial velocities for fresh inbound particles.

    To average correctly across frames and realizations later, we keep:
      - count_in[s]: number of fresh inbound particles in shell s
      - sumv_in[s]:  sum of v_radial for those particles (negative since inbound)

    Density and average velocity are computed at aggregation time.
    """
    n_shells = len(edges) - 1
    count = np.zeros(n_shells, dtype=int)
    sumv = np.zeros(n_shells, dtype=float)

    if particles.size == 0:
        return {"count": count, "sumv": sumv}

    state = particles[:, 5].astype(int)
    fresh = state == FRESH_STATE
    if not np.any(fresh):
        return {"count": count, "sumv": sumv}

    p = particles[fresh]
    x, y, vx, vy = p[:, 1], p[:, 2], p[:, 3], p[:, 4]
    r = np.sqrt(x * x + y * y)
    # Avoid division by zero at r=0.
    safe_r = np.where(r > 1e-12, r, 1e-12)
    # Radial component of velocity: v_r = (x*vx + y*vy) / r
    v_r = (x * vx + y * vy) / safe_r

    inbound = v_r < 0.0
    if not np.any(inbound):
        return {"count": count, "sumv": sumv}

    r_in = r[inbound]
    v_in = v_r[inbound]

    # np.digitize -> bin index (1-based), so subtract 1 to get 0-based shell idx.
    bin_idx = np.digitize(r_in, edges) - 1
    valid = (bin_idx >= 0) & (bin_idx < n_shells)
    bin_idx = bin_idx[valid]
    v_in = v_in[valid]

    np.add.at(count, bin_idx, 1)
    np.add.at(sumv, bin_idx, v_in)
    return {"count": count, "sumv": sumv}


# ── Per-realization aggregation ──────────────────────────────────────────────

def realization_radial_aggregates(
    dynamic_p: Path, t_cut: float
) -> dict[str, np.ndarray]:
    """Sum counts and v_r over time samples (t > t_cut) for one realization.

    Returns:
      total_count[s] — total number of fresh inbound observations in shell s
      total_sumv[s]  — total v_r summed over those observations (negative)
      n_frames       — number of frames included
    """
    edges = shell_edges()
    n_shells = len(edges) - 1
    total_count = np.zeros(n_shells, dtype=int)
    total_sumv = np.zeros(n_shells, dtype=float)
    n_frames = 0

    if not dynamic_p.is_file():
        return {"count": total_count, "sumv": total_sumv, "n_frames": 0}

    for time, particles in iter_dynamic_frames(dynamic_p):
        if time <= t_cut:
            continue
        stats = per_frame_radial_stats(particles, edges)
        total_count += stats["count"]
        total_sumv += stats["sumv"]
        n_frames += 1

    return {"count": total_count, "sumv": total_sumv, "n_frames": n_frames}


def near_obstacle_J(
    edges: np.ndarray,
    total_count: np.ndarray,
    total_sumv: np.ndarray,
    n_frames: int,
) -> tuple[float, float, float]:
    """Returns (J_in_near, rho_near, v_near_abs) averaged over shells near the obstacle.

    Densities: <rho>(s) = (total_count[s] / n_frames) / area[s]
    Velocities: <v>(s)  = total_sumv[s] / total_count[s]   (signed, negative for inbound)
    J_in(s)             = <rho>(s) * |<v>(s)|

    "Near" means shell centers in [S_NEAR_MIN, S_NEAR_MAX].
    Mirrors the assignment's "promediar las capas cercanas al obstáculo".
    """
    if n_frames == 0:
        return float("nan"), float("nan"), float("nan")

    centers = shell_centers(edges)
    areas = shell_areas(edges)

    rho = np.where(areas > 0, (total_count / n_frames) / areas, 0.0)
    safe_count = np.where(total_count > 0, total_count, 1)
    v_avg = np.where(total_count > 0, total_sumv / safe_count, 0.0)
    v_abs = np.abs(v_avg)
    J_in = rho * v_abs

    near_mask = (centers >= S_NEAR_MIN) & (centers <= S_NEAR_MAX)
    if not np.any(near_mask):
        return float("nan"), float("nan"), float("nan")

    # Only include shells with at least some observations.
    has_data = total_count > 0
    use_mask = near_mask & has_data
    if not np.any(use_mask):
        return float("nan"), float("nan"), float("nan")

    return (
        float(np.mean(J_in[use_mask])),
        float(np.mean(rho[use_mask])),
        float(np.mean(v_abs[use_mask])),
    )


# ── Sweep across (k_exp, N, run) ─────────────────────────────────────────────

def build_radial_summary() -> list[dict]:
    edges = shell_edges()
    rows: list[dict] = []
    for k_exp in K_EXPONENTS:
        for N in N_VALUES:
            t_cut = T_CUT_BY_N.get(N, 0.0)
            for run in range(N_RUNS):
                dyn_p = dynamic_path(N, k_exp, run)
                if not dyn_p.is_file():
                    print(f"  MISSING: {dyn_p.name}")
                    rows.append(
                        {
                            "k": k_value(k_exp), "k_exp": k_exp,
                            "N": N, "run": run, "t_cut": t_cut,
                            "n_frames": 0,
                            "J_in_near": float("nan"),
                            "rho_near": float("nan"),
                            "v_near": float("nan"),
                            "dynamic_file": str(dyn_p),
                        }
                    )
                    continue
                aggs = realization_radial_aggregates(dyn_p, t_cut)
                J_near, rho_near, v_near = near_obstacle_J(
                    edges, aggs["count"], aggs["sumv"], aggs["n_frames"]
                )
                rows.append(
                    {
                        "k": k_value(k_exp), "k_exp": k_exp,
                        "N": N, "run": run, "t_cut": t_cut,
                        "n_frames": aggs["n_frames"],
                        "J_in_near": J_near,
                        "rho_near": rho_near,
                        "v_near": v_near,
                        "dynamic_file": str(dyn_p),
                    }
                )
                print(
                    f"  k=10^{k_exp} N={N} run={run}: "
                    f"frames={aggs['n_frames']}, J_in_near={J_near:.4e}"
                )
    return rows


def aggregate_per_kN(rows: list[dict]) -> dict[int, dict[int, dict]]:
    out: dict[int, dict[int, dict]] = {}
    for k_exp in K_EXPONENTS:
        out[k_exp] = {}
        for N in N_VALUES:
            cell = [
                r["J_in_near"]
                for r in rows
                if r["k_exp"] == k_exp and r["N"] == N and not np.isnan(r["J_in_near"])
            ]
            if not cell:
                out[k_exp][N] = {"mean": float("nan"), "std": float("nan"), "n_runs": 0}
                continue
            arr = np.array(cell, dtype=float)
            out[k_exp][N] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "n_runs": int(arr.size),
            }
    return out


# ── Plot C ────────────────────────────────────────────────────────────────────

def plot_J_in_near_vs_N(
    aggregate: dict[int, dict[int, dict]], output_path: Path
) -> None:
    figure, axis = plt.subplots(figsize=FIGSIZE)

    log_ks = np.array(K_EXPONENTS, dtype=float)
    norm = mcolors.Normalize(vmin=log_ks.min(), vmax=log_ks.max())
    cmap = cm.get_cmap("viridis")

    plotted_any = False
    for k_exp in K_EXPONENTS:
        means = np.array([aggregate[k_exp][N]["mean"] for N in N_VALUES])
        stds = np.array([aggregate[k_exp][N]["std"] for N in N_VALUES])
        if np.all(np.isnan(means)):
            print(f"  Plot C: no data for k=10^{k_exp}, skipping curve")
            continue
        color = cmap(norm(k_exp))
        axis.errorbar(
            N_VALUES, means, yerr=stds,
            fmt="-o", markersize=6, linewidth=1.6,
            color=color, ecolor=color, elinewidth=1.2, capsize=4,
        )
        plotted_any = True

    if not plotted_any:
        print("[Plot C] No data plotted; check file paths.")
        plt.close(figure)
        return

    axis.set_xlabel("N (número de partículas)", fontsize=LABEL_SIZE)
    axis.set_ylabel(
        rf"$\langle J_{{in}}|_{{S \in [{S_NEAR_MIN:.1f},{S_NEAR_MAX:.1f}]}} \rangle$",
        fontsize=LABEL_SIZE,
    )
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
    print(f"[Plot C] Saved <J_in|_{{S~2}}>(N) per k to {output_path}")


# ── Summary CSV ───────────────────────────────────────────────────────────────

def write_summary(rows: list[dict], summary_path: Path) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "k", "k_exp", "N", "run", "t_cut", "n_frames",
                "J_in_near", "rho_near", "v_near", "dynamic_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {summary_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TP4 item 2.4: k-sweep on J_in|_{S~2} (Plot C).",
    )
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument("--figure", default=str(DEFAULT_FIG_C_PATH))
    parser.add_argument(
        "--s-near-min", type=float, default=S_NEAR_MIN,
        help=f"Inner edge of obstacle-near window (default {S_NEAR_MIN}).",
    )
    parser.add_argument(
        "--s-near-max", type=float, default=S_NEAR_MAX,
        help=f"Outer edge of obstacle-near window (default {S_NEAR_MAX}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Allow overriding the near window from CLI without editing the file.
    global S_NEAR_MIN, S_NEAR_MAX
    S_NEAR_MIN = args.s_near_min
    S_NEAR_MAX = args.s_near_max
    print(f"Obstacle-near window: S in [{S_NEAR_MIN}, {S_NEAR_MAX}]")

    print("Building radial summary across (k_exp, N, run) ...")
    rows = build_radial_summary()
    write_summary(rows, Path(args.summary))

    print("Aggregating per (k_exp, N) ...")
    aggregate = aggregate_per_kN(rows)

    plot_J_in_near_vs_N(aggregate, Path(args.figure))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
