# Protocol v3: mechanism attribution audit

This is a new experiment, not a rerun or alteration of either sealed final world.
The v2 numbers remain historical observations; their interpretation is under
audit. No positive result is required, and a negative result is a valid stopping
condition. This protocol was written before the first v3 development run.

## Literature motivation

- Bongard and Lipson (2007), [model/test evolution](https://pmc.ncbi.nlm.nih.gov/articles/PMC1891254/).
- Stanley and Miikkulainen (2002), [NEAT and protection of structural innovation](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf).
- Mouret and Clune (2015), [MAP-Elites](https://arxiv.org/abs/1504.04909).
- Lu et al. (2022), [SymDer: hidden states and sparse dynamics](https://www.nature.com/articles/s42005-022-00987-z).
- Clarkson et al. (2022), [Bayesian symbolic experimental design](https://arxiv.org/abs/2211.15860).
- Bruneton (2025 preprint), [quality-diversity symbolic regression](https://arxiv.org/abs/2503.19043).

These papers establish close precedents, not measured performance on our tasks.
No superiority over their implementations is claimed without a matched run.

## What the v2 implementation actually changes

`candidate_niches` controls two separate operations: stage-prioritized parent
expansion, and a stage-balanced ensemble used to select questions. All generated
candidates remain in the posterior and parent pool even when omitted from that
ensemble. Therefore the existing ablation does not isolate candidate survival.
The no-niches parent selector also breaks score ties toward smaller structures.

## Experiment A: exact factorial decomposition of the v2 policies

Four cells independently toggle parent stage priority (P) and question-ensemble
balancing (E): P0E0, P0E1, P1E0, P1E1. The original mutation grammar, shared
class-balanced posterior, question evolution and selection rule, tie-breaking,
generation/query/evaluation ceilings, and aliases remain fixed. These toggles
do not delete candidates. P1E1 and P0E0 must match the corresponding v2 strategy
trajectories in regression tests. The original v2 structural endpoint is reported
only as a secondary compatibility diagnostic.

Run the same cells with a predetermined passive question schedule as a negative
control: since E only changes the question-selection ensemble, changing E must
then have *exactly zero* influence on search and predictions. This checks the
mechanistic interpretation rather than assuming that ensemble membership is
candidate retention.

## Experiment B: small search-control screen

Keep the same v2 grammar and posterior but replace parent expansion with:

- uniform sampling of unexpanded generated candidates;
- breadth-first expansion, independent of posterior and target stage;
- a MAP-Elites-style archive, one data-best model per generic graph descriptor
  (node count and sorted directed in/out degrees), sampled uniformly by cell;
- a scalar archive of the same maximum capacity, sampled uniformly.

The two archive arms really restrict which parents remain eligible. Both use
the same scalar data score, alias tie-breaking, capacity, and parent sampling
seed; all candidates may still contribute to the question ensemble and final
model selection. Thus this screen isolates *parent eligibility*, not every
possible benefit of population pruning. The MAP implementation is inspired by
MAP-Elites; it is not an execution of QDSR or NEAT.

The generic descriptor cannot read task kind, truth, or structural-stage labels.
However, within the restricted three-operation grammar its cells can still
coincide with the hand-designed stages. This is a diagnostic baseline, not proof
of open-ended or truth-independent scientific discovery.

## Representation-neutral evaluation

Primary outcomes are terminal held-out prediction RMSE and paired RMSE changes.
Select the final model using training data only, over *all* generated models,
without requiring a complete latent structure. Hidden validation is scored
only after the search completes. No held-out measurements reach selectors.

A separate fixed-representation baseline searches a prespecified reaction-scale
grid on the exact same acquired data, picks by training error, and is evaluated
on the same held-out interventions. Its computation is charged separately and
reported. This is a restricted two-state reference, not the best possible
two-state or history-dependent model. Relative improvement >=20% is a descriptive
predictive-win endpoint, not a requirement to emit a latent variable. Also report
complete-structure selection on null tasks whether or not prediction improves.

Each task is paired across arms, using common task/alias seeds. Report actual
generation attempts, world queries and model evaluations, not only ceilings.
Do not call unequal actual compute 'compute matched'. The bootstrap resamples
whole truth-parameter clusters and then tasks within clusters. With only a few
clusters, confidence intervals are descriptive and cannot establish broad
cross-system generalization. No post-hoc significance fishing across endpoints.

## Iteration and stopping

1. Development: correctness fixes, resource checks and diagnostic sensitivity.
   Keep each configuration and output; do not overwrite unsuccessful runs.
2. Freeze code and a separate validation configuration with unseen seeds and
   parameter combinations, then run once from a clean commit. This is a local
   frozen out-of-sample replication, not independent-custodian confirmation.
3. If parent priority explains the v2 effect and ensemble balancing contributes
   little, retract the *isolated survival-mechanism* interpretation. If generic
   search controls match the guided strategy, do not claim a new algorithmic
   advantage.
4. Broader grammar, SymDer and history-based baselines are gated follow-up work:
   do them only if this diagnostic produces a concrete surviving question.
   Do not turn a negative attribution result into another success-rate tuning
   exercise. Original Step 8 is not unlocked by this audit.

## Development revision log

Development v1 (commit `24217b2`) completed 216 runs with all integrity checks
passing. During its execution, before examining the complete outcomes, review
identified that the fixed-grid reference was fitted with unweighted squared
error while the strategies used noise-standardized error. Development v2 aligns
these training criteria and expands the grid to 25 coefficients, including all
five founder coefficients. It does not change any search policy. The v1 outputs
are retained, but v2 supersedes its fixed-reference comparisons.

The primary outcome is explicitly summary-feature RMSE, not full-field RMSE.
Development v2 also adds secondary pointwise visible-field RMSE, measured only
after search, and reports raw-RMSE factorial main effects and interaction. These
changes are made before the frozen validation run. They do not retrospectively
change v1 or v2 sealed outcomes.

The implementation is invoked as a separate module so frozen v2 source files,
configuration files and dependency lock remain byte-identical.

## Frozen validation design

`configs/experiments/mechanism-audit-validation-v1.json` specifies six new
parameter combinations with four seeds each (24 latent tasks), plus 30 null
tasks. All 12 arms run every task, for 648 arm-task runs. Query, generation and
evaluation ceilings remain 12, 128 and 4096, respectively. The source and this
configuration must be committed before execution. No strategy adjustment is
permitted after seeing this validation. Every result, including negative and
null results, is retained. Bootstrap intervals use 5000 hierarchical draws.

For reproduction, run from the recorded code revision with a fresh output
directory outside the worktree:

```sh
uv run python -m scientific_parallax.discovery.mechanism_audit \
  --config configs/experiments/mechanism-audit-validation-v1.json \
  --output /absolute/path/to/new-audit-output
```

A reproduction of these now-public seeds is not a new unseen validation.
