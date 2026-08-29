# Reviewed Step 7 blinded development challenge

The clean canonical run at revision
`6c1df312d36c574d100b2c4ec09ebe0bd6c7d68c` completed all 240 preregistered
arm-task runs: eight treatment/baseline/ablation arms across six measurement
strata and five seeds per stratum. All 11 mechanism and validation checks passed.

The unique primary comparison returned:

- co-evolution restricted mean stable-identification time: `1.0` query;
- matched Bayesian optimal design time: `1.0` query;
- relative query reduction: `0.0`;
- stratified bootstrap 95% interval: `[0.0, 0.0]`;
- minimum meaningful effect: `0.20`;
- preregistered decision: **`stop`**.

All five leave-one-seed-index-out analyses independently returned `stop`.
Every primary-treatment task reached a final truth rank of 1, and the conclusion
covered all clean, mixed, partial-channel, downsampled, noisy, and
masked-reflecting conditions.

The executed questions were genuinely discriminating: every treatment run had
positive predicted disagreement and at least one positive realized information
gain. Nevertheless, question strategy could not improve the top-five endpoint
because the true class was already explicitly present in the founder pool. The
endpoint was effectively saturated by all active approaches.

The independent novelty check found no new state variables. This is not a failed
validator: the frozen Gate-PF grammar cannot change the number of state variables,
so a positive new-variable claim is structurally unreachable in this protocol.

Resource ceilings were respected. The 240 runs used 1,920 world queries, 8,886
candidate generation attempts, 63,800 uncached candidate evaluations, and
415,030 cache hits. The largest single run used 43/128 generation attempts and
320/4,096 candidate evaluations. Total simulated work was 336,486,400 stencil
updates.

Reproducibility identities:

- preregistration/config hash:
  `ca64745074cd69d16a2f510997a48323278d60021eb1754edea7f35f55b0b7e8`;
- candidate-generator hash:
  `f6842002c59c21a5c4c944491e78a93f3b9d2c3a23702b5f7f7a6c3325f915fc`;
- report content hash:
  `9b7c0afc134aef167baec16ff88a49f02b3b6d8062b129189bd6ce340f253ede`;
- report file SHA-256:
  `e9627305d4ab6a90eaecf89cad540643f642c7956509e5ac75314bb1ac93bb8a`;
- task-results file SHA-256:
  `3a32b29c5b0b15351c2965c07376ff66517e1a10eb0d02d6935ee0dcf028ef59`;
- run-manifest hash:
  `60add6d2ae33662ea4f21f548badd733fbaa146e074dc1a60ea4f1cac3a8d6af`;
- manifest file SHA-256:
  `fef3286098db995946eeb066c86e509151add635b3bbec37f0a11c4e68812edd`.

The final sealed world was not opened. `strategy-freeze.json`, `access-log.json`,
and `result.json` remain absent. Per the frozen Step 7 rule, this `stop` decision
forbids strategy freeze and automatic progression to Step 8. Any repair must be
a newly named protocol and final-world commitment, not a post-result edit to this
challenge.
