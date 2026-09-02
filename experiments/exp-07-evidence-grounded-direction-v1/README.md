# EXP-07 · 异常证据触发的研究方向试验 v1

**Status:** `stopped`  
**Decision:** `grounding_failed`

## Question

如果只删除一个明确的晚期异常，LLM 选择的可执行实验是否随之改变；相同完整
证据又能否稳定地产生同一个操作？

## Result

两次完整证据回答都引用了晚期强异常，并关注 B 在时刻 60 的均值，但分别选择
第二次刺激强度和刺激间隔。删除晚期异常后，两次回答都转向固定总量下的刺激
半径和空间边界强度。反事实改变通过，完整证据重复稳定性失败，因此没有执行
下游实验。

## Main entry points

- Plan: [`plans/evidence-grounded-direction-pilot-v1.md`](../../plans/evidence-grounded-direction-pilot-v1.md)
- Reviewed result:
  [`artifacts/research-direction-grounding-v1/README.md`](../../artifacts/research-direction-grounding-v1/README.md)
- Deterministic assessment:
  [`assessment.json`](../../artifacts/research-direction-grounding-v1/assessment.json)
- Code: [`grounding.py`](../../src/scientific_parallax/direction/grounding.py)

**Claim boundary:** evidence-sensitive in one case, but not repeatably stable and not shown
to be new to the project or to science.
