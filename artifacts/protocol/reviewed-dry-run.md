# Reviewed Protocol Freeze candidate dry-run

Exact clean code revision:
`656867fe0e1b367b933d2923eee68d1521dd8681`

The expanded dry-run passed all 22 local mechanism checks. Its protocol hash is
`8a28aeae581f0e7d2820bddc590cfef63f0f4e0ab103b408d3a30749558ffb29`.
The write-once run manifest hash is
`8c39130ff8822efce022768acd12c8611f5f8fe48e248d0986b47459db02eb13`.

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
about 0.00455 single-process CPU hours at the 4,096-evaluation ceiling. The
published Linux/arm64 runner passed the same 22 checks and projected about
0.00487 CPU hours. The final multi-platform runner is pinned as
`ghcr.io/ryanchromium/scientific-parallax-confirmatory@sha256:56080a851d6dba6ea2008e6e441d29bcec2e72e4e06f3e6a9331dbcf56a13348`.
Its source revision is `e51f9272ada5346daa22b4fe9ff6c285b0480ddc`.

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
