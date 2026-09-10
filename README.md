# process-decomposition-skill

An agent skill that turns a chemical process description into an ordered list of
steps, each classified as a **unit operation** or a **unit process**, bound to a
SKOS concept, and carrying the quoted span it was read from.

Built to be mounted by [TrueForge](https://github.com/truefoundry/trueforge) as a
git skill, and to be portable into other agent runtimes afterwards.

```
skills/process-decomposition/          ← the only path mounted into the sandbox
├── SKILL.md                           the instructions the agent reads
├── reference/
│   ├── classification.md              the unit operation / unit process rubric and its edge cases
│   ├── flowsheet.md                   reading topology off a diagram: roles, origins, ports, utilities
│   ├── gap-filling.md                 delegating the envelope search to sub-agents, and merging it back
│   ├── operating-envelope.md          SI ranges, unknown vs unbounded, the cited-source rule
│   ├── output-schema.md               JSON and Turtle shapes
│   └── vocabulary.md                  how to bind a step to a concept
├── vocab/unit-operations.default.ttl  a standalone SKOS scheme (replaceable)
└── scripts/
    ├── concepts.py                    query the vocabulary instead of reading it
    ├── fetch_source.py                fetch, then find quotes and quantities by offset
    ├── merge_fragments.py             fold gap-filling fragments into the decomposition
    ├── to_si.py                       unit conversion
    └── validate_decomposition.py      dependency-free output validator

examples/                              deliberately OUTSIDE the mounted path
├── adipic-acid.json                   prose decomposition
└── adipic-acid-flowsheet.json         diagram decomposition with topology and specs
```

Examples live at the repo root on purpose. They were briefly inside the skill, and
an agent asked to decompose adipic acid found a finished adipic acid
decomposition in its own sandbox and mirrored it instead of reading the source.
A worked example of the process a user is likely to analyse is not documentation
in that position — it is an answer key. Keep them out of the mounted path.

## What it is for

Extraction agents reliably produce a *plausible* step list. The failure modes that
matter are quieter:

- a step silently defaulted to one classification because the field was omitted
- a capability URI that was invented rather than looked up, which is
  indistinguishable from a real one once it is in a triple store
- a condition filled in from background knowledge and presented as read
- a reaction and its downstream separation merged because one sentence described both

The skill is built around preventing those four. Every step must state *what
changed chemically* (`kind_basis`), must carry a verbatim quote, and must either
bind to a declared concept or be recorded as a vocabulary gap. The validator
enforces all of it and exits non-zero on any violation.

## Flowsheets and module matching

Given a process flow diagram, the skill also emits `streams` (the topology, as a
directed graph that may contain recycle cycles) and `requirement_specs` (the
matching key: capability plus SI-normalised operating envelope, substances,
materials and safety classes). Field names match a `MaterialStream` /
`RequirementSpec` contract pair so the output loads without re-mapping.

Two rules do most of the work:

- **A diagram gives topology, not numbers.** Block flow diagrams carry equipment
  identity and connectivity, almost never temperature, pressure or flow. Values
  that are not in the source are omitted, and the gap is reported in `unresolved`.
- **Unknown is not unconstrained.** An unknown quantity is an omitted key, never a
  range open on both sides — the latter means "any value qualifies" and matches
  every candidate module. The validator rejects it.

A missing value may be filled only from a citable external source, recorded with
its own `source_id` and marked `applicability: "stated_for_this_process"` or
`"assumed_from_analogous_process"` — because a handbook value proves the number
exists, not that this plant runs there.

Reading a diagram needs a vision-capable model. Text-only sources work on any model.

## Using it with TrueForge

Register it as a skill, then reference it from an agent spec:

```bash
curl -X PUT http://localhost:8791/api/v1/settings/skills \
  -H 'content-type: application/json' \
  -d '{"manifest":{"type":"git","name":"process-decomposition",
       "url":"https://github.com/<owner>/process-decomposition-skill",
       "path":"skills/process-decomposition","ref":"main",
       "description":"Decompose a chemical process description into ordered unit operations and unit processes, bound to a controlled vocabulary and backed by quoted evidence."}}'
```

Two prerequisites, both of which TrueForge enforces:

1. **The repo must be public on github.com or gitlab.com.** The URL is validated
   against those two hosts, and the sandbox clones without credentials. A
   self-hosted GitLab remote is rejected.
2. **A sandbox provider must be configured.** Skills are sparse-cloned into a
   sandbox, so an agent spec requesting one fails with HTTP 422 until
   `PUT /api/v1/settings/sandbox-providers` is set (or the server runs with
   `STANDALONE=true` and the local sandbox fallback available).

It pairs naturally with a browser MCP: scrape the process description, then hand
the text to this skill.

## Replacing the vocabulary

`vocab/unit-operations.default.ttl` uses an `http://example.org/unitop#`
namespace precisely so it cannot be mistaken for anyone's real scheme. To bind
against your own, point `run.vocabulary` at it and pass `--vocab` to the
validator. Do not merge the two schemes — see `reference/vocabulary.md`.

The output field names (`step_id`, `kind`, `capability_uri`, and
`evidence.source_id/quote/offset/note`) were chosen to match a `ProcessStep` /
`Evidence` contract pair, so a consumer can map them without renaming.

## Validating output

```bash
python skills/process-decomposition/scripts/validate_decomposition.py run.json
```

No third-party packages required. Exit code 0 when clean, 1 on any error;
warnings do not fail the run.
