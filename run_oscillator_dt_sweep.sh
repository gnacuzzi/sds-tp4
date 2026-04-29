#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_PATH="$ROOT_DIR/bin/oscillator"
SWEEP_SCRIPT="$ROOT_DIR/python/oscillator/dt_sweep.py"

TF="${TF:-5.0}"
SAMPLE_EVERY="${SAMPLE_EVERY:-1}"

if [[ ! -x "$BIN_PATH" ]]; then
  echo "Executable not found: $BIN_PATH"
  echo "Run 'make' first."
  exit 1
fi

echo "Running dt sweep for oscillator methods"
python3 "$SWEEP_SCRIPT" \
  --binary "$BIN_PATH" \
  --tf "$TF" \
  --sample-every "$SAMPLE_EVERY"

echo "Done."
