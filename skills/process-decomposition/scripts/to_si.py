#!/usr/bin/env python3
"""
Convert a quantity as written in a source into the SI range the schema wants.

Unit conversion done by hand, once per step, across four quantities, is where
gap-filling quietly goes wrong: a bar left unconverted next to a pascal is a
silent wrong answer rather than a visible error. Do it here instead.

    python scripts/to_si.py "120~160 C"          -> temperature range
    python scripts/to_si.py "at least 5 bar"     -> open-topped pressure range
    python scripts/to_si.py "155 degC" --pretty

Prints the range object to stdout, or an explanation to stderr and exit 1 when
the text carries no number ("superatmospheric", "low-temperature"). That failure
is a result: list the quantity in not_stated rather than inventing a bound.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# factor/offset to SI, plus the quantity kind the unit implies.
UNITS: dict[str, tuple[float, float, str, str]] = {
    # spelling        factor   offset    unit_si  quantity_kind
    "c":             (1.0,    273.15,   "K",     "Temperature"),
    "degc":          (1.0,    273.15,   "K",     "Temperature"),
    "celsius":       (1.0,    273.15,   "K",     "Temperature"),
    "f":             (5 / 9,  255.372,  "K",     "Temperature"),
    "degf":          (5 / 9,  255.372,  "K",     "Temperature"),
    "k":             (1.0,    0.0,      "K",     "Temperature"),
    "pa":            (1.0,    0.0,      "Pa",    "Pressure"),
    "kpa":           (1e3,    0.0,      "Pa",    "Pressure"),
    "mpa":           (1e6,    0.0,      "Pa",    "Pressure"),
    "bar":           (1e5,    0.0,      "Pa",    "Pressure"),
    "mbar":          (1e2,    0.0,      "Pa",    "Pressure"),
    "atm":           (101325.0, 0.0,    "Pa",    "Pressure"),
    "psi":           (6894.757, 0.0,    "Pa",    "Pressure"),
    "psig":          (6894.757, 101325.0, "Pa",  "Pressure"),
    "torr":          (133.322, 0.0,     "Pa",    "Pressure"),
    "mmhg":          (133.322, 0.0,     "Pa",    "Pressure"),
    "m3":            (1.0,    0.0,      "m3",    "Volume"),
    "l":             (1e-3,   0.0,      "m3",    "Volume"),
    "litre":         (1e-3,   0.0,      "m3",    "Volume"),
    "liter":         (1e-3,   0.0,      "m3",    "Volume"),
    "kg/s":          (1.0,    0.0,      "kg/s",  "Throughput"),
    "kg/h":          (1 / 3600, 0.0,    "kg/s",  "Throughput"),
    "t/h":           (1000 / 3600, 0.0, "kg/s",  "Throughput"),
    "kt/y":          (1e6 / 31_536_000, 0.0, "kg/s", "Throughput"),
}

NUMBER = r"[-+]?\d+(?:[.,]\d+)?"
# "120~160", "120-160", "120 to 160". The en dash shows up in scanned sources.
RANGE_RE = re.compile(rf"({NUMBER})\s*(?:~|--|-|–|—|to)\s*({NUMBER})", re.IGNORECASE)
SINGLE_RE = re.compile(NUMBER)
LOWER_ONLY = re.compile(r"\b(at least|above|over|minimum|min\.?|greater than|>|>=)\b", re.IGNORECASE)
UPPER_ONLY = re.compile(r"\b(at most|below|under|maximum|max\.?|less than|<|<=|up to)\b", re.IGNORECASE)


def find_unit(text: str) -> tuple[str, tuple[float, float, str, str]]:
    """
    Longest matching unit spelling wins, so 'psig' is not read as 'psi'.

    Returns the unit as the source spelled it, not the lookup key: display_unit
    exists so an answer renders the way an engineer expects to read it, and
    'MPa' lowercased to 'mpa' defeats that.
    """
    cleaned = text.replace("°", " ").replace("º", " ")
    best: tuple[str, tuple[float, float, str, str]] | None = None
    for spelling, conv in UNITS.items():
        match = re.search(rf"(?<![a-z0-9]){re.escape(spelling)}(?![a-z0-9])", cleaned, re.IGNORECASE)
        if match and (best is None or len(spelling) > len(best[0])):
            best = (match.group(0), conv)
    if best is None:
        raise ValueError("no recognised unit; add it to UNITS or record the quantity as not_stated")
    return best


def convert(value: float, factor: float, offset: float) -> float:
    return round(value * factor + offset, 6)


def parse(text: str) -> dict:
    spelling, (factor, offset, unit_si, kind) = find_unit(text)

    match = RANGE_RE.search(text)
    if match:
        lo = convert(float(match.group(1).replace(",", ".")), factor, offset)
        hi = convert(float(match.group(2).replace(",", ".")), factor, offset)
        if lo > hi:
            lo, hi = hi, lo
    else:
        numbers = SINGLE_RE.findall(text)
        if not numbers:
            raise ValueError("no number found - the source states a word, not a bound")
        point = convert(float(numbers[0].replace(",", ".")), factor, offset)
        if LOWER_ONLY.search(text):
            lo, hi = point, None
        elif UPPER_ONLY.search(text):
            lo, hi = None, point
        else:
            lo = hi = point

    return {
        "min_si": lo,
        "max_si": hi,
        "unit_si": unit_si,
        "display_unit": spelling,
        "quantity_kind": kind,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help='the quantity as the source words it, e.g. "120~160 C"')
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        result = parse(args.text)
    except ValueError as exc:
        print(f"cannot convert {args.text!r}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
