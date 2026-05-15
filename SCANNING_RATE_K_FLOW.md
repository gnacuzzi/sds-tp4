# Scanning Rate Workflow For A New `k`

This file lists the commands needed to reproduce the main System 2 plots for a different elastic constant `k`.

The examples below assume:

```sh
K=1000
DT=0.0001
OUTPUT_DIR=output/k1000_dt0001
IMAGE_DIR=images/k1000_dt0001
RADIAL_DIR=output/radial_k1000_dt0001
RADIAL_S2_3_DIR=output/radial_k1000_dt0001_S2_3
```

For another `k`, change those names consistently.

## 1. Compile

Run this after pulling changes, especially if any `.h` file changed.

```sh
make clean
make
```

## 2. Run The Simulations

This runs 10 realizations for each `N`.

```sh
REALIZATIONS=10 TF=2000 DT=0.0001 K=1000 \
AUTO_DT2=0 DT2=2.0 ENERGY_DT2=50 JOBS=3 \
OUTPUT_DIR="$PWD/output/k1000_dt0001" \
SEED_BASE=92345 \
./run_batches_parallel.sh
```

Notes:

- `DT` is the integration timestep.
- `DT2` controls how often dynamic states are written. These files are used for radial profiles and animations.
- `ENERGY_DT2` controls how often energy is written. It can be large here because the energy validation is done separately.
- `JOBS=3` runs three simulations in parallel. Increase only if the machine can handle it.

## 3. Compute Scanning Rate `J`

This reads the `*_cfc*.txt` files and fits `Cfc(t) = J t + b` for each realization.

```sh
python3 python/scanning_rate/interpolate.py 10 \
  --output-dir output/k1000_dt0001 \
  --image-dir images/k1000_dt0001 \
  --summary output/k1000_dt0001/scanning_rate_j_summary.csv \
  --ns 100 200 300 400 500 600 700 800 900 1000
```

Main outputs:

```text
output/k1000_dt0001/scanning_rate_j_summary.csv
images/k1000_dt0001/J_vs_N.png
images/k1000_dt0001/Cfc_fit_N_<N>.png
```

## 4. Compare Scanning Rate With TP3

Use this if the TP3 dynamic/event dataset is available in `output_tp3`.

```sh
python3 python/scanning_rate/compare_scanning_rate_tp3_tp4.py \
  --tp3-dir output_tp3 \
  --tp4-dir output/k1000_dt0001 \
  --tp4-summary output/k1000_dt0001/scanning_rate_j_summary.csv \
  --image-dir images/k1000_dt0001 \
  --summary output/k1000_dt0001/scanning_rate_tp3_tp4_summary.csv
```

## 5. Export Radial CSVs

Full radial profiles:

```sh
python3 python/scanning_rate/export_radial_csv.py \
  --tp4-dir output/k1000_dt0001 \
  --tp3-dir "" \
  --output-dir output/radial_k1000_dt0001 \
  --run-ids 0 1 2 3 4 5 6 7 8 9
```

Radial averages in the obstacle-near region `S=[2,3]`:

```sh
python3 python/scanning_rate/export_radial_csv.py \
  --tp4-dir output/k1000_dt0001 \
  --tp3-dir output_tp3 \
  --output-dir output/radial_k1000_dt0001_S2_3 \
  --run-ids 0 1 2 3 4 5 6 7 8 9 \
  --s-min 2 \
  --s-max 3
```

Main outputs:

```text
output/radial_k1000_dt0001/radial_profiles_tp4.csv
output/radial_k1000_dt0001/radial_vs_N_tp4.csv
output/radial_k1000_dt0001_S2_3/radial_vs_N_tp3.csv
output/radial_k1000_dt0001_S2_3/radial_vs_N_tp4.csv
```

Warnings such as `Mean of empty slice` are expected when no fresh incoming particles exist in some radial layer. In that case velocity is undefined and stored as `nan`, not as zero.

## 6. Plot Full Radial Profiles

This plots `rho(S)`, `|v(S)|`, and `Jin(S)` for all `N`.

```sh
python3 python/scanning_rate/radial_profiles.py \
  --profiles-csv output/radial_k1000_dt0001/radial_profiles_tp4.csv \
  --image-dir images/radial_k1000_dt0001 \
  --output-prefix S_ \
  --plot-s-min 0 \
  --plot-s-max 40 \
  --all
```

Zoom of `Jin(S)` near the obstacle:

```sh
python3 python/scanning_rate/radial_j_zoom_all_n.py \
  --profiles-csv output/radial_k1000_dt0001/radial_profiles_tp4.csv \
  --image-dir images/radial_k1000_dt0001 \
  --output-prefix S_ \
  --ns 100 200 300 400 500 600 700 800 900 1000
```

## 7. Plot `rho` And Velocity Versus `N`

This is the TP4-only multiscale plot with only density and velocity, averaged in `S=[2,3]`.

```sh
python3 python/scanning_rate/radial_vs_N.py \
  --vs-n-csv output/radial_k1000_dt0001_S2_3/radial_vs_N_tp4.csv \
  --image-dir images/radial_k1000_dt0001/radial_vs_N \
  --output-prefix tp4_S2_3_ \
  --s-min 2 \
  --s-max 3 \
  --rho-velocity-only
```

## 8. Compare `Jin` With TP3

This compares the product

```text
Jin(S) = <rho_f^in>(S) * |<v_f^in>(S)|
```

averaged in `S=[2,3]`.

```sh
python3 python/scanning_rate/compare_radial_vs_n.py \
  --metric jin \
  --tp3-csv output/radial_k1000_dt0001_S2_3/radial_vs_N_tp3.csv \
  --tp4-csv output/radial_k1000_dt0001_S2_3/radial_vs_N_tp4.csv \
  --output images/radial_k1000_dt0001/radial_vs_N/Jin_tp3_tp4_S2_3.png
```

## 9. What Is Needed For Item 1.4

If item 1.4 asks to study the effect of changing `k`, the useful outputs for each `k` are:

- `scanning_rate_j_summary.csv`, because it gives `<J>(N)` and error bars.
- The TP3 vs TP4 scanning-rate comparison, if the report compares against the event-driven TP3 result.
- `radial_vs_N_tp4.csv` and the `S=[2,3]` radial averages, because they show how density, incoming speed, and `Jin` change with `N`.
- The `Jin` TP3 vs TP4 comparison, if the report needs to compare the product against the previous TP.

The energy files are only needed to justify the selected `dt`. They are not needed to compute `Cfc`, `J`, or radial profiles.
