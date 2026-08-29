# Protocol v2 draft: latent-state discovery under structural misspecification

Status: development-pilot protocol. It is deliberately separate from the
completed Step 7 v1 stop decision. Pilot runs may change strategy details, but
only on declared development tasks. No v2 confirmatory result may be claimed
until the implementation and thresholds are frozen and a newly generated test
bundle is opened exactly once.

## Scientific question

Can a paradigm population whose every ordinary founder is structurally wrong
create a necessary latent dynamical state through traceable multi-step mutation,
retain the neutral intermediate structures long enough to connect them, and
validate the resulting mechanism on unseen interventions?

The primary v2 hypothesis is representation discovery, corresponding to H3 in
the research plan. The question-coevolution advantage over a matched Bayesian
optimal-design control remains an explicit comparative hypothesis, but it is not
allowed to substitute for successful latent-state recovery.

## Hidden world

The world extends the two visible Gray–Scott fields with an unobserved catalyst
`z`:

```text
du/dt = D_u Laplacian(u) - (1 + gamma z) u v^2 + f (1 - u)
dv/dt = D_v Laplacian(v) + (1 + gamma z) u v^2 - (f + k) v
dz/dt = D_z Laplacian(z) + alpha v - beta z
```

Only anonymous mixtures of `u` and `v` are measured. `z` is never returned by
the world. Local pulses perturb the visible `v` field; the hidden state retains
a delayed memory of this history and changes later visible dynamics.

Development tasks vary the latent drive, decay, feedback strength, initial
condition, measurement noise, and pulse history. Separate no-latent worlds use
the same interface and act as false-discovery controls.

## Structurally wrong founders and neutral bridge

All ordinary founders are two-state models. They differ only in a fixed reaction
coefficient and cannot represent delayed latent feedback. The oracle arm is
reported separately and is never included in the ordinary-founder claim.

A complete latent loop requires three distinct mutations:

1. `add_latent_state` creates an unconnected state;
2. `connect_observed_drive` lets the visible field drive it;
3. `connect_reaction_feedback` connects it back to the visible reaction.

The first two steps have exactly the same visible predictions as their parent.
They therefore cannot survive by immediate predictive gain alone. A structural
niche must retain this neutral bridge long enough for the third mutation to make
the representation empirically testable. Parameter changes may occur before or
after these operations, but the three structural events must appear in this
order in the recorded lineage.

## Questions and held-out validation

Executable questions vary pulse timing and strength, add a second pulse, shift
feed or kill parameters, change initial families and boundaries, or extend the
observation duration. Co-evolution begins with three seed questions and replaces
executed questions with descendants, so mutations can compose over multiple
generations. The matched Bayesian arm receives a fixed one-generation question
library and selects by expected information gain.

Question selectors receive only opaque question hashes and preregistered
diagnostics. They do not receive task truth, latent parameters, measurement
seeds, complete experiment objects, or held-out outcomes.

Three disjoint validation interventions per task are never eligible for a world
query. At each checkpoint an evaluator selects the highest-posterior complete
latent candidate, measures its validation RMSE, and compares it against the
oracle-best generated two-state model. Validation computation is reported
separately and cannot affect candidate or question selection.

## Pilot success and failure criteria

A task reaches the latent-discovery endpoint only when both conditions hold for
three consecutive checkpoints:

- posterior mass of the complete three-stage structural class is at least 0.60;
- its selected candidate improves unseen-intervention RMSE over the best
  two-state candidate by at least 20%.

The development capability gate requires:

- at least 80% task success across four latent-parameter clusters;
- the lower 95% stratified-bootstrap bound on held-out improvement to exceed 20%;
- a no-latent false-positive rate no greater than 10%;
- every successful ordinary structure to have a valid multi-step lineage.

The comparative H2 gate asks whether co-evolution reduces restricted mean
discovery queries by at least 10% relative to matched Bayesian design, with the
lower 95% confidence bound above that margin. Failure of H2 must be reported as
a negative result even when the H3 capability gate passes.

## Comparison set

The pilot runs seven arms under the same world-query ceiling:

- paradigm-question co-evolution;
- matched Bayesian optimal design with the same candidate generator and niches;
- random questions;
- passive coverage;
- fixed-representation Bayesian design;
- co-evolution without structural niches;
- an oracle-structure Bayesian ceiling.

Candidate generation attempts, uncached candidate-question evaluations, cache
hits, world queries, and independent validation evaluations are separate
counters.

## Freeze boundary

The old v1 sealed world remains untouched and cannot validate this new claim.
After pilot iteration ends, v2 requires a committed strategy hash, immutable
thresholds, new hidden seeds, and a new sealed test bundle outside the repository.
Changing the world, grammar, endpoint, or thresholds after that bundle is opened
would invalidate the result.
