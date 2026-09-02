# EXP-05 · LLM 隐藏机制提案与区分试验

**Status:** `stopped`  
**Decision:** stop the “LLM recovered Z” route

## Question

隔离的语言模型能否从匿名残差提出类似记忆的额外状态，并在由候选预测选择的
干预中胜过不增加状态的竞争解释？

## Result

LLM 确实提出了可解析、可执行的记忆状态。但冻结干预中，记忆解释 RMSE 为
0.130194，只比原基线好 5.15%，低于 10% 门槛；无隐藏状态解释达到 0.115293，
比记忆解释更好。单一无隐藏过程对照没有触发错误归因警告。

## Main entry points

- Initial screen: [`llm-hypothesis-screen-v0`](../../artifacts/llm-hypothesis-screen-v0/README.md)
- Null diagnostic: [`llm-hypothesis-null-v0`](../../artifacts/llm-hypothesis-null-v0/README.md)
- Frozen discrimination:
  [`llm-hypothesis-screen-v1`](../../artifacts/llm-hypothesis-screen-v1/README.md)
- Code: [`llm_hypothesis.py`](../../src/scientific_parallax/discovery/llm_hypothesis.py),
  [`llm_discrimination.py`](../../src/scientific_parallax/discovery/llm_discrimination.py)

**Claim boundary:** executable hypothesis generation, not identification of a unique hidden
mechanism and not recovery of Z.
