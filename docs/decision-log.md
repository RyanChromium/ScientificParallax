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
