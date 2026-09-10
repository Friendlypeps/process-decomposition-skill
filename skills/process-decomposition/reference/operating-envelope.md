# Operating envelopes

The envelope decides whether a candidate module is usable, and it is the half of
the matching key most easily fabricated. These rules are stricter than the rest.

## Unknown is not unconstrained

A quantity not stated is **omitted, and named in `not_stated`**.

Never `{"min_si": null, "max_si": null}`. Open on both sides means *any value is
acceptable*, which matches every candidate. An unknown must narrow the search to
"insufficient data", never widen it to "everything qualifies" — the two look
identical and mean opposites.

Open on *one* side is different and legitimate: "at least 150 °C" is
`{"min_si": 423.15, "max_si": null}`. Use it when the source states a one-sided bound.

## Always SI

Convert with `scripts/to_si.py "<value as written>"`:

```json
"temperature": { "min_si": 423.15, "max_si": 433.15, "unit_si": "K",
                 "display_unit": "degC", "quantity_kind": "Temperature" }
```

`display_unit` is the unit the source used, so an answer renders the way an
engineer expects to read it. Consumers compare these numbers in queries that
cannot convert units — a value left in bar beside one in pascal is a silent wrong
answer, not a visible error. Quantities: `temperature`, `pressure`, `volume`,
`throughput`.

If `to_si.py` exits non-zero the source stated a word, not a bound
("superatmospheric", "low-temperature"). That quantity goes to `not_stated`, and
the wording belongs in the step's `notes`.

## Filling a gap: cited sources only

Run `fetch_source.py quantities` first — a value may already be stated and
unnoticed. Where the process document truly states nothing, you may fill the gap
**only** from a citable external source, never from recall:

1. Search, then fetch the page with `fetch_source.py fetch`.
2. Add it to `sources` with its own `source_id`.
3. Set `"source": "external"` on the range, with `evidence` quoting the span.
4. Set `applicability`:
   - `stated_for_this_process` — the source describes *this* process, scale and route
   - `assumed_from_analogous_process` — it describes the chemistry or a comparable
     plant, and applying it here is an assumption

A handbook value proves the number exists in the literature. It does not prove
the plant in the figure runs there. Most cited fills are
`assumed_from_analogous_process`; labelling them honestly is what lets a reviewer
decide which matches to trust.

Ranges from the process document are `"source": "primary"` and need no
`applicability`. If no citable source exists, omit the quantity — an unfilled gap
is a result.

## Envelope is not stream conditions

A stream has conditions at a point; a step has an envelope it must cover. A
reactor fed at 80 °C and discharging at 160 °C needs a module rated across that
span, not for either endpoint. Say in `notes` how you derived it.

## The rest of the matching key

- `phase` — the phase the module must handle, where stated
- `substances` — resolved species as `{name, identifier, scheme}`. "AGS mixture"
  is a label, not a species. Leave `identifier` empty rather than inventing one.
- `materials_required` — materials of construction the chemistry demands
- `safety_classes` — hazard classes relevant to module selection

The last two are almost never drawn on a diagram. That nitric acid at temperature
implies a corrosion-resistant alloy is domain inference, and falls under the
cited-source rule like any other fill: cite it, or leave it out. An invented
material spec silently excludes every module that would have worked.
