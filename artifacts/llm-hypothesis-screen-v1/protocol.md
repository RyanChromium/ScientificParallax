# LLM-proposed memory discrimination protocol

Frozen before querying the development world on 2026-09-01. This is a local development
decision, not a confirmatory protocol.

## Fixed input

- Use the exact three proposals in `../llm-hypothesis-screen-v0/response.json`.
- Use the positive-case parameters in `../llm-hypothesis-screen-v0/evaluation.json` without
  refitting after the new observation.
- Primary contrast: `latent-activation-memory` versus `saturating-v-removal`, the best state-free
  proposal in v0.
- Also score `superquadratic-autocatalysis` and the fitted two-field baseline, but do not use them
  to select the experiment.

## Public intervention pool

Enumerate the Cartesian product of:

- initial pattern: `center_square`, `two_spots`, `stripe`;
- boundary: `periodic`, `reflecting`;
- `(feed, kill)`: `(0.020, 0.052)`, `(0.035, 0.060)`, `(0.046, 0.064)`;
- pulse schedule over 60 steps on a 12-by-12 grid:
  1. no pulse;
  2. one center pulse at step 12, radius 2, delta-v 0.24;
  3. one center pulse at step 36, radius 2, delta-v 0.24;
  4. two center pulses at steps 12 and 24, each radius 2 and delta-v 0.17;
  5. two center pulses at steps 12 and 42, each radius 2 and delta-v 0.17;
  6. one broad center pulse at step 12, radius 3 and delta-v 0.12.

Use initial seed `940000`, sample every 12 steps, identity measurement, and no measurement noise
for candidate predictions. No true-world observation may be used during selection.

For each condition, compare the two candidates' visible summary vectors. Standardize the four
features `(mean, standard deviation, high fraction, gradient energy)` by
`(0.05, 0.05, 0.05, 0.01)`, repeated across fields and times. Select the condition with greatest
root-mean-square standardized disagreement; break exact ties by the serialized condition ID.

Before observing the development world, record the complete pool definition, selected condition,
both committed prediction vectors, their hashes, fitted-parameter hashes, and the design score.

## Frozen decision

After selection, query the existing first positive development world once with measurement noise
standard deviation `0.004`, measurement seed `920000`, and the selected intervention. Compute the
same visible summary RMSE for all four candidates.

Continue the narrow claim that an LLM-proposed memory structure is worth a multi-case recovery
study only if its RMSE is at least 10% lower than both the state-free `saturating-v-removal`
proposal and the fitted two-field baseline. Otherwise stop the “LLM recovered Z” route and retain
the result only as evidence that an LLM can generate executable competing hypotheses.

No threshold, candidate, fitted parameter, experiment-pool member, or primary contrast may be
changed after the true observation is generated. A numerical failure or protocol mismatch is an
engineering failure, not evidence for either mechanism.
