#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_PATH="$ROOT_DIR/bin/scanning_rate"

REALIZATIONS="${REALIZATIONS:-10}"
TF="${TF:-500}"
DT="${DT:-0.001}"
K="${K:-1000}"
AUTO_DT2="${AUTO_DT2:-1}"
JOBS="${JOBS:-2}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/output}"
SEED_BASE="${SEED_BASE:-12345}"
ENERGY_DT2="${ENERGY_DT2:-$DT}"

move_output() {
  local n="$1"
  local run_id="$2"
  local kind="$3"
  local src
  local dst

  src="$ROOT_DIR/output/${n}_${kind}${run_id}.txt"
  dst="$OUTPUT_DIR/${n}_${kind}${run_id}.txt"

  if [[ "$OUTPUT_DIR" == "$ROOT_DIR/output" ]]; then
    return
  fi

  if [[ -f "$src" ]]; then
    if [[ -e "$dst" ]]; then
      echo "Refusing to overwrite existing file: $dst" >&2
      exit 1
    fi
    mv "$src" "$dst"
  fi
}

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

wait_for_available_slot() {
  while (( $(jobs -pr | wc -l | tr -d ' ') >= JOBS )); do
    sleep 1
  done
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
echo "Parameters: tf=${TF}, dt=${DT}, k=${K}, jobs=${JOBS}, seed_base=${SEED_BASE}"
echo "Output sampling: dynamic_dt2=${DT2:-auto}, cfc_every_dt, energy_dt2=${ENERGY_DT2}"
echo "Output directory: ${OUTPUT_DIR}"
if [[ "$AUTO_DT2" == "1" ]]; then
  echo "dt2 mode: automatic by N"
else
  echo "dt2 mode: fixed dt2=${DT2:-0.1}"
fi

mkdir -p "$OUTPUT_DIR"

for N in "${N_VALUES[@]}"; do
  DT2_VALUE="$(resolve_dt2 "$N")"
  echo "=== N=${N}, dt2=${DT2_VALUE} ==="

  for ((run_id = 0; run_id < REALIZATIONS; run_id++)); do
    wait_for_available_slot
    seed=$((SEED_BASE + N * 1000 + run_id))
    echo "  -> launching N=${N} run_id=${run_id} seed=${seed}"
    (
      "$BIN_PATH" "$N" "$run_id" "$TF" "$DT" "$DT2_VALUE" "$seed" "$K" 1 "$ENERGY_DT2"
      move_output "$N" "$run_id" "dynamic"
      move_output "$N" "$run_id" "cfc"
      move_output "$N" "$run_id" "energy"
    ) &
  done
done

wait
echo "All parallel batches completed."
