#!/usr/bin/env python3
"""
Merge gap-filling fragments into a decomposition.

Everything here is bookkeeping: append sources, convert a value to SI, move a
quantity out of not_stated, carry an unfilled gap into unresolved. Done by hand
it is where searches get lost - a fragment discarded for the shape of its range
is a search thrown away over formatting, and a step whose sub-agent never ran
looks identical to one that was searched and found nothing.

    python scripts/merge_fragments.py /tmp/decomposition.json --env /tmp/env
    python scripts/merge_fragments.py run.json --env /tmp/env --out merged.json

Values arrive as the source worded them (`as_read`) and are converted here, so
conversion happens once, the same way, for every fragment. Re-run the validator
afterwards.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from to_si import parse as parse_quantity  # noqa: E402

QUANTITIES = ("temperature", "pressure", "volume", "throughput")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def merge_fragment(data: dict, fragment: dict, notes: list[str]) -> None:
    step_id = fragment.get("step_id")
    spec = next((s for s in data.get("requirement_specs", []) if s.get("step_id") == step_id), None)
    if spec is None:
        notes.append(f"{step_id}: fragment has no matching requirement_specs entry; skipped")
        return

    known = {s.get("source_id") for s in data.setdefault("sources", [])}
    for source in fragment.get("sources", []):
        if source.get("source_id") not in known:
            data["sources"].append(source)
            known.add(source.get("source_id"))

    not_stated = set(spec.get("not_stated") or [])
    for name, entry in (fragment.get("quantities") or {}).items():
        if name not in QUANTITIES:
            notes.append(f"{step_id}: fragment names unknown quantity {name!r}; skipped")
            continue
        # A value read from the process document itself outranks anything a
        # sub-agent found elsewhere.
        existing = spec.get(name)
        if existing is not None and existing.get("source") == "primary":
            notes.append(f"{step_id}.{name}: kept the primary value; external one discarded")
            continue

        as_read = entry.get("as_read")
        if not as_read:
            notes.append(f"{step_id}.{name}: fragment has no as_read value; left unfilled")
            continue
        try:
            si = parse_quantity(str(as_read))
        except ValueError as exc:
            # The source stated a word, not a bound - a real finding, not an error.
            notes.append(f"{step_id}.{name}: {as_read!r} is not a bound ({exc}); left in not_stated")
            continue

        merged = dict(si)
        for key in ("source", "applicability", "evidence"):
            if entry.get(key) is not None:
                merged[key] = entry[key]
        merged.setdefault("source", "external")
        spec[name] = merged
        not_stated.discard(name)

    spec["not_stated"] = [q for q in QUANTITIES if q in not_stated]

    unresolved = data.setdefault("unresolved", [])
    missing = spec["not_stated"]
    if missing:
        unresolved.append({
            "kind": "operating_envelope",
            "applies_to": step_id,
            "detail": f"searched; not stated in any source found: {', '.join(missing)}."
                      + (f" {fragment['notes']}" if fragment.get("notes") else ""),
        })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("decomposition", type=Path)
    parser.add_argument("--env", type=Path, default=Path("/tmp/env"),
                        help="directory holding <step_id>.json fragments")
    parser.add_argument("--out", type=Path, default=None, help="default: overwrite in place")
    args = parser.parse_args()

    try:
        data = load(args.decomposition)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read {args.decomposition}: {exc}", file=sys.stderr)
        return 1

    notes: list[str] = []
    merged_steps = 0
    for path in sorted(args.env.glob("*.json")) if args.env.is_dir() else []:
        try:
            merge_fragment(data, load(path), notes)
            merged_steps += 1
        except (OSError, json.JSONDecodeError) as exc:
            notes.append(f"{path.name}: unreadable ({exc})")

    # A step with no fragment was never searched, which is a different finding
    # from one that was searched and came back empty.
    have = {p.stem for p in args.env.glob("*.json")} if args.env.is_dir() else set()
    for spec in data.get("requirement_specs", []):
        step_id = spec.get("step_id")
        if step_id not in have and (spec.get("not_stated") or []):
            data.setdefault("unresolved", []).append({
                "kind": "operating_envelope",
                "applies_to": step_id,
                "detail": "not attempted - no gap-filling fragment was produced for this step.",
            })

    destination = args.out or args.decomposition
    destination.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    filled = sum(1 for s in data.get("requirement_specs", [])
                 for q in QUANTITIES if s.get(q) is not None)
    print(f"merged {merged_steps} fragment(s) into {destination}")
    print(f"{filled} quantity value(s) now present across "
          f"{len(data.get('requirement_specs', []))} spec(s)")
    for note in notes:
        print(f"  note: {note}")
    print("\nre-run validate_decomposition.py on the result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
