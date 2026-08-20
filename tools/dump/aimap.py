#!/usr/bin/env python3
"""Map every character's AI level, per hour, per night, from the event sheet.

The AI counters are what every movement roll compares against, so they are the
difficulty curve of the whole game -- and the simulator only ever encoded the
10/20 column. This reads the real tables out of the Office frame instead.

The shape in the dump: one group per (night, hour) with
`night = N`, optionally `time of the night = H`, and a list of
`<name> AI -> SetCounterValue`. A night's levels are therefore cumulative --
whatever the night set at 12 AM stays until a later hour overwrites it -- and
group 673 zeroes everything first on any night that is not 7.

  tools/dump/aimap.py [path/to/03-04-Office.txt]
  tools/dump/aimap.py --json
"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT = Path.home() / "fnaf-apks/fnaf2/events/03-04-Office.txt"

GROUP = re.compile(r"^--- group (\d+) ---")
NIGHT = re.compile(r"IF\s+night -> CompareCounter \(COMPARISON\{(\S+) Long\[(\d+)\]\}")
HOUR = re.compile(r"IF\s+time of the night -> CompareCounter \(COMPARISON\{= Long\[(\d+)\]\}")
SET = re.compile(r"DO\s+(.+?) AI -> SetCounterValue \(EXPRESSION\{= (.+?)\}\)")
LONG = re.compile(r"^Long\[(\d+)\]$")
# (Random(D) + 1) / D -- integer division, so 1 only when Random rolls D-1.
RAND = re.compile(r"Parenthesis Random Long\[(\d+)\] EndParenthesis Plus Long\[1\] "
                  r"EndParenthesis Divide Long\[(\d+)\]")

NAMES = ["old Freddy", "old Bonnie", "old Chica", "old Foxy",
         "new Freddy", "new Bonnie", "new Chica", "new Foxy",
         "Balloon Boy", "Sockpuppet", "Paperpals", "Golden Freddy"]
# Post-XOR the dump's "old" is Withered and "new" is Toy; `new Foxy` is Mangle.
PRETTY = {
    "old Freddy": "W. Freddy", "old Bonnie": "W. Bonnie", "old Chica": "W. Chica",
    "old Foxy": "W. Foxy", "new Freddy": "Toy Freddy", "new Bonnie": "Toy Bonnie",
    "new Chica": "Toy Chica", "new Foxy": "Mangle", "Balloon Boy": "BB",
    "Sockpuppet": "Puppet", "Paperpals": "PaperPals", "Golden Freddy": "G. Freddy",
}


def value(expr):
    m = LONG.match(expr)
    if m:
        return int(m.group(1))
    m = RAND.search(expr)
    if m and m.group(1) == m.group(2):
        d = int(m.group(1))
        return f"1/{d}"          # 1 with probability 1/d, else 0
    # Night 7 copies the Custom Night dials rather than a fixed table.
    m = re.search(r"CounterValue\[cust_(.+?) AI\]", expr)
    if m:
        return "dial"
    return expr


def parse(path):
    groups = []
    cur = None
    for line in path.read_text(errors="replace").splitlines():
        m = GROUP.match(line)
        if m:
            cur = {"id": int(m.group(1)), "night": None, "night_op": None,
                   "hour": None, "sets": []}
            groups.append(cur)
            continue
        if cur is None:
            continue
        m = NIGHT.search(line)
        if m:
            cur["night_op"], cur["night"] = m.group(1), int(m.group(2))
        m = HOUR.search(line)
        if m:
            cur["hour"] = int(m.group(1))
        m = SET.search(line)
        if m:
            cur["sets"].append((m.group(1).strip(), value(m.group(2).strip())))
    return [g for g in groups if g["sets"] and g["night"] is not None]


def build(groups):
    """Replay the tables. Levels are cumulative within a night."""
    nights = {}
    for night in range(1, 8):
        levels = {n: 0 for n in NAMES}
        per_hour = {}
        for hour in range(0, 7):
            for g in groups:
                if g["night_op"] == "=" and g["night"] != night:
                    continue
                if g["night_op"] == "<>" and g["night"] == night:
                    continue
                # A group with no hour applies at the start of the night.
                gh = g["hour"] if g["hour"] is not None else 0
                if gh != hour:
                    continue
                for name, val in g["sets"]:
                    if name in levels:
                        levels[name] = val
            per_hour[hour] = dict(levels)
        nights[night] = per_hour
    return nights


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=str(DEFAULT))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"no event sheet at {path}")

    nights = build(parse(path))
    if args.json:
        print(json.dumps(nights, indent=2))
        return 0

    print("AI level by hour, from the Office event sheet.")
    print("Hour 0 is 12 AM. A blank column means the level did not change.")
    print('"1/N" is `(Random(N)+1)/N` -- integer division, so AI 1 with '
          "probability 1/N and 0 otherwise.\n")
    for night in range(1, 8):
        label = "10/20 (Custom)" if night == 7 else f"Night {night}"
        print(f"=== {label} ===")
        head = "character   " + "".join(f"{h:>8}" for h in range(7))
        print(head)
        print("            " + "".join(f"{'12AM' if h == 0 else str(h) + 'AM':>8}"
                                       for h in range(7)))
        for name in NAMES:
            row = [nights[night][h][name] for h in range(7)]
            if all(v == 0 for v in row):
                continue
            cells = "".join(f"{str(v):>8}" for v in row)
            print(f"{PRETTY[name]:<12}{cells}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
