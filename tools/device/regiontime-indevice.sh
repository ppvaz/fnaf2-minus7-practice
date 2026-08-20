#!/bin/bash
# The cost of a region read as the DRIVER pays it.
#
# regiontime.sh measures it from the host, so every read carries an `adb shell`
# spawn and a USB connection setup the real driver never pays: the driver is
# already running on the phone, so its reads are local screencap + dd + awk.
# This times the read from inside a single device shell, which is the number
# the cycle budget actually has to fit.
set -euo pipefail
N="${1:-6}"
X0="${2:-200}"; Y0="${3:-300}"; X1="${4:-700}"; Y1="${5:-700}"; ROWS="${6:-8}"
WIDTH="${SCREEN_WIDTH:-2400}"
HEADER="${SCREENCAP_HEADER:-16}"

adb shell "N=$N X0=$X0 Y0=$Y0 X1=$X1 Y1=$Y1 ROWS=$ROWS W=$WIDTH H=$HEADER sh -c '
raw=/data/local/tmp/fnaf2-regiontime-\$\$.raw
trap \"rm -f \$raw\" EXIT
stride=\$(( W * 4 ))
count=\$(( (X1 - X0) * 4 ))
step=\$(( (Y1 - Y0) / ROWS ))
[ \$step -lt 1 ] && step=1
total=0
n=0
while [ \$n -lt \$N ]; do
  t0=\$(date +%s%N)
  screencap > \$raw
  i=0
  while [ \$i -lt \$ROWS ]; do
    y=\$(( Y0 + i * step ))
    dd if=\$raw bs=1 skip=\$(( H + y * stride + X0 * 4 )) count=\$count 2>/dev/null
    i=\$(( i + 1 ))
  done | od -An -tu1 -v | awk \"
    { for (i = 1; i <= NF; i++) { v[m % 4] += \\\$i; if (m % 4 == 0) px++; m++ } }
    END { printf \\\"%d %d %d\\\", v[0]/px, v[1]/px, v[2]/px }\"
  t1=\$(date +%s%N)
  ms=\$(( (t1 - t0) / 1000000 ))
  total=\$(( total + ms ))
  echo \"  \${ms} ms\"
  n=\$(( n + 1 ))
done
echo \"in-device mean \$(( total / N )) ms over \$N reads\"
'"
