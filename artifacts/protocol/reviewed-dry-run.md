# Reviewed Protocol Freeze candidate dry-run

Exact clean code revision:
`6e117463f8bfaf92535c05040cd32bef60fab3b1`

The expanded dry-run passed all 22 local mechanism checks. Its protocol hash is
`2f1f59560946584cb12a2708877d4e38d7cff37d9e145ba9c4235cc9855b1312`.
The write-once run manifest hash is
`e9615d5c9f29cabcd28c4812212861ea13ed6409cbb7fe50f8cc4215888ef5bb`.

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
about 0.00437 single-process CPU hours at the 4,096-evaluation ceiling. A local
Linux/arm64 candidate image passed the same 22 checks and projected about
0.00481 CPU hours. Its local image ID is
`sha256:c6d8787b17776dbffce7205119aa0392c731f5b8a0d2369aaa200e7615756f2f`;
this is diagnostic and is deliberately not recorded as the final runner digest.

The exact The Well gliders shard passed all external numerical gates across 20
trajectories. Nine-point/RK4 achieved RMSE `0.01717`, a 51.1% improvement over
five-point/Euler. The attributed CI fixture is independently bound into the
protocol hash.

Status: **ready for Protocol Freeze review**, not frozen. Gate PF remains
blocked until the final confirmatory runner is published and pinned, its profile
is retained under that digest, final worlds are externally committed, and the
statistical and protocol choices are independently accepted.
