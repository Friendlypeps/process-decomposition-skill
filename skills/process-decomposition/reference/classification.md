# Classifying a step

The test is always: **does the chemical identity of the substances change?**
Everything below is that test applied where the wording pulls the other way.

## The test, precisely

Compare the species entering the step with those leaving.

- A species at the outlet that was not at the inlet — and is not merely
  concentrated, condensed, dissolved or crushed — means bonds changed →
  **UNIT_PROCESS**.
- Same species, different phase / concentration / size / location / temperature →
  **UNIT_OPERATION**.

Dissolution, adsorption without reaction, and hydration forming a solvate but no
new compound stay unit operations. Salt formation, decomposition, and any change
in molecular formula do not.

## Words that mislead

| Wording | Classify as | Why |
|---|---|---|
| "dehydration" of a wet solid | UNIT_OPERATION | water removed, molecules intact — this is drying |
| "dehydration" of an alcohol to an alkene | UNIT_PROCESS | C–O bond broken, new compound |
| "calcination" | UNIT_PROCESS | thermal decomposition (CaCO₃ → CaO + CO₂), not merely heating |
| "roasting" | UNIT_PROCESS | sulfide → oxide, despite the thermal framing |
| "crystallisation" | UNIT_OPERATION | phase change; the compound is unchanged |
| "neutralisation" | UNIT_PROCESS | acid + base → salt + water, even framed as effluent treatment |
| "digestion" / "leaching" | see below | depends on whether the solid dissolves or reacts |
| "reforming", "cracking" | UNIT_PROCESS | skeletal rearrangement |
| "quench" | UNIT_OPERATION unless it reacts | usually rapid cooling; a unit process if a reagent is consumed |
| "scrubbing" | see absorption below | physical or chemical, depending on the solvent |
| "reactor" / "column" / "vessel" | neither | equipment — record in `equipment_as_stated` |

**Digestion / leaching.** Bayer-process digestion dissolves alumina *by reacting*
it with caustic soda to form sodium aluminate → UNIT_PROCESS. Leaching that only
dissolves an already-soluble species → UNIT_OPERATION. Decide from the chemistry
stated; if the source does not say, flag it.

## Genuine hybrids

Process intensification puts reaction and separation in one device. These are
real, and collapsing them loses what makes the process interesting.

Reactive distillation (methyl acetate); reactive absorption / chemisorption (CO₂
into amine, SO₂ into limestone slurry); reactive extraction with a complexing
agent; catalytic membrane reactors; chromatographic reactors.

Emit **two steps** — the unit process and the unit operation — sharing a
`hybrid_group` id, plus an entry in `hybrids` naming the device. Emit one only if
the source treats it as indivisible; then set `kind` to the dominant function and
record the other in `notes`.

## Decided by convention, not chemistry

State the convention in `notes` so a reviewer can disagree.

- **Ion exchange** — chemically a stoichiometric exchange; conventionally a
  **UNIT_OPERATION**, because it is designed, sized and selected as a separation.
- **Adsorption / desorption** — UNIT_OPERATION when physisorption. Chemisorption
  with a regeneration reaction is a hybrid.
- **Absorption** — UNIT_OPERATION when the gas dissolves unchanged; hybrid when
  the solvent reacts.
- **Electrodialysis** — UNIT_OPERATION (ion transport, no conversion), unlike
  **electrolysis**, a UNIT_PROCESS.
- **Fermentation** — UNIT_PROCESS. Downstream cell separation is a separate unit
  operation; do not merge them.

## Granularity

Decompose to where a step has **one purpose, one set of operating conditions, and
identifiable inlet and outlet streams**.

A described "reactor section" usually hides three: feed preheat (UNIT_OPERATION),
reaction (UNIT_PROCESS), and quench or cooling (UNIT_OPERATION). Split it, and
record the split in `granularity_note`.

Do not split below what the source supports. Inventing a pump the text never
mentions adds a step nobody can trace to a quote.

## Confidence

- **high** — the source names the step and its chemistry explicitly
- **medium** — clearly implied but not named (a distillate is mentioned, so a
  distillation happened)
- **low** — inferred from process logic, or ambiguous between two
  classifications. Always pair with an `open_questions` entry.
