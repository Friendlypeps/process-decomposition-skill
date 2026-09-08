# Reading a flowsheet

A process diagram gives you **topology and equipment identity**. It rarely gives
you numbers. Keep those two readings apart, because a decomposition that quietly
mixes them cannot be checked.

## What a diagram can and cannot tell you

A block flow diagram or PFD with a numbered legend normally carries:

- which block feeds which, and in what direction
- equipment identity, via the legend
- stream labels, and therefore the substances
- recycle loops
- utility markers (CW, ST, and similar)

It normally does **not** carry temperature, pressure, flow rate, composition, or
phase. If a value is not drawn on the diagram, it was not read from the diagram.
Do not supply it from what you know about the chemistry — see
`reference/operating-envelope.md` for the only route by which a missing value may
be filled.

An annotated PFD with a stream table is the exception: when the figure carries a
table of stream conditions, those are stated values and should be read as such.

## Order of work

1. **Bind the legend first.** Map every number on the diagram to its legend
   entry before tracing a single line. The legend gives equipment identity, which
   is what `capability_uri` is derived from.
2. **Trace the lines.** Record each edge as a stream. Follow arrowheads for
   direction; where an arrowhead is not legible, say so rather than assuming
   left-to-right.
3. **Close the loops.** Recycles are edges like any other. The graph is directed
   and may contain cycles — a return line to an upstream block is normal, not an
   error to be straightened out.
4. **Assign roles** (below), then classify each block as a unit operation or unit
   process using `reference/classification.md`.
5. **Report what you could not trace.** A line you lost behind a label is a gap.
   Naming it is a finding; guessing its endpoint is a defect.

## Stream roles

Use exactly these values:

| Value | Use for |
|---|---|
| `Feed` | enters from outside the plant boundary |
| `Intermediate` | between two steps inside the boundary |
| `ProductStream` | the target product leaving |
| `Recycle` | returns to an upstream step |
| `ByproductStream` | a saleable or worked-up co-product leaving |
| `OffGas` | gaseous release |
| `Utility` | cooling water, steam, refrigerant, and the like |
| `Waste` | wastewater, purge, disposal |

`Feed`, `ProductStream`, `OffGas`, `Waste`, `Utility` and `ByproductStream` are
expected to be open at one end — that is the plant boundary, not missing data.
An `Intermediate` or `Recycle` with only one endpoint **is** a gap: either a step
is missing or the line was not followed. Set `origin: "boundary"` for the first
case; report the second.

## Edge origin

- `stated` — the diagram or text draws this connection explicitly.
- `inferred` — reconstructed by matching a substance across adjacent steps.
- `boundary` — one end is the plant boundary and correctly open.

Line-tracing from a raster figure is error-prone. An edge you are confident you
followed is `stated`; an edge you reconstructed because the substance had to come
from somewhere is `inferred`, with a confidence below 1.0. A reviewer has to be
able to see which connections came from the drawing and which from a heuristic.

## Ports

Two streams leaving the same block are often told apart by their substances and
roles alone — a decanter's organic and aqueous outlets carry different species.
Where that is not enough (same species, different phase; a splitter with
identical outlets), add `from_port` / `to_port` as free-text hints taken from the
drawing ("light phase", "overhead", "bottoms", "vent").

These are **annotations, not contract fields**. A consumer may use them to
reconstruct connections unambiguously or ignore them entirely. Never rely on a
port hint to carry information that belongs in `substances` or `role`.

## Utilities and offsites

Utility equipment — cooling towers, boilers, refrigeration packages — is modelled
as steps like any other, so the plant model is complete. Mark every such step
`service: "utility"`; process steps are `service: "process"`.

The marker matters downstream: utility steps generate requirement specifications
like process steps do, and a consumer sourcing process modules will want to
exclude them. Getting the marker wrong puts a cooling tower into a module search.

The utility *streams* (CW, ST) carry `role: "Utility"` and connect the utility
step to the process step it serves. Where the diagram shows a utility marker but
no source equipment, the stream is open at one end with `origin: "boundary"`.

## Granularity

One drawn block is not always one step. A legend entry reading "crystallization
and centrifugation steps" is two unit operations that happen to share a box.
Decompose to unit operations; a module covering both is something the downstream
matching decides, not something the extraction should pre-empt.

Record the diagram's own number for each step in `diagram_ref` so a reviewer can
point at the figure and check.
