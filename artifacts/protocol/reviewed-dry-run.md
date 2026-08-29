# Reviewed Protocol Freeze candidate dry-run

Exact clean code revision:
`312aaf32c877fb6d7cdaf8c9b8ad06ca1c9914f1`

The expanded dry-run passed all 22 local mechanism checks. Its protocol hash is
`41b8229b388e2fb9f0345c7d15fd8a33746c94cd31a103393a692e10a969548b`.
The write-once run manifest hash is
`cfb9aeaf7d42ae03738f5df17369a5b9cdd15f2d2ca891bc479304d9aae391af`.

The reviewed additions are:

- five-point/Euler primary simulation versus nine-point/RK4 reference;
- numerical agreement across all six 32×32, 100-step cluster representatives;
- six measurement clusters, five seeds each, and a content-hashed 30-task design;
- a deterministic finite mutation grammar shared by treatment and H2 control;
- exact mutation-attempt, uncached-evaluation, cache-hit, and world-query accounting;
- schema-v1 artifact boundaries and interrupted-ledger recovery;
- pinned The Well source and attributed fixture manifests, a resumable
  checksum-enforced downloader, and 20-trajectory external validation;
- an external-root, one-shot final evaluator mechanism;
- hash-pinned runner inputs and a candidate execution environment bound to the
  protocol hash.

The largest observed numerical differences remained below the frozen limits:

| Metric | Largest observed | Tolerance |
|---|---:|---:|
| Mean absolute field difference | 0.00209 | 0.005 |
| Maximum absolute field difference | 0.0206 | 0.08 |
| Summary L2 difference | 0.00557 | 0.015 |

The simulated power curve is 0.00 at a true 20% reduction, 0.90 at 30%, and
1.00 at 40%, using 30 tasks. The success rule requires the 95% lower confidence
limit to exceed 20%, so 20% is the null boundary and 30% is the current
design-detectable alternative. This distinction still needs independent review.

The host frozen-mix microbenchmark projects 419,430,400 stencil updates and
about 0.00445 single-process CPU hours at the 4,096-evaluation ceiling. The
published Linux/arm64 runner passed the same 22 checks and projected about
0.00486 CPU hours. The final multi-platform runner is pinned as
`ghcr.io/ryanchromium/scientific-parallax-confirmatory@sha256:d767d7ece6977d4900bd4b3ee505bf9d6a08a06f7a8ca15eb07f8e2ae301d250`.
Its source revision is `453dd9bdf0cc85d42d2e2f3e545f1d3a0685afcb`.

The exact The Well gliders shard passed all external numerical gates across 20
trajectories. Nine-point/RK4 achieved RMSE `0.01717`, a 51.1% improvement over
five-point/Euler. The attributed CI fixture is independently bound into the
protocol hash.

Final-world sealing now has two explicit phases: Gate PF commits the world to
the protocol before Step 4, then a separate strategy-freeze record binds the
eventual strategy to that unchanged commitment immediately before evaluation.

Status: **ready for Protocol Freeze review**, not frozen. Gate PF remains
blocked until final worlds are externally committed and the statistical and
protocol choices are independently accepted.
