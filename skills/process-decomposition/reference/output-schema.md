# Output schema

JSON is canonical; Turtle is a projection of it. Field names and enum values match
the `ProcessStep`, `MaterialStream` and `RequirementSpec` contracts used
downstream, so a consumer loads the output without renaming. Extra keys
(`kind_basis`, `capability_basis`, `evidence`, `source`, `applicability`,
`not_stated`, `from_port`) are ignored by those deserializers.

Examples below use methyl acetate esterification — shape illustrations, **not** a
decomposition to imitate. Never carry a step, substance or condition from here.

```json
{ "run": {...}, "sources": [...], "coverage": [...], "steps": [...],
  "streams": [...], "requirement_specs": [...], "hybrids": [...],
  "vocabulary_gaps": [...], "unresolved": [...] }
```

## sources[]

```json
{ "source_id": "S1", "uri": "https://…", "title": "…", "kind": "web",
  "retrieved_at": "2026-09-08T18:42:00Z", "chars": 18400, "readable": true }
```

`kind`: `web` | `pdf` | `file` | `figure` | `patent`. `chars` is how much text you
read. `readable: false` marks a fetch that failed — **it cannot back a claim**: no
evidence may cite it, no step may rest on it. Produced by `fetch_source.py fetch`.

## coverage[]

Every process action the source names, mapped to a step or excluded.

```json
[ { "action": "final centrifugation", "quote": "final centrifugation and drying",
    "step_id": "O-9" },
  { "action": "butadiene-based route", "quote": "alternative routes have been researched",
    "excluded_because": "a researched alternative, not part of the described route" } ]
```

Exactly one of `step_id` or `excluded_because`. Catches two things invisible to any
check on the steps alone: **a dropped operation** (an action with no entry) and
**compression** (several actions mapping to one step — split it, or set
`merged_because` on the step to say why the source treats them as indivisible).

## steps[]

```json
{ "step_id": "P-1", "order": 1, "diagram_ref": "3",
  "label": "Esterification of acetic acid with methanol",
  "kind": "UNIT_PROCESS",
  "kind_basis": "Acetic acid and methanol become methyl acetate and water; an ester bond forms.",
  "service": "process",
  "capability_uri": "http://example.org/unitop#Esterification",
  "capability_match": "exact",
  "capability_basis": "The source names the duty as esterification over an acid catalyst.",
  "equipment_as_stated": "reactive distillation column",
  "inputs": ["acetic acid", "methanol"], "outputs": ["methyl acetate", "water"],
  "conditions": { "temperature": "70 C", "pressure": null, "catalyst": "sulfuric acid" },
  "reaction": { "equation": "CH3COOH + CH3OH -> CH3COOCH3 + H2O", "balanced": true },
  "hybrid_group": "H1",
  "evidence": [{ "source_id": "S1", "quote": "…", "offset": 4120, "note": "" }],
  "confidence": "high", "open_questions": [], "notes": "" }
```

- `kind` — exactly `UNIT_OPERATION` or `UNIT_PROCESS`. A hybrid is two steps.
- `kind_basis` — one sentence on what changed or did not change chemically.
- `capability_basis` — one sentence on why *this* concept, naming the duty or
  equipment the source gives. Required unless `unmapped`; without it a wrong
  binding is invisible in review.
- `service` — `process` or `utility`.
- `capability_match` — `exact` | `broader` | `unmapped`. When `unmapped`,
  `capability_uri` is `""` and a `vocabulary_gaps` entry must exist.
- `conditions` — strings as written, or `null`. Machine-comparable form lives in
  `requirement_specs`.
- `evidence.offset` — position of the quote in the fetched text, from
  `fetch_source.py find`. `-1` only for a figure.

## streams[]

```json
{ "stream_id": "ST-2", "label": "column overhead",
  "substances": [{ "name": "methyl acetate", "identifier": "79-20-9", "scheme": "CAS" }],
  "role": "ProductStream", "from_step": "P-1", "to_step": "",
  "from_port": "overhead", "to_port": null, "spec": "",
  "origin": "boundary", "confidence": 1.0,
  "evidence": [{ "source_id": "S1", "quote": "…", "offset": 4460, "note": "" }] }
```

- `role` — `Feed` | `Intermediate` | `ProductStream` | `Recycle` |
  `ByproductStream` | `OffGas` | `Utility` | `Waste`
- `origin` — `stated` | `inferred` | `boundary`
- `from_step`/`to_step` — a `step_id`, or `""` at the plant boundary. An
  `Intermediate` or `Recycle` open at one end is a gap; report it in `unresolved`.
- `from_port`/`to_port` — optional free-text hints; annotations only.
- Recycles make the graph cyclic. Expected.

See `reference/flowsheet.md` for roles, origins and reading a diagram.

## requirement_specs[]

One per step, always.

```json
{ "step_id": "P-1", "kind": "UNIT_PROCESS",
  "capability_uri": "http://example.org/unitop#Esterification",
  "temperature": { "min_si": 338.15, "max_si": 348.15, "unit_si": "K",
                   "display_unit": "degC", "quantity_kind": "Temperature",
                   "source": "primary",
                   "evidence": { "source_id": "S1", "quote": "held at 65-75 C", "offset": 4180 } },
  "not_stated": ["pressure", "volume", "throughput"],
  "phase": "liquid",
  "substances": [{ "name": "acetic acid", "identifier": "64-19-7", "scheme": "CAS" }],
  "materials_required": [], "safety_classes": [] }
```

In order of how badly they bite:

1. **Each of `temperature`, `pressure`, `volume`, `throughput` is either a range or
   in `not_stated`.** Never both, never neither. This makes "we did not find it" a
   claim rather than a silence.
2. **Omit an unknown quantity's range entirely.** Never
   `{"min_si": null, "max_si": null}` — that is "any value qualifies".
3. **Always SI.** `unit_si` and `quantity_kind` mandatory. Use `to_si.py`.
4. `source` is `primary` (the process document) or `external` (a cited fill). An
   `external` range needs `applicability` and `evidence` naming a readable source.
5. Utility steps get specs too; `service` on the step is what excludes them.

When any step has a non-empty `not_stated`, `unresolved` must carry an
`operating_envelope` entry.

## Turtle

Bind to the scheme in `run.vocabulary`; keep `step_id` and `stream_id` as local
names so both representations stay joinable.

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

An `unmapped` step carries **no** `pd:requiresCapability` triple, and a quantity in
`not_stated` emits none. An absent triple is honest; an empty or invented one is not.
