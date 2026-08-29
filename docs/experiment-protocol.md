# Step 3.5 protocol candidate and dry-run

Status: ready for local single-account Protocol Freeze. Nothing in this
document opens the future final sealed Gray–Scott worlds.

## Frozen-candidate components

The dry-run serializes a schema-versioned candidate `ProtocolSpec` containing:

- Paradigm IR version and equivalence rule;
- evidence update, noise calibration, and survival rules;
- one primary endpoint, `k`, persistence, minimum effect, and statistical method;
- world-query, candidate-generation, candidate-evaluation, and CPU budgets;
- exact cache accounting, numerical tolerances, and candidate-generator hash;
- six measurement-cluster definitions and their content hash;
- external-data source manifest, attributed CI-fixture manifest, and
  execution-environment hashes;
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

The state machine is a software guardrail, not a security sandbox. The selected
assurance mode is explicitly local and self-audited: final-world data remains
outside normal development paths, but the same operating-system account can
override permissions. Results cannot be described as independently confirmed.

The candidate sets dormancy after two sub-viability checkpoints and death after
four; a declared hard contradiction causes immediate death. Viability requires
non-negative evidence, predictive gain of at least `0.01`, and decoder cost no
greater than `1.0`. Three niches each have capacity four: current predictive
best, minimum description, and validated structure gain.

## Endpoint and statistics

The endpoint implementation finds the first checkpoint at which the true
equivalence class enters the top `k` and remains there for the declared number
of checkpoints. Failures are right-censored at the query budget. Treatment and
control are compared using restricted mean time to identification with
bootstrap resampling stratified by parameter/measurement cluster.

The candidate task design has six parameter/measurement clusters and five
independent initial seeds per cluster (30 tasks). Simulation-based power is
estimated at true relative reductions of 20%, 30%, and 40%. The current
development run estimates power `0.00`, `0.90`, and `1.00`, respectively, for
the stricter success rule that the 95% lower confidence limit exceed the 20%
null boundary. Thus 30% is the design-detectable alternative; this does not mean
the study can confirm an effect that is exactly on the 20% boundary.

## Numerical and generator freeze candidates

Primary simulations use the five-point stencil with explicit Euler. Numerical
replication uses the nine-point stencil with separately implemented classical
RK4. Across one full-size representative from every cluster, frozen tolerances
are mean absolute field difference `0.005`, maximum absolute difference `0.08`,
and summary-vector L2 difference `0.015`. Measurement noise and random masking
are disabled only for this solver comparison so that it measures discretization
rather than independent random draws.

Treatment and the H2 Bayesian-design control share the same deterministic
finite candidate generator. It allows term removal, coefficient-low/high
variants, and adding a decay term; each parent has at most 32 mutation attempts
and each task at most 128 candidates. Every attempted mutation is charged before
equivalence deduplication.

## Persistent-artifact and final-evidence boundaries

Manifests, ledger events, Paradigm IR, and reports carry explicit schema version
1. Future versions are rejected unless a one-version migration is registered.
Evidence ledgers can resume after a completed observation or after interruption
between preregistration and observation while preserving the hash chain.

The final evaluator requires a pre-committed directory outside the development
tree. The local provisioner derives 30 hidden task and measurement seeds from a
fresh 32-byte secret, writes deterministic JSON task descriptors, and commits a
manifest of paths, sizes, and file hashes. The verifier rehashes all bytes before
the evaluator writes an exclusive access record and result record. The actual
directory and commitment do not yet exist; Gate PF therefore remains closed.

Sealing is deliberately two-stage. At Gate PF, the local user creates a
schema-v2 world commitment containing the protocol, assurance-mode, generator,
task-count, and world hashes before any Step 4 strategy exists. Immediately
before final evaluation, a separate strategy-freeze record binds the completed
strategy hash to that unchanged commitment. The evaluator verifies the full
manifest and both records before creating its one-shot access record.

The Well test-split manifest pins the official repository revision, CC-BY-4.0
dataset license, byte counts, and SHA-256 values for all six 2.65 GB shards.
The gliders shard was downloaded outside Git and verified byte-for-byte. A
deterministic 16 KB, attributed, modified fixture is committed for CI and bound
to the protocol hash. Across all 20 trajectories over the first stored
10-second interval, nine-point/RK4 reduced field RMSE from `0.03511` to
`0.01717` relative to five-point/Euler (51.1% improvement). The reference path
also met frozen external-validation limits: mean RMSE at most `0.02`, worst
trajectory RMSE at most `0.04`, and at least 25% improvement.

The confirmatory runner uses a digest-pinned Python 3.12.13 base and hash-pinned
NumPy 2.5.2 wheels for Linux amd64 and arm64. Version `0.3.5` is published as a
multi-platform OCI index at
`ghcr.io/ryanchromium/scientific-parallax-confirmatory@sha256:1b99d310dfa0fe98019489d00763ec3321676ba86384ac2c6eb78979d0c6533f`.
Both the release digest record and an exact repository copy are retained.

Pushing a `runner-v*` tag invokes the repository's pinned-action publication
workflow. It builds both declared Linux platforms, publishes them as one OCI
index in GitHub Container Registry, and attaches a machine-readable
`runner-digest.json` to the corresponding public GitHub release. Only that
published digest may populate `container_image_digest`; a local image ID or
base-image digest is insufficient. The published arm64 manifest was pulled by
the OCI-index digest and used for the frozen-mix profile.

## Required dry-run controls

- variable-renaming equivalence and structural-change non-equivalence;
- access to final evidence before freeze and repeated access after opening;
- residual shuffling to destroy repeatable residual structure;
- random contradictory candidate rejection;
- synthetic-truth recovery by the endpoint and bootstrap code;
- an exact accounting exercise and frozen-mix compute-ceiling estimate before
  Protocol Freeze.

Run with:

```bash
uv run scientific-parallax protocol dry-run \
  --config configs/experiments/protocol-dry-run.json \
  --output artifacts/protocol/runs/development
```

Passing the dry-run means the mechanisms are ready for local Protocol Freeze.
Gate PF still requires the updated published runner digest and a verified local
final-world commitment outside the repository. The statistical and protocol
choices are accepted under self-audit only.
