# 018 独立数值、资源与归档审计

审计日期：2026-10-18，Asia/Shanghai。只读原始 JSON/JSONL、冻结 Notebook 和 harness 控制代码，使用独立标准库计算，没有导入主分析器的评分/统计 helper；没有读取游戏实现源码、运行模型生成代码、模型、游戏、GPU 或网络。完整数值和输入哈希见 [018-independent-audit.json](018-independent-audit.json)。本轮另获授权修复分析器一处日志归档遗漏，原始数据和运行版本未改。

**结论：成绩和执行预算有效；初始 `validation=false` 是分析器漏读默认日志，不是018运行失败。018本轮不支持晋升。** 采用链另行审阅，本审计不从得分、关键词或旧实验推断采用。

| 指标 | baseline | observation_grounding | 差值 |
|---|---:|---:|---:|
| 均分 | 67.010582 | 63.782652 | −3.227930 |
| 加权完成覆盖 | 68.154762 | 65.178571 | −2.976190 |
| 完成关卡 | 22/28 | 22/28 | 0 |
| 全通游戏 | 2 | 1 | −1 |
| 动作 | 550 | 597 | +47 |
| 成功请求生成 tokens，含 drain | 332,285 | 354,387 | +22,102 |
| 动作附着及 final tokens | 291,569 | 347,029 | +55,460 |

4个相同开发游戏、同顺序、单pass。每关按 `min(115,100*(baseline_actions/actions)^2)` 和关卡权重1..N重算，再应用游戏cap；8局全部与 reported_score 吻合，最大浮点误差小于1e-12。没有把未完成关、截断请求或超时动作补进分数。

| 游戏 | 分数 A→B | 关卡 A→B | 对均分差贡献 |
|---|---:|---:|---:|
| ft09 | 100.000000→71.428571 | 6→5/6 | −7.142857 |
| tr87 | 9.708995→47.619048 | 2→4/6 | +9.477513 |
| ar25 | 58.333333→41.666667 | 6→5/8 | −4.166667 |
| sb26 | 100.000000→94.416324 | 8→8/8 | −1.395919 |

tr87多2关，ft09和ar25各少1关，所以总关数不变；不同深度/总关数权重导致完成覆盖下降。sb26仍全通但效率分降低。这个分解是算术贡献，不证明提示造成了相应变化。

## 单因素与时序

- 冻结Notebook SHA256仍为 `731fd4335c20bcec86ea93f3be9449be82175a28ea6835582090b3b3999aefc7`；manifest config、全部嵌入源hash、两臂共用runtime hash均一致。candidate唯一新增模块是observation_grounding.py；唯一环境差是冻结prefix。
- 全部真实request中，baseline没有candidate prefix，candidate都有prefix；剥掉prefix后的system集合与baseline完全相同，工具schema集合也完全相同。
- 两臂各4游戏并发，10只是流容量；strict窗口约1000秒，差异仅为微秒级记录精度。所有已记录动作和完成关都在窗口内。没有新chat/HTTP在deadline后开始；observer无丢事件、会话全部结束、worker无残留。
- 两次缓存清理均有HTTP成功、manifest确认及独立serve.log成功行。没有OOM行。server进程组停止，末次GPU样本显存为0。
- baseline的drain至CPU finish约3.717秒，candidate约11.725秒。迟到成功响应仍消耗生成tokens，但没有deadline后得分动作；不能把这些tokens描述成严格窗口内可用吞吐。

## 初始校验失败的真实原因与修复

baseline tr87的逐游戏日志有56请求/55响应，看似少3918 tokens；candidate ft09有57请求/56响应，看似少2955。原始文件中实际各有一个完整默认日志响应：

- [baseline/requests.jsonl:1](../runs/018-observation-grounding/baseline/requests.jsonl:1) 完整匹配 [tr87最后请求:111](../runs/018-observation-grounding/baseline/tr87-cd924810_p0_requests.jsonl:111)，timing request56返回晚于deadline 2.010789秒。
- [candidate/requests.jsonl:1](../runs/018-observation-grounding/observation_grounding/requests.jsonl:1) 完整匹配 [ft09最后请求:113](../runs/018-observation-grounding/observation_grounding/ft09-0d8bbf25_p0_requests.jsonl:113)，timing request57返回晚于deadline 10.160902秒。

唯一匹配同时要求 messages、tools、action、analysis_step、request_index_within_turn、tool_choice、chat_template_kwargs 七个字段逐值完全相同，绝非按tokens猜归属。合并后8局请求数等于timing chat_begin，响应数等于chat_return，usage tokens等于timing成功生成及benchmark solver_note。正常超时的未完成请求仍与响应分开计数。

冻结 [tool_agent.py:3234](../research/runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py:3234) 根据artifacts里现存state文件数量决定日志名：≤1时使用默认requests.jsonl；[solver.py:742](../research/runtime-bundle/src/ARC3-Inference/inference/framework/solver.py:742) 在游戏结束时删除state。response返回后 [tool_agent.py:6787](../research/runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py:6787) 再次解析日志路径，因此其他游戏结束时最后存活游戏的响应可能转入默认文件。

分析器现只补这一精确匹配路径，保存fallback文件绝对路径、SHA256、原始行、对应请求路径/行和完整identity hash。0/多匹配、重复响应、已匹配请求和非response都保留为完整性错误，不自动放过。补充response的历史快照不计新工具调用。原日志未追加或重写，Notebook、模型和已部署源码未改；本审计的修补没有修改采用字段和门槛。root随后将语义审阅者字段改为准确的attributed reviewer表述。修复后现有018分析validation全部通过，分数完全不变。

首次修补后、尚未传入外部审阅文件时的`pending_manual_review`仅是中间快照，JSON中已单列保存。最终[report.json](018-analysis/report.json)为`validation_passes=true`、`adoption_status=review_supplied`、`adoption_passes=false`。[独立语义审阅汇总](018-adoption-review.json)有14条事件、覆盖8个arm/game，全部引用完整性通过；唯一未通过的采用门是`no_reported_candidate_new_misuse`。审阅归属是具名Codex AI agent，不声称人类审阅。本审计只核对最终状态和引用门记账，没有重新独立认证14条语义判定。最终分析器及报告hash另存于JSON，避免将中间采用状态误当最终结论。

## GPU利用率与成本边界

| 严格1000秒窗口 | 样本数 | 平均利用率 | 中位数 | ≥90%样本占比 | 显存峰值 MiB | 平均功率 W |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 100 | 91.75% | 98% | 91% | 95,685 | 315.09 |
| observation_grounding | 100 | 90.40% | 98% | 91% | 95,873 | 328.57 |

共271个GPU样本、零采样错误。startup至model ready 559.847秒；session内部总墙钟 **2587.887秒 = 0.71886小时，约43分8秒**。这是单卡会话占用的内部记录，不是GPU busy-time、CPU算时、精确能耗或Kaggle计费证明。采样均值没有时间加权；startup和drain独立列出，未将startup空闲混入strict均值。

账户quota快照按SDK显示格式解析，从42,724.952增至52,294.895801秒，差 **9569.943801秒 = 2.65832小时**。它与018内部0.71886小时不同；其他账户作业或统计更新时间、口径未确认，不能把2.6583小时归因于本实验，也不能用它代替本实验时长。两个quota原始字符串和快照hash均保留。

## 解释范围

本次可以确认短筛结果、单因素接入、已记录动作与预算边界、请求账本和资源运行正常。没有因归档误报否定整个实验，也没有为让validation通过而降低证据门。高GPU利用率说明设备忙，不能说明提示有效。018得分和覆盖下降，全通减少；四游戏固定顺序单次结果不构成隐藏榜分预测。是否存在有价值的个别纠错链，应由逐帧、逐请求审阅回答，不应由此次负分或校验布尔值自动判断。
