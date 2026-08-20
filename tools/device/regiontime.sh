#!/bin/bash
# How long does one device-side region read take?
#
# This is the number that decides whether the pilot can branch on what it sees
# at all. The vent check has to fit between flashing the left vent light and
# the monitor raise that would let Balloon Boy in -- about 1.25 s in the
# shipped cycle. For reference, measured on the moto g56:
#
#   host-side screenstate.py --adb-fast   692-785 ms
#   pull the rectangle, average on host    ~3300 ms
#
#   tools/device/regiontime.sh [N] [X0 Y0 X1 Y1 ROWS]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
N="${1:-6}"
X0="${2:-200}"; Y0="${3:-300}"; X1="${4:-700}"; Y1="${5:-700}"; ROWS="${6:-8}"

total=0
for i in $(seq 1 "$N"); do
  s=$(date +%s%N)
  out=$(bash "$HERE/regionmean.sh" "$X0" "$Y0" "$X1" "$Y1" "$ROWS")
  e=$(date +%s%N)
  ms=$(( (e - s) / 1000000 ))
  total=$(( total + ms ))
  echo "${ms} ms  -> ${out}"
done
echo "mean $(( total / N )) ms over $N reads (${ROWS} rows)"
