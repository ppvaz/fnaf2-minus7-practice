#!/bin/bash
# How long does a touch have to be before the game reliably takes it?
#
# Graded over four real trials, the shipped schedule landed 3-5 visible hall
# flashes out of about 12 scheduled, and mask flicks registered on roughly half
# of cycles. That is not a strategy problem -- no schedule survives if half its
# inputs are dropped -- and it is worth measuring on its own, away from a timed
# cycle that confounds it with CPU contention and animation windows.
#
# The mask is the ideal probe: it is a toggle with an unmistakable view, so a
# press either flipped the state or it did not, and we can check directly
# instead of grading a video. The harness rule of record is that zero-duration
# `input tap` is dropped about half the time and a touch must be a duration
# press; fast-swipe uses 60 ms and this asks whether that is actually enough.
#
#   tools/device/inputtest.sh <name> [presses-per-duration]
#
# Prints, per duration, how many presses actually changed the mask state.
set -euo pipefail

OUT="${1:?name}"
REPS="${2:-10}"
HERE="$(cd "$(dirname "$0")" && pwd)"
NIGHT="${NIGHT:-6th}"
DURATIONS="${DURATIONS:-60 120 200 300}"

# shellcheck source=/dev/null
. "$HERE/coords.sh"

press() { adb shell input swipe $1 $1 "$2"; }

cleanup() { adb shell am force-stop com.scottgames.fnaf2 >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "== launching =="
adb shell input keyevent KEYCODE_WAKEUP >/dev/null 2>&1 || true
adb shell am force-stop com.scottgames.fnaf2 >/dev/null 2>&1 || true
sleep 1
adb shell am start -n com.scottgames.fnaf2/.Main >/dev/null
sleep 8

NIGHT_TAP=$TAP_CONTINUE
[ "$NIGHT" = "6th" ] && NIGHT_TAP=$TAP_6TH
press "$NIGHT_TAP" 120; sleep 1
press "$NIGHT_TAP" 120

echo "== waiting for the office =="
for _ in $(seq 1 40); do
  sleep 1
  python3 "$HERE/screenstate.py" --adb-fast 2 2>/dev/null | grep -q night && break
done

# The masked view is far darker than the office across the whole upper screen,
# so mean brightness separates the two states without any calibration beyond
# one baseline reading.
sample() { bash "$HERE/regionmean.sh" 800 200 1600 260 6 | cut -d' ' -f1; }

echo "== baseline =="
base=$(sample)
echo "office mean brightness: $base"

for dur in $DURATIONS; do
  flips=0
  attempts=0
  prev="$base"
  i=0
  while [ "$i" -lt "$REPS" ]; do
    state=$(python3 "$HERE/screenstate.py" --adb-fast 2 2>/dev/null || echo unavailable)
    if [ "$state" != "night" ]; then
      echo "  (left the night after $attempts presses at ${dur} ms)"
      break
    fi
    press "$TAP_MASK" "$dur"
    sleep 0.55
    now=$(sample)
    attempts=$(( attempts + 1 ))
    # A flip is a large brightness change in either direction.
    delta=$(( now - prev )); [ "$delta" -lt 0 ] && delta=$(( -delta ))
    [ "$delta" -gt 12 ] && flips=$(( flips + 1 ))
    prev="$now"
    i=$(( i + 1 ))
  done
  if [ "$attempts" -gt 0 ]; then
    echo "${dur} ms: ${flips}/${attempts} presses changed the mask state"
  else
    echo "${dur} ms: no attempts completed"
  fi
done
