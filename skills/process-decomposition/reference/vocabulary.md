# Binding a step to a vocabulary

Classification says *what kind* of step it is. Binding says *which* operation it
is, in a controlled vocabulary a downstream consumer can query.

## Which vocabulary

The skill ships `vocab/unit-operations.default.ttl` — a small SKOS scheme with
the standard top-level split (separation, reaction, heat transfer, mixing,
conveying, size change) and common leaves. It exists so the skill works standalone.

**It is a default, not a recommendation.** If the caller has their own scheme,
bind to that instead: read it, use its concept URIs, and record the file or
endpoint in `run.vocabulary`. Do not translate their concepts into the default
scheme's names, and do not merge the two — a process vocabulary must have one
owner, and a second scheme sitting beside the first is how a knowledge graph
starts disagreeing with itself.

## How to bind

1. Find the most specific concept whose definition covers the step.
2. If only a parent fits, bind to the parent and set `capability_match: "broader"`.
   Binding "rectification" to `Distillation` is honest; binding it to `Separation`
   when `Distillation` exists is lazy.
3. If nothing fits, set `capability_uri: ""`, `capability_match: "unmapped"`, and
   write a `vocabulary_gaps` entry naming the nearest concept and why it fails.

**Never mint a URI the scheme does not contain.** An invented
`uo:MeltCrystallisationWithSweating` is indistinguishable from a real concept once
it is in a triple store, and it will not resolve. The gap list is the deliverable
for missing concepts — it is how the scheme gets extended deliberately.

## Matching against a hierarchy

Schemes of this kind are usually walked upward with `skos:broader*`: a
requirement for "distillation" is satisfied by a resource offering
"rectification". Two consequences:

- Bind as deep as the evidence supports — depth is information, and a consumer can
  always generalise upward but cannot specialise downward.
- Never bind a unit process to a separation concept (or the reverse) to force a
  match. A wrong branch is worse than an unmapped step, because upward traversal
  will silently make it look satisfiable.

## Reaction steps

For a `UNIT_PROCESS`, the concept names the *reaction type* (oxidation, nitration,
hydrogenation) — not the vessel. Equipment goes in `equipment_as_stated`.

This matters downstream: a reactor is generally selected on operating envelope and
material compatibility rather than on a named capability, so a unit process bound
to a vessel type will match against the wrong criteria.
