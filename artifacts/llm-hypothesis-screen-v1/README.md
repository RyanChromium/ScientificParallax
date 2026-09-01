# LLM memory-discrimination result

Date: 2026-09-01. Decision: **stop the “LLM recovered Z” route**.

The protocol in `protocol.md` was written before the development-world observation. It fixed the
v0 LLM response and fitted parameters, named the LLM's memory field and its best state-free rival
as the primary contrast, enumerated 108 allowed interventions, and required the memory model to
beat both the rival and baseline by at least 10% RMSE.

Candidate predictions alone selected `design-034`: a reflecting, high-feed/high-kill condition
with two center pulses at steps 12 and 42. `run/design-commitment.json` records the selected
condition and prediction hashes before `run/result.json` records the observation.

## Result

| Frozen candidate | Added states | Selected-intervention RMSE |
|---|---:|---:|
| saturating removal | 0 | 0.115293 |
| LLM memory field `w` | 1 | 0.130194 |
| cubic autocatalysis | 0 | 0.132686 |
| fitted two-field baseline | 0 | 0.137260 |

The memory candidate improved on the baseline by 5.15%, below the required 10%. More decisively,
it was 12.92% worse than the state-free saturating-removal proposal. The frozen decision is
`stop_llm_recovered_z_route`.

## What remains true

The isolated LLM independently generated a qualitative memory mechanism from anonymous residual
summaries, and all three proposed models were safe to compile and test. The candidate set also
contained a state-free explanation that outperformed the memory proposal on both the original
held-out screen and this candidate-designed intervention.

That is evidence for a hypothesis-generation capability, not recovery of a unique mechanism. The
LLM did not reproduce spatial diffusion in the withheld state, its memory candidate was not the
best predictor, and a single local development intervention provides no general error guarantee.

No additional tuning, prompt rerun, threshold change, or new Z-recovery test is licensed by this
result. A future project may compare LLM-generated candidate diversity against random symbolic
generation and published model-discovery systems, but generic LLM hypothesis generation is
already a crowded research area and cannot be treated as novel without a separate literature
gap.
