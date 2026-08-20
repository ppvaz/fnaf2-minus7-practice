#!/bin/bash
# Mean R,G,B over a screen rectangle, computed entirely ON THE DEVICE.
#
# The Minus 7 driver runs inside one adb shell so host/USB round trips cannot
# accumulate cycle drift. Any observation the schedule branches on has to be
# computed the same way or the branch reintroduces the latency the design
# avoids: a host-side classify measured 692-785 ms per call, and pulling the
# pixels to the host to average them measured 3.3 s. Both are outside the
# roughly 1.25 s between flashing the vent light and the monitor raise that
# would let Balloon Boy in.
#
# So screencap, the row reads and the average all run on the phone, and the
# only thing crossing USB is one line of text. Sample a handful of rows, not
# the whole rectangle -- each row costs a dd spawn.
#
#   tools/device/regionmean.sh X0 Y0 X1 Y1 [ROWS]
#
# Prints "R G B" as integers 0-255.
set -euo pipefail

X0="${1:?x0}"; Y0="${2:?y0}"; X1="${3:?x1}"; Y1="${4:?y1}"; ROWS="${5:-8}"
WIDTH="${SCREEN_WIDTH:-2400}"
HEADER="${SCREENCAP_HEADER:-16}"

adb shell "REGION_X0=$X0 REGION_Y0=$Y0 REGION_X1=$X1 REGION_Y1=$Y1 \
REGION_ROWS=$ROWS REGION_WIDTH=$WIDTH REGION_HEADER=$HEADER sh -c '
raw=/data/local/tmp/fnaf2-region-\$\$.raw
trap \"rm -f \$raw\" EXIT
screencap > \$raw || exit 2
stride=\$(( REGION_WIDTH * 4 ))
count=\$(( (REGION_X1 - REGION_X0) * 4 ))
span=\$(( REGION_Y1 - REGION_Y0 ))
step=\$(( span / REGION_ROWS ))
[ \$step -lt 1 ] && step=1
i=0
while [ \$i -lt \$REGION_ROWS ]; do
  y=\$(( REGION_Y0 + i * step ))
  [ \$y -ge \$REGION_Y1 ] && break
  dd if=\$raw bs=1 skip=\$(( REGION_HEADER + y * stride + REGION_X0 * 4 )) count=\$count 2>/dev/null
  i=\$(( i + 1 ))
done | od -An -tu1 -v | awk \"
{ for (i = 1; i <= NF; i++) { v[n % 4] += \\\$i; if (n % 4 == 0) px++; n++ } }
END { if (px == 0) { print \\\"0 0 0\\\"; exit 1 }
      printf \\\"%d %d %d\\\\n\\\", v[0] / px, v[1] / px, v[2] / px }\"
'"
