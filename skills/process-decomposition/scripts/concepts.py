#!/usr/bin/env python3
"""
Query the vocabulary instead of reading it.

The scheme is a few thousand tokens of data. Reading it to find one concept
costs that on every run, and reading it badly is how a URI gets invented. Ask it
a question instead.

    python scripts/concepts.py search dissolution
    python scripts/concepts.py search "centrifug"
    python scripts/concepts.py list                 # every concept, one line each

`search` prints each match with its full URI and its broader chain, so binding
deep and generalising upward are both visible. No match is an answer: the step is
unmapped and belongs in vocabulary_gaps.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_VOCAB = Path(__file__).resolve().parent.parent / "vocab" / "unit-operations.default.ttl"

PREFIX_RE = re.compile(r"^@prefix\s+([A-Za-z][\w.-]*):\s*<([^>]*)>\s*\.", re.MULTILINE)
# One concept block: the subject line through the terminating period.
BLOCK_RE = re.compile(r"^([A-Za-z][\w.-]*):([\w.-]+)\s+a\s+skos:Concept\b(.*?)\.\s*$",
                      re.MULTILINE | re.DOTALL)
LABEL_RE = re.compile(r'skos:(prefLabel|altLabel)\s+"([^"]+)"')
BROADER_RE = re.compile(r"skos:broader\s+[A-Za-z][\w.-]*:([\w.-]+)")
NOTE_RE = re.compile(r'skos:(definition|scopeNote)\s+"([^"]+)"')


def load(path: Path) -> tuple[dict[str, dict], str]:
    text = path.read_text(encoding="utf-8")
    prefixes = dict(PREFIX_RE.findall(text))
    concepts: dict[str, dict] = {}
    base = ""
    for prefix, local, body in BLOCK_RE.findall(text):
        base = prefixes.get(prefix, "")
        concepts[local] = {
            "uri": f"{base}{local}",
            "labels": [value for _, value in LABEL_RE.findall(body)],
            "broader": (BROADER_RE.search(body).group(1) if BROADER_RE.search(body) else ""),
            "note": (NOTE_RE.search(body).group(2) if NOTE_RE.search(body) else ""),
        }
    return concepts, base


def chain(concepts: dict[str, dict], local: str) -> list[str]:
    """Upward path, which is how a consumer matches (skos:broader*)."""
    path, seen = [], set()
    current = concepts.get(local, {}).get("broader", "")
    while current and current not in seen:
        seen.add(current)
        path.append(current)
        current = concepts.get(current, {}).get("broader", "")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search", help="find concepts whose label or name matches")
    search.add_argument("term")
    listing = sub.add_parser("list", help="every concept, one line each")
    for p in (search, listing):
        p.add_argument("--vocab", type=Path, default=DEFAULT_VOCAB)
    args = parser.parse_args()

    if not args.vocab.is_file():
        print(f"no vocabulary at {args.vocab}", file=sys.stderr)
        return 1
    concepts, _ = load(args.vocab)

    if args.command == "list":
        for local in sorted(concepts):
            up = " < ".join(chain(concepts, local))
            print(f"{local:<24} {up}")
        print(f"\n{len(concepts)} concepts in {args.vocab.name}")
        return 0

    term = args.term.lower()
    hits = [local for local, c in concepts.items()
            if term in local.lower() or any(term in label.lower() for label in c["labels"])]
    if not hits:
        print(f"no concept matches {args.term!r}. The step is unmapped: leave "
              "capability_uri empty, set capability_match to 'unmapped', and add a "
              "vocabulary_gaps entry. Do not invent a URI.")
        return 1
    for local in sorted(hits):
        c = concepts[local]
        print(c["uri"])
        print(f"  labels : {', '.join(c['labels'])}")
        print(f"  broader: {' < '.join(chain(concepts, local)) or '(top concept)'}")
        if c["note"]:
            print(f"  note   : {c['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
