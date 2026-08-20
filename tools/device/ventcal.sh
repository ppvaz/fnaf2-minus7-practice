#!/bin/bash
# Calibration capture for the left-vent check.
#
# The pilot's one observation is: hold the left vent light with the cams down
# and decide whether Balloon Boy is standing in the opening. That is sourced --
# g289 draws him there, g287 draws the opening empty -- but "sourced" only says
# the two views differ, not which pixels differ on this phone at this
# resolution. This captures both classes so a threshold can be measured instead
# of guessed.
#
# Holding the vent light is free: g284 drains the battery on `lit?` alone, so
# the vent lights cost no power, which is what makes a per-cycle check
# affordable at all.
#
#   tools/device/ventcal.sh <name> [seconds]
#
# Starts 6th Night, then every 5 s holds the left vent light and saves a
# screenshot of the office under it. Post-hoc, ventscan.py reads the region
# statistic out of these and finds the frames where BB was there.
set -euo pipefail

OUT="${1:?name}"
SECONDS_TO_RUN="${2:-180}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="$HERE/../../captures/$OUT"
NIGHT="${NIGHT:-6th}"

case "$OUT" in
  ''|.*|*..*|*[!A-Za-z0-9._-]*) echo "name must be a plain basename"; exit 2 ;;
esac
[ ! -e "$DIR" ] || { echo "refusing to overwrite $DIR"; exit 2; }
mkdir -p "$DIR"

# shellcheck source=/dev/null
. "$HERE/coords.sh"

# coords.sh stores "X Y" pairs, so these take the pair unquoted.
press() { adb shell input swipe $1 $1 "${2:-120}"; }
hold_bg() { adb shell input swipe $1 $1 "$2" & }

focused() { adb shell dumpsys window 2>/dev/null | grep -m1 mCurrentFocus; }

echo "== launching =="
adb shell input keyevent KEYCODE_WAKEUP >/dev/null 2>&1 || true
adb shell monkey -p com.scottgames.fnaf2 -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep 12
focused

echo "== selecting $NIGHT =="
if [ "$NIGHT" = "6th" ]; then
  press "$TAP_6TH"; sleep 1
  press "$TAP_6TH"; sleep 1
else
  press "$TAP_CONTINUE"; sleep 1
  press "$TAP_CONTINUE"; sleep 1
fi

echo "== waiting for the office =="
for _ in $(seq 1 40); do
  sleep 1
  if python3 "$HERE/screenstate.py" --adb-fast 2 2>/dev/null | grep -q night; then
    echo "office is up"
    break
  fi
done

echo "== sampling; ctrl-c to stop early =="
end=$(( $(date +%s) + SECONDS_TO_RUN ))
i=0
while [ "$(date +%s)" -lt "$end" ]; do
  state=$(python3 "$HERE/screenstate.py" --adb-fast 2 2>/dev/null || echo unavailable)
  if [ "$state" != "night" ]; then
    echo "left the night ($state) after $i samples"
    break
  fi
  # Hold the left vent light and capture underneath it. The hold has to still
  # be running when screencap fires, so launch it in the background.
  # A matched pair each round: the same office with the vent light off, then
  # on. The region the light actually illuminates is whatever changes between
  # them -- measuring that beats guessing coordinates off a screenshot, since
  # the office view is centred and the opening is not obviously in frame.
  adb exec-out screencap -p > "$DIR/$(printf 'off-%04d' "$i").png" 2>/dev/null || true
  hold_bg "$TAP_CAM_LIGHT" 1200
  holder=$!
  sleep 0.45
  adb exec-out screencap -p > "$DIR/$(printf 'on-%04d' "$i").png" 2>/dev/null || true
  wait "$holder" 2>/dev/null || true
  i=$(( i + 1 ))
  sleep 0.8
done

echo "saved $i captures in $DIR"
