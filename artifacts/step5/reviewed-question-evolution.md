# Reviewed Step 5 question-evolution control

The clean run at revision
`497b97896cd6ca17b316c9de50319648a9bf4a77` passed all 14 Step 5 mechanism
checks. A second run produced byte-identical `report.json`, `evidence.jsonl`, and
`question-lineage.jsonl`.

The control held eight paradigms fixed and evolved only executable questions.
Across two mutation generations it attempted 82 question generations, retained
64 unique semantic questions, performed 704 fixed-paradigm prediction evaluations,
and used 3 development-world queries. All ten configured mutation operators were
exercised. Eighteen semantic duplicates were removed before resource allocation.

The selected questions and information-gain audit were:

| Generation | Question | Expected IG | Actual IG | Actual − expected |
|---:|---|---:|---:|---:|
| 0 | `step5-seed-0` | 0.576098 | 0.257943 | -0.318155 |
| 1 | `step5-g1-step5-seed-0-08` | 0.412280 | 0.479735 | 0.067455 |
| 2 | `step5-g2-step5-g1-step5-seed-0-08-04` | 0.207776 | 0.220186 | 0.012410 |

The first realized gain being below its expectation is not a failed mechanism
check: expected information gain averages over the predictive mixture and
measurement noise, while actual gain records one realized observation. Preserving
this gap rather than hiding it is part of the Step 5 requirement.

The constructed two-model test selected the known separating experiment over an
outcome-identical experiment. Semantic aliases with different language were
collapsed, language-only novelty with zero predictive difference received no
resource, malformed experiments were rejected, and every descendant bound its
parent and child semantic hashes. Question objects contain no truth label,
observation, posterior, or update rule; the independent evidence engine accepts
only predictions and observations.

Reproducibility identities:

- report file SHA-256:
  `6aeabb0f30dd87e54db4848ec1a9f374dbd1f5b2aa87a70ba3c547f0f52c328c`;
- report content hash:
  `0ad01a61888efab3dade1f68686a9bff5fe6323cce3d1220184e99bcd8828fdf`;
- run-manifest hash:
  `e9f8009ae492407c937ab55125b075718b21ab452f303fe87245614750ac2395`;
- evidence-ledger file SHA-256:
  `b233070526c409787bdff497f00fc14f2b166c0e743649ce7ceb3108ab41183f`;
- final evidence event hash:
  `e6459e850de19141a7989b1a7ea647e0a9375ea7f7b60217b9c3285d067b6ea9`;
- question-lineage file SHA-256:
  `ff40af24c61bc5fe16102f856eab589b1626d701ae6b79fc3bb03e067664886b`;
- final lineage event hash:
  `ea764b91ac44e72b638d123b3657f8d991f03a52baa8621de82c60d520493817`.

After the run, the local final-world commitment was reverified at protocol hash
`0c4685639302f4db81fc2c752911d0b7f70bfb8937e0aa2a55a3fc5bd2a8d892`.
Its 30-task world and commitment hashes remain unchanged, and no strategy freeze,
access log, or result exists.

Status: **Step 5 initial exit criteria satisfied in the development-only fixed-
paradigm control**. This is not final-world evidence and does not yet implement
the Step 6 two-population scheduler.
