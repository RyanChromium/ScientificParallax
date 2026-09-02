# EXP-06 · 失败历史驱动的研究方向试验 v0

**Status:** `stopped`  
**Decision:** no proposal survived the novelty-gap check

## Question

只向 LLM 提供项目的失败历史，它能否主动提出一个可执行、可证伪，而且不是成熟
通用模板的研究方向？

## Result

模型给出五个方向，三个通过结构化批评。冻结规则只允许检查排名最高的两个；二者
分别落入成熟的配对刺激和对称性诊断研究家族。没有发现由具体异常选择的问题，
所以没有执行下游实验。

## Main entry points

- Plan: [`plans/autonomous-research-direction-pilot.md`](../../plans/autonomous-research-direction-pilot.md)
- Outcome: [`outcome.json`](../../artifacts/research-direction-pilot-v0/outcome.json)
- Literature kill check:
  [`literature-review.md`](../../artifacts/research-direction-pilot-v0/literature-review.md)

**Claim boundary:** failure history can remove some bad directions, but cannot by itself
select a non-generic scientific problem.
