# Reviewed Protocol v3 mechanism-attribution audit

## Decision

Withdraw the interpretation that the v2 ablation isolated survival of neutral
structural intermediates. Retain all historical v2 measurements and its
protocol-level decision record, but interpret that comparison as a composite
search-policy effect. A distinct algorithmic advantage over the MAP-Elites-style
control has **not been demonstrated**. This is not proof of equivalence.

Disposition: stop the current novelty/mechanism claim. Do not unlock Step 8 or
keep tuning this world to recover a preferred conclusion. The contribution of
this iteration is a reproducible attribution audit and correction, not a new
law of nature or a new general scientific-discovery algorithm.

## What was tested

The audit follows the [prewritten v3 protocol](../../docs/protocol-v3-mechanism-audit.md).
It separates two switches previously conflated in `candidate_niches`:

- P: prioritize expansion of higher structural stages;
- E: balance the ensemble used to choose questions by structural stage.

E does not remove candidates from the posterior or the parent pool. Consequently,
the old ablation was not a test of whether intermediates survive deletion.
Four adaptive factorial cells and four passive-schedule negative controls were
run, plus uniform search, breadth-first search, a degree-signature MAP-Elites-style
parent archive, and a scalar parent archive.

There were two development runs of 216 arm-task pairs each, followed by 648
frozen-validation pairs: 24 latent tasks from six unseen parameter combinations
and 30 null tasks, each evaluated with all 12 arms. These are **not 1080 independent
worlds**: the two development runs reuse the same 18 tasks; validation has 54
new tasks paired across arms.

## Iteration record

1. Development v1, revision `24217b2`: implementation and attribution screen.
2. Development v2, revision `e85377c`: correct the reference model's training
   objective to match the strategy's noise-standardized error, expand its grid
   to include every founder coefficient, and add secondary full-field scoring.
   No search rule changed. All 216 search traces, selected models, primary
   prediction errors and v2 compatibility decisions are identical across the
   two development runs.
3. Validation, frozen revision `250569d88e35c0ea3ce37b9cdaa0e604d2b8e531`:
   run once after committing the implementation, tests and validation config.
   No subsequent strategy adjustment or validation rerun was performed.

The first development run's reference comparisons are superseded, not erased.
Its strategy comparisons remain unchanged. Raw files are in `development-v1/`,
`development-v2/` and `validation-v1/` next to this report.

## Frozen validation results

Models are selected using training data only, over all generated representations.
The primary metric is held-out **summary-feature RMSE**, not hidden-state error.
The secondary metric is pointwise visible-field RMSE. Lower is better for both.
A predictive win means at least 20% lower primary RMSE than a 25-point two-state
reaction-scale grid fitted to that arm's acquired training data. A latent state
is not required by this predictive-win definition.

| Strategy | Primary RMSE | Full-field RMSE | Predictive wins /24 | Old structural endpoint /24 |
|---|---:|---:|---:|---:|
| P0E0: neither switch | 0.063462 | 0.130375 | 6 | 4 |
| P0E1: ensemble only | 0.058593 | 0.119433 | 7 | 7 |
| P1E0: priority only | 0.022298 | 0.048832 | 23 | 23 |
| P1E1: both, v2 treatment | 0.022513 | 0.049509 | 23 | 23 |
| Passive P0E0 / P0E1, each | 0.069395 | 0.141347 | 5 | 2 |
| Passive P1E0 / P1E1, each | 0.022656 | 0.049503 | 24 | 24 |
| MAP-Elites-style archive | 0.027833 | 0.059443 | 23 | 23 |
| Scalar archive | 0.068981 | 0.139482 | 4 | 3 |
| Uniform parent sampling | 0.066846 | 0.136177 | 5 | 2 |
| Breadth-first parent expansion | 0.079937 | 0.160140 | 0 | 0 |

The historical structural endpoint is secondary and is not interchangeable with
the representation-neutral predictive endpoint. In particular, failure of a
fixed-representation model to emit a latent state is not independent evidence
that it predicts poorly.

### Factorial attribution

Main effects average the paired error benefit of each switch across the other
switch's settings. Positive means lower error when enabled. Intervals are 95%
hierarchical bootstrap intervals, resampling parameter clusters and then tasks.

| Primary RMSE effect | Estimate | Descriptive 95% interval |
|---|---:|---:|
| Parent-priority benefit | 0.038622 | [0.026908, 0.050805] |
| Ensemble-balancing benefit | 0.002326 | [-0.004853, 0.010029] |
| Interaction: priority benefit at E1 minus at E0 | -0.005084 | [-0.019892, 0.009453] |

The secondary full-field analysis agrees in direction: priority benefit is
`0.075733 [0.050570, 0.101153]`; ensemble benefit is
`0.005132 [-0.009622, 0.021351]`.

For every validation task and both priority settings, toggling E under the fixed
passive schedule produces exactly identical search traces, selected laws and
primary errors. This is the expected negative control for the actual code path,
not a newly discovered natural phenomenon.

The evidence therefore favors parent-priority scheduling as the dominant source
of the old composite effect on these tasks. It does not establish that E has
zero effect in every adaptive setting, or that structural diversity is generally
unimportant.

### Search controls and null worlds

The paired mean relative primary-RMSE reduction for P1E1 versus MAP-Elites is
`0.023010`, with interval `[-0.331274, 0.347668]`. The mean absolute errors differ,
but there is no clear superiority evidence from this comparison. Mean paired
relative reductions are not ratios of the two aggregate mean errors.

MAP-Elites versus the scalar archive yields a paired mean relative reduction of
`0.554950 [0.427303, 0.661663]`. This is consistent with the known usefulness of
structural diversity, not evidence that we invented that mechanism. Actual
generation attempts average 93 for MAP-Elites versus 108 for the scalar archive
and guided treatment; their evaluation costs also differ. The ceilings are
matched, but actual compute is **not equal**.

Each of the 12 arms selected a complete latent structure on 0/30 null tasks.
These are the same 30 null worlds paired across arms, not 360 independent null
worlds. They are simple no-latent controls from the specified family, not a broad
test of false discoveries under alternative unknown dynamics.

## Integrity and resources

All eight recorded integrity checks passed. There are exactly 648 unique
arm-task pairs, every arm uses 12 world queries, and all generation/evaluation
ceilings are respected. Totals:

- world queries: 7776;
- candidate-generation attempts: 69174;
- uncached candidate evaluations: 432052;
- separately fitted reference evaluations: 194400;
- hidden summary-validation evaluations: 24768;
- additional secondary full-field model evaluations: 3888.

The new factorial corners match the corresponding original v2 prediction
commitments and question choices in unit tests and a full-12-query development
regression check. Changing held-out interventions cannot change search traces
or final training-based selection in the leakage test. The four v2 frozen source
components and confirmatory config remain byte-identical; `uv.lock` remains
unchanged. The old v1 final world remains unopened. The v2 result and task-result
files still match their original external copies.

Reproducibility identities:

- frozen revision: `250569d88e35c0ea3ce37b9cdaa0e604d2b8e531`;
- resolved validation config hash:
  `3d1c17a52e3dd55f20a639562f4ec01f5817254eacbb1569c6aca42614bbc955`;
- source/dependency identity:
  `1fe44752d64bcc7d2c8d8fd7018b00f59ec58ea4f82914ac531037da116f6f53`;
- validation task-results SHA-256:
  `6a39f7f2fed44ba0ac8a94ec00a29b7b62721aabf7de1994c19979a9e6ab72a6`.

## Remaining limits and disposition

The graph descriptor does not inspect stage labels or task truth, but its four
cells coincide with stages in this restrictive grammar. All search-control arms
also retain the original question ensemble and posterior conventions. Thus this
is not an unrestricted, answer-independent benchmark. The comparison does not
identify a unique physical hidden variable, establish causality beyond the
simulated intervention family, or prove superiority over published methods.

SymDer, an actual QDSR implementation and history-based dynamical alternatives
were **not run**. Broader-grammar comparisons were deliberately not implemented
after the attribution/novelty claim failed this audit's stopping rule. A future
project may investigate neutral paths in genuinely competing graph structures,
but it must begin with a new explicit hypothesis and matched baselines rather
than treating this diagnostic as a discovery breakthrough.

This is local single-account frozen out-of-sample validation, not independent
custody or independent replication. Only six parameter clusters from one world
family were tested; the intervals are descriptive and not multiplicity-corrected
generalization claims.
