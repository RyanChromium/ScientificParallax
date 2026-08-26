# Step 3.5 reviewed protocol dry-run

Exact code revision: `443ca98b89dc40716569513ad3a0708a249ffbdd`

All ten synthetic-development checks passed:

- variable renaming collapsed while a structural change remained distinct;
- final evidence was blocked before freeze, bound to the frozen strategy hash,
  and available only once;
- the right-censored stratified bootstrap recovered a planted 43.1% query
  reduction with a 95% interval of 37.5%–50.2%;
- residual shuffling destroyed serial structure;
- the contradictory candidate lost evidential support;
- noise calibration enforced a positive floor;
- active, dormant, dead, and hard-contradiction transitions executed correctly.

The protocol hash includes the top-5 threshold, five-checkpoint persistence,
20% minimum relative effect, baseline/ablation lists, evidence rules, stop rule,
and all declared budgets.

The measured single-process microbenchmark projects roughly `0.0025 CPU hours`
for 4,096 evaluations at the current small Step 3 task size. This is not a Level
1 cost estimate and must be re-profiled on the frozen candidate and task mix.

Status: **ready for Protocol Freeze review**, not frozen. The unresolved
scientific and engineering blockers are listed in
`docs/protocol-freeze-checklist.md`.
