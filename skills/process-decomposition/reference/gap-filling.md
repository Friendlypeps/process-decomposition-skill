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

**Spawn in batches of two or three.** Sub-agents share the parent's token budget
against a per-minute account limit, and a burst of them exceeds it: a refused
spawn is a step nobody ever searched. Launch a batch, merge its fragments, launch
the next. Any step whose sub-agent never started is recorded in `unresolved` as
*not attempted* — a different finding from *searched and not found*, and the
difference matters to whoever picks the work up.

**Tell each sub-agent not to read this skill.** They inherit the parent's tools
and will otherwise each pull the reference files into context — the same several
thousand tokens, once per sub-agent, for rules the brief already contains. That
duplication is what pushes a fan-out over a per-minute limit. The brief is the
sub-agent's whole instruction set; state the rules in it and say plainly that the
skill directory is not to be read.

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
8. **"Do not read the skill directory."** Said outright — the brief is complete
   without it, and reading it multiplies the token cost of the fan-out by the
   number of sub-agents.

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

Run the merger. It is all bookkeeping and none of it is judgment:

```bash
python scripts/merge_fragments.py /tmp/decomposition.json --env /tmp/env
python scripts/validate_decomposition.py /tmp/decomposition.json
```

It appends each fragment's sources, converts every `as_read` value through
`to_si.py`, writes the range into the matching `requirement_specs` entry and
clears it from `not_stated`, keeps a `"source": "primary"` value over anything a
sub-agent found, and records what is still missing in `unresolved` — separating
*searched and not found* from *not attempted*, which is what a step with no
fragment means.

Read its notes. A value it could not convert ("superatmospheric",
"low-temperature") is a source stating a word rather than a bound: that quantity
stays in `not_stated`, and the wording is worth a line in the step's `notes`.

Do not merge by hand. Every part of it is mechanical, and doing it by hand is how
a fragment gets discarded over the shape of its range.

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
