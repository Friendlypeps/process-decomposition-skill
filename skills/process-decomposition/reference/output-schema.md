# Output schema

JSON is canonical. Turtle is a projection of it — emit Turtle only when asked, and
never emit Turtle that says something the JSON does not.

Field names and enum values deliberately match the `ProcessStep`, `MaterialStream`
and `RequirementSpec` contracts used downstream, so a consumer can load the output
without renaming. Extra keys this skill adds (`kind_basis`, `capability_basis`,
`evidence`, `source`, `applicability`, `not_stated`, `from_port`) are ignored by
those deserializers, so carrying them costs nothing.

The examples below use methyl acetate esterification. They are shape
illustrations, **not** a decomposition to imitate — never carry a step, substance
or condition from this file into your output.

## Top level

```json
{
  "run":               { ... },
  "sources":           [ ... ],
  "steps":             [ ... ],
  "streams":           [ ... ],
  "requirement_specs": [ ... ],
  "hybrids":           [ ... ],
  "vocabulary_gaps":   [ ... ],
  "unresolved":        [ ... ]
}
```

**Every step gets a `requirement_specs` entry.** A spec with no ranges is a
meaningful statement — "this step's envelope was not stated" — and an absent spec
is not. Omitting them is how a decomposition ends up silently claiming nothing was
missing.

## sources[]

```json
{ "source_id": "S1", "uri": "https://example.org/article", "title": "...",
  "kind": "web", "retrieved_at": "2026-09-08T18:42:00Z", "chars": 18400,
  "readable": true }
```

`kind` is `web`, `pdf`, `file`, `figure`, or `patent`. `chars` is how much text you
actually read; `readable: false` marks a source you tried and failed to fetch.

**A source you could not fetch cannot back a claim.** If `readable` is false, no
evidence may cite it, and no step may rest on it. A download that 403s is a gap to
report, not a source to cite. If you could not read the source at all, say so and
emit nothing rather than reconstructing the process from what you know.

## steps[]

```json
{
  "step_id": "P-1", "order": 1, "diagram_ref": "3",
  "label": "Esterification of acetic acid with methanol",
  "kind": "UNIT_PROCESS",
  "kind_basis": "Acetic acid and methanol are converted to methyl acetate and water; an ester bond forms.",
  "service": "process",
  "capability_uri": "http://example.org/unitop#Esterification",
  "capability_match": "exact",
  "capability_basis": "The source names the duty as esterification over an acid catalyst.",
  "equipment_as_stated": "reactive distillation column",
  "inputs": ["acetic acid", "methanol"], "outputs": ["methyl acetate", "water"],
  "conditions": { "temperature": "70 C", "pressure": null, "catalyst": "sulfuric acid" },
  "reaction": { "equation": "CH3COOH + CH3OH -> CH3COOCH3 + H2O", "balanced": true },
  "hybrid_group": "H1",
  "evidence": [{ "source_id": "S1", "quote": "...", "offset": 4120, "note": "" }],
  "confidence": "high", "open_questions": [], "notes": ""
}
```

- `kind` — exactly `"UNIT_OPERATION"` or `"UNIT_PROCESS"`. A hybrid is two steps.
- `kind_basis` — one sentence naming what changed or did not change chemically.
- `capability_basis` — one sentence saying why *this* concept, referring to the
  duty or equipment the source names. Required unless `capability_match` is
  `"unmapped"`. Without it a wrong binding is invisible in review.
- `service` — `"process"` or `"utility"`.
- `capability_match` — `"exact"`, `"broader"`, or `"unmapped"`. When `"unmapped"`,
  `capability_uri` must be `""` and a `vocabulary_gaps` entry must exist.
- `conditions` — strings as written, or `null`. The machine-comparable form lives
  in `requirement_specs`.
- `evidence.offset` — the character position of the quote in the fetched text. Use
  `-1` only for a figure, where there is no text offset.

## streams[]

One edge of the flowsheet. See `reference/flowsheet.md` for roles and origins.

```json
{
  "stream_id": "ST-2", "label": "column overhead",
  "substances": [{ "name": "methyl acetate", "identifier": "79-20-9", "scheme": "CAS" }],
  "role": "ProductStream", "from_step": "P-1", "to_step": "",
  "from_port": "overhead", "to_port": null, "spec": "",
  "origin": "boundary", "confidence": 1.0,
  "evidence": [{ "source_id": "S1", "quote": "...", "offset": 4460, "note": "" }]
}
```

- `role` — `Feed`, `Intermediate`, `ProductStream`, `Recycle`, `ByproductStream`,
  `OffGas`, `Utility`, `Waste`.
- `origin` — `stated`, `inferred`, `boundary`.
- `from_step` / `to_step` — a `step_id`, or `""` at the plant boundary. An
  `Intermediate` or `Recycle` open at one end is a gap; report it in `unresolved`.
- `from_port` / `to_port` — optional free-text hints. Annotations only.
- Recycles make the graph cyclic. That is expected.

## requirement_specs[]

The machine-comparable matching key. One per step, always.

```json
{
  "step_id": "P-1", "kind": "UNIT_PROCESS",
  "capability_uri": "http://example.org/unitop#Esterification",
  "temperature": {
    "min_si": 338.15, "max_si": 348.15, "unit_si": "K",
    "display_unit": "degC", "quantity_kind": "Temperature",
    "source": "primary",
    "evidence": { "source_id": "S1", "quote": "held at 65-75 C", "offset": 4180 }
  },
  "not_stated": ["pressure", "volume", "throughput"],
  "phase": "liquid",
  "substances": [{ "name": "acetic acid", "identifier": "64-19-7", "scheme": "CAS" }],
  "materials_required": [], "safety_classes": []
}
```

Rules, in order of how badly they bite when broken:

1. **Each of `temperature`, `pressure`, `volume`, `throughput` is either present as
   a range or listed in `not_stated`.** Never both, never neither. This is what
   makes "we did not find it" a claim in the data rather than a silence.
2. **Omit an unknown quantity's range entirely.** Never
   `{"min_si": null, "max_si": null}` — that is "any value qualifies", the opposite
   of unknown.
3. **Always SI.** `unit_si` and `quantity_kind` are mandatory on every range.
   Consumers compare these numbers in queries that cannot convert units.
4. **`source`** is `"primary"` (read from the process document) or `"external"`
   (filled from a cited source). An `"external"` range must carry `applicability`
   and `evidence` naming a `source_id` that exists and is `readable`.
5. Emit a spec for utility steps too; `service` on the step is what excludes them.

When any step has a non-empty `not_stated`, `unresolved` must carry at least one
`operating_envelope` entry. A report that says "unresolved: none" while no
envelope was found is worse than no report.

## Turtle

Bind to the scheme named in `run.vocabulary`; keep `step_id` and `stream_id` as
local names so the two representations stay joinable.

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix ex:   <http://example.org/run/methyl-acetate#> .
@prefix uo:   <http://example.org/unitop#> .
@prefix pd:   <http://example.org/process-decomposition#> .

ex:P-1 a pd:UnitProcess ;
    skos:prefLabel "Esterification of acetic acid with methanol"@en ;
    pd:requiresCapability uo:Esterification ;
    pd:service "process" ;
    pd:minTemperature [ qudt:numericValue 338.15 ; qudt:hasUnit "K" ] ;
    prov:wasDerivedFrom ex:S1 .
```

A step with `capability_match "unmapped"` carries **no** `pd:requiresCapability`
triple, and a quantity in `not_stated` emits no triple at all. An absent triple is
honest; an empty or invented one is not.
