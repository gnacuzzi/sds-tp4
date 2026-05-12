#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_PATH="$ROOT_DIR/bin/scanning_rate"

N="${N:-1000}"
REALIZATIONS="${REALIZATIONS:-10}"
TF="${TF:-2000}"
K="${K:-1000}"
DT2="${DT2:-20}"
JOBS="${JOBS:-2}"
RUN_ID_OFFSET="${RUN_ID_OFFSET:-7000}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/output/dt_observable_N${N}}"
DTS="${DTS:-0.005 0.002 0.001 0.0005}"
SEED_BASE="${SEED_BASE:-12345}"
ENERGY_DT2="${ENERGY_DT2:-$DT2}"
WRITE_DYNAMIC="${WRITE_DYNAMIC:-0}"
WRITE_CFC="${WRITE_CFC:-0}"
WRITE_ENERGY="${WRITE_ENERGY:-1}"

dt_label() {
  echo "$1" | sed 's/\./p/g'
}

wait_for_available_slot() {
  while (( $(jobs -pr | wc -l | tr -d ' ') >= JOBS )); do
    sleep 1
  done
}

move_output() {
  local kind="$1"
  local run_id="$2"
  local dt="$3"
  local realization="$4"
  local label
  local src
  local dst

  label="$(dt_label "$dt")"
  src="$ROOT_DIR/output/${N}_${kind}${run_id}.txt"
  dst="$OUTPUT_DIR/${N}_${kind}_dt${label}_run${realization}.txt"

  if [[ -f "$src" ]]; then
    if [[ -e "$dst" ]]; then
      echo "Refusing to overwrite existing file: $dst" >&2
      exit 1
    fi
    mv "$src" "$dst"
  fi
}

echo "Building project"
make -C "$ROOT_DIR"

if [[ ! -x "$BIN_PATH" ]]; then
  echo "Executable not found: $BIN_PATH" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "Running dt observable validation"
echo "N=${N}, realizations=${REALIZATIONS}, tf=${TF}, k=${K}, dt2=${DT2}, energy_dt2=${ENERGY_DT2}, jobs=${JOBS}, seed_base=${SEED_BASE}"
echo "write_dynamic=${WRITE_DYNAMIC}, write_cfc=${WRITE_CFC}, write_energy=${WRITE_ENERGY}"
echo "DTS=${DTS}"
echo "OUTPUT_DIR=${OUTPUT_DIR}"

dt_index=0
for dt in $DTS; do
  for ((realization = 0; realization < REALIZATIONS; realization++)); do
    internal_run_id=$((RUN_ID_OFFSET + dt_index * 100 + realization))
    seed=$((SEED_BASE + dt_index * 1000 + realization))
    label="$(dt_label "$dt")"
    wait_for_available_slot

    echo "  -> launching dt=${dt} realization=${realization} internal_run_id=${internal_run_id} seed=${seed}"
    (
      "$BIN_PATH" "$N" "$internal_run_id" "$TF" "$dt" "$DT2" "$seed" "$K" 1 "$ENERGY_DT2" "$WRITE_DYNAMIC" "$WRITE_CFC" "$WRITE_ENERGY" \
        > "$OUTPUT_DIR/${N}_dt${label}_run${realization}.log" 2>&1

      move_output "dynamic" "$internal_run_id" "$dt" "$realization"
      move_output "cfc" "$internal_run_id" "$dt" "$realization"
      move_output "energy" "$internal_run_id" "$dt" "$realization"
    ) &
  done

  dt_index=$((dt_index + 1))
done

wait
echo "All dt observable runs completed."
