# Filling envelope gaps with sub-agents

A diagram pass ends with steps and topology but no operating envelope. Closing
those gaps means searching the literature once per step, which is slow, fills the
context window with pages that are mostly irrelevant, and is embarrassingly
parallel. Delegate it.

Use this only when a sub-agent facility is available. Everything here is
otherwise the same work done sequentially by one agent.

## When to fan out

After the decomposition validates and `unresolved` lists the gaps — not before.
Fanning out first wastes searches on steps that later merge or get dropped.

One sub-agent per **step**, not per quantity. A step needing temperature,
pressure and materials is one brief; splitting it makes three agents read the
same paper.

Do not delegate the classification or the vocabulary binding. Those depend on the
whole source and on judgments the parent has already made. A sub-agent fills
values; it does not decide what the step is.

## The brief

A sub-agent has **no access to the conversation, the original request, or the
parent's reasoning**. Everything it needs goes in the brief. A brief that says
"find the temperature for step P-6" is useless — the sub-agent does not know what
P-6 is.

Include, in this order:

1. **The step**, described so it could be searched by someone who has never seen
   the diagram: the transformation, the substances by name, the equipment as the
   source names it, and the neighbouring steps.
2. **What is wanted** — the specific quantities, named: temperature, pressure,
   volume, throughput, materials of construction, safety classes.
3. **What is already known**, so it does not re-derive it: the target product, the
   route, and any quantity already filled.
4. **The rules**, restated (the sub-agent may not have read them):
   - a value must come from a source it actually fetched, never from recall
   - record the URI, the title, and the retrieval timestamp
   - quote the span the number sits in
   - SI-normalise, and keep the unit the source used as `display_unit`
   - judge `applicability`: does the source describe *this* process and route, or
     an analogous one?
   - **"not found" is a valid, useful answer** — say so rather than settling for
     a number about a different process
5. **The output path**, exactly: `/tmp/env/<step_id>.json`.
6. **The source-id prefix**, exactly: `<step_id>-S1`, `<step_id>-S2`, …

That last point is not cosmetic. Sub-agents work independently and will all
choose `S2` for their second source; prefixing by step is what stops the merge
from silently attributing one step's quote to another step's source.

## The fragment

Each sub-agent writes one file. It does not touch the main decomposition — a
shared file written by several agents at once loses writes.

```json
{
  "step_id": "P-6",
  "sources": [
    { "source_id": "P-6-S1", "uri": "https://patents.google.com/patent/US3644526A/en",
      "title": "Oxidation of cyclohexane", "kind": "patent",
      "retrieved_at": "2026-09-08T17:40:00Z" }
  ],
  "quantities": {
    "temperature": {
      "min_si": 418.15, "max_si": 448.15, "unit_si": "K",
      "display_unit": "degC", "quantity_kind": "Temperature",
      "source": "external",
      "applicability": "stated_for_this_process",
      "evidence": { "source_id": "P-6-S1", "quote": "...", "offset": -1,
                    "note": "the patent describes the metaboric acid route drawn in the figure" }
    }
  },
  "materials_required": [],
  "safety_classes": [],
  "not_found": ["throughput", "volume"],
  "notes": "Pressure is given only as 'superatmospheric'; no bound could be read."
}
```

`not_found` is as much a result as `quantities`. It tells the parent the gap was
searched and stays open, which is different from a gap nobody looked at.

## Merging

The parent, not a sub-agent, does this:

1. Read every fragment. A missing file means that sub-agent failed — record it in
   `unresolved`, do not silently drop the step.
2. Append each fragment's `sources` to the top-level `sources`. Ids are already
   prefixed, so there is nothing to renumber.
3. Copy each quantity into the step's `requirement_specs` entry. Never overwrite a
   value already read from the primary document — a `"source": "primary"` range
   outranks anything a sub-agent found.
4. Carry every `not_found` entry into `unresolved` with the step it belongs to.
5. Run `scripts/validate_decomposition.py` on the merged file. The validator
   checks that every external range cites a `source_id` that now exists, which is
   what catches a fragment whose sources were dropped in the merge.

## What goes wrong

- **The plausible-but-different process.** A search for "cyclohexane oxidation
  temperature" returns the cobalt-catalysed route when the figure shows the boric
  acid route. The conditions differ. This is what `applicability` exists to
  record, and a sub-agent that cannot tell which route its source describes should
  say so in `notes` and mark `assumed_from_analogous_process`.
- **Agreement that is really one source.** Three pages repeating the same
  handbook figure are one source, not three. Prefer a primary source — patent,
  paper, plant description — over an aggregator.
- **Filling the gap by inference anyway.** A sub-agent under instruction to find a
  number will be tempted to compute one. The brief must say plainly that an
  unfilled gap is an acceptable outcome, or it will get a fabricated one.
