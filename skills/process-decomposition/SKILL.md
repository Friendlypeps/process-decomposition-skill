---
name: process-decomposition
description: Decompose a chemical process description or process flow diagram into ordered unit operations and unit processes, with flowsheet topology and operating envelopes, each bound to a controlled vocabulary concept and backed by a quoted span. Use when given process text or a PFD/block flow diagram (paper, patent, encyclopaedia entry, vendor page, scraped web content, figure) and asked what steps the process consists of, how they connect, or to produce a flowsheet, a step list, module-matching requirements, or RDF triples describing a process.
---

# Process decomposition

Turn a process description into ordered steps, the streams connecting them, and
the operating envelope each step needs — every claim classified, bound to a
vocabulary concept, and carrying the quote it came from.

The output is checked line by line by an engineer, not read as a summary. A step
nobody can trace to a sentence is worth less than no step at all.

## The one distinction that matters

**Unit process** — chemical identity changes; bonds break or form. Nitration,
oxidation, hydrogenation, calcination, combustion, electrolysis, fermentation.

**Unit operation** — chemical identity unchanged; only phase, composition,
particle size, temperature, pressure or location changes. Distillation,
filtration, drying, crystallisation, extraction, heat exchange, milling.

Apply the test **to the substances, not the equipment and not the wording**.
"Reactor" is equipment. "Dehydration" is a unit operation when water leaves a wet
solid and a unit process when an alcohol becomes an alkene. Read the chemistry.

Ambiguous cases get `low` confidence and an `open_questions` entry. A flagged
uncertainty is a finding; a confident wrong classification propagates.

## Three readings, kept apart

| Reading | From | Lands in |
|---|---|---|
| what the steps are | text, or a figure's legend | `steps` |
| how they connect | a figure, or explicit text | `streams` |
| what conditions they need | text, or a cited external source | `requirement_specs` |

A diagram gives topology and equipment identity, almost never temperature,
pressure, flow or phase. **A number not in the source was not read from the
source.** `reference/operating-envelope.md` gives the only route to a missing
value, and it requires a citation.

## Scripts — use them, they are not optional

Each replaces a stage with no judgment in it, and each exists because doing that
stage by hand produced a repeated error.

```bash
scripts/fetch_source.py fetch <URL> --id S1 --out /tmp/src   # read a page
scripts/fetch_source.py find "<phrase>" --in /tmp/src/S1.txt # offset for a quote
scripts/fetch_source.py quantities --in /tmp/src/S1.txt      # every stated value
scripts/fetch_source.py window <offset> --in /tmp/src/S1.txt # read around a hit
scripts/concepts.py search <term>                            # bind to a concept
scripts/to_si.py "<value as written>"                        # unit conversion
scripts/merge_fragments.py <file> --env /tmp/env             # fold in gap fills
scripts/validate_decomposition.py <file>                     # after every edit
```

`quantities` returning nothing means the source states no conditions — a finding
to report, not a gap to fill. `concepts.py search` finding nothing means the step
is unmapped. Never read the vocabulary file to pick a URI; query it.

Use a browser only for what the fetcher cannot reach: figures, and pages needing
interaction. Never navigate by evaluating script in whatever document is loaded —
that reads an empty tab as easily as an article.

**A source you could not fetch cannot support a claim.** Record it
`readable: false`; no evidence may cite it and no step may rest on it. If nothing
was readable, say so and emit nothing — a decomposition assembled from what you
know about the chemistry is indistinguishable from one that was read.

## How to work

1. **Read the whole source first.** Do not classify while reading; sources state
   conditions out of order and qualify earlier claims later.
2. **If there is a diagram**, load `reference/flowsheet.md`: bind the legend
   before tracing any line, close recycle loops, report lines you could not follow.
3. **Fix granularity and say so** in `granularity_note`. One step per
   transformation with its own purpose, conditions and inlet/outlet streams. One
   drawn block may be two steps.
4. **Classify** with the identity test. Load `reference/classification.md` for the
   boundary cases — reactive distillation, ion exchange, calcination,
   absorption vs chemisorption — whenever a step is not obviously one or the other.
5. **Bind to a concept** via `concepts.py search`, and say why in
   `capability_basis`. No match means `capability_uri: ""`,
   `capability_match: "unmapped"`, and a `vocabulary_gaps` entry. **Never invent a
   URI** — a fabricated one looks authoritative and is wrong.
6. **Build envelopes — one `requirement_specs` entry per step, no exceptions.**
   Run `quantities` before concluding anything is unstated. Every quantity is
   either a range or named in `not_stated`. See
   `reference/operating-envelope.md`.
7. **Quote evidence** for every step and stream, with the offset from
   `fetch_source.py find`. Never `-1` for a text source. Inferred rather than
   read goes in `evidence[].note` with lower confidence.
8. **Coverage pass.** Re-read looking only for process verbs — oxidised,
   separated, crystallised, centrifuged, dried, recycled, decomposed, hydrolysed,
   concentrated, filtered. Each becomes a `coverage` entry naming its step or why
   it is excluded. Sources spend paragraphs on chemistry and half a clause on
   "final centrifugation and drying"; this is where dropped operations surface.
9. **Emit** JSON, and Turtle when asked. See `reference/output-schema.md`.
10. **Validate, fix, validate again.** Every edit invalidates the last result.
    Quote the validator's step table as your report rather than retyping it — a
    typed list drifts from the file, that one cannot. If your count and its count
    disagree, the file is not what you think it is.
11. **If gaps remain** and sub-agents are available, load
    `reference/gap-filling.md` and delegate — after validation passes, never
    before. Merge with `merge_fragments.py`, then validate again.

## What not to do

- Do not merge a reaction and its downstream separation because one sentence
  described both. A label containing "and" or "then" is usually several steps.
- Do not stop at the chemistry. Five reactions plus "centrifugation and drying"
  in passing is seven steps.
- Do not classify from a verb alone. "Extraction" is a unit operation; "reactive
  extraction" is a hybrid — two steps, or a `hybrid` marker.
- Do not supply conditions from background knowledge. Unstated is omitted plus
  `not_stated`, never a typical value.
- Do not emit a range open on both sides for an unknown. That means "anything
  qualifies" and matches every candidate module.
- Do not report "unresolved: none" while quantities sit in `not_stated`.
- Do not straighten out a recycle. The flowsheet is a directed graph with cycles.
- Do not renumber steps to look tidier. Unstated order is `order: null`.
