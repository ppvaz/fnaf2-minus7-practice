#!/bin/bash
# Where does the 404 ms of a device-side region read actually go?
#
# The first working probe cost about 400 ms and pushed the Minus 7 schedule
# ~500 ms late, which is a cycle-breaking amount. Before restructuring the
# cycle around that cost it is worth knowing whether the cost is real work or
# just the 10 MB screencap file. Three variants, same rectangle:
#
#   file      screencap to /data/local/tmp, then dd rows out of the file
#   devshm    same, but to /dev (tmpfs on Android) instead of flash
#   stream    screencap piped straight into one dd, no file at all
#
# The stream variant needs the rows to be contiguous, and uses bs=stride so
# the skip is counted in whole rows.
set -euo pipefail
N="${1:-5}"
Y0="${2:-800}"; ROWS="${3:-8}"
W="${SCREEN_WIDTH:-2400}"

adb shell "N=$N Y0=$Y0 ROWS=$ROWS W=$W sh -c '
stride=\$(( W * 4 ))
bench() {
  label=\$1; total=0; n=0
  while [ \$n -lt \$N ]; do
    t0=\$(date +%s%3N)
    case \$label in
      file)   raw=/data/local/tmp/bench.raw
              screencap > \$raw
              dd if=\$raw bs=\$stride skip=\$Y0 count=\$ROWS 2>/dev/null | od -An -tu1 -v | head -2 > /dev/null
              rm -f \$raw ;;
      devshm) raw=/dev/bench.raw
              screencap > \$raw 2>/dev/null || { echo \"  devshm unwritable\"; return; }
              dd if=\$raw bs=\$stride skip=\$Y0 count=\$ROWS 2>/dev/null | od -An -tu1 -v | head -2 > /dev/null
              rm -f \$raw ;;
      stream) screencap | dd bs=\$stride skip=\$Y0 count=\$ROWS 2>/dev/null | od -An -tu1 -v | head -2 > /dev/null ;;
    esac
    t1=\$(date +%s%3N)
    total=\$(( total + t1 - t0 ))
    n=\$(( n + 1 ))
  done
  echo \"  \$label mean \$(( total / N )) ms\"
}
echo \"screencap alone:\"
t0=\$(date +%s%3N); screencap > /data/local/tmp/bench.raw; t1=\$(date +%s%3N)
echo \"  \$(( t1 - t0 )) ms (\$(wc -c < /data/local/tmp/bench.raw) bytes)\"
rm -f /data/local/tmp/bench.raw
bench file
bench devshm
bench stream
'"
