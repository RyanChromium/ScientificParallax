# Evidence-grounded direction pilot v1

Status: **stopped after partial but insufficient evidence grounding**.

All four v1.1 responses passed the response schema and local cross-field
validation. Both full-evidence proposals cited the strongest late anomaly, and
both counterfactual proposals moved to an earlier, weaker spatial signature.

The operational results were:

| condition | replicate | intervention | response |
|---|---:|---|---|
| full | 1 | second-pulse amplitude | field_b mean at t60 |
| full | 2 | pulse lag | field_b mean at t60 |
| late anomaly ablated | 1 | radius at fixed total dose | field_b gradient energy at t60 |
| late anomaly ablated | 2 | radius at fixed total dose | field_b gradient energy at t48 |

This is evidence of coarse counterfactual sensitivity: removing the late surge
changed the selected causal theme from temporal pulse history to spatial pulse
geometry. It is not a pass. The two full-evidence calls did not select the same
intervention, so the preregistered reproducibility requirement failed and no
downstream experiment was run.

The failure also exposes an input-design error. v0 supplied research history but
no concrete anomaly; v1 supplied a concrete anomaly but omitted the negative
research history. Both full-evidence proposals therefore revived a memory/history
direction that the earlier frozen discrimination experiment had already stopped.
The next pilot must combine numerical evidence with explicit stopped-route
records. It must not weaken or retroactively rescore the v1 stability rule.

The first v1 launch is separately marked invalid because the output directory
did not exist. v1.1 repeated the unchanged scientific design after fixing only
that capture precondition. This history is retained in the two protocol files.
