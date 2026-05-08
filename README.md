# TP4 - Molecular Dynamics with Time-Driven Integration

This repository contains the implementation for **Trabajo Practico 4** of *Simulacion de Sistemas*.

The assignment is split into two independent systems:

1. **System 1: Damped point oscillator**
2. **System 2: Scanning rate in a circular enclosure with a fixed obstacle**

The repository is organized so both systems can be built and executed separately.

## Current Status

- **System 1** is implemented in C and can be simulated from the command line.
- **System 1.2 and 1.3** post-processing scripts are implemented in Python.
- **System 2** has a first working time-driven simulation engine in C.
- The later analysis stages requested by the assignment for **System 2** are still incomplete.

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
- `images/oscillator/dt_vs_mse_velocity.png`

## System 2: Scanning Rate

System 2 simulates soft particles inside a circular enclosure with:

- a fixed obstacle at the center,
- elastic pair interactions,
- elastic contact with the outer wall,
- fresh/used particle state changes based on obstacle and wall contacts.

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

### Output Files

Each System 2 run currently generates:

- `output/<N>_dynamic<run_id>.txt`
- `output/<N>_cfc<run_id>.txt`
- `output/<N>_energy<run_id>.txt`

Current meaning:

- `dynamic`: saved particle states for animation and spatial post-processing
- `cfc`: time series with `t`, `Cfc(t)`, and `fu(t)`
- `energy`: kinetic/potential energy components and total energy

### Visualize a Run

You can animate a dynamic output file with:

```bash
python3 python/scanning_rate/animation.py output/100_dynamic0.txt
```

Or choose the output video explicitly:

```bash
python3 python/scanning_rate/animation.py output/100_dynamic0.txt -o videos/100_dynamic0.mp4
```

### Current Scope of System 2

Implemented now:

- time-driven integration
- non-overlapping particle initialization
- particle-particle elastic forces
- obstacle and wall contact forces
- fresh/used state transitions
- dynamic, cfc, and energy outputs

Still pending:

- full scanning-rate analysis workflow
- radial profile workflow integrated with the new simulation
- `k` sweeps and derived observables

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

## Notes

- The repository was reorganized so both TP parts remain independent and easier to maintain.
- Generated outputs are stored outside the simulation code to keep simulation and post-processing decoupled.
