# Step 6 budgeted co-evolution scheduler

Status: the initial Step 6 development control closes the paradigm-question
loop under the locally self-audited Protocol Freeze. It does not access final
sealed tasks and is not a confirmatory result.

## Round boundary and resource accounting

The scheduler has no arbitrary fixed generation count. It continues until the
declared world-query ceiling, stable-top-k convergence, fewer than two viable
paradigms, or exhaustion of executable questions. The development control uses
a four-query ceiling and a minimum of four observations, so it terminates by its
query budget.

Every attempted frozen paradigm mutation is charged before generation. Every
uncached paradigm-question prediction and fixed-probe phenotype evaluation is
charged as a candidate evaluation. Cache hits are counted separately. Question
generation uses its own visible counter. Treatment, ablation, and baseline arms
are assigned the same world-query ceiling; their independent computation counts
remain separate instead of being disguised as world queries.

## Closed loop

```text
active + dormant paradigm archive
             |
             v
frozen mutation + backfilled development evidence
             |
             v
survival gates + three paradigm niches + Pareto archive
             |
             v
retarget executable question population to active paradigms
             |
             v
three question niches + question Pareto front
             |
             v
preregister all predictions in a hash ledger
             |
             v
execute one development-world experiment
             |
             v
independent calibrated likelihood update
             |
             v
advance survival exactly once and write immutable checkpoint
```

The three paradigm niches remain the Gate PF axes: current predictive best,
minimum description length, and validated structure gain. The question
population adds three finite-capacity axes: information per cost, raw predictive
disagreement, and minimum experiment cost. A rotating allocation order ensures
that no one objective selects every executed question. Both current fronts and
a cumulative paradigm Pareto archive are reported each round.

## Independent evidence and lifecycle

Questions and mutators never receive observations, hidden labels, posterior
objects, or an evidence-update callback. Before each query, the scheduler writes:

- the registered active candidate set;
- all backfilled historical predictions needed for dynamic candidates;
- the reconstructed prior;
- the selected question and anticipated outcomes.

Only then may the development world return an observation. The independent
engine loads the frozen noise floor and likelihood rule, applies the calibrated
component noise profile, and writes the posterior. A separate verifier rebuilds
every dynamic prior and every update from ledger values alone.

Low-viability checkpoints advance only after a new observation—never during
selection or historical backfill. The frozen thresholds therefore drive active,
dormant, and dead states without an invented post-freeze contradiction rule.
Dead and equivalent candidates remain in the append-only fossil lineage.

One parent producing multiple distinct frozen children is recorded as a split,
including every child ID. The scheduler also accepts typed recombination requests,
but Gate PF did not freeze a `recombine` generator operator. Current requests are
therefore recorded and rejected. Executing them would require a protocol
amendment, a new strategy freeze, and a newly named final-world commitment.

## Question trace and measurement fidelity

Question mutations retain their Step 5 parent and child semantic hashes. Because
the active paradigm set changes, each selected question also receives a
round-specific retargeting event that binds its stored base question, active
targets, and executed semantic hash.

Paradigm predictions honor the executable measurement mixing and downsampling as
well as local pulse interventions. For the founder IR, a unit check compares this
prediction compiler directly with the online Gray–Scott world to numerical
precision. Expected information gain and realized evidence updates use the same
frozen likelihood noise.

## Recovery and negative controls

At the end of every completed round, the scheduler writes an immutable,
hash-linked checkpoint containing both populations, all observations, cached
predictions, budget counters, fronts, and the hashes of all ledgers. Resume first
verifies that no ledger advanced beyond the checkpoint, then restores counters
without reset. An interrupted-after-round-zero run produces byte-identical final
reports and ledgers to an uninterrupted run.

The circular-reward negative control gives two candidates identical predictions:
language or question scoring cannot move their posterior. Leakage controls check
the question schema and prediction-before-observation ordering. Any change to a
preregistered prediction breaks its event hash.

Run with:

```bash
uv run scientific-parallax step6 run \
  --config configs/experiments/step6-coevolution.json \
  --output artifacts/step6/runs/development
```

Resume an interrupted completed-round checkpoint with the same command plus
`--resume`. The control satisfies the initial Step 6 exit condition only when all
evidence reconstructs, lifecycle failures remain traceable, multiple resource
objectives are active, budgets match the frozen ceilings, negative controls pass,
and the final-world evaluation path remains untouched.
