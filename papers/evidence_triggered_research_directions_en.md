# Does an Anomaly Really Change an LLM's Research Idea?

## An Auditable Local Study from Hidden-Factor Recovery to Counterfactual Evidence Testing

ScientificParallax Project Research Report | Version 1.0 | 2 September 2026

> One-sentence conclusion: the language model changed its research direction when a key anomaly was removed, but it did not reliably choose the same experiment when shown the same evidence. We can therefore claim evidence-triggered, testable proposal generation in this case; we cannot claim a scientifically novel idea.

## Abstract

Large language models can quickly produce plausible scientific hypotheses, but plausibility does not show that an idea came from data or that it is scientifically new. We ask a narrower question: when a record contains a clear anomaly, is the model's proposed next study triggered by it? If only the anomaly is removed, does the proposal change?

We used a fully controlled two-dimensional simulation and made two versions of the same numerical evidence. The full version retained a late anomaly after a second pulse; the counterfactual version replaced only that segment with the existing reference model's predictions. Each version went to two independent model instances. Responses had to cite evidence, give distinguishable explanations, and select a locally executable two-condition experiment. Fixed code applied rules written in advance.

With full evidence, both responses focused on the mean of field B at time 60, but one changed pulse amplitude and the other changed pulse interval. After the anomaly was removed, both shifted to spatial geometry, changing pulse radius at fixed total dose and measuring B's boundary strength. The anomaly changed the proposal theme, but identical full evidence did not produce the same intervention. The frozen overall rule therefore failed and no downstream experiment was run. The result supports only a limited claim: proposals in this case responded to evidence, but were not stable, and neither project-level nor scientific novelty was established.

Keywords: large language models; scientific ideas; anomalies; counterfactual testing; reproducibility; negative results

## A short explanation for readers from any field

Imagine a medical case record with one striking late change. We ask two independent “AI doctors” what test should come next. We then copy the record, erase only that late change, and ask two more. If the recommendations stay the same, they may be generic routines. If they change with the anomaly, the data affected the reasoning. But if the first two doctors still order different key tests from the same original record, the recommendation is not yet reliable.

That is the state reached here: the AI responded to evidence, but not stably enough. The scientific value is not an announcement that AI discovered a new law. It is a clearer way to test such announcements.

## 1. Research question

The concrete question is:

**Can a language model use a clear, measurable anomaly to autonomously propose a locally executable and falsifiable research direction that changes when the anomaly disappears?**

This question contains four requirements. First, the proposal must point to specific observations, rather than merely recommend more data or a more complex model. Second, it must become an executable local experiment. Third, the two possible outcomes must favor different explanations; the proposal cannot claim success regardless of the result. Fourth, and most importantly here, the direction must depend on the anomaly itself. Removing the anomaly should produce a measurable change in the proposed study.

We added a fifth, stricter requirement: independent repetitions with the same evidence should select the same operational question. This separates “the evidence influenced the broad theme” from “the model formed a stable judgment.”

## 2. Why the project moved from Z to evidence-triggered ideas

### 2.1 What the hidden quantity Z taught us

The project began with a Gray–Scott-type simulation, a simple rule system known to produce spots, stripes, and other spatial patterns [1]. The program could observe two quantities over time. In some synthetic worlds, however, the data generator also contained an unobserved quantity Z. Z stored part of the effect of earlier stimulation and later changed the visible dynamics.

In one frozen test, a structural search system met the predefined hidden-structure endpoint on all 20 tasks containing the hidden quantity and added no hidden quantity in 30 simple controls without it. This showed that, when the search language already permits adding and connecting a hidden quantity, the program can preserve intermediate structures and reach a useful model.

It did not establish discovery. We wrote the truth into the simulator, and we predefined the allowed structural changes. A later mechanism audit also found that the earlier advantage attributed to preserving neutral intermediate structures mixed together different search-order and question-selection rules. More detailed controls indicated that prioritizing expansion of higher structural stages explained most of the observed effect. We withdrew the stronger interpretation and stopped presenting this path as a new discovery algorithm.

### 2.2 Why “another variable improves fit” is not enough

Adding a variable generally gives a model more freedom. If success means only lower fitting error, a hidden quantity has an automatic advantage. Later tests therefore required evaluation on conditions not used for selection, a competing explanation with no hidden quantity, a minimum predeclared improvement, and controls with no hidden process. Thresholds, proposals, and samples could not be changed after the result was seen.

The language model did independently propose a memory-like extra quantity from anonymous residuals. Yet in the selected two-pulse experiment, its error was 0.1302, while a state-free explanation that changed only visible removal dynamics achieved 0.1153. The memory proposal improved on the original baseline by 5.15%, below the frozen 10% requirement, and was 12.92% worse than the state-free rival. The project therefore stopped the “LLM recovered Z” route.

### 2.3 The corrected question

These failures changed the target from “can the model say Z?” to a more basic and testable issue: when the model proposes a next study, is it responding to the data or retrieving a familiar scientific template? That is the question tested in this report.

| Stage | Question at the time | Result | Knowledge retained |
|---|---|---|---|
| Hidden-structure search | Can a program recover Z in a synthetic world? | Yes, but the search language already allowed Z; the mechanism attribution was later corrected | Controlled search ability, not a new natural law |
| LLM hypothesis screen | Can an LLM propose a memory-like explanation? | Yes, but a state-free explanation predicted better | A plausible story is not mechanism identification |
| Direction pilot v0 | Can failure history alone produce a worthwhile direction? | Five proposals; high-ranked ideas were mature methods | Negative history prevents some mistakes but does not select a non-generic question |
| Direction pilot v1 | Does a direction change with a specific anomaly? | Broad theme changed; exact experiment was not stable | Evidence-sensitive, not yet reliable |

## 3. Study design

### 3.1 A fully inspectable simulation

We used a 12×12 grid. Every location contained two visible fields, A and B. They spread to neighboring locations and interacted. The experiment ran for 60 time units, with readings at times 12, 24, 36, 48, and 60. To make the evidence compact and readable, each field was summarized in four ways: overall average, variation across locations, proportion of high-valued locations, and strength of differences between neighboring locations. Two fields, five times, and four summaries produced 40 evidence cells.

The reference explanation was the best earlier model that added no hidden state. It matched the early observations reasonably well but strongly underestimated B after a second local pulse. At time 60, it predicted a B mean of 0.4635; the observation was 0.8923. After division by a fixed comparison scale, this was an 8.58-unit discrepancy, the strongest anomaly in the packet. B's variation, high-valued fraction, and spatial boundary strength were also elevated at times 48 and 60. The surprise was therefore a coordinated pattern, not one isolated number.

### 3.2 Two evidence packets differing in one key fact

The full packet retained all 40 cells. The counterfactual packet kept the same design, reference predictions, and all observations before the second pulse. It replaced only the later observations with the reference predictions. In plain language, it created a version of the record in which the late anomaly did not happen.

The two packets used neutral random identifiers. The model did not see labels such as “full” or “anomaly removed,” the true generator, the repository, previous answers, or the web. This does not prove that a pretrained model had no relevant prior knowledge. It only reduced direct answer leakage from names and surrounding files.

### 3.3 What every response had to provide

Every call used a fresh context. The model had to:

- cite at least two exact evidence cells;
- state two competing explanations;
- give mutually incompatible outcome predictions;
- choose one two-level experiment from five locally executable intervention families;
- preselect field A or B, the summary measure, and the observation time;
- state what result would stop or redirect the question.

The available interventions were pulse radius at fixed total dose, second-pulse amplitude, time between pulses, and two public control settings. This menu made local execution possible. It did not list candidate mechanisms such as memory, interfaces, or thresholds.

### 3.4 Frozen success rule

The full packet was sampled independently twice, and the counterfactual packet was sampled independently twice. Each full-evidence proposal had to cite multiple strong anomalies and at least one cell replaced in the counterfactual packet. More strictly, the two full responses had to have the same operational signature: intervention family, response field, response feature, and response time.

If the full evidence produced a stable signature, each counterfactual response then had to differ from it in at least two of those four components. Only after all these checks passed would the selected downstream experiment run. A failure did not license more samples, weaker criteria, rewritten responses, or an experiment chosen after looking at the outputs.

![Figure 1. Study logic: compare proposals from full evidence with proposals after removing the late anomaly.](assets/paper_logic_en.png)

## 4. Results

### 4.1 Both full-evidence responses found the late anomaly

Both full-evidence responses selected B's mean at time 60 as the primary observation, and both cited several strong deviations at times 48 and 60. One framed the question as whether the second pulse reactivated B-rich regions and proposed including versus omitting that pulse. The other asked whether a longer interval between pulses created a sensitized state and proposed changing pulse lag. Both belonged to a temporal-history theme, but they were not the same experiment.

### 4.2 Removing the anomaly shifted proposals toward spatial geometry

Neither counterfactual response centered on the removed late surge. Both focused instead on a weaker but coordinated spatial pattern at time 36. Both proposed comparing a small and large pulse radius while keeping total dose fixed, and measuring the spatial boundary strength of B. They differed only in reading the outcome at time 48 or 60. The evidence manipulation therefore produced a structured change in attention and experiment theme.

| Evidence condition | Independent replicate | Selected intervention | Outcome |
|---|---:|---|---|
| Full evidence | 1 | Change second-pulse amplitude | B mean at time 60 |
| Full evidence | 2 | Change interval between pulses | B mean at time 60 |
| Late anomaly removed | 1 | Change pulse radius at fixed total dose | B spatial boundary strength at time 60 |
| Late anomaly removed | 2 | Change pulse radius at fixed total dose | B spatial boundary strength at time 48 |

### 4.3 Preregistered decision: overall failure

Both full responses passed the strong-anomaly citation check. The two counterfactual signatures differed from the respective full signatures in two and three of four components, passing the counterfactual-change check. The full responses, however, selected different interventions. Exact replicate stability therefore failed. Under the frozen rule, the overall status was failure, and the downstream experiment was not executed.

![Figure 2. Agreement and disagreement across four independent responses. Green denotes pass, amber partial agreement, and red failure.](assets/paper_result_en.png)

## 5. What can “the LLM generated a new idea” mean?

The word “new” has at least four distinct meanings.

| Level of novelty | Supported here? | Reason |
|---|---|---|
| Not directly stated in the prompt | Yes | The model named temporal memory, pulse-lag, and spatial-geometry questions on its own |
| Produced in response to these data | Partly | Removing the late anomaly shifted the direction from temporal history to spatial geometry |
| Never previously present in this project | Not established | Memory and fixed-dose spatial concentration had close predecessors in earlier work |
| New to the scientific community | Cannot be claimed | Paired perturbations, symmetry, memory, and spatial thresholds all have substantial adjacent literature; no systematic novelty review or expert confirmation was completed |

The most defensible statement is therefore: **the language model independently generated executable research proposals that were not enumerated in the prompt and were counterfactually sensitive to the evidence. The proposals did not demonstrate scientific novelty relative to project history or prior literature, and they did not reach operational repeatability.**

## 6. Why this is not the trivial claim that more parameters fit better

The present endpoint did not reward a larger model for fitting better. The reference predictions were fixed in both evidence packets, and no parameters were refitted after proposal generation. Success depended on whether removing evidence changed the selected experiment and whether repeated exposure to the same evidence produced the same operation. Model complexity could not directly improve either score.

The earlier Z work did face the risk that a more complex model would win automatically. That is why later stages added state-free competitors, unseen conditions, a minimum improvement threshold, and no-hidden-process controls. The state-free rival ultimately beat the LLM memory proposal. That negative result is evidence that the stop rule was active rather than decorative.

## 7. Relation to prior work

Recent benchmarks study different aspects of scientific idea generation. LiveIdeaBench uses very limited context to measure whether models produce diverse, clear, and apparently original ideas [2]. ProjectionBench progressively reveals information from papers and compares generated claims with the papers' conclusions [3]. SCOPE evaluates the completeness and configuration quality of experimental plans [4]. These studies ask how much models can generate, how plausible it is, or how complete it is.

Other work offers caution. Xu and colleagues reported that a model tended to search a familiar hypothesis space and did not reliably revise its views in response to anomalies [5]. A large scientist-rating study by Bao and colleagues found weak agreement between automated evaluators and domain experts [6]. Recent work on experimental fidelity also stresses that code execution alone does not show that the intended scientific claim was tested [7].

Our small study does not replace these broad evaluations. It adds a causalized local question: hold all other information fixed, remove one real anomaly, and test whether the selected executable experiment changes. It also avoids an LLM judge. Exact evidence references, operational signatures, and a real stop decision determine the result.

The v0 literature kill check additionally found that the model's paired-perturbation and symmetry directions belonged to established research families [8–11]. This explains why a fluent, falsifiable proposal can still be generic and supports our conservative language about novelty.

## 8. Limitations

First, one simulated anomaly, one model, and two calls per condition cannot estimate a general success rate. Second, the project constructed the simulation and had already used the same world family during development; this was not an independent real scientific problem. Third, the five-intervention menu constrained the form of the proposals, even though it did not supply mechanism names. Fourth, the full-evidence input omitted earlier stopped research routes, and both responses revived a temporal-memory direction. Numerical evidence without negative research history can therefore mislead the model. Fifth, one local account designed, ran, reviewed, and documented the study. There was no independent custodian, external reproduction, or domain-expert panel. Sixth, a short literature kill check can reject obvious near-neighbors but cannot prove the absence of closer prior work.

A further boundary matters: counterfactual sensitivity is not the same as understanding. A model may react statistically to conspicuous numbers without forming a stable causal representation. Distinguishing these explanations requires more anomaly types, more repetitions, label-permutation controls, and downstream experiments capable of eliminating mechanisms.

## 9. Next study

The next version should neither weaken the failed rule nor continue tuning the same case. A stronger test should:

1. use a new simulation or real case not seen during development;
2. provide both the numerical anomaly and explicit records of stopped routes and why they failed;
3. freeze at least three to five independent repetitions and compare multiple language models with a simple non-language-model generator;
4. include full evidence, anomaly removal, anomaly relocation, and no-anomaly controls;
5. execute a discrimination experiment only if the same evidence yields a stable operation and controls change as predicted;
6. retain only explanations supported by the outcome, followed by an independent domain literature review.

Only repeated success across independent cases would support the claim that the system stably produces anomaly-driven research directions. A claim of novelty to science would additionally require systematic prior-art review, expert scrutiny, and evidence from a real or independently governed experiment.

## 10. Conclusion

The project's main progress was not finding Z or producing an impressive explanation. It was progressively tightening the meaning of “generating a scientific idea.” Hidden-structure recovery demonstrated search. Competing models showed that a more elaborate story need not predict better. Literature checks showed that executable proposals can still be generic. The counterfactual experiment directly tested whether proposal selection depended on anomalous evidence.

The present answer is: **it depended on the evidence, but it was not stable.** Removing the late anomaly shifted proposals from temporal history to spatial geometry. Yet two responses to the same full evidence did not choose the same key intervention. The frozen rule therefore failed, and no attractive follow-up experiment was added after the fact.

This is not proof that an LLM produced a scientifically new idea. It is a reproducible developmental negative result and a stricter evaluation approach: separate prompt-level generation, data dependence, repeatability, project novelty, and scientific novelty, and allow failure at every layer. For AI systems intended to participate in research across disciplines, the ability to stop may be as important as the ability to propose.

## Materials, roles, and integrity

Code, frozen inputs, four raw model responses, deterministic assessments, and stop records are stored in the local ScientificParallax repository under `artifacts/research-direction-grounding-v1/` and the related historical directories. The current research-direction implementation corresponds to local commit `286e246`. At this report version, the new branch has not been released as an independently reproduced public result.

The language model generated candidate questions under restricted inputs. Fixed software checked format, evidence citations, signature changes, and pass criteria. The same local operator designed, ran, reviewed, and documented the study. No human or animal subjects were involved. Launcher errors, invalid output capture, and stop decisions were retained rather than rewritten into an apparently flawless run.

## References

[1] Pearson, J. E. Complex patterns in a simple system. *Science* 261, 189–192 (1993). https://doi.org/10.1126/science.261.5118.189

[2] Ruan, K. et al. Evaluating LLMs' divergent thinking capabilities for scientific idea generation with minimal context. *Nature Communications* 17, 3625 (2026). https://doi.org/10.1038/s41467-026-70245-1

[3] Lew, A. J., Cao, Y. & Buehler, M. J. ProjectionBench: Evaluating scientific hypothesis generation in LLMs under progressive information disclosure. arXiv:2605.30284 (2026). https://arxiv.org/abs/2605.30284

[4] Liu, Z. et al. Can LLM design high-quality experiments? A comprehensive and systematic benchmark on autonomous experimental design. arXiv:2608.03501 (2026). https://arxiv.org/abs/2608.03501

[5] Xu, F. et al. Generative AI lacks the human creativity to achieve scientific discovery from scratch. *Scientific Reports* 15 (2025). https://doi.org/10.1038/s41598-025-93794-9

[6] Bao, H. et al. Contemporary AI lacks the imagination to diverge or negate in science. arXiv:2606.08251, version 3 (2026). https://arxiv.org/abs/2606.08251

[7] Yu, L., Xu, X., Zhou, Y., He, S. & Pan, A. Beyond execution: Auditing experimental fidelity in LLM-driven scientific research. arXiv:2608.26753 (2026). https://arxiv.org/abs/2608.26753

[8] Caldera, M. et al. Mapping the perturbome network of cellular perturbations. *Nature Communications* 10, 5140 (2019). https://doi.org/10.1038/s41467-019-13058-9

[9] Chatterjee, M. S. et al. Pairwise agonist scanning predicts cellular signaling responses to combinatorial stimuli. *Nature Biotechnology* 28, 727–732 (2010). https://doi.org/10.1038/nbt.1642

[10] Wang, R., Walters, R. & Yu, R. Approximately equivariant networks for imperfectly symmetric dynamics. *Proceedings of Machine Learning Research* 162, 23078–23091 (2022). https://proceedings.mlr.press/v162/wang22aa.html

[11] Yang, J., Dehmamy, N., Walters, R. & Yu, R. Latent space symmetry discovery. *Proceedings of Machine Learning Research* 235, 56047–56070 (2024). https://proceedings.mlr.press/v235/yang24g.html

## Appendix: frozen criteria and observed outcomes

- Strong-anomaly citation: both full-evidence responses passed.
- Full-evidence operational signatures: “second-pulse amplitude / B / mean / 60” and “pulse lag / B / mean / 60”; inconsistent.
- Counterfactual signatures: both used “pulse radius at fixed total dose / B / spatial boundary strength,” with response times 60 and 48.
- Full-to-counterfactual signature changes: two and three of four components, meeting the counterfactual-change threshold.
- Overall decision: `grounding_failed`; downstream experiment not executed.
