#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_PATH="$ROOT_DIR/bin/scanning_rate"

REALIZATIONS="${REALIZATIONS:-10}"
TF="${TF:-500}"
DT="${DT:-0.001}"
K="${K:-1000}"
AUTO_DT2="${AUTO_DT2:-1}"

resolve_dt2() {
  local n="$1"

  if [[ "$AUTO_DT2" == "0" ]]; then
    echo "${DT2:-0.1}"
    return
  fi

  if (( n <= 200 )); then
    echo "0.1"
  elif (( n <= 400 )); then
    echo "0.2"
  elif (( n <= 600 )); then
    echo "0.5"
  elif (( n <= 800 )); then
    echo "1.0"
  else
    echo "2.0"
  fi
}

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

echo "Building project"
make -C "$ROOT_DIR"

if [[ ! -x "$BIN_PATH" ]]; then
  echo "Executable not found: $BIN_PATH"
  exit 1
fi

echo "Running ${REALIZATIONS} realizations for N = 100, 200, ..., 1000"
echo "Parameters: tf=${TF}, dt=${DT}, k=${K}"
if [[ "$AUTO_DT2" == "1" ]]; then
  echo "dt2 mode: automatic by N"
else
  echo "dt2 mode: fixed dt2=${DT2:-0.1}"
fi

for N in "${N_VALUES[@]}"; do
  DT2_VALUE="$(resolve_dt2 "$N")"
  echo "=== N=${N} ==="
  echo "  dt2=${DT2_VALUE}"
  for ((run_id = 0; run_id < REALIZATIONS; run_id++)); do
    echo "  -> run_id=${run_id}"
    "$BIN_PATH" "$N" "$run_id" "$TF" "$DT" "$DT2_VALUE" 0 "$K"
  done
done

echo "All batches completed."
