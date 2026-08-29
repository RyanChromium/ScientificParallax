# Protocol Freeze local self-audit record

Status: accepted and frozen under local single-account self-audit. Independent
review and custody are explicitly waived; this record is not an independent
approval.

## Frozen candidate identity

- Protocol ID: `protocol-dry-run-v1`
- Assurance mode: `local_single_account_self_audit`
- Protocol hash:
  `0c4685639302f4db81fc2c752911d0b7f70bfb8937e0aa2a55a3fc5bd2a8d892`
- Confirmatory runner:
  `ghcr.io/ryanchromium/scientific-parallax-confirmatory@sha256:1b99d310dfa0fe98019489d00763ec3321676ba86384ac2c6eb78979d0c6533f`
- Runner source revision: `78a59bf68c58c592d30bcf8aeb2f145ecb347cfc`
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

The local final-world verification summary is recorded in
`../artifacts/protocol/gate-pf-local-v1.json`. Any change to a hashed component
requires a new protocol hash and, for code or runtime changes, a newly
published runner and a newly named final-world bundle.
