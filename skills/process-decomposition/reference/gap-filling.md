# Filling envelope gaps with sub-agents

One literature search per step: slow, context-hungry, embarrassingly parallel.
Delegate it. Without a sub-agent facility, this is the same work done in sequence.

## When to fan out

After the decomposition validates and `unresolved` lists the gaps — never before,
or you search steps that later merge or get dropped.

One sub-agent per **step**, not per quantity. Splitting a step's four quantities
makes three agents read the same paper.

**Batches of two or three.** Sub-agents share the parent's token budget against a
per-minute account limit; a burst exceeds it and a refused spawn is a step nobody
searched. Launch, merge, launch again. Record un-started steps in `unresolved` as
*not attempted* — different from *searched and not found*.

**Tell each sub-agent not to read the skill.** They inherit the parent's tools and
will otherwise each pull the reference files into context — the same few thousand
tokens per sub-agent, for rules the brief already contains. That duplication is
what tips a fan-out over the limit.

Do not delegate classification or vocabulary binding. Those depend on the whole
source and on judgments the parent already made.

## Searching: use the source's own words

Search a distinctive sentence lifted from the process description:

> "cyclohexane is fed to the first of several staged air oxidation vessels, along
> with metaboric acid"

That lands on documents about *that* route. "cyclohexane oxidation temperature"
returns the cobalt-catalysed route, whose conditions differ and whose numbers look
perfectly plausible in your output.

**Read search highlights before fetching.** A citation record whose abstract says
`120~160°C` beats a forty-page patent saying the same thing — you can read all of
it and quote it exactly. Prefer: abstracts and citation records → handbooks and
reviews → a patent's claims → full patent text last.

## Fetching

Use `scripts/fetch_source.py fetch`, then `find` for the offset. If a browser
tool spills a large response to a file, do **not** read it whole and do **not**
run schema inference on it — it is prose, not JSON. Grep for units and read
around the hit:

```bash
grep -nEi '[0-9]+ *(°|deg)? *[CFK][^a-z]|[0-9]+ *(bar|psig?|kPa|MPa|atm|torr)' FILE | head -40
```

A number you cannot quote in context is a number you cannot cite — check the line
is about your step, not a comparative example or prior art.

## The brief

A sub-agent sees **no conversation and no original request**. "Find the
temperature for step P-6" is useless; it does not know what P-6 is. Include:

1. **The step**, searchable by someone who never saw the diagram: the
   transformation, substances by name, equipment as the source names it, and the
   neighbouring steps.
2. **A distinctive quote** from the primary source describing it, to search with.
3. **What is wanted**: temperature, pressure, volume, throughput, materials of
   construction, safety classes.
4. **What is already known**, so it does not re-derive it.
5. **The rules**: a value must come from a source it actually fetched, never
   recall; record URI, title and retrieval time; quote the span; judge
   `applicability` — does the source describe *this* route or an analogous one;
   **"not found" is a valid answer**.
6. **Output path**, exactly `/tmp/env/<step_id>.json`.
7. **Source-id prefix**, exactly `<step_id>-S1`, `<step_id>-S2`, … Sub-agents work
   independently and all pick `S2` for their second source; prefixing stops the
   merge attributing one step's quote to another step's source.
8. **"Do not read the skill directory."**

## The fragment

One file per sub-agent. Never the shared decomposition — concurrent writes lose data.

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
  "materials_required": [], "safety_classes": [],
  "not_found": ["pressure", "volume", "throughput"],
  "notes": "The abstract gives no pressure."
}
```

**Report the value as the source words it, in `as_read`.** Do not convert units in
a sub-agent — the parent normalises every fragment through one converter, so a
fragment is never discarded over unit formatting.

`not_found` says the gap was searched and stays open. That is a result.

## Merging

```bash
python scripts/merge_fragments.py /tmp/decomposition.json --env /tmp/env
python scripts/validate_decomposition.py /tmp/decomposition.json
```

It appends sources, converts each `as_read` through `to_si.py`, writes the range
into the matching spec and clears `not_stated`, keeps a `"source": "primary"`
value over an external one, and separates *searched and not found* from *not
attempted*.

Read its notes: a value it could not convert ("superatmospheric",
"low-temperature") is a source stating a word rather than a bound. That quantity
stays in `not_stated`; the wording belongs in the step's `notes`.

**Do not merge by hand.** All of it is mechanical, and by hand is how a fragment
gets discarded over the shape of its range.

## What goes wrong

- **The plausible-but-different process.** A generic query returns the
  cobalt-catalysed route when the figure shows the boric acid route. That is what
  `applicability` records; a sub-agent unsure which route its source describes
  marks `assumed_from_analogous_process` and says so in `notes`.
- **Agreement that is really one source.** Three pages repeating one handbook
  figure are one source. Prefer a primary over an aggregator.
- **Drowning in a document.** Fetch a full patent, try to read it, spend the whole
  budget on retrieval mechanics, return nothing. Highlights first, grep second,
  full read never.
- **Filling the gap by inference anyway.** An agent told to find a number and
  given no acceptable way to fail will produce one.
