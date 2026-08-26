# Gray–Scott reviewed development baseline

Exact code revision: `443ca98b89dc40716569513ad3a0708a249ffbdd`

This is a development-world result, not sealed evidence and not a test of
paradigm–question co-evolution.

Eight locally perturbed fixed laws were compared over a frozen 16-question
pool. Each strategy used 14 questions in 12 measurement-noise replicates. The
true standard law had median final rank 1 under every strategy.

| Strategy | Median true posterior | Runs reaching 0.95 |
|---|---:|---:|
| Maximum disagreement | 0.949 | 3/12 |
| Bayesian design | 0.944 | 1/12 |
| Active learning | 0.929 | 5/12 |
| Random | 0.926 | 0/12 |
| Coverage | 0.762 | 0/12 |

The 0.95 threshold remains strongly censored and is retained only as a
diagnostic. The result does not support declaring a winning selector. It does
show that the fixed pool, query scarcity, measurement noise, selection paths,
and evidence updates are no longer degenerate.

On the highest-feed parameter block, the fixed predictor RMSE was `0.0423` and
the bootstrap ensemble RMSE was `0.0406`. Out-of-bag variance inflation made the
ensemble conservative on this block: RMSE was about `0.60×` its average
predicted standard deviation.

The full ignored run output contains 60 verified hash-chained ledgers, all
candidate predictive distributions, bootstrap member predictions, observations,
and per-query posterior histories. The committed JSON is only a compact review
record.
