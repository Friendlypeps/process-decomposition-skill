# Binding a step to a vocabulary

Classification says *what kind* of step it is. Binding says *which* operation, in
a controlled vocabulary a consumer can query.

## Query, do not read

```bash
python scripts/concepts.py search dissolution   # matches, URIs, broader chains
python scripts/concepts.py list                 # every concept, one line each
```

Reading the scheme to pick a URI costs thousands of tokens and is how a URI gets
invented. Ask it instead. **No match is an answer**: the step is unmapped.

## Which vocabulary

`vocab/unit-operations.default.ttl` ships so the skill works standalone. If the
caller has their own scheme, bind to that: pass `--vocab`, and record it in
`run.vocabulary`. Do not translate their concepts into the default scheme's names
and do not merge the two — a process vocabulary must have one owner, and a second
scheme beside the first is how a knowledge graph starts disagreeing with itself.

## How to bind

1. Find the most specific concept whose definition covers the step.
2. If only a parent fits, bind to the parent with `capability_match: "broader"`.
   Binding "rectification" to `Distillation` is honest; binding it to `Separation`
   when `Distillation` exists is lazy.
3. If nothing fits: `capability_uri: ""`, `capability_match: "unmapped"`, and a
   `vocabulary_gaps` entry naming the nearest concept and why it fails.

**Never mint a URI the scheme does not contain.** An invented
`uo:MeltCrystallisationWithSweating` is indistinguishable from a real concept once
it is in a triple store, and will not resolve. The gap list is the deliverable for
missing concepts — it is how a scheme gets extended deliberately.

## Matching walks upward

Consumers match with `skos:broader*`: a requirement for "distillation" is
satisfied by a resource offering "rectification". Two consequences:

- Bind as deep as the evidence supports. Depth is information; a consumer can
  generalise upward but cannot specialise downward.
- Never bind a unit process to a separation concept or the reverse to force a
  match. A wrong branch is worse than an unmapped step, because upward traversal
  silently makes it look satisfiable.

## Reaction steps

For a `UNIT_PROCESS` the concept names the *reaction type* — not the vessel.
Equipment goes in `equipment_as_stated`.

**Bind to what happens to the molecules, not the section of plant it happens in.**
A sequence inside an "oxidation section" is not all oxidation. Observed failures,
all correctly labelled and then wrongly bound:

| Step | Wrongly bound to | Belongs to |
|---|---|---|
| Trapping a hydroperoxide as a borate ester | `Oxidation` | `Esterification` |
| Decomposing a hydroperoxide over a catalyst | `Oxidation` | `Reaction` (broader) |
| Hydrolysing an ester to alcohol and acid | `Oxidation` | `Hydrolysis` |

The test: read your own `kind_basis` back. If it says an ester formed, the concept
cannot be oxidation. `capability_basis` names the feature that makes the concept
fit — "an ester bond forms" — not the step's position in the process.

This matters downstream: a reactor is selected on operating envelope and material
compatibility rather than a named capability, so a unit process bound to a vessel
type matches against the wrong criteria.
