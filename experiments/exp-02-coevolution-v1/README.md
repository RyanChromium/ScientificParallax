# EXP-02 · 范式—问题共进化 v1

**Status:** `stopped`  
**Decision:** stop before Step 8

## Question

共同演化模型候选和实验问题，能否比使用同一候选生成器的贝叶斯实验设计更快
识别真候选？

## Result

Step 4、5、6 的谱系、问题生成、调度、预算和断点恢复检查均通过。Step 7 在
240 个预先安排的臂—任务运行上得到 1.0 对 1.0 次查询，改进为 0。冻结规则
因此给出 `stop`，最终封存世界没有打开，Step 8 没有执行。

## Main entry points

- Protocol sequence: [`Step 4`](../../docs/step4-paradigm-evolution.md),
  [`Step 5`](../../docs/step5-question-evolution.md),
  [`Step 6`](../../docs/step6-coevolution-scheduler.md),
  [`Step 7`](../../docs/step7-blind-development-challenge.md)
- Reviewed results: [`Step 4`](../../artifacts/step4/reviewed-paradigm-evolution.md),
  [`Step 5`](../../artifacts/step5/reviewed-question-evolution.md),
  [`Step 6`](../../artifacts/step6/reviewed-coevolution.md),
  [`Step 7`](../../artifacts/step7/reviewed-blind-development.md)
- Original research plan:
  [`scientific-parallax-research-plan.md`](../../plans/scientific-parallax-research-plan.md)

**Claim boundary:** the system is auditable and executable; superiority over the
matched baseline was not demonstrated.
