# Experiment registry · 实验索引

This directory is the canonical map of the repository's experiments. It does
not duplicate or move frozen outputs. Historical files remain under
`artifacts/`, because their paths and hashes are part of the audit trail.

本目录是仓库中各项实验的统一入口。冻结结果仍保留在 `artifacts/` 原位置，避免
破坏历史路径、哈希和已有引用。每个实验页只负责说明“问题—结果—边界—入口”。

## Current experiment map · 当前实验地图

| ID | Experiment | Status | Honest conclusion |
|---|---|---|---|
| [EXP-01](exp-01-foundation-baselines/README.md) | 数值与固定候选基线 | development complete | 工程链路可用，不是科学发现 |
| [EXP-02](exp-02-coevolution-v1/README.md) | 范式—问题共进化 v1 | stopped | 盲测未优于匹配基线，未进入 Step 8 |
| [EXP-03](exp-03-latent-discovery-v2/README.md) | 受限隐藏结构恢复 v2 | mixed | 合成结构恢复通过，问题策略优势失败 |
| [EXP-04](exp-04-mechanism-audit-v3/README.md) | 机制归因审计 v3 | corrected | 撤回旧机制解释，主要效果来自父代优先级 |
| [EXP-05](exp-05-llm-hidden-mechanism/README.md) | LLM 隐藏机制提案 | stopped | 能提出记忆故事，但无状态解释预测更好 |
| [EXP-06](exp-06-direction-pilot-v0/README.md) | 失败历史方向试验 v0 | stopped | 可执行提案仍是成熟通用方法 |
| [EXP-07](exp-07-evidence-grounded-direction-v1/README.md) | 异常证据方向试验 v1 | stopped | 方向随异常改变，但相同证据下不稳定 |

## How to use this directory · 使用方式

- Human-readable entry point: this file and the seven experiment pages.
- Machine-readable source of truth: [`registry.json`](registry.json).
- CLI: `scientific-parallax experiments list`, `show EXP-07`, or `validate`.
- Papers and synthesis are not experiments. They are indexed separately in
  [`papers/README.md`](../papers/README.md).

Status is a decision record, not a quality score. `stopped` means a rule written
before the result prevented the next step. `mixed` means different frozen
hypotheses had different outcomes. `corrected` means a later audit narrowed an
earlier interpretation.

## Adding a future experiment · 新增实验规则

1. Give a genuinely new scientific question a new permanent `EXP-NN` ID.
2. Keep engineering retries inside the same experiment and label invalid or
   superseded runs; do not silently replace them.
3. Never reopen a `stopped` experiment by weakening its old rule. A revised
   question, evidence packet, or endpoint is a new experiment.
4. Store immutable evidence under `artifacts/`, then link it from the experiment
   page and `registry.json`.
5. Record one short result and one explicit claim boundary even when the result
   is negative.
6. Run `scientific-parallax experiments validate` before committing.
