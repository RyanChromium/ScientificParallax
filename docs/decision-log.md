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
make discretization artifacts observable during early development. Because they
currently share explicit Euler time integration, this is not treated as fully
independent numerical replication. A separately implemented time integrator is
required before the final Gray–Scott challenge.

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
