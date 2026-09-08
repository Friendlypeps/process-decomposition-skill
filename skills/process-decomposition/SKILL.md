---
name: process-decomposition
description: Decompose a chemical process description into ordered unit operations and unit processes, each bound to a controlled vocabulary concept and backed by a quoted span from the source. Use when given process text (a paper, patent, encyclopaedia entry, vendor page, or scraped web content) and asked what steps the process consists of, or asked to produce a flowsheet skeleton, a step list, or RDF triples describing a process.
---

# Process decomposition

Turn prose about a chemical process into an ordered list of steps, each classified
as a **unit operation** or a **unit process**, bound to a vocabulary concept, and
carrying the quote it was read from.

The output is a decomposition an engineer can check line by line — not a summary.
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

## How to work

1. **Read the whole source first.** Do not classify while reading. Process
   descriptions state conditions out of order and qualify earlier claims later.
2. **Fix the granularity and say so.** One step per transformation with its own
   purpose, conditions, and inlet/outlet streams. Record the choice in
   `granularity_note` — "reactor section split into preheat / reaction / quench"
   is a defensible decision; leaving it implicit is not.
3. **Classify each step** with the identity test above. Load
   `reference/classification.md` for the boundary cases — reactive distillation,
   ion exchange, calcination, absorption vs chemisorption. Consult it whenever a
   step is not obviously one or the other; those cases are where decompositions
   go wrong.
4. **Bind each step to a vocabulary concept.** See `reference/vocabulary.md`.
   When no concept fits, leave `capability_uri` empty, set
   `capability_match: "unmapped"`, and add an entry to `vocabulary_gaps`.
   **Never invent a concept URI** — a fabricated URI looks authoritative and is
   wrong.
5. **Quote your evidence.** Every step needs at least one `evidence` entry with a
   verbatim span. If you inferred a step rather than read it, say so in
   `evidence[].note` and drop confidence to `medium` or `low`.
6. **Emit** JSON, and Turtle when asked. See `reference/output-schema.md`.
7. **Validate** before reporting:
   `python scripts/validate_decomposition.py <file.json>`
   Fix what it reports. Do not hand over output that fails validation.

## What not to do

- Do not merge a reaction and its downstream separation into one step because the
  source describes them in one sentence.
- Do not classify from a verb in isolation. "Extraction" is a unit operation;
  "reactive extraction" is a hybrid and gets two steps or a `hybrid` marker.
- Do not fill in conditions from background knowledge and present them as read.
  Unstated is `null`, not a typical value.
- Do not renumber or reorder steps to look tidier than the source supports. If the
  order is not stated, set `order: null` and note it.
