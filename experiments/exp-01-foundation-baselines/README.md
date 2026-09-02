# EXP-01 · 数值与固定候选基线

**Status:** `development_complete`  
**Decision:** retain as regression and protocol baselines

## Question

数值模拟、证据账本和固定候选问题选择是否稳定到足以支撑后续实验？

## Result

Gray–Scott 数值实现、外部 The Well 数值对照和 Step 0 固定候选流程均可重放。
Step 0 中贝叶斯设计更早识别真候选，但真候选预先位于八个候选中，噪声模型也被
正确指定。因此，这一组实验验证的是工程和评估机制，不是共进化或科学发现。

## Main entry points

- Protocols: [`docs/gray-scott-baseline.md`](../../docs/gray-scott-baseline.md),
  [`docs/step0-protocol.md`](../../docs/step0-protocol.md)
- Reviewed results:
  [`artifacts/gray_scott`](../../artifacts/gray_scott/reviewed-development-baseline.md),
  [`artifacts/step0`](../../artifacts/step0/reviewed-baseline.md),
  [`artifacts/external-data`](../../artifacts/external-data/reviewed-the-well-validation.md)
- Configs: [`gray-scott-baseline.json`](../../configs/experiments/gray-scott-baseline.json),
  [`step0.json`](../../configs/experiments/step0.json)

**Claim boundary:** regression baseline only; no claim of autonomous discovery.
