# process-decomposition-skill

An agent skill that turns a chemical process description into an ordered list of
steps, each classified as a **unit operation** or a **unit process**, bound to a
SKOS concept, and carrying the quoted span it was read from.

Built to be mounted by [TrueForge](https://github.com/truefoundry/trueforge) as a
git skill, and to be portable into other agent runtimes afterwards.

```
skills/process-decomposition/
├── SKILL.md                          the instructions the agent reads
├── reference/
│   ├── classification.md             the unit operation / unit process rubric and its edge cases
│   ├── output-schema.md              JSON and Turtle shapes
│   └── vocabulary.md                 how to bind a step to a concept
├── vocab/unit-operations.default.ttl a standalone SKOS scheme (replaceable)
├── examples/adipic-acid.json         a worked decomposition that validates clean
└── scripts/validate_decomposition.py dependency-free output validator
```

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
