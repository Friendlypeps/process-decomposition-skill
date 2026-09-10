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

**Spawn in batches of four or five.** Sub-agent creation is rate-limited, and a
spawn that is refused is a step nobody ever searched. Launch a batch, merge its
fragments, launch the next. Any step whose sub-agent never started is recorded in
`unresolved` as *not attempted* — which is a different finding from *searched and
not found*, and the difference matters to whoever picks the work up.

Do not delegate the classification or the vocabulary binding. Those depend on the
whole source and on judgments the parent has already made. A sub-agent fills
values; it does not decide what the step is.

## Searching: use the source's own words

Search with a distinctive sentence lifted from the process description, not a
generic description of the chemistry.

> "cyclohexane is fed to the first of several staged air oxidation vessels, along
> with metaboric acid"

lands on documents about *that* route. "cyclohexane oxidation temperature"
returns the cobalt-catalysed route, whose conditions are different and whose
numbers will look perfectly plausible in your output.

**Read the search highlights before fetching anything.** Results carry snippets,
and a snippet frequently contains the number. A citation record whose abstract
says `120~160°C` is a *better* source than a forty-page patent that says the same
thing, because you can read all of it and quote it exactly.

Prefer, in this order:

1. abstracts and citation records
2. encyclopaedia, handbook and review entries
3. a patent's claims section
4. full patent text — last resort

## When a fetch comes back too large

A full patent overflows the tool response and gets written to a file instead. When
that happens:

- **Do not read the file whole.** That is the context blowup you delegated to
  avoid, now happening inside the sub-agent.
- **Do not run schema inference on it.** It is prose, not JSON; the inferrer exits
  with an error and you have spent a turn learning nothing.
- **Grep it for units**, then read the lines around a hit:

  ```bash
  grep -nEi '[0-9]+ *(°|deg)? *[CFK][^a-z]|[0-9]+ *(bar|psig?|kPa|MPa|atm|torr)' FILE | head -40
  sed -n '1180,1200p' FILE
  ```

A number you cannot quote in context is a number you cannot cite. Grep finds the
line; read around it to check the line is about your step and not a comparative
example or a prior-art paragraph.

## The brief

A sub-agent has **no access to the conversation, the original request, or the
parent's reasoning**. Everything it needs goes in the brief. A brief that says
"find the temperature for step P-6" is useless — the sub-agent does not know what
P-6 is.

Include, in this order:

1. **The step**, described so it could be searched by someone who has never seen
   the diagram: the transformation, the substances by name, the equipment as the
   source names it, and the neighbouring steps.
2. **A distinctive quote from the primary source** describing this step, to search
   with directly.
3. **What is wanted** — the specific quantities: temperature, pressure, volume,
   throughput, materials of construction, safety classes.
4. **What is already known**, so it does not re-derive it.
5. **The rules**, restated (the sub-agent may not have read them):
   - a value must come from a source it actually fetched, never from recall
   - record the URI, the title, and the retrieval timestamp
   - quote the span the number sits in
   - judge `applicability`: does the source describe *this* process and route, or
     an analogous one?
   - **"not found" is a valid, useful answer** — say so rather than settling for
     a number about a different process
6. **The output path**, exactly: `/tmp/env/<step_id>.json`.
7. **The source-id prefix**, exactly: `<step_id>-S1`, `<step_id>-S2`, …

That last point is not cosmetic. Sub-agents work independently and will all
choose `S2` for their second source; prefixing by step is what stops the merge
from silently attributing one step's quote to another step's source.

## The fragment

Each sub-agent writes one file. It does not touch the main decomposition — a
shared file written by several agents at once loses writes.

```json
{
  "step_id": "P-5",
  "sources": [
    { "source_id": "P-5-S1", "uri": "https://hero.epa.gov/reference/7947766/",
      "title": "Autoxidation of cyclohexane in the presence of metaboric acid",
      "kind": "web", "retrieved_at": "2026-09-10T09:40:00Z", "readable": true }
  ],
  "quantities": {
    "temperature": {
      "as_read": "120~160°C",
      "source": "external",
      "applicability": "stated_for_this_process",
      "evidence": { "source_id": "P-5-S1",
                    "quote": "the decomposition was measured over 120~160°C",
                    "offset": 812 }
    }
  },
  "materials_required": [],
  "safety_classes": [],
  "not_found": ["pressure", "volume", "throughput"],
  "notes": "The abstract gives no pressure."
}
```

**Report the value as the source words it, in `as_read`.** Do not convert units in
a sub-agent. The parent normalises every fragment through one converter, so the
conversion is done the same way everywhere and a fragment is never rejected for a
malformed range — a search discarded over unit formatting is a search wasted.

`not_found` is as much a result as `quantities`. It says the gap was searched and
stays open, which is different from a gap nobody looked at.

## Merging

The parent, not a sub-agent, does this:

1. Read every fragment. A missing file means that sub-agent failed — record it in
   `unresolved`, do not silently drop the step.
2. Convert each `as_read` value:

   ```bash
   python scripts/to_si.py "120~160°C"
   ```

   It returns the `min_si`/`max_si`/`unit_si`/`display_unit`/`quantity_kind`
   object. If it exits non-zero the source stated a word and not a bound
   ("superatmospheric", "low-temperature") — that quantity goes to `not_stated`,
   and the wording is worth a line in `notes`.
3. Append each fragment's `sources` to the top-level `sources`. Ids are already
   prefixed, so there is nothing to renumber.
4. Copy each converted quantity into the step's `requirement_specs` entry, and
   remove it from that spec's `not_stated`. Never overwrite a value read from the
   primary document — a `"source": "primary"` range outranks anything a sub-agent
   found.
5. Carry every `not_found` and every un-started sub-agent into `unresolved`.
6. Re-run `scripts/validate_decomposition.py`. It checks that every external range
   cites a `source_id` that now exists and is readable, which is what catches a
   fragment whose sources were dropped in the merge.

## What goes wrong

- **The plausible-but-different process.** A search for "cyclohexane oxidation
  temperature" returns the cobalt-catalysed route when the figure shows the boric
  acid route. The conditions differ. This is what `applicability` exists to
  record, and a sub-agent that cannot tell which route its source describes should
  say so in `notes` and mark `assumed_from_analogous_process`.
- **Agreement that is really one source.** Three pages repeating the same
  handbook figure are one source, not three. Prefer a primary source — patent,
  paper, plant description — over an aggregator.
- **Drowning in a document.** A sub-agent that fetches a full patent and tries to
  read it spends its whole budget on retrieval mechanics and returns nothing.
  Search highlights first, grep second, full read never.
- **Filling the gap by inference anyway.** A sub-agent under instruction to find a
  number will be tempted to compute one. The brief must say plainly that an
  unfilled gap is an acceptable outcome, or it will get a fabricated one.
