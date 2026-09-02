# EXP-03 · 受限隐藏结构恢复 v2

**Status:** `mixed`  
**Decision:** retain the narrow structural result; reject question-strategy superiority

## Question

当搜索语言明确允许增加并连接隐藏状态时，系统能否穿过三个结构步骤，在未用于
选择的干预条件上恢复被留出的合成结构？

## Result

20/20 个隐藏结构任务达到冻结终点；30 个简单无隐藏结构对照中没有误加隐藏
状态。无生态位对照仅通过 4/20。但共同演化问题与匹配贝叶斯设计都需要 4.5 次
查询，H2 被拒绝。

## Main entry points

- Protocol: [`docs/protocol-v2-latent-discovery.md`](../../docs/protocol-v2-latent-discovery.md)
- Reviewed result:
  [`artifacts/protocol-v2/reviewed-latent-discovery.md`](../../artifacts/protocol-v2/reviewed-latent-discovery.md)
- Configs: [`pilot`](../../configs/experiments/latent-discovery-pilot.json),
  [`confirmatory`](../../configs/experiments/latent-discovery-confirmatory-v1.json)

**Claim boundary:** controlled recovery inside a pre-authorized synthetic grammar;
not discovery of a new natural variable.
