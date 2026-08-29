# Protocol Freeze local self-audit record

Status: candidate for local single-account Protocol Freeze. Independent review
and custody are explicitly waived; this record must not be represented as an
independent approval.

## Frozen candidate identity

- Protocol ID: `protocol-dry-run-v1`
- Assurance mode: `local_single_account_self_audit`
- Protocol hash: updated after the next runner digest is pinned
- Confirmatory runner: updated after runner `0.3.5` is published
- Runner platforms: Linux amd64 and Linux arm64
- External validation source SHA-256:
  `b22d51b7f1b33743934b608d94f845f458dd480fac4ee981cc516fb9170ff4e9`

Primary evidence:

- [`experiment-protocol.md`](experiment-protocol.md)
- [`protocol-freeze-checklist.md`](protocol-freeze-checklist.md)
- [`decision-log.md`](decision-log.md)
- [`../artifacts/protocol/reviewed-dry-run.md`](../artifacts/protocol/reviewed-dry-run.md)
- [`../artifacts/external-data/reviewed-the-well-validation.md`](../artifacts/external-data/reviewed-the-well-validation.md)
- [`../configs/experiments/protocol-dry-run.json`](../configs/experiments/protocol-dry-run.json)

## Self-audited decisions

| Item | Accepted decision | Evidence and limitation |
|---|---|---|
| Statistical design | 30 tasks; 95% lower bound above 20%; 30% detectable alternative | Simulated power 0.00, 0.90, 1.00 at 20%, 30%, 40%; no independent statistical review |
| Numerical gates | Mean ≤0.005, max ≤0.08, summary L2 ≤0.015 | Six local clusters and 20 external trajectories; author-reviewed only |
| Survival policy | Dormant after 2; dead after 4 or a hard contradiction | Executable tests and protocol binding |
| Viability and niches | Gain ≥0.01, decoder cost ≤1.0; three niches of capacity 4 | Development rationale only |
| Generator grammar | Four mutation types; 32 attempts; 128 candidates | Deterministic and shared by treatment/control |
| Accounting | Charge attempts, uncached evaluations, completed queries | Executable ledger and fixed ceilings |
| Custody | Same account, repository-external write-once bundle | Prevents accidents; cannot prevent deliberate local access |

Any change to a hashed component requires a new protocol hash and, for code or
runtime changes, a newly published runner. Gate PF can close only after the
local final-world verification summary is recorded against those final
identities.
