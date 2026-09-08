#!/usr/bin/env python3
"""
Check a decomposition JSON file against the rules in reference/output-schema.md.

Dependency-free on purpose: this runs inside whatever sandbox the agent was given,
and a validator that needs installing is a validator that gets skipped. The
vocabulary is parsed with a regex rather than an RDF library for the same reason -
it only needs the set of declared concept URIs, not a full graph.

    python scripts/validate_decomposition.py run.json
    python scripts/validate_decomposition.py run.json --vocab vocab/other.ttl

Exit code 0 when clean, 1 when any ERROR is reported. WARNINGs do not fail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KINDS = {"UNIT_OPERATION", "UNIT_PROCESS"}
MATCHES = {"exact", "broader", "unmapped"}
CONFIDENCES = {"high", "medium", "low"}

PREFIX_RE = re.compile(r"^@prefix\s+([A-Za-z][\w.-]*):\s*<([^>]*)>\s*\.", re.MULTILINE)
CONCEPT_RE = re.compile(r"^([A-Za-z][\w.-]*):([\w.-]+)\s+a\s+skos:Concept\b", re.MULTILINE)


def load_vocabulary(path: Path) -> set[str]:
    """Expanded URIs of every skos:Concept declared in a Turtle file."""
    text = path.read_text(encoding="utf-8")
    prefixes = dict(PREFIX_RE.findall(text))
    concepts: set[str] = set()
    for prefix, local in CONCEPT_RE.findall(text):
        base = prefixes.get(prefix)
        if base is not None:
            concepts.add(f"{base}{local}")
    return concepts


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"ERROR  {where}: {message}")

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"WARN   {where}: {message}")


def check_step(step: dict, index: int, concepts: set[str], source_ids: set[str],
               seen_ids: set[str], report: Report) -> None:
    where = f"steps[{index}]"
    step_id = step.get("step_id") or ""
    if not step_id:
        report.error(where, "step_id is missing")
    else:
        where = f"steps[{index}] {step_id}"
        if step_id in seen_ids:
            report.error(where, "duplicate step_id")
        seen_ids.add(step_id)

    kind = step.get("kind")
    if kind not in KINDS:
        report.error(where, f"kind must be one of {sorted(KINDS)}, got {kind!r}")

    if not (step.get("kind_basis") or "").strip():
        report.error(where, "kind_basis is empty - state what did or did not change chemically")
    elif (step.get("kind_basis") or "").strip() == (step.get("label") or "").strip():
        report.warn(where, "kind_basis merely repeats label")

    match = step.get("capability_match")
    uri = step.get("capability_uri", "")
    if match not in MATCHES:
        report.error(where, f"capability_match must be one of {sorted(MATCHES)}, got {match!r}")
    elif match == "unmapped":
        if uri:
            report.error(where, "capability_match is 'unmapped' but capability_uri is set")
    else:
        if not uri:
            report.error(where, f"capability_match is {match!r} but capability_uri is empty")
        elif concepts and uri not in concepts:
            # The single most damaging failure mode: a URI that looks real and is not.
            report.error(where, f"capability_uri {uri!r} is not declared in the vocabulary")

    evidence = step.get("evidence") or []
    if not evidence:
        report.error(where, "no evidence - every step needs at least one quoted span")
    for j, item in enumerate(evidence):
        if not (item.get("quote") or "").strip():
            report.error(f"{where} evidence[{j}]", "quote is empty")
        src = item.get("source_id") or ""
        if src and source_ids and src not in source_ids:
            report.error(f"{where} evidence[{j}]", f"source_id {src!r} is not in sources")

    confidence = step.get("confidence")
    if confidence not in CONFIDENCES:
        report.error(where, f"confidence must be one of {sorted(CONFIDENCES)}, got {confidence!r}")
    elif confidence == "low" and not (step.get("open_questions") or []):
        report.error(where, "confidence is 'low' but open_questions is empty")

    conditions = step.get("conditions")
    if isinstance(conditions, dict):
        for key, value in conditions.items():
            if value is not None and not isinstance(value, str):
                report.error(where, f"conditions.{key} must be a string as written, or null")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--vocab", type=Path, default=None,
                        help="Turtle vocabulary (default: the scheme named in run.vocabulary, "
                             "else vocab/unit-operations.default.ttl)")
    args = parser.parse_args()

    try:
        data = json.loads(args.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR  {args.path}: {exc}", file=sys.stderr)
        return 1

    report = Report()
    skill_root = Path(__file__).resolve().parent.parent

    vocab_path = args.vocab
    if vocab_path is None:
        named = (data.get("run") or {}).get("vocabulary")
        candidate = (skill_root / named) if named else (skill_root / "vocab" / "unit-operations.default.ttl")
        vocab_path = candidate if candidate.is_file() else None

    concepts: set[str] = set()
    if vocab_path is not None and vocab_path.is_file():
        concepts = load_vocabulary(vocab_path)
        if not concepts:
            report.warn(str(vocab_path), "no skos:Concept declarations found - URIs cannot be checked")
    else:
        report.warn("run.vocabulary", "vocabulary not found - capability_uri values are unchecked")

    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        report.error("steps", "missing or empty")
        steps = []

    source_ids = {s.get("source_id") for s in (data.get("sources") or []) if s.get("source_id")}
    if not source_ids:
        report.warn("sources", "no sources listed - evidence cannot be traced")

    seen_ids: set[str] = set()
    for index, step in enumerate(steps):
        check_step(step, index, concepts, source_ids, seen_ids, report)

    gap_ids = {g.get("step_id") for g in (data.get("vocabulary_gaps") or [])}
    for step in steps:
        if step.get("capability_match") == "unmapped" and step.get("step_id") not in gap_ids:
            report.error(f"steps {step.get('step_id')}",
                         "unmapped step has no vocabulary_gaps entry")

    hybrid_groups = {h.get("hybrid_group") for h in (data.get("hybrids") or [])}
    for step in steps:
        group = step.get("hybrid_group")
        if group and group not in hybrid_groups:
            report.error(f"steps {step.get('step_id')}",
                         f"hybrid_group {group!r} has no entry in hybrids")

    for line in report.errors + report.warnings:
        print(line)
    total = len(report.errors)
    print(f"\n{total} error(s), {len(report.warnings)} warning(s) across {len(steps)} step(s).")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
