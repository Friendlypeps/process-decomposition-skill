# Output schema

JSON is canonical. Turtle is a projection of it — emit Turtle only when asked, and
never emit Turtle that says something the JSON does not.

Field names and enum values deliberately match the `ProcessStep`, `MaterialStream`
and `RequirementSpec` contracts used downstream, so a consumer can load the output
without renaming or re-mapping. Extra keys this skill adds (`kind_basis`,
`evidence`, `source`, `applicability`, `from_port`) are ignored by those
deserializers, so carrying them costs nothing.

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

`streams` and `requirement_specs` are omitted when the source is prose with no
topology and no conditions. `unresolved` lists what could not be read — a traced
line that was lost, a block whose legend entry is illegible, a quantity with no
citable source.

## steps[]

```json
{
  "step_id": "P-2",
  "order": 2,
  "diagram_ref": "6",
  "label": "Catalytic oxidation of CHHP to KA oil",
  "kind": "UNIT_PROCESS",
  "kind_basis": "Cyclohexyl hydroperoxide is decomposed to cyclohexanol/cyclohexanone; new compounds are formed.",
  "service": "process",
  "capability_uri": "http://example.org/unitop#Oxidation",
  "capability_match": "exact",
  "equipment_as_stated": "converters",
  "inputs": ["CHHP stream"],
  "outputs": ["KA oil"],
  "conditions": { "temperature": "160 C", "pressure": null, "catalyst": "cobalt salt" },
  "reaction": { "equation": "C6H11OOH -> C6H11OH + C6H10O", "balanced": false },
  "hybrid_group": null,
  "evidence": [{ "source_id": "S1", "quote": "...", "offset": 1180, "note": "" }],
  "confidence": "high",
  "open_questions": [],
  "notes": ""
}
```

- `kind` — exactly `"UNIT_OPERATION"` or `"UNIT_PROCESS"`. A hybrid is two steps.
- `kind_basis` — one sentence naming what changed or did not change chemically.
- `service` — `"process"` or `"utility"`. Cooling towers, boilers and refrigeration
  packages are `"utility"`; everything on the process path is `"process"`. A
  consumer sourcing process modules filters on this.
- `diagram_ref` — the number the figure gives this block, when reading a diagram.
- `capability_match` — `"exact"`, `"broader"`, or `"unmapped"`. When `"unmapped"`,
  `capability_uri` must be `""` and a `vocabulary_gaps` entry must exist.
- `conditions` — strings as written in the source, or `null`. This is the free-text
  reading; the machine-comparable form lives in `requirement_specs`.

## streams[]

One edge of the flowsheet. See `reference/flowsheet.md` for roles and origins.

```json
{
  "stream_id": "ST-7",
  "label": "boric acid recycle",
  "substances": [{ "name": "boric acid", "identifier": "10043-35-3", "scheme": "CAS" }],
  "role": "Recycle",
  "from_step": "O-3",
  "to_step": "P-1",
  "from_port": "recovered acid",
  "to_port": null,
  "spec": "",
  "origin": "stated",
  "confidence": 1.0,
  "evidence": [{ "source_id": "S1", "quote": "Figure 2, line from block 3 to block 1", "offset": -1, "note": "traced from the figure" }]
}
```

- `role` — one of `Feed`, `Intermediate`, `ProductStream`, `Recycle`,
  `ByproductStream`, `OffGas`, `Utility`, `Waste`.
- `origin` — `stated`, `inferred`, or `boundary`.
- `from_step` / `to_step` — a `step_id`, or `""` at the plant boundary. An
  `Intermediate` or `Recycle` open at one end is a gap, not a boundary; report it
  in `unresolved`.
- `from_port` / `to_port` — optional free-text hints, `null` when not needed.
  Annotations only; a consumer may ignore them entirely.
- Recycles make the graph cyclic. That is expected.

## requirement_specs[]

The machine-comparable matching key, one per step. Loads directly into a
`RequirementSpec`.

```json
{
  "step_id": "P-2",
  "kind": "UNIT_PROCESS",
  "capability_uri": "http://example.org/unitop#Oxidation",
  "temperature": {
    "min_si": 428.15, "max_si": 438.15, "unit_si": "K",
    "display_unit": "degC", "quantity_kind": "Temperature",
    "source": "external",
    "applicability": "assumed_from_analogous_process",
    "evidence": { "source_id": "S2", "quote": "the decomposition is run at 155-165 C", "offset": 940 }
  },
  "phase": "liquid",
  "substances": [{ "name": "cyclohexane", "identifier": "110-82-7", "scheme": "CAS" }],
  "materials_required": [],
  "safety_classes": []
}
```

Rules, in order of how badly they bite when broken:

1. **Omit an unknown quantity entirely.** Never `{"min_si": null, "max_si": null}` —
   that is "any value qualifies", which is the opposite of "unknown".
2. **Always SI.** `unit_si` and `quantity_kind` are mandatory on every range.
   Consumers compare these numbers in queries that cannot convert units.
3. **`source`** is `"primary"` (read from the process document) or `"external"`
   (filled from a cited source). An `"external"` range must carry `applicability`
   and `evidence` pointing at a `source_id` that exists in `sources`.
4. `pressure`, `volume`, `throughput` follow the same shape as `temperature`.
5. Emit a spec for utility steps too — the `service` marker on the step is what
   lets a consumer exclude them.

## Turtle

Bind to the scheme named in `run.vocabulary`; keep `step_id` and `stream_id` as
local names so the two representations stay joinable.

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix ex:   <http://example.org/run/adipic#> .
@prefix uo:   <http://example.org/unitop#> .
@prefix pd:   <http://example.org/process-decomposition#> .

ex:P-2 a pd:UnitProcess ;
    skos:prefLabel "Catalytic oxidation of CHHP to KA oil"@en ;
    pd:requiresCapability uo:Oxidation ;
    pd:service "process" ;
    pd:minTemperature [ qudt:numericValue 428.15 ; qudt:hasUnit "K" ] ;
    pd:maxTemperature [ qudt:numericValue 438.15 ; qudt:hasUnit "K" ] ;
    prov:wasDerivedFrom ex:S1 .

ex:ST-7 a pd:MaterialStream ;
    pd:role "Recycle" ;
    pd:fromStep ex:O-3 ; pd:toStep ex:P-1 ;
    pd:origin "stated" .
```

A step with `capability_match "unmapped"` carries **no** `pd:requiresCapability`
triple. An absent triple is honest; an empty or invented one is not. Likewise a
quantity omitted from the JSON emits no triple — never a bare node with no value.
