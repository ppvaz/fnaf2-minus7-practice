#!/usr/bin/env python3
"""Find Golden Freddy in the office in an existing capture.

He has to be *seen* rather than prevented. A blind pilot flicks the mask every
cycle just in case, and that flick is what squeezes the hall flash: g778 kills
if the hall is flashed with him present and g776 makes a mask touch the only
clear, so the flick must precede the flash, while g75/g84 mean the flash must
follow the mask being fully off. Dropping the flick blind is not an option --
without it he takes 199/200 nights at a median of 13 s. Seeing him is.

He is observable on the night the harness is allowed to run: g804 zeroes his AI
only *below* night 6, and g830 caps it at 10 so 10/20 is exactly one in two.
6th Night has him.

He is also an easy target compared with the vent: he fills the centre of the
office and he is the only large saturated-gold thing that appears there. This
scores that, so a threshold can be measured off footage already on disk instead
of guessed, and so we can confirm he actually shows up in runs we have.

  tools/device/goldenscan.py CAPTURE.mp4 [--fps 6] [--top 15]
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

# The office centre, where the figure appears. Deliberately wide: the exact
# frame is not known and a miss costs a whole calibration run.
BOX = (700, 150, 1700, 900)


def frames(path, fps, outdir):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps}",
         "-q:v", "3", str(outdir / "f_%05d.jpg")],
        check=True,
    )
    return sorted(outdir.glob("f_*.jpg"))


def gold_score(img, box):
    """Fraction of the region that is bright and gold.

    Gold here is red and green both high and clearly above blue, which is what
    separates him from the office's warm brown desk lamp and from the pink mask
    bar. Scored as a fraction so region size does not matter.
    """
    im = img.convert("RGB").crop(box)
    im = im.resize((im.width // 4, im.height // 4))
    px = list(im.getdata())
    hits = 0
    for r, g, b in px:
        if r > 110 and g > 90 and r - b > 55 and g - b > 35:
            hits += 1
    return hits / len(px)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture")
    ap.add_argument("--fps", type=float, default=6)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--box", nargs=4, type=int, default=list(BOX))
    args = ap.parse_args()

    path = Path(args.capture)
    if not path.exists():
        raise SystemExit(f"no such capture: {path}")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        fs = frames(path, args.fps, out)
        if not fs:
            raise SystemExit("ffmpeg produced no frames")
        scored = []
        for i, f in enumerate(fs):
            s = gold_score(Image.open(f), tuple(args.box))
            scored.append((s, i / args.fps, f.name))
        scored.sort(reverse=True)
        print(f"{path.name}: {len(fs)} frames at {args.fps} fps, "
              f"box {tuple(args.box)}")
        mean = sum(s for s, _, _ in scored) / len(scored)
        print(f"mean gold fraction {mean:.4f}\n")
        print(f"{'t':>8}  {'gold':>7}")
        for s, t, _ in scored[:args.top]:
            print(f"{t:8.2f}  {s:7.4f}")
        print("\nA flat list near the mean means he never appeared; a clear "
              "cluster well above it is him.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
