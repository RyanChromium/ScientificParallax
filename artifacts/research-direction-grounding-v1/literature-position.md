# Literature position before v1 model calls

The v1 question is not whether LLMs can produce fluent or diverse ideas. It is
whether an executable research direction causally depends on a specific
experimental anomaly.

Adjacent primary work found before freezing the pilot:

- **LiveIdeaBench** evaluates divergent scientific ideation from minimal
  keyword context using originality, feasibility, fluency, flexibility, and
  clarity. It does not test whether an executable direction changes under a
  controlled anomaly ablation.
  https://www.nature.com/articles/s41467-026-70245-1
- **ProjectionBench** progressively reveals information from recent papers and
  compares atomic claims with the papers' conclusions. It measures grounded
  alignment as context grows, but retains a ground-truth-conclusion target and
  does not execute a direction selected from paired factual/counterfactual
  observations. https://arxiv.org/abs/2605.30284
- Xu et al. report that ChatGPT-4 tends to search a familiar hypothesis space
  rather than let anomalies trigger curiosity, and that it fails to revise
  unsupported hypotheses. This directly motivates the v1 causal question but
  does not provide its numerical ablation test.
  https://www.nature.com/articles/s41598-025-93794-9
- Bao et al. use large-scale scientist ratings and find weak agreement between
  automated evaluators and experts, motivating v1's avoidance of LLM-as-judge.
  https://arxiv.org/abs/2606.08251

The local pilot therefore occupies a plausible evaluation gap, but this short
search does not establish publication-level novelty. Any positive result must
remain a development result until repeated across systems, anomalies, models,
and independent human/domain review.
