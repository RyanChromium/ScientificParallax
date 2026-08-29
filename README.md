# Scientific Parallax

> 让 AI 不只在既有科学地图中预测，而是尝试改变地图的画法。

Scientific Parallax 是一个探索性 AI 科研项目，目标是研究：能否让 AI 系统生成、检验并演化不同于人类常规思路的“范式候选”。

项目不把科学发现简化为更低的预测误差，也不要求预先定义一个完整的“好范式评分函数”。核心设想是同时维护两个共同演化的种群：

- **范式候选**：关于对象、变量、规律、测量方式和适用范围的可执行描述；
- **科研问题**：能够使不同范式产生可区分预测的观测或干预。

实验结果由独立证据层评估，范式和问题不能通过相互制造分歧来循环奖励自己。

## 核心问题

当前多数 AI for Science 系统在预先定义的变量、标签和评价指标中优化，擅长解决 known unknown，却可能被限制在已有概念词汇中。

Scientific Parallax 关注的是更早期的“认识论裂缝”：

- 多个模型共同失败的区域；
- 被视为噪声、但具有重复结构的残差；
- 不同表征在已知数据上等价、外推时却产生分歧的区域；
- 依赖越来越多辅助假设才能维持的理论谱系；
- 当前变量或测量语言无法自然表达的现象。

项目不会声称直接搜索 unknown unknown，而是尝试构造一种更容易暴露这些裂缝的人工科学生态。

## 工作方式

```text
范式种群产生竞争性预测
          ↓
问题种群寻找高信息量实验
          ↓
模拟、观测或真实实验返回证据
          ↓
独立证据引擎更新范式排名
          ↓
范式修正、分裂、重组或死亡
          ↓
新的范式差异产生新的问题
```

系统遵循几个基本约束：

1. 预测必须在实验前封存；
2. 预测分歧只能用于选择实验，不能直接证明科学价值；
3. 最终评价使用一次性封存世界，不能参与日常进化；
4. 范式修改必须记录谱系和补丁成本；
5. 坐标重命名或等价变量变换不算新范式；
6. 模拟器内成功不等于真实科学发现；
7. 负结果和死亡谱系与成功结果同样保留。

## 首个实验领域

第一阶段选择**可控的非线性时空动力系统**，从 Gray–Scott 二维反应—扩散开始。

选择它不是因为它最可能产生重大科学突破，而是因为它适合低成本证伪本项目的方法：

- 可以快速生成丰富的时空数据；
- 可以主动改变参数、初始条件和局部扰动；
- 存在斑点、条纹、前沿和相态等涌现结构；
- 已知生成方程允许评估结构恢复是否有效；
- 可以使用第二套求解器排除数值伪影；
- 后续能够迁移到 Rayleigh–Bénard 对流、剪切流、湍流和真实 PIV 数据。

## 证据路线

项目按四级证据推进：

1. 已知模拟世界中的方法验证；
2. 跨动力系统的概念与问题策略迁移；
3. 封存真实数据上的前瞻预测；
4. 新测量或新干预下的独立复现。

只有达到第3级或第4级，项目才会使用“潜在科学发现”的表述。

## 当前状态

项目目前已完成 **Step 0–3.5**、本地单账户自审计 Protocol Freeze，以及
**Step 4 范式种群初版**；尚未实现问题种群和完整双种群共进化。

Step 0 薄切片已经完成：

- 一个低维合成世界；
- 八个预先声明的竞争范式；
- 一个有限问题池；
- 一个独立证据引擎；
- 随机选择、最大分歧和贝叶斯实验设计基线；
- 明确的 go / redo / no-go 结果。

薄切片给出了仅限机制和评价设计的 `go`。随后完成的开发组件包括：

- 稳定实验 ID、环境捕获、只写一次的运行清单和 CI；
- 可在线查询和干预的二维 Gray–Scott 世界；
- 五点与九点两套空间离散，以及周期/反射边界；
- 匿名混合、降采样、遮挡、噪声和块状留出测量管线；
- 固定特征预测器、bootstrap 集成和五种问题选择基线；
- 有限类型 Paradigm IR 原型与等价变换检查；
- 训练、开发与一次性最终证据的隔离状态机；
- 右删失终点、分层 bootstrap 和预冻结负控干跑。
- 独立 Euler/RK4 时间积分、六类共 30 个测量任务及数值一致性门禁；
- 有限候选生成器、精确预算/缓存计费与可恢复证据账本；
- The Well 外部数据版本/许可/分片校验清单、可续传下载器和带署名 CI 夹具；
- 基于完整官方 gliders 测试分片的 20 轨迹外部数值校验；
- 固定基础镜像与 NumPy wheel 哈希的确认性 runner 构建输入；
- schema-v1 迁移边界与位于开发目录外的一次性最终评估器。
- 可执行范式基因型/表现型、父子谱系、结构化冻结变异和逐项补丁成本；
- 可完整重建的哈希谱系账本、失败谱系化石档案和三个容量受限生态位；
- 固定开发问题、只进化范式的 Step 4 对照实验。

扩展后的本地 dry-run 已通过全部机制检查，Gate PF 已完成。30 个任务对
30% 改善的模拟功效为
0.90。一个 2.65 GB 官方测试分片已按 SHA-256 验证；独立的九点/RK4
路径相对五点/Euler 的一步外部 RMSE 改善 51.1%，并满足预声明绝对误差
门槛。Linux amd64/arm64 确认性 runner 已发布、固定 OCI 摘要并完成摘要下
画像。确认阶段已明确降级为本地单账户自审计：不再要求独立审查或独立保管，
但结论不得称为独立确认。30 个最终任务已在仓库外完成承诺与双重哈希验证，
Gate PF 已关闭；任务内容保持未打开，等待未来策略冻结后的一次性评估。

Step 0 协议见 [`docs/step0-protocol.md`](docs/step0-protocol.md)，Gray–Scott
开发基线见 [`docs/gray-scott-baseline.md`](docs/gray-scott-baseline.md)，
Step 3.5 协议候选见 [`docs/experiment-protocol.md`](docs/experiment-protocol.md)。
Gate PF 完成记录见
[`docs/protocol-freeze-checklist.md`](docs/protocol-freeze-checklist.md)。
本地自审计记录见
[`docs/protocol-freeze-review-packet.md`](docs/protocol-freeze-review-packet.md)，
最终世界保管流程见
[`docs/final-world-custodian-runbook.md`](docs/final-world-custodian-runbook.md)。
Step 4 实现与边界见
[`docs/step4-paradigm-evolution.md`](docs/step4-paradigm-evolution.md)。
审核后的开发结果见
[`artifacts/gray_scott/reviewed-development-baseline.md`](artifacts/gray_scott/reviewed-development-baseline.md)
、[`artifacts/protocol/reviewed-dry-run.md`](artifacts/protocol/reviewed-dry-run.md)
、[`artifacts/step4/reviewed-paradigm-evolution.md`](artifacts/step4/reviewed-paradigm-evolution.md)
和 [`artifacts/external-data/reviewed-the-well-validation.md`](artifacts/external-data/reviewed-the-well-validation.md)。

## 详细计划

项目的思想脉络与核心假设见：

[Idea：从预测机器到人工科学生态](docs/idea.md)

完整研究假设、统计终点、系统架构、数据路线、实施步骤、风险和停止条件见：

[范式—问题共进化研究计划](plans/scientific-parallax-research-plan.md)

## 背景阅读

- Alvin Djajadikerta, *Designing AI for Disruptive Science*, Asimov Press, 2026, DOI: `10.62211/29ej-27et`
- [《为颠覆性科学设计 AI：如何做出“范式转移”的发现？》](https://mp.weixin.qq.com/s/kU1D5y4F-6KELCtVNH8kqA)
- [PDEBench](https://github.com/pdebench/PDEBench)
- [The Well](https://polymathic-ai.org/the_well/)
- [Johns Hopkins Turbulence Database](https://turbulence.pha.jhu.edu/)

## 项目原则

Scientific Parallax 的价值不由它生成了多少“有趣理论”决定，而由它是否能够：

- 提出真正区分竞争解释的问题；
- 在严格预算下减少识别有效结构所需的实验；
- 以更低的概念成本统一异常；
- 产生跨条件、跨系统成立的新增预测；
- 在失败时清楚地证伪自身。
