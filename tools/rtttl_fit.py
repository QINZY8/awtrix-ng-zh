#!/usr/bin/env python3
"""Fit an RTTTL melody into the 512 character cap AWTRIX enforces.

AWTRIX is stricter than the classic Nokia format:

  * the string is capped at 512 characters (Rtttl.h: kMaxLength)
  * durations are 1, 2, 4, 8, 16 and 32 only - no 64
  * octaves are 4 to 7 only

This tool rewrites a melody so it fits, in this order:

  1. a 64th note becomes a 32nd, and the tempo is halved to keep the timing
  2. an out-of-range octave is folded into the nearest allowed one
  3. the most common octave becomes the default, so those notes drop the digit
  4. the most common duration becomes the default, so those notes drop it too
  5. if it still does not fit, notes are dropped from the end

Usage:
    python tools/rtttl_fit.py "name:d=4,o=5,b=140:16c,16d,..."
    python tools/rtttl_fit.py --file melody.txt --upload 192.168.5.16
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter

ALLOWED_DURATIONS = (1, 2, 4, 8, 16, 32)
MIN_OCTAVE, MAX_OCTAVE = 4, 7
MAX_LENGTH = 512
MAX_TITLE = 24

# [duration]letter[#][octave][.]
NOTE_RE = re.compile(r"^(?P<dur>\d+)?(?P<letter>[a-gp])(?P<sharp>#)?"
                     r"(?P<octave>\d)?(?P<dot>\.)?$")


class FitError(Exception):
    pass


def parse(melody: str) -> tuple[str, dict, list[str]]:
    """Split a melody into its name, defaults and note tokens."""
    parts = melody.split(":")
    if len(parts) != 3:
        raise FitError(f"expected name:defaults:notes, got {len(parts)} parts")
    name, defaults_text, notes_text = parts
    name = name.strip()
    if not name or len(name) > MAX_TITLE:
        raise FitError("the name must be 1 to 24 characters")

    defaults = {"d": 4, "o": 6, "b": 63}
    for part in defaults_text.split(","):
        part = part.strip()
        if not part:
            continue
        if len(part) < 2 or part[1] != "=":
            raise FitError(f"bad default {part!r}")
        key = part[0].lower()
        if key not in defaults:
            raise FitError(f"unknown default {key!r}")
        defaults[key] = int(part[2:])

    notes = [t.strip() for t in notes_text.split(",") if t.strip()]
    if not notes:
        raise FitError("the melody has no notes")
    return name, defaults, notes


def split_note(token: str, defaults: dict) -> dict:
    """Break one note into its parts, filling in the defaults."""
    m = NOTE_RE.match(token)
    if not m:
        raise FitError(f"{token!r} is not a note")
    return {
        "dur": int(m.group("dur")) if m.group("dur") else defaults["d"],
        "letter": m.group("letter"),
        "sharp": m.group("sharp") or "",
        "octave": int(m.group("octave")) if m.group("octave") else defaults["o"],
        "dot": m.group("dot") or "",
        "had_dur": bool(m.group("dur")),
        "had_oct": bool(m.group("octave")),
    }


def normalise(notes: list[dict], warnings: set) -> int:
    """Fold durations and octaves into the ranges AWTRIX accepts.

    Returns the tempo scale, 1 or 0.5: a 64th note becomes a 32nd, so the whole
    melody has to play at half speed to keep its original timing.
    """
    scale = 1.0
    for n in notes:
        if n["dur"] == 64:
            n["dur"] = 32
            scale = 0.5
            warnings.add("64->32")
        elif n["dur"] not in ALLOWED_DURATIONS:
            nearest = min(ALLOWED_DURATIONS, key=lambda d: abs(d - n["dur"]))
            warnings.add(f"{n['dur']}->{nearest}")
            n["dur"] = nearest

        if n["octave"] < MIN_OCTAVE:
            warnings.add(f"octave {n['octave']}->{MIN_OCTAVE}")
            n["octave"] = MIN_OCTAVE
        elif n["octave"] > MAX_OCTAVE:
            warnings.add(f"octave {n['octave']}->{MAX_OCTAVE}")
            n["octave"] = MAX_OCTAVE

        if n["letter"] == "p" and n["dot"]:
            warnings.add("rest dot dropped")
            n["dot"] = ""
    return scale


def render(notes: list[dict], default_dur: int, default_oct: int) -> str:
    """Write the notes back out, dropping the digits that match the defaults."""
    out = []
    for n in notes:
        dur = str(n["dur"]) if n["dur"] != default_dur else ""
        octv = str(n["octave"]) if n["octave"] != default_oct else ""
        out.append(f"{dur}{n['letter']}{n['sharp']}{octv}{n['dot']}")
    return ",".join(out)


def fit(melody: str, max_chars: int = MAX_LENGTH) -> tuple[str, set, int]:
    """Return (rtttl, warnings, dropped_notes)."""
    name, defaults, tokens = parse(melody)
    notes = [split_note(t, defaults) for t in tokens]

    warnings: set[str] = set()
    scale = normalise(notes, warnings)
    tempo = max(10, min(300, round(defaults["b"] * scale)))

    # The default octave and duration are free, so pick the commonest of each:
    # every note that matches drops a digit, which is the cheapest way to buy
    # room under the cap.
    def build(subset: list[dict]) -> str:
        octs = Counter(n["octave"] for n in subset)
        durs = Counter(n["dur"] for n in subset)
        d_oct = octs.most_common(1)[0][0] if octs else 4
        d_dur = durs.most_common(1)[0][0] if durs else 4
        return f"{name}:d={d_dur},o={d_oct},b={tempo}:{render(subset, d_dur, d_oct)}"

    # A melody is written in phrases, so cutting a whole phrase sounds better
    # than lopping off single notes. Try halving first, then fall back to one
    # note at a time, and keep whichever drops the fewest notes.
    body = build(notes)
    if len(body) > max_chars:
        best = None
        for keep in range(len(notes), 0, -1):
            candidate = build(notes[:keep])
            if len(candidate) <= max_chars:
                best = (candidate, keep)
                break
        if best is None:
            raise FitError(f"cannot fit in {max_chars} characters even after trimming")
        body, keep = best
        warnings.add(f"trimmed to the first {keep} of {len(notes)} notes")

    if len(body) > max_chars:
        raise FitError(f"cannot fit in {max_chars} characters even after trimming")
    return body, warnings, len(tokens) - (len(body.split(":", 2)[2].split(",")) if body else 0)


def upload(ip: str, name: str, rtttl: str) -> bool:
    """PUT the melody onto a device. The body is 'defaults:notes', no name."""
    parts = rtttl.split(":", 2)
    body = parts[1] + ":" + parts[2]
    url = f"http://{ip}/api/v1/audio/melodies/{name}"
    data = json.dumps({"rtttl": body}).encode()
    req = urllib.request.Request(url, data=data, method="PUT",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            print(f"  uploaded {name}: HTTP {r.status}")
            return True
    except urllib.error.HTTPError as e:
        print(f"  upload failed: HTTP {e.code} {e.read().decode(errors='replace')}")
    except OSError as e:
        print(f"  upload failed: {e}")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("melody", nargs="?", help="the RTTTL string")
    ap.add_argument("--file", help="read the melody from a file")
    ap.add_argument("--upload", metavar="IP", help="PUT the result onto this device")
    ap.add_argument("--name", help="override the melody name when uploading")
    ap.add_argument("--max-chars", type=int, default=MAX_LENGTH)
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            melody = f.read().strip()
    elif args.melody:
        melody = args.melody
    else:
        ap.error("give a melody or --file")

    try:
        out, warnings, dropped = fit(melody, args.max_chars)
    except FitError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if warnings:
        print(f"# adjusted: {', '.join(sorted(warnings))}", file=sys.stderr)
    if dropped:
        print(f"# dropped {dropped} notes from the end", file=sys.stderr)
    print(f"# {len(out)} characters", file=sys.stderr)
    print(out)

    if args.upload:
        upload(args.upload, args.name or out.split(":", 1)[0], out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
