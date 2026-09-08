# Operating envelopes

The envelope is what a module must provide or withstand. It is the half of the
matching key that decides whether a candidate is actually usable, and it is the
half most easily fabricated — so the rules here are stricter than anywhere else
in this skill.

## Unknown is not unconstrained

If a quantity is not stated, **omit the key entirely**.

Do not emit `{"min_si": null, "max_si": null}`. A range open on both sides means
*any temperature is acceptable*, which matches every candidate module. An unknown
temperature must reduce the search to "insufficient data", never widen it to
"everything qualifies". These two produce identical-looking results and opposite
meanings.

Open on *one* side is legitimate and different: "at least 150 °C" is
`{"min_si": 423.15, "max_si": null}`. Use it when the source genuinely states a
one-sided bound.

## Always SI-normalise

Every range carries five fields:

```json
"temperature": {
  "min_si": 423.15,
  "max_si": 433.15,
  "unit_si": "K",
  "display_unit": "degC",
  "quantity_kind": "Temperature"
}
```

- `min_si` / `max_si` — numbers in SI, or `null` for an open side
- `unit_si` — `"K"`, `"Pa"`, `"m3"`, `"kg/s"`
- `display_unit` — the unit the source used, so an answer can be rendered the way
  an engineer expects to read it
- `quantity_kind` — `Temperature`, `Pressure`, `Volume`, `Throughput`

Normalising at extraction time is not a nicety. Consumers compare these numbers
in queries that cannot convert units, so a value left in bar next to one in
pascal is a silent wrong answer rather than a visible error. Convert once, here.

Which quantities to emit: `temperature`, `pressure`, `volume`, `throughput`.

## Filling a gap: cited sources only

When the process document states no value, you may fill the gap **only** by
finding a citable external source for that specific quantity. Never from
recollection.

The procedure:

1. Search for the value. Fetch the page or document.
2. Add it to `sources` with its own `source_id` and URI, exactly like the primary
   document.
3. Set `"source": "external"` on the range and attach `evidence` quoting the span.
4. Set `applicability` — and this is the field that matters most:
   - `"stated_for_this_process"` — the external source describes *this* process,
     at this scale, for this route
   - `"assumed_from_analogous_process"` — the source describes the chemistry or a
     comparable plant, and applying it here is an assumption

A handbook value for cyclohexane oxidation proves the number exists in the
literature. It does not prove the plant in the figure runs there. Most cited
fills are `assumed_from_analogous_process`, and labelling them honestly is what
lets a reviewer decide which matches to trust.

Ranges read from the process document itself are `"source": "primary"` and need
no `applicability`.

If you cannot find a citable source, omit the quantity. An unfilled gap is a
result.

## Envelope is not the same as stream conditions

A stream has conditions at a point. A step has an envelope it must cover.

Where a step's inlet and outlet differ, the envelope spans both: a reactor fed at
80 °C and discharging at 160 °C needs a module rated across that span, not for
either endpoint. Derive the envelope from the conditions around the step and say
in `notes` how you derived it.

## The rest of the matching key

Alongside the ranges, a requirement specification carries:

- `phase` — the phase the module must handle, where stated
- `substances` — resolved species, as `{name, identifier, scheme}`. "AGS mixture"
  is a label, not a species; resolve to formulas or registry identifiers where the
  source allows, and leave `identifier` empty rather than inventing one.
- `materials_required` — materials of construction the chemistry demands
- `safety_classes` — hazard classes relevant to module selection

`materials_required` and `safety_classes` are almost never drawn on a diagram.
That nitric acid at temperature implies a corrosion-resistant alloy is domain
inference, and it falls under the cited-source rule above like any other filled
gap: cite it, or leave it out. An invented material specification will silently
exclude every module that would in fact have worked.
