#!/usr/bin/env python3
"""Mean R,G,B over a screen rectangle, host-side, plus a device cross-check.

`regionmean.sh` computes the same statistic on the phone, because the Minus 7
driver runs inside one adb shell and anything the schedule branches on has to
be computed without a USB round trip. That makes the device implementation
load-bearing and awkward to trust: it hand-decodes a raw screencap using an
assumed 16-byte header and a 2400-px stride, in shell.

This module is how that gets checked. Same rectangle, same sampling, computed
from a PNG with PIL, and `--verify` runs both against one screen and compares.
If the header offset or stride assumption is ever wrong, --verify is what says
so; the device script alone would just return plausible numbers.

  tools/device/regionmean.py IMAGE X0 Y0 X1 Y1 [--rows N]
  tools/device/regionmean.py --verify X0 Y0 X1 Y1 [--rows N] [--tolerance T]

Prints "R G B".
"""
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent


def rows_for(y0, y1, rows):
    """The same rows regionmean.sh samples: N evenly spaced, integer step."""
    span = y1 - y0
    step = max(1, span // rows)
    out = []
    for i in range(rows):
        y = y0 + i * step
        if y >= y1:
            break
        out.append(y)
    return out


def mean_from_image(path, x0, y0, x1, y1, rows):
    im = Image.open(path).convert("RGB")
    px = im.load()
    total = [0, 0, 0]
    count = 0
    for y in rows_for(y0, y1, rows):
        for x in range(x0, x1):
            r, g, b = px[x, y]
            total[0] += r
            total[1] += g
            total[2] += b
            count += 1
    if not count:
        raise SystemExit("empty rectangle")
    return tuple(v // count for v in total)


def mean_from_device(x0, y0, x1, y1, rows):
    out = subprocess.run(
        ["bash", str(HERE / "regionmean.sh"), str(x0), str(y0), str(x1),
         str(y1), str(rows)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    parts = out.stdout.decode().split()
    if len(parts) != 3:
        raise SystemExit("device read failed")
    return tuple(int(p) for p in parts)


def grab(path):
    with open(path, "wb") as fh:
        subprocess.run(["adb", "exec-out", "screencap", "-p"],
                       stdout=fh, stderr=subprocess.DEVNULL, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?")
    ap.add_argument("coords", nargs=4, type=int)
    ap.add_argument("--rows", type=int, default=8)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--tolerance", type=int, default=12)
    args = ap.parse_args()
    x0, y0, x1, y1 = args.coords

    if not args.verify:
        if not args.image:
            ap.error("need an image, or --verify")
        print("%d %d %d" % mean_from_image(args.image, x0, y0, x1, y1, args.rows))
        return 0

    # One screen, both paths. The static overlay animates every frame, so the
    # two captures are never the same instant -- the tolerance is against that,
    # not against arithmetic error.
    tmp = Path(args.image or "/tmp/fnaf2-regionmean-verify.png")
    grab(tmp)
    host = mean_from_image(tmp, x0, y0, x1, y1, args.rows)
    device = mean_from_device(x0, y0, x1, y1, args.rows)
    delta = max(abs(h - d) for h, d in zip(host, device))
    print(f"host   {host[0]} {host[1]} {host[2]}")
    print(f"device {device[0]} {device[1]} {device[2]}")
    print(f"max channel delta {delta} (tolerance {args.tolerance})")
    if delta > args.tolerance:
        print("FAIL  the device decode disagrees with the host decode")
        return 1
    print("PASS  device and host agree on the same rectangle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
