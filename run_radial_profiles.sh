#!/bin/bash

set -euo pipefail

mkdir -p images

if [ "$#" -gt 0 ]; then
    NS=("$@")
else
    mapfile -t NS < <(
        find output -maxdepth 1 -name '*_dynamic*.txt' -size +0 -print |
        sed 's#output/##' |
        sed 's/_dynamic.*//' |
        sort -n |
        uniq
    )
fi

if [ "${#NS[@]}" -eq 0 ]; then
    echo "No dynamic files found in output/"
    exit 1
fi

echo "Processing N values: ${NS[*]}"

RUN_ID_ARGS=()
if [ "${RUN_IDS:-}" != "" ]; then
    read -r -a RUN_ID_ARGS <<< "$RUN_IDS"
    echo "Filtering run ids: ${RUN_ID_ARGS[*]}"
fi

if [ "${#RUN_ID_ARGS[@]}" -gt 0 ]; then
    python3 python/scanning_rate/radial_profiles.py --ns "${NS[@]}" --run-ids "${RUN_ID_ARGS[@]}"
    python3 python/scanning_rate/radial_j_zoom_all_n.py --ns "${NS[@]}" --run-ids "${RUN_ID_ARGS[@]}"
    python3 python/scanning_rate/radial_vs_N.py --ns "${NS[@]}" --run-ids "${RUN_ID_ARGS[@]}"
else
    python3 python/scanning_rate/radial_profiles.py --ns "${NS[@]}"
    python3 python/scanning_rate/radial_j_zoom_all_n.py --ns "${NS[@]}"
    python3 python/scanning_rate/radial_vs_N.py --ns "${NS[@]}"
fi

echo "Radial plots generated in images/"
