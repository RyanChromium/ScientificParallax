# Step 0 protocol: fixed-candidate thin slice

Status: exploratory implementation, protocol ID `step0-v1`.

This experiment validates the mechanics and evaluation design of Scientific
Parallax. It does **not** test co-evolution and cannot support a claim of
scientific discovery.

## Synthetic world

The shared local theory is a linear response. Three independent terms can be
present in observations:

1. a quadratic term belonging to the physical dynamics;
2. an asymmetric bias present only in the primary instrument;
3. a cubic artifact present only in the primary numerical solver.

The sealed world contains all three terms. Questions select a condition `x`, an
instrument, and a solver. Reference channels remove the corresponding
systematic effect. This makes theory omission, measurement error, and numerical
artifact experimentally distinguishable.

The finite pool contains 32 questions: eight values of `x`, two instruments,
and two solvers. Extreme values have more raw disagreement and substantially
more noise. This deliberately distinguishes raw maximum-disagreement selection
from noise-aware Bayesian experimental design.

## Candidate pool

The eight preregistered paradigms are the complete `2^3` combinations of the
physical, measurement, and numerical terms. Their IDs are `p_TMN`, where each
bit records whether that term is present. The true candidate is `p_111`.

A ninth, hash-driven contradictory model is used only as a negative-control
diagnostic. The diagnostic places it in a maximum-disagreement selection loop
and checks that actual evidence reduces its posterior. It is not added to the
formal eight-candidate endpoint.

## Evidence and endpoint

All candidates start with equal prior probability and share the question's
known Gaussian noise model. The independent evidence engine updates posterior
weights from preregistered predictions and the returned observation.

The primary endpoint is the first query after which the true candidate remains
at posterior probability `>= 0.95` through the end of the query budget. A run
that never meets this condition is right-censored at the budget.

Every run executes the full budget. Stopping at the first threshold crossing
would make the “remains through budget end” clause impossible to verify.

## Strategies

- `random`: uniform sampling without replacement;
- `max_disagreement`: maximum posterior-weighted variance of predicted means;
- `bayesian_design`: maximum expected reduction in posterior entropy per unit
  cost, integrated over the candidates' predictive mixture.

Question selection cannot access realized observations. For a given seed and
question ID, all strategies receive the same potential observation regardless
of query order.

## Audit trail

Each prediction event is appended before the world is queried. The following
observation must reference that prediction's content hash. Events form a SHA-256
hash chain, and completed ledgers can be independently verified.

## Running the protocol

```bash
uv sync --extra dev
uv run scientific-parallax step0 benchmark \
  --config configs/experiments/step0.json \
  --output artifacts/step0/runs/baseline
```

Generated run ledgers are intentionally ignored by Git. A compact reviewed
benchmark summary may be committed separately.
