# Reading a flowsheet

A diagram gives **topology and equipment identity**. It rarely gives numbers.
Keep the two readings apart.

A block flow diagram or PFD with a numbered legend normally carries: which block
feeds which and in what direction, equipment identity via the legend, stream
labels and therefore substances, recycle loops, and utility markers (CW, ST).

It normally does **not** carry temperature, pressure, flow, composition or phase.
A value not drawn on the diagram was not read from it — see
`reference/operating-envelope.md` for the only route to a missing value. The
exception is an annotated PFD with a stream table; those are stated values.

## Order of work

1. **Bind the legend first**, before tracing a single line. It gives equipment
   identity, which is what `capability_uri` derives from.
2. **Trace the lines**, one stream per edge. Follow arrowheads; where one is not
   legible, say so rather than assuming left-to-right.
3. **Close the loops.** Recycles are edges like any other. The graph is directed
   and may contain cycles — a return line upstream is normal, not an error.
4. **Assign roles**, then classify each block via `reference/classification.md`.
5. **Report what you could not trace.** A line lost behind a label is a gap;
   naming it is a finding, guessing its endpoint is a defect.

## Stream roles

| Value | For |
|---|---|
| `Feed` | enters from outside the plant boundary |
| `Intermediate` | between two steps inside the boundary |
| `ProductStream` | the target product leaving |
| `Recycle` | returns to an upstream step |
| `ByproductStream` | a saleable or worked-up co-product leaving |
| `OffGas` | gaseous release |
| `Utility` | cooling water, steam, refrigerant |
| `Waste` | wastewater, purge, disposal |

All but `Intermediate` and `Recycle` are expected to be open at one end — that is
the plant boundary, `origin: "boundary"`, not missing data. An `Intermediate` or
`Recycle` with one endpoint **is** a gap: a missing step, or a line not followed.

## Edge origin

- `stated` — the diagram or text draws this connection explicitly
- `inferred` — reconstructed by matching a substance across adjacent steps
- `boundary` — one end is the plant boundary and correctly open

Line-tracing a raster figure is error-prone. An edge you are confident you
followed is `stated`; one reconstructed because the substance had to come from
somewhere is `inferred`, confidence below 1.0. A reviewer must be able to see
which connections came from the drawing and which from a heuristic.

## Ports

Two streams leaving one block are usually told apart by substances and roles — a
decanter's organic and aqueous outlets carry different species. Where that is not
enough (same species, different phase; a splitter with identical outlets), add
`from_port` / `to_port` as free-text hints from the drawing ("light phase",
"overhead", "bottoms", "vent").

These are **annotations, not contract fields**. A consumer may use or ignore them.
Never let a port hint carry information belonging in `substances` or `role`.

## Utilities and offsites

Utility equipment — cooling towers, boilers, refrigeration packages — is modelled
as steps like any other so the plant model is complete, and marked
`service: "utility"`; process steps are `service: "process"`.

The marker matters: utility steps generate requirement specifications like any
other, and a consumer sourcing process modules will filter on it. Getting it wrong
puts a cooling tower into a module search.

Utility *streams* (CW, ST) carry `role: "Utility"` and connect the utility step to
the process step it serves. Where a marker has no source equipment drawn, the
stream is open at one end with `origin: "boundary"`.

## Granularity

One drawn block is not always one step. A legend entry reading "crystallization
and centrifugation steps" is two unit operations sharing a box. Decompose to unit
operations; whether a module covers both is decided downstream, not pre-empted here.

Record the diagram's own number for each step in `diagram_ref` so a reviewer can
point at the figure and check.
