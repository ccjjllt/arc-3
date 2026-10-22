# 001 — 赛制、数据与强基线研究

日期：2026-10-10（Asia/Shanghai）  
对应结果：[001-baseline](../progress/001-baseline.md)  
范围：完成研究底座、选择可复现基线；GPU 完整复现安排在 [003](003-next-experiment.md)。

## 研究结论

以 **Daniel Franzen 的 Milestone 2 v3 Notebook 为离线基线**，继承 Duck/TAAF 的 Python 工具交互、推理历史、动画观察与跨关卡函数复用。在其上研究新机制理解、跨越首个未解关和后段关卡覆盖，动作效率与计算分配为支撑。当前阶段不从零训练通用智能体，不把旧 ARC-AGI-1/2 的静态网格方法直接当成解法。

本轮没有我们的完整 GPU 推理或隐藏榜单分数。公开代码可读、依赖可定位，不等于已经复现作者成绩。

## 1. 目标与现实竞争位置

信息依据为 2026-10-10 Kaggle MCP 快照：[比赛元数据](../../research/snapshots/get_competition.json)、[页面全文](../../research/snapshots/list_competition_pages.json)、[榜单前 20](../../research/snapshots/get_competition_leaderboard.json)。它们会随比赛推进失效。

| 项目 | 已核验事实与研究影响 |
|---|---|
| 任务 | 64×64 以内、16 色、交互式多关卡游戏；需要自己发现控制、规则和目标 |
| 数据 | 25 个公开开发游戏；另有 110 个隐藏评测游戏，55/55 用于 public/private leaderboard |
| 已参赛 | MCP 返回 user_has_entered=true |
| 当前团队数 | 4090；不是终局有效参赛队数保证 |
| 当前前五分数 | 62.96、56.52、44.32、42.66、40.97 |
| 当前第 18 名 | 35.79 |
| 提交 | Notebook code competition，每天最多 1 次，最终可选 2 份 |
| 运行 | CPU/GPU 均最多 9 小时，评测断网；当前强基线使用 RTX PRO 6000 |
| 最终截止 | 2026-11-02 23:59 UTC，即北京时间 **11 月 3 日 07:59** |
| 里程碑奖金 | 6/30 和 9/30 的截止均已过去 |
| 终局前五奖金 | $40,000 / $15,000 / $10,000 / $5,000 / $5,000 |
| 额外大奖 | Kaggle 规则写明须达到 100%，总计 $700,000，按符合条件的前五分配；不能视为现实保底收益 |

按 [Kaggle 官方奖牌规则](https://www.kaggle.com/progression/competitions)，大赛金牌为前 10 名加队数的 0.2%，向下取整。若最终计入队数恰为 4090，估算金牌到第 18 名，银牌前 204、铜牌前 409。**这是条件计算，不是当前官方锁定奖牌线。** 奖牌与奖金是不同目标；最终看 private leaderboard，当前 public 分数无法保证奖牌。

研究里程碑：先取得可重复的强基线，再争取超过当前金牌附近表现，最后追赶前五。可用 40+、50+ 作阶段性挑战目标，但它们是我们设置的目标，不能写成预计得分或最终分数线。

## 2. 评分决定研究方向

Kaggle 数据页面仍写每关 `min(h/a,1)^2`。当前官方 [methodology](https://docs.arcprize.org/methodology) 与比赛提供的 `arc_agi-0.9.8` wheel 则支持每关最高 115%，并按已完成关卡权重限制游戏总分。实际源码核对见 [data-findings](../../research/overview/data-findings.md)。

对已完成关卡 i，h 为人类基线动作数、a 为智能体动作数，使用百分制：

```text
s_i = min(100 × (h_i / a_i)^2, 115)
未完成关卡 s_i = 0
W = Σ(i=1..L) i
game_score = min(Σ i×s_i / W, 100×Σ(已完成关卡 i)/W)
total_score = 所有游戏的 game_score 等权平均
```

这只是已核验 wheel 的计算方式；隐藏服务的实际部署版本仍以真实运行输出为准。保留每关动作数、完成状态及版本，避免只保存一个无法重算的平均分。

由评分公式得出的研究推论：

- 动作数从 2h 降到 1.5h，未触及 cap 时关卡得分从 25 提高到约 44.44；它说明公式的敏感性，实际剩余空间要由轨迹决定。
- 五关游戏只过前四关，最高游戏得分为 10/15，即 66.67%。后续关卡迁移非常重要。
- 内部推理和自建模型里的搜索不增加环境动作，但消耗 9 小时计算预算。必须同时优化动作与时间。
- 游戏等权而非关卡等权。所有游戏都应获得初始机会；简单按“通关数最多”分配算力可能偏向关卡多的游戏。
- 尚未过当前关的探索会影响通往后续关卡的价值；不能只看当前即时得分放弃全部难游戏。

这些是公式推论，不是实测提升。

另对作者 v3 的原始 benchmark 做了描述性重算：25 个公开游戏 ×4 遍共 100 条轨迹，平均分 46.4930；固定各条轨迹已完成关卡集合，其游戏完成权重上限均值为 49.1227，差 2.6297 分。因此这批记录的主要缺口是新增通关覆盖。这个差值不包含减少动作后解锁新关的间接收益，也不能外推隐藏集。四遍共享一个约 8 小时 11 分钟调度任务，并非四次独立完整运行。来源与计算见 [Notebook 分析](../../research/overview/notebook-findings.md) 和 [重算 JSON](../../research/notebooks/dfranzen-v3-audit-recomputed.json)。

## 3. 必须区分的四种成绩

1. **25 个公开游戏本地开发分**：环境可见、可能被作者长期调过，不是陌生游戏成绩。
2. **Kaggle public leaderboard**：来自隐藏游戏中的公开计分部分，是当前竞赛证据，但有采样和推理随机性。
3. **Kaggle private leaderboard**：最终排名依据，本轮不能读取。
4. **论文/ARC 官方 API benchmark**：模型、环境集合、允许计算、first-exposure、动作上限和重放条件可能不同。

“公开集 100”“Notebook 名称里写 100”“fork 比父版高 2 分”均不能自动证明可迁移改进。特别是相同算法重复运行、不同提交版本的混合比较，需要保留来源限定。

## 4. 可复现基线

主要源码：[dfranzen Notebook](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution)、[GitHub](https://github.com/da-fr/arc-agi-3-solution)、[作者说明](https://github.com/da-fr/arc-agi-3-solution/blob/main/WRITEUP.md)。本地副本与版本证据见 [Notebook 研究](../../research/overview/notebook-findings.md)。

选择理由：同一竞赛、实际离线单卡路径、完整模型和运行时来源、已有隐藏 public LB 记录、明确公开算法，而不是只发布一个排名或论文摘要。

需原样继承的起点：

- Qwen3.8-Flash-Next W4A16，PLE 卸载到主机；MTP 草稿模型；Pennyroyal/SGLang 运行时。
- 原版长上下文和推理历史；每个游戏保留模型编写的 Python 函数。
- 动画中间帧、差分、失败画面及可用动作接口。
- 原版游戏调度及缓存友好的切换位置。
- 保持旧式结构化世界模型摘要关闭，作为明确对照。

不要在复现阶段同时更换 serving 框架、量化、提示词、调度和记忆。大模型的速度/上下文利用率已经是基线能力的一部分，不必先自研 CUDA。

## 5. 数据与代码工作

本轮产物：

- `research/snapshots/`：Kaggle MCP 原始比赛、榜单、讨论证据。
- `research/data/`：实际下载的比赛文件，隔离第三方源码和 wheel。
- `research/data-inventory.json`：资产及公开环境元数据清单。
- `research/notebooks/`：候选公开 Notebook、源码抽取、metadata、CLI pull 参考。
- `README.md`：MCP 查询、CLI pull/push/status/output/submit 的已核对用法。

下一轮代码边界：

- 从已下载 Notebook 生成我们自己的 `notebooks/001-baseline/`，仅修改身份、私有可见性和开发集运行设置。
- 首个完整运行只补充研究轨迹导出，记录真实动作、关卡、时间、tokens 和中间帧；核心算法保持对照一致。
- 不新增测试文件，不搭建 CI 或门控框架；手动看日志、回放和得分。

## 6. 实施顺序与继承信息

1. 核对本地模型、数据和 Notebook 版本及实际目录；不要根据旧教程假定挂载路径。
2. 阅读 Notebook 的运行模式切换逻辑和真实配置，不仅看 Markdown 标题。
3. 固定原版环境与输入，手动运行一次完整公开集基线。
4. 人工审阅“未通过/已通过但动作过多/推理消耗过大”各类轨迹。
5. 再执行 [002](002-strategy-improvement.md) 中最能解释实际失败的单项修改。
6. 依照 [003](003-next-experiment.md) 逐轮留下对应 progress，而非只维护最佳分数。

## 7. 冲突与已知限制

- **评分**：页面旧公式 vs wheel 和当前文档新公式；已定位来源，不混用。
- **截止时刻**：metadata 入赛截止为 10/26 11:59 UTC，而 Timeline 通用文字为当日 23:59 UTC；用户已参赛，不影响研究。组队若有需要按较早时刻处理并再次核实。
- **奖金**：ARC 官网与 Kaggle 的大奖分配/里程碑明细不完全一致；本项目引用 Kaggle 本场规则，最终由主办方解释。
- **模型资格**：关于 Qwen3.8 Community License 的 [745079](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/745079) 与 [745837](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/745837) 讨论截至本次读取未见官方裁定。已有高分公开使用不等于最终奖金资格确认。研究继续，模型后端保持可替换，所有自有改动保留可公开复现记录。
- 我们没有隐藏游戏逐关真值，也没有榜首私有实现，不能声称已定位追平榜首的确定方法。

