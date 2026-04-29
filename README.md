# TP4 - Molecular Dynamics with Time-Driven Integration

This repository contains the implementation for **Trabajo Practico 4** of *Simulacion de Sistemas*.

The assignment is split into two independent systems:

1. **System 1: Damped point oscillator**
2. **System 2: Scanning rate in a circular enclosure with a fixed obstacle**

The repository is organized so both systems can be built and executed separately.

## Current Status

- **System 1** is implemented in C and can be simulated from the command line.
- **System 1.2 and 1.3** post-processing scripts are implemented in Python.
- **System 2** already has its own executable entry point, but the simulation itself is not implemented yet.

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

Outputs:

- `output/oscillator_dt_sweep/*.csv`
- `output/oscillator_dt_sweep_summary.csv`
- `images/oscillator/dt_vs_mse_position.png`
- `images/oscillator/dt_vs_mse_velocity.png`

## System 2: Scanning Rate

System 2 has a separate executable reserved for the second part of the assignment:

```bash
./bin/scanning_rate
```

At the moment it only reports that the simulation is not implemented yet.

The repository already includes a `python/scanning_rate/` directory intended for analysis and visualization of that system.

## Notes

- The repository was reorganized so both TP parts remain independent and easier to maintain.
- Generated outputs are stored outside the simulation code to keep simulation and post-processing decoupled.
