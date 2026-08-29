# Reviewed local Protocol Freeze dry-run

Exact clean code revision:
`d8ed5c800bafd30b5e18b35e593321c356fe18ab`

The expanded dry-run passed all 23 local mechanism checks. Its protocol hash is
`0c4685639302f4db81fc2c752911d0b7f70bfb8937e0aa2a55a3fc5bd2a8d892`.
The write-once run manifest hash is
`aa4e85d055e4d92bd945775f0045493b62040262fdb65786ca5bb880230e85cc`.

The reviewed additions are:

- five-point/Euler primary simulation versus nine-point/RK4 reference;
- numerical agreement across all six 32×32, 100-step cluster representatives;
- six measurement clusters, five seeds each, and a content-hashed 30-task design;
- a deterministic finite mutation grammar shared by treatment and H2 control;
- exact mutation-attempt, uncached-evaluation, cache-hit, and world-query accounting;
- schema-v1 artifact boundaries and interrupted-ledger recovery;
- pinned The Well source and attributed fixture manifests, a resumable
  checksum-enforced downloader, and 20-trajectory external validation;
- a local external-root provisioner, manifest verifier, and one-shot evaluator;
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
design-detectable alternative. This distinction is accepted for the local
self-audited run and has not received independent statistical review.

The host frozen-mix microbenchmark projects 419,430,400 stencil updates and
about 0.00424 single-process CPU hours at the 4,096-evaluation ceiling. The
published Linux/arm64 runner passed the same 23 checks and projected about
0.00478 CPU hours. The final multi-platform runner is pinned as
`ghcr.io/ryanchromium/scientific-parallax-confirmatory@sha256:1b99d310dfa0fe98019489d00763ec3321676ba86384ac2c6eb78979d0c6533f`.
Its source revision is `78a59bf68c58c592d30bcf8aeb2f145ecb347cfc`.

The exact The Well gliders shard passed all external numerical gates across 20
trajectories. Nine-point/RK4 achieved RMSE `0.01717`, a 51.1% improvement over
five-point/Euler. The attributed CI fixture is independently bound into the
protocol hash.

Gate PF generated 30 repository-external task descriptors and committed world
hash `755df6b5ee69a75f7e6d8dff771356222d3633a493663ebd889a394d9e15a26b`.
Host and exact published-runner verification agreed. A later strategy-freeze
record will bind the eventual strategy before one-shot evaluation.

Status: **protocol frozen under local single-account self-audit**. Independent
review and custody were waived, so the result cannot be described as
independently confirmed. Final task contents remain unopened.
