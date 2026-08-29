# Decision log

## ADR-001: Step 0 uses eight formal candidates

- Status: accepted before baseline execution
- Date: 2026-08-26
- Applies to: Step 0 / protocol `step0-v1`

The research plan specifies eight candidates in the Step 0 primary endpoint and
strict scope, but two candidates in the milestone summary and closing checklist.
The implementation uses eight candidates because the primary endpoint is not
defined for a two-candidate pool. Two-candidate cases remain useful unit tests,
not the formal thin-slice experiment.

The eight candidates are the complete combinations of three possible anomaly
sources. This avoids choosing an arbitrary favored subset after observing
results and gives every modeled explanation a symmetric prior.

## ADR-002: Full-budget execution for a sustained endpoint

- Status: accepted before baseline execution
- Date: 2026-08-26
- Applies to: Step 0 / protocol `step0-v1`

Every run uses the full finite question budget. The endpoint is computed after
the run as the earliest query after which the true candidate remains above the
posterior threshold. Early stopping at the first crossing would not establish
the required persistence through budget end.

Queries are sampled without replacement. A question-specific deterministic
noise stream gives all strategies the same potential observation for the same
seed and question, independent of query order.

## ADR-003: Gray–Scott starts with two spatial stencils

- Status: accepted for development before Protocol Freeze
- Date: 2026-08-26
- Applies to: Steps 2–3.5

The primary solver uses a five-point finite-difference Laplacian and the
reference solver uses a nine-point isotropic stencil. Both are CPU-friendly and
make discretization artifacts observable during early development. The primary
path uses explicit Euler and the reference path now uses separately implemented
classical RK4. The Well external data adds a Fourier spectral plus ETDRK4 path,
but remains offline validation rather than a queryable world.

## ADR-004: Step 3 baselines use anonymous field summaries

- Status: accepted for development before Protocol Freeze
- Date: 2026-08-26
- Applies to: Step 3

The initial fixed representation contains experimental-condition features and
anonymous final-field summary statistics. This keeps the baseline cheap and
auditable while exercising hidden parameter blocks and interventions. It is a
deliberately limited comparator, not the future Paradigm IR representation and
not evidence that summary statistics are scientifically sufficient.

## ADR-005: Gray–Scott candidate neighborhood narrowed after development run v1

- Status: accepted during development; invalidates development run v1
- Date: 2026-08-26
- Applies to: Step 3 development baseline

The first development run made all strategies identify the standard candidate
in a median of two queries. The candidate alternatives were too distant and the
summary likelihood too sharp, so the endpoint could not distinguish question
selection. Before Protocol Freeze, the law variants were narrowed to local
perturbations and the summary noise scale was made more conservative. The v1
run remains ignored development output and cannot be used as evidence.

The second development run used the entire 16-question pool. Every strategy
therefore ended with the same evidence, while the median true posterior sat on
the 0.95 threshold. The development query budget was reduced to 12 so that
question selection is evaluated under scarcity. The threshold was not relaxed.

A 12-query dry run left every strategy below the 0.95 endpoint in almost all
replicates, so it was also non-informative for time-to-identification. The final
development candidate uses 14 of 16 questions. This tuning remains explicitly
exploratory and must be frozen before any confirmatory world is opened.

Weak ridge regularization was unstable under the development parameter-block
extrapolation. A development-only scan selected ridge `1.0`; bootstrap variance
is inflated only by out-of-bag training residuals. Hidden-block targets are not
used for fitting or uncertainty calibration. This setting must be frozen before
confirmatory evaluation.

## ADR-006: Protocol candidate uses six clusters and a 30% detectable alternative

- Status: proposed for independent Protocol Freeze review
- Date: 2026-08-29
- Applies to: Gate PF candidate

The design uses six parameter/measurement clusters with five independent seeds
each. Its success rule remains a 95% lower confidence limit above a 20% relative
query reduction. Simulation estimates power 0.00 at a true 20% effect, 0.90 at
30%, and 1.00 at 40%. This is expected at the null boundary, but makes 30%—not
20%—the design-detectable alternative. Gate PF requires explicit independent
acceptance of that distinction.

## ADR-007: Numerical replication couples a different stencil and integrator

- Status: proposed for independent Protocol Freeze review
- Date: 2026-08-29
- Applies to: Gate PF candidate

The primary path is five-point plus Euler; the reference is nine-point plus
classical RK4. Across one 32×32, 100-step representative of each cluster, the
largest observed mean field difference was about 0.00209, maximum field
difference 0.0206, and summary L2 difference 0.00557. Candidate tolerances are
0.005, 0.08, and 0.015. Noise and masking are disabled only in this diagnostic
to avoid comparing unrelated random draws.

## ADR-008: Candidate and evaluation budgets count attempted work

- Status: proposed for independent Protocol Freeze review
- Date: 2026-08-29
- Applies to: Gate PF candidate

Every attempted mutation is charged before equivalence deduplication. Every
uncached candidate-question score costs one evaluation; a cache hit costs zero
evaluations but is counted separately. A completed `World.observe` call costs
one world query. Treatment and H2 control share the same content-hashed finite
generator with 32 attempts per parent and 128 candidates per task.

## ADR-009: External evidence is committed but remains physically absent

- Status: accepted for development; blocks Gate PF until provisioned
- Date: 2026-08-29
- Applies to: external validation and final evidence

The Well test manifest pins official revision, license, sizes, and SHA-256 for
six shards, but marks all shards undownloaded. The final evaluator refuses a
directory under the development tree and creates its one-shot access record
before reading final data. These controls make absent external inputs visible;
they do not substitute for downloading a development shard or externally
provisioning the final world.
