# Local final-world sealing runbook

Status: procedure for the explicitly chosen
`local_single_account_self_audit` assurance mode. This mode preserves ordering,
hash integrity, and one-shot evaluation, but it does not provide independent
review or independent custody.

## Assurance boundary

The same local user develops the strategy and stores the final-world bundle.
The final directory must still be outside the repository. The tool does not
print hidden initial-state or measurement seeds, makes committed task files
read-only, and refuses to overwrite an existing bundle. These controls prevent
accidental preview, regeneration, and silent reuse; the local user can override
them and must not describe the resulting evidence as independently confirmed.

## Gate PF world commitment

After the final runner digest and protocol hash are fixed, but before Step 4
strategy development, run:

```bash
uv run scientific-parallax protocol seal-world \
  --config configs/experiments/protocol-dry-run.json \
  --output /Users/ran/ScientificParallax-FinalWorld-v1 \
  --development-root /Users/ran/Project/ScientificParallax \
  --acknowledge-local-self-audit
```

The generator draws a fresh 32-byte local secret, derives separate initial and
measurement seeds with HMAC-SHA-256, and writes 30 task descriptors. It does
not retain the secret. `manifest.json` binds every relative path, byte count,
and SHA-256; `commitment.json` binds the canonical manifest hash to the frozen
protocol and the local self-audit assurance mode.

Verify the result without printing task contents:

```bash
uv run scientific-parallax protocol verify-world \
  --root /Users/ran/ScientificParallax-FinalWorld-v1 \
  --protocol-hash <frozen-protocol-hash> \
  --development-root /Users/ran/Project/ScientificParallax
```

Keep only the verification summary and commitment in normal project records.
Do not inspect files below `tasks/` before the one-shot evaluation.

## Later strategy freeze

After Steps 4–7, freeze the exact strategy source/configuration hash and create
`strategy-freeze.json` in the final-world root:

```json
{
  "schema_version": 1,
  "protocol_hash": "<frozen protocol SHA-256>",
  "strategy_hash": "<frozen strategy SHA-256>",
  "world_commitment_hash": "<canonical content hash of commitment.json>"
}
```

The strategy-freeze record binds the future strategy to the already committed
world. Regenerating the world requires a new protocol run and must not replace
the existing directory.

## One-shot opening

The evaluator rehashes every committed task before creating `access-log.json`.
It then verifies the strategy-freeze record, writes the access record with
exclusive-create semantics, evaluates once, and writes `result.json` once. A
changed file, mismatched hash, repeated access, or different strategy stops the
run.

Retain the final directory, commitment, strategy freeze, access log, result,
protocol hash, and runner digest as one evidence bundle. If a pre-access check
fails, preserve the failed bundle and return to Protocol Freeze instead of
repairing it in place.
