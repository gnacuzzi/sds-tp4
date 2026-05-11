#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_PATH="$ROOT_DIR/bin/scanning_rate"
OUTPUT_PATH="$ROOT_DIR/output/performance.csv"

TF="${TF:-500}"
DT="${DT:-0.0005}"
DT2="${DT2:-2.0}"
K="${K:-1000}"
RUNS="${RUNS:-10}"
SEED="${SEED:-12345}"

N_VALUES=(
  100
  200
  300
  400
  500
  600
  700
  800
  900
  1000
)

make -C "$ROOT_DIR"
mkdir -p "$ROOT_DIR/output"

echo "N,time" > "$OUTPUT_PATH"

for N in "${N_VALUES[@]}"; do
  for ((run_id = 0; run_id < RUNS; run_id++)); do
    "$BIN_PATH" "$N" "$run_id" "$TF" "$DT" "$DT2" "$((SEED + run_id))" "$K" 0
  done
done
