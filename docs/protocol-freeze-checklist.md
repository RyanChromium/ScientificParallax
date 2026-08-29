# Protocol Freeze review checklist

Step 3.5 and the local pre-freeze hardening pass are implemented. The expanded
synthetic dry-run passes all current checks. Gate PF has **not** been executed.

## Resolved locally

- [x] The top-`k`, five-checkpoint primary endpoint is executable.
- [x] Six parameter/measurement clusters and 30 tasks are content-hashed.
- [x] Power is simulated at 20%, 30%, and 40% alternatives; the candidate
  design has 0.90 estimated power at its 30% detectable alternative.
- [x] Development-only noise calibration and positive floor are executable.
- [x] Numerical tolerances are checked across all six full-size clusters.
- [x] The reference path uses a separately implemented RK4 integrator.
- [x] Numeric survival thresholds, viability gates, and niche capacities are
  included in the protocol hash.
- [x] A deterministic finite generator is shared by treatment and H2 control.
- [x] Query, mutation-attempt, uncached-evaluation, and cache-hit accounting is
  executable and included in the protocol hash.
- [x] The actual frozen 30-task mix is microbenchmarked locally.
- [x] Manifests, ledgers, Paradigm IR, and reports have schema-v1 boundaries.
- [x] Interrupted Gray–Scott ledger recovery is integration-tested.
- [x] A final evaluator enforces an external root and exclusive one-shot access
  and result records.
- [x] Official The Well test-shard metadata, sizes, license, revision, and
  SHA-256 identities are pinned in a validated manifest.
- [x] One pinned 2.65 GB The Well gliders shard was downloaded outside Git and
  matched its declared byte count and SHA-256.
- [x] A deterministic 16 KB CC-BY-4.0 fixture with source attribution and
  modification metadata is committed and checked in CI.
- [x] All 20 external trajectories passed the frozen one-interval numerical
  validation: reference RMSE `0.01717`, worst-trajectory RMSE `0.03548`, and
  51.1% improvement over the primary method.
- [x] The Python base-image digest, NumPy version, and Linux amd64/arm64 wheel
  hashes are pinned; a local arm64 candidate was built and profiled.
- [x] A tag-triggered, commit-pinned GitHub Actions workflow can publish the
  exact multi-platform runner and emit a public machine-readable digest record.
- [x] Runner `0.3.3` is published for Linux amd64/arm64, its OCI-index digest is
  pinned, and the frozen task mix was profiled from the published digest.

## Remaining Gate PF blockers

- [ ] Independently accept or revise the statistical design: a true 30%
  reduction has estimated power 0.90, while an effect exactly at the 20% null
  boundary is not expected to pass a lower-confidence-limit-above-20% test.
- [ ] Define and generate final sealed task instances outside the repository,
  create their commitment, and provision the external access directory.
- [ ] Obtain independent review of the numerical tolerances, survival values,
  niche capacities, generator grammar, and exact budget-accounting language.

Until every unchecked item is resolved, the correct status is **ready for
Protocol Freeze review**, not frozen and not ready for final-world access.
