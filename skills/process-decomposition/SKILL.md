---
name: process-decomposition
description: Decompose a chemical process description or process flow diagram into ordered unit operations and unit processes, with flowsheet topology and operating envelopes, each bound to a controlled vocabulary concept and backed by a quoted span. Use when given process text or a PFD/block flow diagram (paper, patent, encyclopaedia entry, vendor page, scraped web content, figure) and asked what steps the process consists of, how they connect, or to produce a flowsheet, a step list, module-matching requirements, or RDF triples describing a process.
---

# Process decomposition

Turn a process description into an ordered list of steps, the streams that
connect them, and the operating envelope each step requires — every claim
classified, bound to a vocabulary concept, and carrying the quote it came from.

The output is a decomposition an engineer can check line by line, not a summary.
A step nobody can trace back to a sentence is worth less than no step at all.

## The one distinction that matters

**Unit process** — chemical identity changes. Bonds break or form. Nitration,
oxidation, hydrogenation, esterification, calcination, combustion, electrolysis,
fermentation, polymerisation.

**Unit operation** — chemical identity is unchanged. Only phase, composition,
particle size, temperature, pressure, or location changes. Distillation,
filtration, drying, crystallisation, extraction, heat exchange, milling, conveying.

Apply the test **to the substances, not to the equipment and not to the wording**.
"Reactor" is equipment. "Dehydration" is a unit operation when water is driven off
a wet solid and a unit process when an alcohol becomes an alkene. Read the
chemistry, not the noun.

Do not guess when the source is genuinely ambiguous — mark the step `low`
confidence and record the question in `open_questions`. A flagged uncertainty is
a finding; a confident wrong classification is a defect that propagates.

## Three readings, kept apart

A source carries three different kinds of claim, and mixing them is what makes a
decomposition unusable:

| Reading | Comes from | Lands in |
|---|---|---|
| What the steps are | text or a figure's legend | `steps` |
| How they connect | a figure, or explicit text | `streams` |
| What conditions they need | text, or a cited external source | `requirement_specs` |

A diagram gives topology and equipment identity. It almost never gives
temperature, pressure, flow or phase. **If a number is not in the source, it was
not read from the source** — do not supply it from what you know about the
chemistry. `reference/operating-envelope.md` gives the only route by which a
missing value may be filled, and it requires a citation.

## How to work

1. **Read the whole source first.** Do not classify while reading. Process
   descriptions state conditions out of order and qualify earlier claims later.
2. **If there is a diagram**, load `reference/flowsheet.md` and follow it: bind the
   legend before tracing any line, then trace edges, close recycle loops, assign
   stream roles, and report every line you could not follow.
3. **Fix the granularity and say so.** One step per transformation with its own
   purpose, conditions, and inlet/outlet streams. One drawn block may be two
   steps. Record the choice in `granularity_note`.
4. **Classify each step** with the identity test above. Load
   `reference/classification.md` for the boundary cases — reactive distillation,
   ion exchange, calcination, absorption vs chemisorption. Consult it whenever a
   step is not obviously one or the other; those cases are where decompositions
   go wrong.
5. **Bind each step to a vocabulary concept.** See `reference/vocabulary.md`.
   When no concept fits, leave `capability_uri` empty, set
   `capability_match: "unmapped"`, and add a `vocabulary_gaps` entry.
   **Never invent a concept URI** — a fabricated URI looks authoritative and is
   wrong.
6. **Build the operating envelopes.** Load `reference/operating-envelope.md`.
   SI-normalise every range; omit unknown quantities entirely rather than
   emitting open-ended ones. When gaps remain and sub-agents are available,
   load `reference/gap-filling.md` and delegate the search — one sub-agent per
   step, after the decomposition validates, never before.
7. **Quote your evidence.** Every step and every stream needs at least one
   `evidence` entry. If you inferred something rather than read it, say so in
   `evidence[].note` and lower the confidence.
8. **Emit** JSON, and Turtle when asked. See `reference/output-schema.md`.
9. **Validate** before reporting:
   `python scripts/validate_decomposition.py <file.json>`
   Fix what it reports. Do not hand over output that fails validation.

## What not to do

- Do not merge a reaction and its downstream separation into one step because the
  source describes them in one sentence.
- Do not classify from a verb in isolation. "Extraction" is a unit operation;
  "reactive extraction" is a hybrid and gets two steps or a `hybrid` marker.
- Do not fill in conditions from background knowledge and present them as read.
  Unstated is omitted, not a typical value.
- Do not emit a range that is open on both sides to represent an unknown. That
  means "anything qualifies" and matches every candidate module.
- Do not straighten out a recycle. The flowsheet is a directed graph with cycles.
- Do not renumber or reorder steps to look tidier than the source supports. If the
  order is not stated, set `order: null` and note it.
