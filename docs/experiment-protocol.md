# Step 3.5 protocol candidate and dry-run

Status: ready for review before Protocol Freeze. Nothing in this document opens
or defines the future final sealed Gray–Scott worlds.

## Frozen-candidate components

The dry-run serializes a candidate `ProtocolSpec` containing:

- Paradigm IR version and equivalence rule;
- evidence update, noise calibration, and survival rules;
- one primary endpoint, `k`, persistence, minimum effect, and statistical method;
- world-query, candidate-generation, candidate-evaluation, and CPU budgets;
- confirmatory baselines and one-factor ablations;
- mechanical stop conditions.

Changing one of these after Protocol Freeze invalidates the corresponding
confirmatory run.

## Paradigm IR v0.1

The finite DSL permits field variables and four typed operators: Laplacian,
product, source, and decay. Every term declares a target, arguments, and
coefficient symbol. The IR also includes a measurement model, scope, decoder
cost, and auxiliary assumptions.

Equivalence requires both:

1. the same canonical structure under finite variable permutation and allowed
   commutative rewriting;
2. the same observable intervention behavior on a frozen probe set.

Variable renaming alone therefore collapses, while structural or behavioral
changes remain distinct. This is a conservative prototype, not a complete
algebraic equivalence solver.

## Evidence isolation

Training and repeatable development evidence live in a normal evidence store.
Final evidence is owned by a separate `ProtocolGate`. It cannot be accessed
before the protocol and strategy hash are frozen, rejects a different strategy
hash, and can be opened only once.

The state machine is a software guardrail, not a security sandbox. Final-world
data must additionally be stored outside normal development paths before Gate
PF.

The development implementation includes executable active/dormant/dead
transitions. Repeated sub-viability checkpoints first cause dormancy and later
death; a declared hard contradiction can cause immediate death. Thresholds must
be frozen at Gate PF.

## Endpoint and statistics

The endpoint implementation finds the first checkpoint at which the true
equivalence class enters the top `k` and remains there for the declared number
of checkpoints. Failures are right-censored at the query budget. Treatment and
control are compared using restricted mean time to identification with
bootstrap resampling stratified by parameter/measurement cluster.

## Required dry-run controls

- variable-renaming equivalence and structural-change non-equivalence;
- access to final evidence before freeze and repeated access after opening;
- residual shuffling to destroy repeatable residual structure;
- random contradictory candidate rejection;
- synthetic-truth recovery by the endpoint and bootstrap code;
- a naive compute-ceiling estimate before Protocol Freeze.

Run with:

```bash
uv run scientific-parallax protocol dry-run \
  --config configs/experiments/protocol-dry-run.json \
  --output artifacts/protocol/runs/development
```

Passing the dry-run means the protocol is ready for adversarial review. It does
not itself execute Gate PF or authorize use of the final sealed worlds.
