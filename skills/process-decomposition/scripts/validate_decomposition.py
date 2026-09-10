#!/usr/bin/env python3
"""
Check a decomposition JSON file against the rules in reference/output-schema.md.

The checks that matter most are about *absence*, not shape. A decomposition that
quietly omits its operating envelopes and reports nothing unresolved looks clean
to any validator that only inspects what is present, so this one requires every
step to account for every quantity explicitly.

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
SERVICES = {"process", "utility"}

ROLES = {"Feed", "Intermediate", "ProductStream", "Recycle",
         "ByproductStream", "OffGas", "Utility", "Waste"}
# Roles that legitimately have one end at the plant boundary.
OPEN_ROLES = {"Feed", "ProductStream", "OffGas", "Waste", "Utility", "ByproductStream"}
ORIGINS = {"stated", "inferred", "boundary"}

QUANTITIES = ("temperature", "pressure", "volume", "throughput")
RANGE_SOURCES = {"primary", "external"}
APPLICABILITY = {"stated_for_this_process", "assumed_from_analogous_process"}

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
        # Grouped by message: sixteen copies of one warning is one finding, and
        # printing it sixteen times buries the other fifteen findings.
        self.warnings: dict[str, list[str]] = {}

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"ERROR  {where}: {message}")

    def warn(self, where: str, message: str) -> None:
        self.warnings.setdefault(message, []).append(where)

    def warning_lines(self) -> list[str]:
        lines = []
        for message, places in self.warnings.items():
            if len(places) == 1:
                lines.append(f"WARN   {places[0]}: {message}")
            else:
                shown = ", ".join(places[:3])
                more = f", +{len(places) - 3} more" if len(places) > 3 else ""
                lines.append(f"WARN   {message} [x{len(places)}: {shown}{more}]")
        return lines

    @property
    def warning_count(self) -> int:
        return sum(len(places) for places in self.warnings.values())


def check_evidence(items: list, where: str, sources: dict, report: Report,
                   *, required: bool = True) -> None:
    if not items:
        if required:
            report.error(where, "no evidence - every claim needs at least one quoted span")
        return
    for j, item in enumerate(items):
        spot = f"{where} evidence[{j}]"
        if not (item.get("quote") or "").strip():
            report.error(spot, "quote is empty")
        src = item.get("source_id") or ""
        if not src:
            continue
        if sources and src not in sources:
            report.error(spot, f"source_id {src!r} is not in sources")
            continue
        source = sources.get(src, {})
        # A source that could not be fetched cannot support a claim.
        if source.get("readable") is False:
            report.error(spot, f"source {src!r} is marked unreadable and cannot back a claim")
        if item.get("offset", -1) == -1 and source.get("kind") not in (None, "figure"):
            report.warn(spot, f"offset is -1 on a {source.get('kind')} source - "
                              "a quote from fetched text should carry its position")


def check_step(step: dict, index: int, concepts: set[str], sources: dict,
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

    if step.get("kind") not in KINDS:
        report.error(where, f"kind must be one of {sorted(KINDS)}, got {step.get('kind')!r}")

    label = (step.get("label") or "").strip()
    basis = (step.get("kind_basis") or "").strip()
    if not basis:
        report.error(where, "kind_basis is empty - state what did or did not change chemically")
    elif basis == label:
        report.warn(where, "kind_basis merely repeats label")

    service = step.get("service")
    if service is not None and service not in SERVICES:
        report.error(where, f"service must be one of {sorted(SERVICES)}, got {service!r}")

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
        cap_basis = (step.get("capability_basis") or "").strip()
        if not cap_basis:
            report.error(where, "capability_basis is empty - say why this concept, "
                                "citing the duty or equipment the source names")
        elif cap_basis == label:
            report.warn(where, "capability_basis merely repeats label")

    check_evidence(step.get("evidence") or [], where, sources, report)

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


def check_stream(stream: dict, index: int, step_ids: set[str], sources: dict,
                 seen_ids: set[str], report: Report) -> None:
    where = f"streams[{index}]"
    stream_id = stream.get("stream_id") or ""
    if not stream_id:
        report.error(where, "stream_id is missing")
    else:
        where = f"streams[{index}] {stream_id}"
        if stream_id in seen_ids:
            report.error(where, "duplicate stream_id")
        seen_ids.add(stream_id)

    role = stream.get("role")
    if role not in ROLES:
        report.error(where, f"role must be one of {sorted(ROLES)}, got {role!r}")

    origin = stream.get("origin")
    if origin not in ORIGINS:
        report.error(where, f"origin must be one of {sorted(ORIGINS)}, got {origin!r}")

    from_step = stream.get("from_step") or ""
    to_step = stream.get("to_step") or ""
    for label, ref in (("from_step", from_step), ("to_step", to_step)):
        if ref and step_ids and ref not in step_ids:
            report.error(where, f"{label} {ref!r} is not a known step_id")

    # An Intermediate or Recycle open at one end is a gap, not a boundary.
    if role in ROLES and role not in OPEN_ROLES and not (from_step and to_step):
        report.error(where, f"role {role!r} requires both from_step and to_step; "
                            "an open end here is a gap, not the plant boundary")
    if origin == "boundary" and from_step and to_step:
        report.error(where, "origin is 'boundary' but both ends are connected")

    for label, port, ref in (("from_port", stream.get("from_port"), from_step),
                             ("to_port", stream.get("to_port"), to_step)):
        if port and not ref:
            report.error(where, f"{label} is set but {label.replace('_port', '_step')} is empty")

    confidence = stream.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            report.error(where, f"confidence must be a number in [0, 1], got {confidence!r}")
        elif origin == "stated" and confidence < 1:
            report.warn(where, "origin is 'stated' but confidence is below 1.0")

    check_evidence(stream.get("evidence") or [], where, sources, report, required=False)


def check_range(rng: dict, where: str, sources: dict, report: Report) -> None:
    if not isinstance(rng, dict):
        report.error(where, "must be an object")
        return

    lo, hi = rng.get("min_si"), rng.get("max_si")
    if lo is None and hi is None:
        # The rule that matters most: this reads as "any value qualifies".
        report.error(where, "both min_si and max_si are null - list the quantity in "
                            "not_stated instead; an unbounded range matches every candidate")
    for label, value in (("min_si", lo), ("max_si", hi)):
        if value is not None and not isinstance(value, (int, float)):
            report.error(where, f"{label} must be a number or null, got {value!r}")
    if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo > hi:
        report.error(where, f"min_si ({lo}) is greater than max_si ({hi})")

    if not (rng.get("unit_si") or "").strip():
        report.error(where, "unit_si is required - consumers cannot convert units")
    if not (rng.get("quantity_kind") or "").strip():
        report.error(where, "quantity_kind is required")

    source = rng.get("source")
    if source is not None and source not in RANGE_SOURCES:
        report.error(where, f"source must be one of {sorted(RANGE_SOURCES)}, got {source!r}")
    if source == "external":
        if rng.get("applicability") not in APPLICABILITY:
            report.error(where, "an external range must state applicability, one of "
                                f"{sorted(APPLICABILITY)}")
    evidence = rng.get("evidence")
    if not evidence:
        if source == "external":
            report.error(where, "an external range must cite the source it was filled from")
    else:
        check_evidence([evidence] if isinstance(evidence, dict) else evidence,
                       where, sources, report)


def check_requirement_spec(spec: dict, index: int, steps_by_id: dict, concepts: set[str],
                           sources: dict, report: Report) -> list[str]:
    """Returns the quantities this spec declared not stated."""
    where = f"requirement_specs[{index}]"
    step_id = spec.get("step_id") or ""
    if not step_id:
        report.error(where, "step_id is missing")
    else:
        where = f"requirement_specs[{index}] {step_id}"
        step = steps_by_id.get(step_id)
        if step is None:
            report.error(where, f"step_id {step_id!r} is not a known step")
        else:
            if spec.get("kind") != step.get("kind"):
                report.error(where, f"kind {spec.get('kind')!r} disagrees with the step's "
                                    f"{step.get('kind')!r}")
            if spec.get("capability_uri", "") != step.get("capability_uri", ""):
                report.error(where, "capability_uri disagrees with the step's")

    uri = spec.get("capability_uri", "")
    if uri and concepts and uri not in concepts:
        report.error(where, f"capability_uri {uri!r} is not declared in the vocabulary")

    not_stated = spec.get("not_stated")
    if not isinstance(not_stated, list):
        report.error(where, "not_stated is missing - list every quantity the source "
                            "did not state, so absence is a claim rather than a silence")
        not_stated = []
    for name in not_stated:
        if name not in QUANTITIES:
            report.error(where, f"not_stated names {name!r}, which is not one of {list(QUANTITIES)}")

    # Every quantity is either given or explicitly declared missing - never neither.
    for quantity in QUANTITIES:
        present = spec.get(quantity) is not None
        declared = quantity in not_stated
        if present and declared:
            report.error(where, f"{quantity} is both given and listed in not_stated")
        elif not present and not declared:
            report.error(where, f"{quantity} is neither given nor listed in not_stated")
        elif present:
            check_range(spec[quantity], f"{where}.{quantity}", sources, report)

    for substance in spec.get("substances") or []:
        if not (substance.get("name") or "").strip():
            report.error(where, "a substance has no name")
        if substance.get("identifier") and not (substance.get("scheme") or "").strip():
            report.error(where, f"substance {substance.get('name')!r} has an identifier "
                                "but no scheme naming what it identifies")
    return list(not_stated)


def check_coverage(data: dict, steps_by_id: dict, report: Report) -> None:
    """
    Every process action named in the source must reach a step or an explicit
    exclusion. This is what catches the two quiet failures a shape check cannot:
    an action that was dropped, and several actions compressed into one step.
    """
    coverage = data.get("coverage")
    if not isinstance(coverage, list) or not coverage:
        report.error("coverage", "missing - list every process action the source names, "
                                 "each mapped to a step_id or excluded_because")
        return

    per_step: dict[str, list[str]] = {}
    for index, entry in enumerate(coverage):
        where = f"coverage[{index}]"
        action = (entry.get("action") or "").strip()
        if not action:
            report.error(where, "action is empty - name the operation as the source words it")
        if not (entry.get("quote") or "").strip():
            report.error(where, "quote is empty - coverage is a claim about the source")

        step_id = entry.get("step_id") or ""
        excluded = (entry.get("excluded_because") or "").strip()
        if bool(step_id) == bool(excluded):
            report.error(where, "needs exactly one of step_id or excluded_because")
        elif step_id:
            if step_id not in steps_by_id:
                report.error(where, f"step_id {step_id!r} is not a known step")
            else:
                per_step.setdefault(step_id, []).append(action or f"entry {index}")

    # Several distinct actions on one step is compression, not decomposition.
    for step_id, actions in per_step.items():
        if len(actions) > 1 and not (steps_by_id[step_id].get("merged_because") or "").strip():
            report.error(f"steps {step_id}",
                         f"{len(actions)} source actions map to this one step "
                         f"({'; '.join(actions)}) - split them, or set merged_because "
                         "to say why the source treats them as indivisible")

    for step_id in steps_by_id:
        if step_id not in per_step:
            report.warn(f"steps {step_id}",
                        "no coverage entry names the source action this step came from")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--vocab", type=Path, default=None,
                        help="Turtle vocabulary (default: the scheme named in run.vocabulary, "
                             "else vocab/unit-operations.default.ttl)")
    args = parser.parse_args()

    try:
        # utf-8-sig so a byte-order mark does not fail the file for a reason
        # that has nothing to do with the decomposition.
        data = json.loads(args.path.read_text(encoding="utf-8-sig"))
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

    sources = {s.get("source_id"): s for s in (data.get("sources") or []) if s.get("source_id")}
    if not sources:
        report.warn("sources", "no sources listed - evidence cannot be traced")
    for source_id, source in sources.items():
        if not (source.get("uri") or "").strip():
            report.error(f"sources {source_id}", "uri is missing - a source with no locator "
                                                 "cannot be checked by a reader")
    if sources and all(s.get("readable") is False for s in sources.values()):
        report.error("sources", "every source is marked unreadable - nothing here was actually "
                                "read, so no step can be supported")

    seen_steps: set[str] = set()
    for index, step in enumerate(steps):
        check_step(step, index, concepts, sources, seen_steps, report)

    steps_by_id = {s.get("step_id"): s for s in steps if s.get("step_id")}

    seen_streams: set[str] = set()
    for index, stream in enumerate(data.get("streams") or []):
        check_stream(stream, index, seen_steps, sources, seen_streams, report)

    specs = data.get("requirement_specs") or []
    any_not_stated = False
    for index, spec in enumerate(specs):
        if check_requirement_spec(spec, index, steps_by_id, concepts, sources, report):
            any_not_stated = True

    # Absence check: silence must not read as completeness.
    spec_step_ids = {s.get("step_id") for s in specs if s.get("step_id")}
    for step in steps:
        if step.get("step_id") not in spec_step_ids:
            report.error(f"steps {step.get('step_id')}",
                         "no requirement_specs entry - every step must account for its "
                         "envelope, even if only to say nothing was stated")

    unresolved = data.get("unresolved") or []
    if any_not_stated and not any(u.get("kind") == "operating_envelope" for u in unresolved):
        report.error("unresolved", "quantities are marked not_stated but no "
                                   "'operating_envelope' entry reports the gap")

    check_coverage(data, steps_by_id, report)

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

    for line in report.errors + report.warning_lines():
        print(line)
    total = len(report.errors)
    print(f"\n{total} error(s), {report.warning_count} warning(s) across "
          f"{len(steps)} step(s), {len(data.get('streams') or [])} stream(s), "
          f"{len(specs)} spec(s).")

    # The step list is printed from the file that was just checked, so a report
    # cannot pair a stale pass with a newer set of steps. Quote this block rather
    # than retyping it.
    if steps:
        not_stated_by_step = {s.get("step_id"): s.get("not_stated") or [] for s in specs}
        print(f"\nsteps in {args.path.name}:")
        for step in steps:
            uri = step.get("capability_uri") or ""
            concept = uri.rsplit("#", 1)[-1].rsplit("/", 1)[-1] if uri else "unmapped"
            match = step.get("capability_match", "")
            gaps = not_stated_by_step.get(step.get("step_id"))
            envelope = "no envelope" if gaps and len(gaps) == len(QUANTITIES) else \
                       f"{len(QUANTITIES) - len(gaps or [])}/{len(QUANTITIES)} quantities" \
                       if gaps is not None else "NO SPEC"
            print(f"  {str(step.get('step_id')):<6} {str(step.get('kind')):<14} "
                  f"{concept:<18} {match:<8} {str(step.get('confidence')):<7} {envelope}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
