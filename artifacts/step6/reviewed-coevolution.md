# Reviewed Step 6 co-evolution control

The clean run at revision
`097d9f654a530b394c5b145cb3302ae6a8d9653c` passed all 22 Step 6 mechanism
checks. A separate interrupted-after-round-zero run resumed from its immutable
checkpoint and produced byte-identical `report.json`, evidence, paradigm lineage,
question lineage, and scheduler ledgers.

The scheduler completed four budget-driven rounds. It charged 4 development-world
queries, 120 attempted frozen paradigm mutations, 846 uncached candidate-question
or fixed-probe evaluations, and 1,212 cache hits. Question evolution made 93
generation attempts and retained 82 unique executable experiments.

The round summaries were:

| Round | Selected question niche | Active | Dormant | Fossils | Expected IG | Actual IG |
|---:|---|---:|---:|---:|---:|---:|
| 0 | Information efficiency | 4 | 17 | 0 | 1.575181 | 1.479714 |
| 1 | Raw disagreement | 7 | 69 | 5 | 0.402121 | 0.229379 |
| 2 | Minimum cost | 5 | 71 | 5 | 0.389979 | 0.531934 |
| 3 | Information efficiency | 4 | 57 | 20 | 0.334567 | 0.621124 |

The paradigm ledger contains 81 individuals across 540 events. Twenty dead or
equivalent lineages remain fossilized, four parent splits bind their child IDs,
and the cumulative Pareto archive contains 16 candidates. All three paradigm
niches and all three question niches operated. Expected and actual information
gain used the same frozen calibrated likelihood.

Every dynamic prior and posterior was reconstructed from the evidence ledger.
Every executed question maps back through a round retargeting event to its base
question lineage. Prediction events precede observations and are protected by
the ledger hash chain. The direct and resumed controls preserved resource counters
and output order exactly.

Recombination is an explicit protocol boundary: the scheduler records typed
requests, but every request was denied because the Gate PF candidate generator
contains no `recombine` operator. This is a successful enforcement check, not a
claim that genotype recombination was executed.

Reproducibility identities:

- report file SHA-256:
  `21894933b5d103794794d8a13babfa097af09eeaaccfd5e9c12ae500b0bb40a3`;
- report content hash:
  `b773f0182fec0bbdd51896b7bb26b286441f393337d81adecb548879ac0d44fd`;
- run-manifest hash:
  `7152dc5256ca9bd8ee34f0fbf59c12829dff8798b172c7612d71d568d6ae909f`;
- evidence-ledger file SHA-256:
  `9662110b507834e2b67f45cf9aec1acea759b6c9cfa2f7ba7114f3b5c87d71f6`;
- final evidence event hash:
  `212ee7d026691aac8cc041d530844ada719dc44b4d910ae95af9667d24abb024`;
- paradigm-lineage file SHA-256:
  `af10260554e196ee9618e1f55fc4910b97a019cb6a3eb4a863ae742390cc28ec`;
- final paradigm-lineage event hash:
  `b00691dbe0e91f9403ddb8e1437b5efa88d25bf8e9cc77e52db54876f7299805`;
- question-lineage file SHA-256:
  `978574e8a9a8dda71d6931b58bc6ca0a0056503fbafa41be6990f216c8ca975c`;
- final question-lineage event hash:
  `2a921750c639a7457fec316580baf638af727da010d7ef309ffc888c8fe0b2d0`;
- scheduler-ledger file SHA-256:
  `3f549cc04e887f852be1332f329b82050ef8808afd9e13a2a0cb4def7da2790c`;
- final scheduler event hash:
  `facad14919d4bfa491c4ea7758b560027217e25a77739bfc9c6911dd67d710a8`;
- final checkpoint hash:
  `78b04c4c5c8c219d7ce4531b00a87f31ec575d4201831b6c892f5e14685805a5`.

After the run, the 30-task local final-world commitment was reverified. Its world
and commitment hashes remain unchanged, and no strategy freeze, access log, or
result exists.

Status: **Step 6 initial development exit criteria satisfied within the frozen
operator boundary**. This is not final-world evidence. The next research step is
the Step 7 blind Gray–Scott challenge and its preregistered baselines/ablations.
