#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_PATH="$ROOT_DIR/bin/oscillator"
OUTPUT_DIR="$ROOT_DIR/output"
ANALYSIS_SCRIPT="$ROOT_DIR/python/oscillator/analyze_solution.py"

DT="${DT:-0.001}"
TF="${TF:-5.0}"
SAMPLE_EVERY="${SAMPLE_EVERY:-1}"

METHODS=(
  euler
  verlet
  beeman
  gear5
)

if [[ ! -x "$BIN_PATH" ]]; then
  echo "Executable not found: $BIN_PATH"
  echo "Run 'make' first."
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

for method in "${METHODS[@]}"; do
  csv_path="$OUTPUT_DIR/oscillator_${method}.csv"
  echo "Running method: $method"
  "$BIN_PATH" "$method" "$csv_path" "$DT" "$TF" "$SAMPLE_EVERY"
done

echo "Generating comparison plots and MSE summary"
python3 "$ANALYSIS_SCRIPT"

echo "Done."
