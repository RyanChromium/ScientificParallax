# Step 5 executable question genotype and population

Status: the initial Step 5 exit criteria are implemented in a development-only,
fixed-paradigm control. The final sealed task bundle remains outside the
development workflow and unopened for strategy evaluation.

## Question boundary

A question is no longer a natural-language suggestion. Its schema contains only:

- an executable Gray–Scott condition, initial state, boundary, and duration;
- an optional typed local intervention;
- a typed sampling, mixing, downsampling, visibility, and noise specification;
- the registered fixed paradigms that the experiment is intended to distinguish;
- a display ID and non-scoring prose label.

The semantic identity excludes the display ID, experiment ID, and prose label.
Relabeling an experiment therefore cannot manufacture novelty. Initial seed,
condition, intervention, measurement, and target paradigms remain part of the
identity because changing any of them changes the executable scientific question.

The schema has no hidden truth, realized observation, posterior, or update-rule
field. The mutator accepts only a parent question. It cannot see the world or the
evidence engine.

## Closed mutation grammar

The Step 5 strategy configuration declares ten deterministic one-step operators:

- lower or raise feed;
- lower or raise kill;
- cycle the initial-condition family;
- toggle periodic and reflecting boundaries;
- add or remove a local pulse;
- increase temporal sampling frequency;
- toggle spatial downsampling;
- toggle a fixed invertible channel mixing.

Every child records its operator, attempted index, details, parent semantic hash,
and child semantic hash. Invalid children are rejected before they can occupy a
semantic identity. Duplicate executable questions collapse even when their prose
labels differ.

This grammar is versioned as `step5-question-evolution-v0.1`. Gate PF fixes the
protocol and candidate-paradigm generator; this question strategy is a
post-freeze development component and must itself be strategy-frozen before any
one-shot final evaluation.

## Scoring and resource allocation

Fixed paradigms produce anticipated outcome summaries under a noiseless version
of the proposed measurement. External scoring then computes:

- posterior-weighted predictive disagreement;
- Monte Carlo expected information gain;
- simulation work, measured-value count, and intervention cost;
- expected information gain per weighted cost.

Only questions with positive predictive difference and expected information gain
can receive a population slot. Capacity is finite and ties are deterministic.
Language novelty is neither a score nor a tie-breaker. Cost weights must be finite,
non-negative, and not all zero, so expensive experiments cannot gain resources
through a negative-cost configuration.

## Independent evidence path

```text
typed question
     |
     v
validate + semantic deduplicate
     |
     v
fixed paradigms make anticipated outcomes
     |
     v
external EIG/cost scorer selects one question
     |
     v
hash-ledger preregistration  --->  development world observation
                                         |
                                         v
                              independent evidence engine
                                         |
                                         v
                         actual information gain and gap audit
                                         |
                                         v
                              next question generation
```

The evidence engine accepts only a registered prediction map and an observation.
It never accepts a question object. Preregistration is written before observation,
and each observation must reference the pending prediction event. Expected and
realized information gain are both retained; a negative single-round difference
is allowed because expected gain averages over possible noisy outcomes.

## Development control

The control keeps all eight Step 3 paradigms fixed while evolving questions for
two generations. It executes one selected question in generation 0, 1, and 2.
Question lineage and prediction/observation evidence use separate append-only
SHA-256 ledgers.

Run with:

```bash
uv run scientific-parallax step5 run \
  --config configs/experiments/step5-question-evolution.json \
  --output artifacts/step5/runs/development
```

The exit condition is a mechanism result, not evidence for the project hypothesis.
It requires the constructed two-model discriminator to beat a prediction-identical
experiment, hidden-truth and update-rule isolation, duplicate and invalid filtering,
language-only novelty rejection, complete mutation traceability, deterministic
replay, budget compliance, and no final-world evaluation access.
