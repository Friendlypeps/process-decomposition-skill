# Output schema

JSON is canonical. Turtle is a projection of it — emit Turtle only when asked, and
never emit Turtle that says something the JSON does not.

Field names deliberately match the `ProcessStep` / `Evidence` contracts used
downstream (`step_id`, `kind`, `capability_uri`, `evidence.source_id/quote/offset/note`)
so a consumer can map without renaming.

## JSON

```json
{
  "run": {
    "target_product": "adipic acid",
    "granularity_note": "Reactor section split into preheat / reaction / quench.",
    "vocabulary": "vocab/unit-operations.default.ttl"
  },
  "sources": [
    { "source_id": "S1", "uri": "https://…", "title": "…", "retrieved_at": "2026-09-08T10:00:00Z" }
  ],
  "steps": [
    {
      "step_id": "P-1",
      "order": 1,
      "label": "Oxidation of KA oil with nitric acid",
      "kind": "UNIT_PROCESS",
      "kind_basis": "Cyclohexanol/cyclohexanone converted to adipic acid; new compound formed.",
      "capability_uri": "http://example.org/unitop#Oxidation",
      "capability_match": "exact",
      "equipment_as_stated": "stirred tank reactor cascade",
      "inputs": ["KA oil", "60% nitric acid", "Cu/V catalyst"],
      "outputs": ["crude adipic acid solution", "NOx off-gas"],
      "conditions": { "temperature": "60–80 °C", "pressure": null, "catalyst": "Cu(II)/NH4VO3" },
      "reaction": { "equation": "C6H12O + HNO3 → C6H10O4 + N2O + H2O", "balanced": false },
      "hybrid_group": null,
      "evidence": [
        { "source_id": "S1", "quote": "oxidised with 60% nitric acid at 60–80 °C", "offset": 4213, "note": "" }
      ],
      "confidence": "high",
      "open_questions": [],
      "notes": ""
    }
  ],
  "hybrids": [
    { "hybrid_group": "H1", "device": "reactive distillation column", "step_ids": ["P-3", "O-4"] }
  ],
  "vocabulary_gaps": [
    { "step_id": "O-7", "described_as": "melt crystallisation with sweating", "nearest_concept": "…#Crystallisation", "why_not": "sweating stage is not represented in the scheme" }
  ]
}
```

### Rules

- `kind` is exactly `"UNIT_OPERATION"` or `"UNIT_PROCESS"`. No other value, no
  lowercase, no third value — a hybrid is two steps, not a new kind.
- `kind_basis` is one sentence naming *what changed or did not change chemically*.
  It is not a restatement of the label. This field is what makes a wrong
  classification visible in review.
- `capability_match` is `"exact"`, `"broader"` (bound to a parent concept because
  no leaf fits), or `"unmapped"`. When `"unmapped"`, `capability_uri` **must** be
  `""` and a `vocabulary_gaps` entry must exist.
- `conditions` values are strings as written in the source, or `null`. Never
  substitute a typical value for an unstated one.
- Unstated order is `null`, not a guess.
- Every step needs ≥1 `evidence` entry. `offset` is `-1` when unknown.
- `step_id` prefix convention: `P-` for unit processes, `O-` for unit operations.
  It is a readability aid; `kind` remains authoritative.

## Turtle

Bind to the scheme named in `run.vocabulary`. Keep the JSON `step_id` as the
local name so the two representations stay joinable.

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix ex:   <http://example.org/run/adipic#> .
@prefix uo:   <http://example.org/unitop#> .
@prefix pd:   <http://example.org/process-decomposition#> .

ex:P-1 a pd:UnitProcess ;
    skos:prefLabel "Oxidation of KA oil with nitric acid"@en ;
    pd:requiresCapability uo:Oxidation ;
    pd:capabilityMatch "exact" ;
    pd:order 1 ;
    pd:hasInput  "KA oil", "60% nitric acid" ;
    pd:hasOutput "crude adipic acid solution", "NOx off-gas" ;
    pd:confidence "high" ;
    prov:wasDerivedFrom ex:S1 ;
    pd:evidence [ pd:quote "oxidised with 60% nitric acid at 60–80 °C" ; pd:offset 4213 ] .
```

`pd:UnitProcess` / `pd:UnitOperation` are the two step classes. A step with
`capability_match "unmapped"` carries **no** `pd:requiresCapability` triple at
all — an absent triple is honest, an empty or invented one is not.

When the consumer's own scheme and predicates are known (see
`reference/vocabulary.md`), use those instead of the `pd:` placeholders and say
in `run` which mapping was applied.
