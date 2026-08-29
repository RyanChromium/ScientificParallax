# Reviewed Protocol v2 latent-discovery result

Protocol v2 produced a scientifically meaningful mixed result under local
single-account self-audit. It supports a narrow representation-discovery and
structural-niche claim, while rejecting the proposed advantage of question
co-evolution over matched Bayesian optimal design.

## Why this test differs from Step 7 v1

Every ordinary founder was deliberately structurally wrong: all contained only
the two visible states. A successful model had to acquire an unobserved state,
connect the visible field to it, and connect the latent state back to the visible
reaction in three separately recorded mutations. The first two changes were a
neutral bridge with exactly the same visible predictions as their parent.

The one-shot world contained 20 latent tasks from four parameter combinations
not used as pilot clusters and 30 no-latent controls. Three intervention
conditions per task were held outside question selection and used only by the
independent evaluator. The old v1 final world was not opened.

## Confirmatory decisions

| Hypothesis | Confirmatory result | Decision |
|---|---:|---|
| H3: recover and validate withheld latent structure | 20/20 tasks | `go` |
| H1: niches preserve the neutral structural bridge | 20/20 vs 4/20 | supported |
| H2: question co-evolution beats matched Bayesian design | 4.5 vs 4.5 queries | rejected |

For H3, the one-sided 95% lower bound on task success was `0.880842`, above the
predeclared `0.80` threshold. Mean held-out intervention improvement over the
oracle-best generated two-state model was `0.644371`; its 95% stratified
bootstrap interval was `[0.546245, 0.730477]`, wholly above the `0.20` margin.
All 20 successful candidates had the required three-operation lineage.

The treatment produced zero latent discoveries in 30 no-latent worlds. The
one-sided 95% Wilson upper bound was `0.082724`, below the predeclared `0.10`
false-positive ceiling.

The no-niches ablation succeeded on only 4/20 latent tasks. The paired absolute
success-rate difference was `0.80`, with a stratified bootstrap interval of
`[0.40, 1.00]`. Fixed-representation Bayesian design succeeded on 0/20 tasks,
showing that parameter adjustment alone could not satisfy the structural and
held-out intervention endpoint.

H2 did not pass. Co-evolution and matched Bayesian design both required a
restricted mean of `4.5` queries. Relative reduction was `0.0`, with a 95%
interval of `[-0.115441, 0.093750]`, which does not clear the registered `0.10`
margin. Random and passive questions also recovered all 20 latent tasks. No claim
of question-coevolution superiority is permitted.

## Resource and integrity audit

The evaluator completed 170 arm-task runs and charged 2,040 world queries,
16,680 candidate-generation attempts, 103,129 uncached candidate evaluations,
and 1,665,818 cache hits. It separately reported 6,234 hidden-validation
evaluations. Every run used all 12 world queries. The largest single run used
108/128 generation attempts and 794/4,096 candidate evaluations.

All 11 implementation and boundary checks passed. The task-results file contains
170 unique arm-task pairs, 20/20 treatment latent successes, 0/30 treatment null
false positives, and zero malformed successful lineages.

## Reproducibility identities

- frozen code revision:
  `40841cbc330f0ff5aabb8c22b22b71b271e5b0b6`;
- confirmatory config hash:
  `1f014226c37f137014de599b8e8fc1ebeb3ace1b6b82b3b172a22efcc69eb8cd`;
- strategy hash:
  `7d8745844e28b2c8a344a3fe4de576bc74d6af48c3da4fa0e36f1df5af11ce34`;
- strategy-freeze content hash:
  `639ee53af589eb581b61fc5955da41780f595e322ea6a849a029faa5e6ecf7b7`;
- world hash:
  `825912334812797f84b8471f24a11aec55fea7a4912fae2ac4a19e687ab2f2c2`;
- world commitment content hash:
  `b1a7e3ed4dd50399ffe75958ade5fbb0499b2398ae14d67782c2f4aeea86b85e`;
- report content hash:
  `979596aa2af4eb0c9ce6d25674a3006ec488c920c4f506a4eb58cc8233049d36`;
- task-results file SHA-256:
  `c625f50db6d9af62af5fb6be50e7ddf7048f75bbe4a207538e67b20af906dfd3`;
- copied result-record file SHA-256:
  `10fcb7f8d9bac9436c86a94b617631da3ab05d3836ccd9141119616073c3cbfa`.

## Claim boundary

This is controlled recovery of a withheld structural class in a synthetic world,
not discovery of a new natural law. The mutation grammar explicitly permits
adding and connecting a latent state, although no ordinary founder contains that
state and success requires a three-generation lineage plus unseen-intervention
validation. The evidence supports the importance of structural diversity and
neutral-bridge retention. It does not support the stronger claim that evolving
questions are more efficient than matched Bayesian design.

The result was generated and reviewed by one local account. It has cryptographic
commitment and one-shot access enforcement but no independent custodian or
independent reproduction.
