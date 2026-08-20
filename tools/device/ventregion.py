#!/usr/bin/env python3
"""Find the region the left vent light illuminates, and score it for BB.

Two jobs, both about turning "g289 draws Balloon Boy at the opening, g287 draws
it empty" into numbers this phone can act on:

  --find    diff matched off/on capture pairs and report the bounding box of
            whatever the vent light actually lights up. The office view is
            centred and the opening is not obviously in frame, so the region is
            measured rather than read off a screenshot.

  --score   print the region statistic for every `on-` capture, so the frames
            where Balloon Boy was standing there separate from the empty ones
            by inspection instead of by assumption.

  tools/device/ventregion.py --find  captures/<dir>
  tools/device/ventregion.py --score captures/<dir> X0 Y0 X1 Y1
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageChops


def pairs(d):
    for on in sorted(d.glob("on-*.png")):
        off = on.with_name(on.name.replace("on-", "off-", 1))
        if off.exists():
            yield off, on


def find(d, threshold):
    boxes = []
    for off, on in pairs(d):
        a = Image.open(off).convert("L")
        b = Image.open(on).convert("L")
        diff = ImageChops.subtract(b, a)          # only where ON is brighter
        # Drop the HUD strip the debug overlay draws across the top.
        diff.paste(0, (0, 0, diff.width, 30))
        mask = diff.point(lambda v: 255 if v > threshold else 0)
        box = mask.getbbox()
        if box:
            boxes.append(box)
            print(f"{on.name}: lit box {box}")
        else:
            print(f"{on.name}: nothing brightened above {threshold}")
    if not boxes:
        print("no illuminated region found -- was the light actually on?")
        return 1
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    print(f"\nunion of lit boxes: {x0} {y0} {x1} {y1}")
    return 0


def grid(d, cells):
    """Where does the light actually change pixels?

    A bounding box is useless here: the office sways, the static overlay
    animates and characters move, so *something* differs almost everywhere.
    Averaging the signed brightening per grid cell across every pair cancels
    that noise -- only a change correlated with the light survives.
    """
    acc = None
    n = 0
    for off, on in pairs(d):
        a = Image.open(off).convert("L")
        b = Image.open(on).convert("L")
        w, h = a.size
        cw, ch = w // cells, h // cells
        vals = []
        for gy in range(cells):
            row = []
            for gx in range(cells):
                boxc = (gx * cw, gy * ch, (gx + 1) * cw, (gy + 1) * ch)
                ma = sum(Image.Image.getdata(a.crop(boxc))) / (cw * ch)
                mb = sum(Image.Image.getdata(b.crop(boxc))) / (cw * ch)
                row.append(mb - ma)
            vals.append(row)
        acc = vals if acc is None else [
            [acc[y][x] + vals[y][x] for x in range(cells)] for y in range(cells)]
        n += 1
    if not n:
        print("no pairs found")
        return 1
    w, h = Image.open(next(pairs(d))[0]).size
    cw, ch = w // cells, h // cells
    print(f"mean brightening per cell over {n} pairs ({cw}x{ch} px cells)\n")
    best = []
    for gy in range(cells):
        line = []
        for gx in range(cells):
            v = acc[gy][gx] / n
            best.append((v, gx, gy))
            line.append(f"{v:6.1f}")
        print(f"y={gy * ch:4d}  " + " ".join(line))
    best.sort(reverse=True)
    print("\nbrightest cells:")
    for v, gx, gy in best[:5]:
        print(f"  +{v:5.1f}  x {gx * cw}-{(gx + 1) * cw}  y {gy * ch}-{(gy + 1) * ch}")
    return 0


def score(d, box):
    x0, y0, x1, y1 = box
    print(f"{'capture':16} {'mean':>6} {'max':>5} {'sat':>6}")
    for on in sorted(d.glob("on-*.png")):
        im = Image.open(on).convert("RGB").crop((x0, y0, x1, y1))
        px = list(im.getdata())
        n = len(px)
        mean = sum(sum(p) for p in px) / (3 * n)
        peak = max(max(p) for p in px)
        # Balloon Boy is the only saturated thing that can appear there: the
        # empty vent is a grey/brown wall, he is red-and-blue striped.
        sat = sum(max(p) - min(p) for p in px) / n
        print(f"{on.name:16} {mean:6.1f} {peak:5d} {sat:6.2f}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--find", action="store_true")
    ap.add_argument("--grid", type=int, metavar="N")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("dir")
    ap.add_argument("coords", nargs="*", type=int)
    ap.add_argument("--threshold", type=int, default=18)
    args = ap.parse_args()
    d = Path(args.dir)
    if not d.is_dir():
        raise SystemExit(f"no such directory: {d}")
    if args.grid:
        return grid(d, args.grid)
    if args.find:
        return find(d, args.threshold)
    if args.score:
        if len(args.coords) != 4:
            ap.error("--score needs X0 Y0 X1 Y1")
        return score(d, args.coords)
    ap.error("pick --find or --score")


if __name__ == "__main__":
    sys.exit(main())
