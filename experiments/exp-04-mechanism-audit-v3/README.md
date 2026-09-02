# EXP-04 · 机制归因审计 v3

**Status:** `corrected`  
**Decision:** withdraw the neutral-bridge attribution and stop the novelty claim

## Question

v2 的表现究竟来自保留中性结构，还是来自被混在一起的搜索顺序、父代优先级和
问题集平衡规则？

## Result

冻结的因子拆分和验证显示，主要效果由优先展开更高结构阶段解释；只改变问题集
平衡的效果很小。与 MAP-Elites 风格对照相比，没有建立独特算法优势。因此保留
全部 v2 测量，但撤回原机制解释。

## Main entry points

- Protocol: [`docs/protocol-v3-mechanism-audit.md`](../../docs/protocol-v3-mechanism-audit.md)
- Reviewed result:
  [`artifacts/protocol-v3/reviewed-mechanism-audit.md`](../../artifacts/protocol-v3/reviewed-mechanism-audit.md)
- Configs: [`development v1`](../../configs/experiments/mechanism-audit-development-v1.json),
  [`development v2`](../../configs/experiments/mechanism-audit-development-v2.json),
  [`validation`](../../configs/experiments/mechanism-audit-validation-v1.json)

**Claim boundary:** a reproducible correction of attribution, not a new discovery algorithm.
