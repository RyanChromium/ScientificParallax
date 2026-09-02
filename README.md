# Scientific Parallax · 科学视差

> 让 AI 不只在既有科学地图中预测，而是尝试改变地图的画法。

**[中文官网](https://www.scientific-parallax.com/) · [English website](https://www.scientific-parallax.com/en/) · [联系我们 / Contact us](mailto:ran.chen2025@gmail.com)**

## 我们在做什么

Scientific Parallax 是一个探索 **AI 如何参与科学发现** 的项目。

今天许多科学 AI 的工作，是在已有变量、问题和评价标准下寻找更好的答案。我们想往前走一步：让 AI 帮助人们重新描述现象、提出值得验证的问题、设计能区分不同解释的测量，并让所有想法接受独立证据检验。

我们目前关注四件事：**表征、问题生成、测量与独立证据**。项目仍处于探索阶段，不把模拟结果或未经验证的方法优势称为科学发现。

## What we do

Scientific Parallax explores **how AI can take part in scientific discovery**.

Much of today's scientific AI searches for better answers within predefined variables, questions, and metrics. We want to move one step earlier: helping people reframe phenomena, ask testable questions, design measurements that distinguish competing explanations, and evaluate every idea against independent evidence.

Our current focus is **representation, question generation, measurement, and independent evidence**. This is an exploratory project; simulation results and unverified methodological advantages are not presented as scientific discoveries.

## 当前结论 · Current conclusion

当前最稳妥的结论不是“AI 已经发现了新规律”，而是：在一个本地模拟案例中，
LLM 的研究方向会随关键异常的删除而改变，但面对相同证据还不能稳定选择同一个
实验。完整研究叙事见 [`papers/`](papers/)；每次实验的独立结论见
[`experiments/`](experiments/)。

Our current result is not that AI has discovered a new law. In one local
simulation case, an LLM changed its research direction when a key anomaly was
removed, but did not reliably select the same experiment from identical
evidence. See [`papers/`](papers/) for the synthesis and [`experiments/`](experiments/)
for the separate record of every experiment.

## Repository map · 仓库导航

| Path | Purpose |
|---|---|
| [`experiments/`](experiments/) | Canonical experiment index: question, status, result, claim boundary, and links |
| [`artifacts/`](artifacts/) | Frozen and reviewed outputs; historical paths are not rearranged |
| [`configs/experiments/`](configs/experiments/) | Executable experiment configurations |
| [`docs/`](docs/) | Protocols, design notes, and decision log |
| [`plans/`](plans/) | Research plans, including routes that were later stopped |
| [`papers/`](papers/) | Chinese and English paper sources and generated-document index |
| [`src/`](src/) and [`tests/`](tests/) | Implementation and verification |
| [`CHANGELOG.md`](CHANGELOG.md) | Current unreleased repository changes |

List or inspect experiments locally:

```text
scientific-parallax experiments list
scientific-parallax experiments show EXP-07
scientific-parallax experiments validate
```

Detailed historical plans and protocols remain in [`plans/`](plans/) and
[`docs/`](docs/). The machine-readable experiment map is
[`experiments/registry.json`](experiments/registry.json).
