# Step 4 paradigm genotype, lineage, and mutation

Status: initial Step 4 exit criteria implemented on development probes. The
final sealed task bundle remains unopened.

## Scope fixed by Protocol Freeze

Step 4 uses protocol hash
`0c4685639302f4db81fc2c752911d0b7f70bfb8937e0aa2a55a3fc5bd2a8d892`
and the exact candidate-generator hash already bound to it. The available
single-step mutation grammar is therefore limited to:

- remove one law term;
- lower one coefficient;
- raise one coefficient;
- add one field-decay term.

The broader representation operations listed in the research-plan draft—new
nonlinear state combinations, coordinate reparameterization, and
coarse-graining—are not silently added after Gate PF. They require a future
protocol amendment and a newly named final-world bundle.

## Implemented model

Each paradigm individual contains:

- a schema-versioned genotype with frozen Paradigm IR and executable signed
  coefficients;
- a phenotype consisting of its behavior signature on a fixed development
  probe set;
- generation, parent, mutation record, and parent/child genotype hashes;
- current and cumulative patch-cost components;
- a unified description-length breakdown;
- evidence, predictive-gain, structure-gain, survival, and lineage status.

Parameter changes contribute behavioral distance but not structural distance.
Variable renaming is canonicalized before structure and description-length
comparison, so shorter names cannot win resources. The executable compiler is
limited to the frozen two-field Gray–Scott IR and uses the development world,
not final sealed task descriptors.

## Patch cost and description length

Patch cost retains all five planned components: new entities, new parameters,
special conditions, scope contraction, and preregistration violations. The
development-control weights are declared before the run in
`configs/experiments/step4-paradigm-evolution.json` and every component remains
visible alongside the weighted total.

Total description length is the sum of canonical UTF-8 JSON encoding lengths
for structure, free parameters, decoder, measurement model, assumptions, and
search metadata, plus an explicit residual encoding length. Descendants inherit
cumulative patch burden; mutation, splitting, or dormancy does not reset it.

## Lineage and population

The append-only lineage ledger records founders, offspring, and status changes
in a SHA-256 hash chain. Rebuilding validates event order, parent existence,
generation increments, genotype hashes, and mutation-parent binding. Dead and
equivalent lineages remain in a fossil archive.

After the frozen viability and survival gates, three capacity-four niches are
maintained:

- current predictive best;
- minimum total description length;
- validated structure gain.

Equivalent variable-renamed candidates are collapsed before niche selection.
Candidates outside every niche become dormant rather than silently disappearing.

## Fixed-question control

The development-only control uses three predeclared 16×16, 25-step probes. The
world observations are acquired once and charged as three world queries. All
paradigms then predict those fixed conditions; no question evolution occurs.
Attempted mutations and uncached candidate evaluations use the Protocol Freeze
accounting rules and ceilings.

Run with:

```bash
uv run scientific-parallax step4 run \
  --config configs/experiments/step4-paradigm-evolution.json \
  --output artifacts/step4/runs/development
```

The control is an engineering and mechanism result, not final-world evidence.
It satisfies the Step 4 exit condition when all offspring are traceable,
renamed equivalents collapse, overfit patches cost more, the lineage fully
rebuilds, failed lineages remain available, all three niches operate, the
frozen mutation grammar is exercised, and the final-world directory is never
opened.
