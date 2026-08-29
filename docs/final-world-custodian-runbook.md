# Final-world custodian runbook

Status: instructions for an external custodian. Do not generate or place final
world bytes in this repository or in a directory visible during development.

## Separation of duties

The custodian should be a person or service separate from strategy development.
They receive the frozen protocol hash and final-task generation specification,
create the task instances under a separately controlled external root, and
return only the commitment record. Developers must not receive task seeds,
world bytes, hidden labels, or previews before the one-shot evaluation.

Current protocol hash:
`41b8229b388e2fb9f0345c7d15fd8a33746c94cd31a103393a692e10a969548b`.

## Gate PF world commitment

At Gate PF, before Step 4 strategy development, the custodian creates the final
task files and a deterministic manifest of every relative path, byte count, and
SHA-256. Hash that manifest as `world_hash`, then place this record alongside
the inaccessible world files:

```json
{
  "schema_version": 2,
  "protocol_hash": "41b8229b388e2fb9f0345c7d15fd8a33746c94cd31a103393a692e10a969548b",
  "world_hash": "<lowercase SHA-256 of the deterministic world manifest>"
}
```

The external root must not be equal to or nested beneath the development
repository. Access should be denied to the development process until the final
evaluation ceremony. The custodian retains the unhashed manifest privately so
the evaluated bytes can later be checked against `world_hash`.

## Later strategy freeze

After Steps 4–7 are complete, but before final-world access, freeze the exact
strategy source/configuration hash. Create `strategy-freeze.json` in the
external root:

```json
{
  "schema_version": 1,
  "protocol_hash": "41b8229b388e2fb9f0345c7d15fd8a33746c94cd31a103393a692e10a969548b",
  "strategy_hash": "<frozen strategy SHA-256>",
  "world_commitment_hash": "<canonical content hash of commitment.json>"
}
```

The strategy-freeze record binds a future strategy to the world already sealed
at Gate PF; it does not permit regenerating or changing that world.

## One-shot opening

The evaluator verifies both records before writing `access-log.json` with
exclusive-create semantics. It writes the access record before reading final
evidence, then writes `result.json` exactly once. A missing, mismatched, or
modified commitment; repeated access; or strategy mismatch must stop the run.

The custodian should retain the final directory, permissions audit, commitment,
strategy freeze, access log, result, and runner digest as one immutable evidence
bundle. If any pre-access integrity check fails, do not repair the bundle in
place; record the failure and return to Protocol Freeze review.
