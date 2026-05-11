# TP4 - Molecular Dynamics with Time-Driven Integration

This repository contains the implementation for **Trabajo Practico 4** of *Simulacion de Sistemas*.

The assignment is split into two independent systems:

1. **System 1: Damped point oscillator**
2. **System 2: Scanning rate in a circular enclosure with a fixed obstacle**

The repository is organized so both systems can be built and executed separately.

## Current Status

- **System 1** is implemented in C and can be simulated from the command line.
- **System 1.2 and 1.3** post-processing scripts are implemented in Python.
- **System 2** is implemented as a time-driven soft-particle simulation.
- **System 2.2 and 2.3** post-processing scripts are implemented, including TP3/TP4 comparison plots.

## Repository Layout

```text
src/
  common/          Shared headers and utilities
  oscillator/      System 1: damped oscillator
  scanning_rate/   System 2: circular enclosure with obstacle

python/
  oscillator/      Analysis scripts for System 1
  scanning_rate/   Visualization and analysis scripts for System 2

bin/               Compiled executables
output/            Simulation outputs and summaries
images/            Generated plots
```

## Requirements

### Build

- `gcc`
- `make`

### Python

- `python3`
- `numpy`
- `matplotlib`

No `pandas` dependency is required.

## Build

Compile everything with:

```bash
make
```

This generates:

- `bin/oscillator`
- `bin/scanning_rate`

Useful maintenance targets:

```bash
make clean
make fclean
make re
```

Convenience scripts in the project root:

```bash
./run_oscillator_all.sh
./run_oscillator_dt_sweep.sh
```

## System 1: Damped Oscillator

The oscillator is solved numerically and compared against the analytical solution.

Implemented integration schemes:

- Euler
- Original Verlet
- Beeman
- Gear predictor-corrector (5th order)

### Run a Simulation

General usage:

```bash
./bin/oscillator METHOD OUTPUT.csv [dt] [tf] [sample_every]
```

Where:

- `METHOD` is one of: `euler`, `verlet`, `beeman`, `gear5`
- `OUTPUT.csv` is the output trajectory file
- `dt` is the integration time step
- `tf` is the final simulation time
- `sample_every` controls how often the state is written

Examples:

```bash
./bin/oscillator euler output/oscillator_euler.csv
./bin/oscillator verlet output/oscillator_verlet.csv 0.001 5.0 1
./bin/oscillator beeman output/oscillator_beeman.csv 0.001 5.0 1
./bin/oscillator gear5 output/oscillator_gear5.csv 0.001 5.0 1
```

Run all four methods and generate the System 1.2 plots in one step:

```bash
./run_oscillator_all.sh
```

### Output Format

The generated CSV contains:

- `time`
- `x_numeric`
- `v_numeric`
- `x_analytic`
- `v_analytic`

### Default Oscillator Parameters

The current defaults are defined in [src/common/config.h](src/common/config.h):

- `m = 70`
- `k = 10000`
- `gamma = 100`
- `x0 = 1`
- `v0 = -gamma / (2m)`

These values should be validated against **slide 36** of `Teorica_4.pdf`.

## System 1.2: Analytical vs Numerical Comparison

The script below reads oscillator CSV files, computes the mean squared error, and generates comparison plots.

```bash
python3 python/oscillator/analyze_solution.py
```

You can also analyze a single file:

```bash
python3 python/oscillator/analyze_solution.py output/oscillator_euler.csv
```

Outputs:

- `images/oscillator/*_solution_comparison.png`
- `output/oscillator_mse_summary.csv`

## System 1.3: Error vs Time Step

The following script sweeps multiple `dt` values for all four methods, runs the simulator, stores intermediate CSV files, and generates log-log error plots.

```bash
python3 python/oscillator/dt_sweep.py
```

Or use the root helper script:

```bash
./run_oscillator_dt_sweep.sh
```

Outputs:

- `output/oscillator_dt_sweep/*.csv`
- `output/oscillator_dt_sweep_summary.csv`
- `images/oscillator/dt_vs_mse_position.png`

## System 2: Scanning Rate

System 2 simulates soft particles inside a circular enclosure with:

- a fixed obstacle at the center,
- elastic pair interactions,
- elastic contact with the outer wall,
- fresh/used particle state changes based on obstacle and wall contacts.
- a Cell Index Method (CIM) neighbor search for particle-particle forces.

### Run a Simulation

General usage:

```bash
./bin/scanning_rate [N] [run_id] [tf] [dt] [dt2] [seed] [k] [write_output]
```

Arguments:

- `N`: number of particles
- `run_id`: identifier appended to output filenames
- `tf`: final simulation time
- `dt`: integration time step
- `dt2`: snapshot output interval
- `seed`: RNG seed. If omitted, a time-based random seed is used
- `k`: elastic constant
- `write_output`: optional flag. Use `1` to write files and `0` for benchmark runs without file I/O

Example:

```bash
./bin/scanning_rate 100 0 10 0.001 0.1 12345 1000
```

Benchmark-style execution without writing output files:

```bash
./bin/scanning_rate 100 0 10 0.001 0.1 12345 1000 0
```

If you do not provide a seed, the simulator generates one automatically and prints the effective value at the end of the run so it can be reused later.

The production runs used for the current plots use:

- `dt = 0.0005`
- `k = 1000`
- `tf = 2000`
- `REALIZATIONS = 10`

The `dt` choice was checked by comparing total-energy drift for high-density runs. For `N=900`, the relative energy drift stayed around `10^-4` with `dt=0.0005`.

### Output Files

Each System 2 run currently generates:

- `output/<N>_dynamic<run_id>.txt`
- `output/<N>_cfc<run_id>.txt`
- `output/<N>_energy<run_id>.txt`

Current meaning:

- `dynamic`: saved particle states for animation and spatial post-processing
- `cfc`: time series with `t` and `Cfc(t)`
- `energy`: kinetic/potential energy components and total energy

`dynamic` is saved every `dt2`. `cfc` and `energy` are saved every integration step `dt`.
This is intentional for `cfc`, because the assignment asks for maximum temporal resolution for `Cfc(t)`.

### Visualize a Run

You can animate a dynamic output file with:

```bash
python3 python/scanning_rate/animation.py output/100_dynamic0.txt
```

Or choose the output video explicitly:

```bash
python3 python/scanning_rate/animation.py output/100_dynamic0.txt -o videos/100_dynamic0.mp4
```

### Scanning Rate From Cfc(t)

After running several realizations, compute the scanning rate `J` from the Cfc files:

```bash
python3 python/scanning_rate/interpolate.py 10 --ns 100 200 300 400 500 600 700 800 900 1000
```

This reads `output/<N>_cfc<run>.txt`, fits `Cfc(t)` linearly for each realization, and writes:

- `images/Cfc_fit_N_<N>.png`
- `images/J_vs_N.png`
- `output/scanning_rate_j_summary.csv`

You can restrict the fit interval if needed:

```bash
python3 python/scanning_rate/interpolate.py 10 --t-min 100 --t-max 500
```

To compare the scanning rate curve with TP3 data stored in `output_tp3/`:

```bash
python3 python/scanning_rate/compare_scanning_rate_tp3_tp4.py --runs 10
```

This writes:

- `images/J_vs_N_tp3_tp4.png`
- `output/scanning_rate_tp3_tp4_summary.csv`

If `output/scanning_rate_j_summary.csv` exists, the comparison script uses it directly for TP4 instead of re-reading all `cfc` files.

### Radial Profiles

Radial profiles use the `dynamic` files and select only fresh particles whose radial velocity points toward the center (`x . v < 0`).
The scripts compute:

- `<rho_f^in>(S)`
- `|<v_f^in>(S)|`
- `J_in(S) = <rho_f^in>(S) |<v_f^in>(S)|`

First export reusable CSV summaries:

```bash
python3 python/scanning_rate/export_radial_csv.py --run-ids 0 1 2 3 4 5 6 7 8 9
```

This writes:

- `output/radial_profiles_tp3.csv`
- `output/radial_profiles_tp4.csv`
- `output/radial_vs_N_tp3.csv`
- `output/radial_vs_N_tp4.csv`

Then generate the TP4 radial plots:

```bash
RUN_IDS='0 1 2 3 4 5 6 7 8 9' ./run_radial_profiles.sh 100 200 300 400 500 600 700 800 900 1000
```

The radial plotting scripts use the CSV files automatically if they exist, which avoids re-reading large `dynamic` files.

Main radial outputs:

- `images/radial_rho_all_N.png`
- `images/radial_velocity_all_N.png`
- `images/radial_Jin_all_N.png`
- `images/radial_Jin_zoom_all_N.png`
- `images/radial_vs_N_rho.png`
- `images/radial_vs_N_velocity.png`
- `images/radial_vs_N_Jin.png`
- `images/radial_vs_N_multiscale.png`

The all-`N` radial profile plots show `S=[1.8, 38]` by default to avoid edge artifacts. You can change that range with:

```bash
python3 python/scanning_rate/radial_profiles.py --ns 100 200 300 400 500 600 700 800 900 1000 --plot-s-min 1.8 --plot-s-max 38
```

To compare the near-obstacle radial averages between TP3 and TP4:

```bash
python3 python/scanning_rate/compare_radial_vs_n.py
```

This writes:

- `images/radial_vs_N_tp3_tp4_multiscale.png`

### Benchmark Runs

Use the root script below to measure execution time without counting output-file writing:

```bash
./benchmark.sh
```

The script runs the simulator with `write_output=0`. In that mode, the C executable measures `simulation_time` with `clock()` and appends each run directly to `output/performance.csv`.

The script writes:

- `output/performance.csv`

Configurable environment variables:

- `RUNS`: number of realizations per `N`
- `TF`: final simulation time
- `DT`: integration time step
- `DT2`: snapshot interval passed to the simulator, unused for output when `write_output=0`
- `K`: elastic constant
- `SEED`: base RNG seed

Example:

```bash
RUNS=3 TF=100 DT=0.001 K=1000 ./benchmark.sh
```

### Batch Runs

The root script below is prepared to run multiple realizations for:

- `N = 100, 200, ..., 1000`

```bash
./run_batches.sh
```

By default it uses:

- `REALIZATIONS=10`
- `tf=500`
- `dt=0.001`
- `k=1000`

To keep dynamic output files at reasonable sizes, the script automatically increases `dt2` as `N` grows.
You can disable that behavior and force a fixed `dt2` value if needed:

```bash
AUTO_DT2=0 DT2=0.1 ./run_batches.sh
```

For the final System 2 simulations, use the smaller validated integration step:

```bash
REALIZATIONS=10 TF=2000 DT=0.0005 AUTO_DT2=1 ./run_batches.sh
```

There is also a parallel batch runner:

```bash
REALIZATIONS=10 TF=2000 DT=0.0005 AUTO_DT2=1 JOBS=3 ./run_batches_parallel.sh
```

Use `JOBS=2` or `JOBS=3` on a laptop to avoid saturating disk writes. Higher values may not be faster because `dynamic`, `cfc`, and `energy` files are large.

Automatic `dt2` values used by the batch scripts:

- `N <= 200`: `dt2 = 0.1`
- `N <= 400`: `dt2 = 0.2`
- `N <= 600`: `dt2 = 0.5`
- `N <= 800`: `dt2 = 1.0`
- `N > 800`: `dt2 = 2.0`

## Notes

- The repository was reorganized so both TP parts remain independent and easier to maintain.
- Generated outputs are stored outside the simulation code to keep simulation and post-processing decoupled.
