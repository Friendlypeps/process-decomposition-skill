# Classifying a step

The test is always the same: **does the chemical identity of the substances
change?** Everything below is that test applied to cases where the wording of a
source pulls the other way.

## The test, stated precisely

Compare the set of chemical species entering the step with the set leaving it.

- A species present at the outlet that was not at the inlet (and is not merely
  concentrated, condensed, dissolved, or crushed) means bonds changed →
  **UNIT_PROCESS**.
- Same species, different phase / concentration / size / location / temperature →
  **UNIT_OPERATION**.

Dissolution, adsorption without reaction, and hydration that forms a solvate but
no new compound stay unit operations. Salt formation, decomposition, and any
change in molecular formula do not.

## Words that mislead

| Wording in the source | Classify as | Why |
|---|---|---|
| "Dehydration" of a wet solid | UNIT_OPERATION | water removed, molecules intact — this is drying |
| "Dehydration" of an alcohol to an alkene | UNIT_PROCESS | C–O bond broken, new compound |
| "Calcination" | UNIT_PROCESS | thermal decomposition (CaCO₃ → CaO + CO₂), not merely heating |
| "Roasting" | UNIT_PROCESS | sulfide → oxide; a chemical conversion despite the thermal framing |
| "Crystallisation" | UNIT_OPERATION | phase change; the compound is unchanged |
| "Neutralisation" | UNIT_PROCESS | acid + base → salt + water, even when framed as effluent treatment |
| "Digestion" / "leaching" | see note below | depends on whether the solid dissolves or reacts |
| "Reforming", "cracking" | UNIT_PROCESS | skeletal rearrangement |
| "Quench" | UNIT_OPERATION unless it reacts | usually rapid cooling; becomes a unit process if a reagent is consumed |
| "Scrubbing" | see absorption below | physical or chemical depending on the solvent |
| "Reactor" / "column" / "vessel" | neither | equipment, not a step — record in `equipment_as_stated` |

**Digestion / leaching.** Bayer-process digestion dissolves alumina *by reacting*
it with caustic soda to form sodium aluminate → UNIT_PROCESS. Leaching that only
dissolves an already-present soluble species → UNIT_OPERATION (solid–liquid
extraction). Decide from the chemistry stated, and if the source does not say,
flag it.

## Genuine hybrids

Process intensification deliberately puts reaction and separation in one device.
These are not classification failures — they are real, and collapsing them loses
the thing that makes the process interesting.

- **Reactive distillation** (e.g. methyl acetate) — esterification plus
  fractionation in one column.
- **Reactive absorption / chemisorption** — CO₂ into amine, SO₂ into limestone
  slurry: mass transfer plus an acid–base reaction.
- **Reactive extraction** — extraction where a complexing agent forms a new species.
- **Catalytic membrane reactors**, **chromatographic reactors**.

Handle a hybrid by emitting **two steps** — the unit process and the unit
operation — sharing a `hybrid_group` id, and add an entry to `hybrids` naming the
device. Emit one step only if the source treats it as indivisible, and then set
`kind` to the dominant function and record the other in `notes`.

## Cases decided by convention, not by chemistry

State the convention in `notes` so a reviewer can disagree with it.

- **Ion exchange** — chemically a stoichiometric exchange; conventionally a
  **UNIT_OPERATION**, because it is designed, sized, and selected as a separation.
- **Adsorption / desorption** — UNIT_OPERATION when physisorption. Chemisorption
  with a regeneration reaction is a hybrid.
- **Absorption** — UNIT_OPERATION when the gas dissolves unchanged; hybrid when
  the solvent reacts.
- **Electrodialysis** — UNIT_OPERATION (ion transport under a field, no conversion),
  unlike **electrolysis**, which is a UNIT_PROCESS.
- **Fermentation** — UNIT_PROCESS. Downstream cell separation is a separate
  unit operation; do not merge them.

## Granularity

Decompose to the level at which a step has **one purpose, one set of operating
conditions, and identifiable inlet and outlet streams**.

A described "reactor section" usually hides three steps: feed preheat
(UNIT_OPERATION), reaction (UNIT_PROCESS), and product quench or cooling
(UNIT_OPERATION). Split it, and record the split in `granularity_note`.

Do not split below what the source supports. Inventing a pump the text never
mentions adds a step nobody can trace to a quote — which is exactly the failure
this skill exists to prevent.

## Confidence

- **high** — the source names the step and its chemistry explicitly.
- **medium** — the step is clearly implied (a distillate is mentioned, so a
  distillation happened) but not named.
- **low** — inferred from process logic, or the source is ambiguous between two
  classifications. Always pair with an `open_questions` entry.
