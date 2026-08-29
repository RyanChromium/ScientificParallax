# Protocol Freeze independent review packet

Status: candidate for independent review; this document is not an approval and
does not execute Gate PF.

## Frozen candidate identity

- Protocol ID: `protocol-dry-run-v1`
- Protocol hash:
  `8a28aeae581f0e7d2820bddc590cfef63f0f4e0ab103b408d3a30749558ffb29`
- Confirmatory runner:
  `ghcr.io/ryanchromium/scientific-parallax-confirmatory@sha256:56080a851d6dba6ea2008e6e441d29bcec2e72e4e06f3e6a9331dbcf56a13348`
- Runner platforms: Linux amd64 and Linux arm64
- Runner source revision: `e51f9272ada5346daa22b4fe9ff6c285b0480ddc`
- External validation source SHA-256:
  `b22d51b7f1b33743934b608d94f845f458dd480fac4ee981cc516fb9170ff4e9`

Primary evidence for review:

- [`experiment-protocol.md`](experiment-protocol.md)
- [`protocol-freeze-checklist.md`](protocol-freeze-checklist.md)
- [`decision-log.md`](decision-log.md)
- [`../artifacts/protocol/reviewed-dry-run.md`](../artifacts/protocol/reviewed-dry-run.md)
- [`../artifacts/external-data/reviewed-the-well-validation.md`](../artifacts/external-data/reviewed-the-well-validation.md)
- [`../configs/experiments/protocol-dry-run.json`](../configs/experiments/protocol-dry-run.json)

## Decisions requiring an independent reviewer

The reviewer should mark each item `accept`, `revise`, or `reject`, and provide
a reason that can be evaluated without reference to final-world outcomes.

| Review item | Candidate decision | Evidence to challenge |
|---|---|---|
| Statistical design | 30 tasks; success requires the 95% lower bound above 20%; 30% is the detectable alternative | Simulated power is 0.00, 0.90, and 1.00 at true effects 20%, 30%, and 40% |
| Numerical gates | Mean absolute difference ≤0.005, max difference ≤0.08, summary L2 ≤0.015 | Six-cluster local checks and 20-trajectory external validation |
| Survival policy | Dormant after 2 sub-viability checkpoints; dead after 4 or one hard contradiction | Executable transition tests and protocol hash binding |
| Viability and niches | Predictive gain ≥0.01, decoder cost ≤1.0; three niches of capacity 4 | Candidate diversity and resource-allocation rationale |
| Generator grammar | Four finite mutation types, 32 attempts per parent, 128 candidates per task | Determinism, finiteness, and equal treatment/control access |
| Accounting | Charge attempted mutations, uncached evaluations, completed world queries; cache hits cost zero | Executable ledger exercise and CPU/query ceilings |

Any requested change to a hashed component prevents approval of this protocol
hash. The change must receive an ADR, a new protocol hash, a new runner when
code changes, and a fresh review packet before Gate PF.

## Reviewer record

The independent record should contain:

- reviewer name and affiliation;
- relationship or conflicts with the project;
- review date;
- exact protocol hash and runner digest above;
- one decision and rationale for every row;
- overall decision: `accept`, `revise`, or `reject`;
- signature or independently verifiable account identity.

Only an unconditional `accept` for every row can satisfy the independent-review
blocker. Project-authored self-review cannot fill this role.
