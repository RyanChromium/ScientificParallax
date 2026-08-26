# Protocol Freeze review checklist

Step 3.5 is implemented and its synthetic dry-run passes. Gate PF has **not**
been executed. The following items remain blockers before freezing a
confirmatory Gray–Scott protocol.

## Scientific blockers

- Define and generate final sealed Gray–Scott task clusters outside normal
  development paths.
- Replace the development-only posterior-0.95 diagnostic with the declared
  top-`k`, five-checkpoint primary endpoint used by the frozen protocol.
- Complete power analysis for six parameter/measurement clusters and 30 tasks.
- Calibrate likelihood noise on designated development residuals without using
  final tasks.
- Freeze numerical tolerances for five-point versus nine-point solver checks.
- Add a separately implemented time integrator before treating the reference
  solver as high-independence numerical replication.
- Obtain and checksum a licensed The Well Gray–Scott development shard. The
  offline adapter exists, but no external shard is currently downloaded or
  claimed as validated.

## Protocol blockers

- Turn Paradigm IR v0.1 strings for viability thresholds and niche capacities
  into reviewed numeric values.
- Freeze the exact candidate generator shared by treatment and the H2 Bayesian
  design control; it does not exist yet because candidate evolution starts in
  Step 4.
- Freeze measurement-cluster definitions used by stratified bootstrap.
- Freeze candidate and question evaluation accounting, including cache hits.
- Re-profile the actual frozen candidate mix rather than relying on the Step 3
  microbenchmark projection.
- Store the final evaluator and access log outside ordinary development code.

## Engineering blockers

- Add schema migration policy for manifests, ledgers, Paradigm IR, and reports.
- Add interrupted-run recovery tests for Gray–Scott ledgers.
- Add a small licensed external-data fixture to CI without downloading a large
  dataset during tests.
- Pin the execution environment used for confirmatory runs beyond the current
  lockfile and environment manifest.

Passing the current dry-run means these decisions can now be reviewed and made
explicitly. It does not mean they have already been resolved.
