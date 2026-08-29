# Step 7 blinded Gray–Scott development challenge

Status: the preregistered development challenge completed with a **stop**
decision. The co-evolution treatment did not beat its matched Bayesian optimal
design control on the unique primary endpoint. Under the frozen decision rule,
the project must not create a strategy freeze, open the sealed final world, or
advance automatically to Step 8.

This is a scientifically informative negative result under local single-account
self-audit. It is not independent confirmation and it is not final-world
evidence.

## Preregistered design

The committed development configuration fixes six measurement-shift strata and
five fresh initial/measurement seeds per stratum. Every arm runs all 30 tasks.
Each run has the same ceiling of eight world queries, 128 attempted candidate
mutations, and 4,096 uncached candidate-question evaluations.

The unique primary endpoint is the first query at which the true structural
equivalence class enters the external-evidence top five and remains there for
five checkpoints. Unidentified runs are right-censored at eight queries. The
primary effect is the relative reduction in restricted mean identification time,
with a 95% stratified bootstrap interval and a minimum meaningful effect of 20%.

The three-way decision is fixed:

- `go` only if the interval lower bound is strictly above 20%;
- `redo` only if the interval contains 20%, with at most one newly preregistered rerun;
- `stop` if the interval upper bound is strictly below 20%.

The primary comparison is co-evolution against a matched Bayesian optimal design
arm. Both use the same frozen candidate generator, initial candidate set,
evidence update, candidate niches, and resource ceilings. The control replaces
evolving question ecology with standard expected-information-gain selection from
a fixed finite question pool.

The complete comparison set also contains random selection, passive coverage,
fixed-candidate co-evolution, no question evolution, no representation mutation,
and no niches.

## Blinding boundary

The development evaluator applies three levels of semantic hiding:

1. state variables are anonymous `x0` and `x1`, while observations expose only
   anonymous `field_0` and `field_1` channels;
2. measurement-cluster labels and truth-equivalence membership remain in the
   evaluator-only task object;
3. task and measurement seeds never enter the selector. Its question diagnostic
   contains only an opaque question hash, expected information gain, predicted
   disagreement, and cost.

Truth ranking is implemented in a separate evaluator-owned scorer. It uses an
anonymous, task-fixed tie break that is identical across experimental arms. The
selector cannot request or inspect truth rank.

## Result

Both primary arms identified the true class on all 30 tasks. Both had a restricted
mean identification time of exactly 1.0 query. The estimated relative reduction
was 0.0, with a 95% bootstrap interval of `[0.0, 0.0]`. This is unambiguously below
the preregistered 20% threshold, so the decision is `stop`, not `redo`.

| Arm | Identified | Restricted mean queries | Mean final truth posterior | Mean actual IG |
|---|---:|---:|---:|---:|
| Co-evolution | 30/30 | 1.0000 | 0.8423 | 0.3705 |
| Bayesian optimal design | 30/30 | 1.0000 | 0.8203 | 0.3582 |
| Random | 30/30 | 1.0000 | 0.7186 | 0.3308 |
| Passive coverage | 30/30 | 1.0333 | 0.7650 | 0.3426 |
| Fixed-candidate co-evolution | 30/30 | 1.0000 | 0.9035 | 0.3471 |
| No question evolution | 30/30 | 1.0000 | 0.8401 | 0.3714 |
| No representation mutation | 30/30 | 1.0000 | 0.7221 | 0.3260 |
| No niches | 30/30 | 1.0000 | 0.8357 | 0.3691 |

Every leave-one-seed-index-out analysis also returned `stop`. The treatment's
median final truth rank was 1 in each of the six measurement strata. Executed
questions had positive predicted disagreement and positive realized information
gain, so the failure is not that questions were inert. They simply did not
improve the preregistered identification endpoint relative to the matched
control.

## Diagnosed failure modes

The main endpoint is saturated by construction. The known true structural class
is explicitly present in every founder candidate pool. A top-five endpoint can
therefore be satisfied before question strategies have room to separate, even
though later posterior concentration differs.

The frozen Gate-PF mutation grammar also preserves exactly two state variables.
It can remove terms, perturb coefficients, or add decay terms, but cannot add a
state variable. The challenge consequently proposed zero novel variables, and
independent cross-condition validation of a new variable is not applicable. A
positive novel-variable claim is unreachable under this grammar.

These are protocol-design findings, not permission to change the endpoint after
seeing the result. Repair would require a new protocol version, a new Gate PF,
and a newly committed final world whose primary endpoint is not trivially
satisfied by the initial pool. The current frozen final world cannot be reused
for that amended claim.

## Resource and reproducibility boundary

Across 240 runs, the challenge charged 1,920 world queries, 8,886 candidate
generation attempts, 63,800 uncached candidate evaluations, and 415,030 cache
hits. Candidate predictions plus world observations represented 336,486,400
stencil updates, or approximately 0.00391 projected CPU hours at the recorded
published-runner calibration rate.

The canonical run was made from clean revision
`6c1df312d36c574d100b2c4ec09ebe0bd6c7d68c`. All implementation checks passed,
the selector-input hardening produced the same numerical report as the first
run, and the final-world `strategy-freeze.json`, `access-log.json`, and
`result.json` remain absent.

Run the development challenge with:

```bash
uv run scientific-parallax step7 run \
  --config configs/experiments/step7-blind-development.json \
  --output artifacts/step7/run-6c1df31
```
