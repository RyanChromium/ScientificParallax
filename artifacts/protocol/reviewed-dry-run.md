# Reviewed Protocol Freeze candidate dry-run

Exact clean code revision:
`3de7bb76958856e02acb78bba44e77969dbf48d8`

The expanded dry-run passed all 21 local mechanism checks. Its protocol hash is
`e69f41f07cf120e72510171543e7994847fd1dcccab7b8fdcd1d0d2f4a88eb03`.
The write-once run manifest hash is
`50d3980923198b503e9c51ba78313d482a12a7d1ae2af19d35587bd99a55fab0`.

The reviewed additions are:

- five-point/Euler primary simulation versus nine-point/RK4 reference;
- numerical agreement across all six 32×32, 100-step cluster representatives;
- six measurement clusters, five seeds each, and a content-hashed 30-task design;
- a deterministic finite mutation grammar shared by treatment and H2 control;
- exact mutation-attempt, uncached-evaluation, cache-hit, and world-query accounting;
- schema-v1 artifact boundaries and interrupted-ledger recovery;
- pinned The Well test-shard metadata and an opt-in checksum-enforced downloader;
- an external-root, one-shot final evaluator mechanism;
- a candidate execution environment bound to the protocol hash.

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

The local frozen-mix microbenchmark projects 419,430,400 stencil updates and
about 0.00423 single-process CPU hours at the 4,096-evaluation ceiling. That
timing is diagnostic only and must be repeated on the pinned confirmatory runner.

Status: **ready for Protocol Freeze review**, not frozen. Gate PF remains
blocked until at least one pinned The Well shard is downloaded and validated,
the confirmatory runner image is pinned, final worlds are externally committed,
and the statistical design is independently accepted.
