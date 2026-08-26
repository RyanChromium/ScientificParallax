# Step 0 reviewed exploratory baseline

Protocol: `step0-v1`

Configuration hash: `abf722626571565c29a12034d9f4c0a99bab6b0bad80123c55c473d5c80f9997`

Independent noise worlds: 30, evaluated as three sequential batches of 10

## Result

The preliminary decision is **go for Step 0 mechanics and evaluation design**.
This decision does not claim that co-evolution works; Step 0 contains a fixed
candidate pool and tests only whether auditable question selection can separate
known competing explanations.

| Strategy | Successful worlds | Median stable-identification query |
|---|---:|---:|
| Bayesian experimental design | 30/30 | 4 |
| Maximum raw disagreement | 30/30 | 8 |
| Random selection | 30/30 | 12 |

Bayesian design beat random selection in each batch: `3 vs 11`, `4 vs 12`, and
`4.5 vs 14.5` median queries. All strategies eventually consumed the same full
32-question pool, so their final posterior is intentionally identical; the
primary endpoint measures how early the true candidate becomes and remains
identified, not the final posterior after exhaustive evidence.

The contradictory negative-control candidate was placed inside a
maximum-disagreement selection loop. Its posterior fell below its `1/9` prior
after the first observation, never exceeded `1.61e-7` after evidence arrived,
and ended at numerical zero. It therefore created disagreement without gaining
evidential support.

## Review limitations

- The true explanation is guaranteed to be in the eight-candidate pool.
- The likelihood and data-generating noise model are correctly specified.
- The world is deliberately small and synthetic.
- Thirty replicates establish a software/protocol smoke test, not a powered
  scientific conclusion.
- No candidate generation, paradigm mutation, lineage selection, or
  co-evolution occurs in Step 0.

The next stage may build the reproducible project skeleton and world interface,
but should preserve this baseline as a regression test rather than present it
as evidence for the full Scientific Parallax hypothesis.
