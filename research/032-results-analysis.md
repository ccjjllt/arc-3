# 032 成功关卡记忆：结果与提交进展

2026-10-22 08:43北京时间最新查询：**正式submission57481712已COMPLETE，public30.20；较009 v2／57101330的31.16低0.96，未实现本次正式提分。009继续作为已知公开榜最佳保留。** GetSubmission与提交列表两处一致，冻结源码与正式版本均未改变。[正式原件](../experiments/032-formal-result-snapshot.json)。

| 正式版本 | submission | public分数 | 较009 |
|---|---:|---:|---:|
| 009 v2 | 57101330 | 31.16 | — |
| 032记忆v1 | 57481712 | 30.20 | −0.96 |
| 030持久化v1 | 57447779 | 24.40 | −6.76 |

这次结果说明，公开短跑+25.655和全25题跨会话+11.140没有转化为此次正式公开分提高。它不证明全部记忆方案无效，也不能把回退直接认定为随机噪声。实际经验复用是机制证据；净收益和隐藏迁移仍需各自的结果支持。候选49.21798没有超过005历史基线49.89969，原baseline38.07781偏弱及跨会话波动限制了+11.14的外推可信度。

正式episodes为空，DownloadSubmission返回403；GetSubmission未提供隐藏逐题、正式求解日志、覆盖或运行时长，因此目前不能确定−0.96来自哪些游戏，也不能断言正式资源无问题、错规则pin导致退步或记忆成本耗尽预算。保存smoke与开发池日志不能替代正式日志。[可用性查询](../experiments/032-formal-diagnostics-availability.json)。

决策：保留009；停止032 v1原样重提及扩大，不以再跑baseline解释掉正式回退。保留r11l/vc33等真实经验→程序→行动证据，记忆作为后续可纠正的辅助候选。下一研究重点应回到准确输入、当前目标/动力学计算、实际程序执行的闭环：033准确像素未进入目标重算，su15已有guard却漏报真实失败，均比继续堆摘要更接近已定位能力缺口。这是研究优先级调整，不把尚未实现的新方案当作下一份高分submission。[独立结果评估](../experiments/032-memory-analysis/formal-result-assessment.json)。

全25题记忆候选补跑已COMPLETE，49.21798分、108/183关、7题全通。本轮与先前保存baseline作跨会话描述性比较，38.07781→49.21798（+11.14017），96→108关、4→7全通，13题涨、8题跌、4题平。两个模型服务会话不同，不能称同会话A/B或稳定增益。

| 全25题指标 | 已保存baseline | memory补跑 |
|---|---:|---:|
| 均分 | 38.07781 | 49.21798 |
| 完成关 | 96/183 | 108/183 |
| 全通游戏 | 4 | 7 |
| 动作 | 4747 | 5645 |

候选25题均有分数且按官方动作公式复算一致，原题序、7254秒、10 streams、warmup1、deadline=false及冻结helper/基础solver保持一致。7 won、11 cancelled、7 gave_up均为有效终态；gave_up不能直接译为模型主动认输，部分末尾是deadline附近请求超时。CPU退出0、无残留线程或强制退出，GPU进程组已关闭。会话8458.23秒（2.3495h），加载1110.88秒；进程7341.33秒包括排空和导出。动作挂接生成token为4540800→4413799；baseline分析器计数缺3题，不能直接与候选完整25题总计比较成本。

最大涨题为r11l、vc33、tr87、cd82、ka59；最大退步为s5i5、su15、sc25。短跑5涨0跌的模式没有在全25题延续，因此保留方向和已提交版本，继续用实际轨迹解释收益/回退，正式结果已为30.20；不原样重提、不追加另一轮baseline门槛。[逐题比较与背景](../experiments/032-memory-analysis/recovery-comparison.md)。

2026-10-21，`qingyu1232/arc3-032-memory-short` v1 COMPLETE。10题、两臂各2700秒、10 streams、相同009模型与求解配置。**均分45.00597→70.66115，+25.65519；40→53关，3→4题全通，5题上涨、5题持平。** 原full会话因runner退出检查误停，只完成baseline；该会话没有memory候选结果，后来仅补候选完成，见上方。032 v1已真正提交比赛，编号**57481712**，现已COMPLETE／30.20。短跑分差是开发集结果，不能直接换算成榜单提升或奖牌预期。

| 游戏 | 基线 | 记忆候选 | 完成关数 |
|---|---:|---:|---|
| cd82 | 1.5592 | 99.6087 | 2→6 |
| m0r0 | 0 | 71.4286 | 0→5 |
| r11l | 21.1195 | 71.4286 | 3→5 |
| sc25 | 47.6190 | 71.0505 | 4→5 |
| tu93 | 33.3333 | 46.6667 | 5→6 |

ar25、ft09、tr87两臂均为100，re86与sp80持平。整体生成token按分析器完整口径为1,517,784→1,549,942，约+2.12%；动作2153→2257，同时完成更多关。超时未返回的成本不能当零；并发请求时间之和不能当GPU墙钟。会话6845.83秒，加载1398.07秒，结束后服务已关闭。

候选包含两个渠道：通关后在已有请求中主动总结规则，以及历史裁剪后固定经验。49条已通关事实被记录，40条模型规则被捕获，415次成功请求带记忆；这些计数本身不等于收益。完整下载后的分析器索引出27个记忆交付审阅窗口，五题轨迹与实际request payload已交叉核对。窗口是审阅入口，不是27次独立收益。实际轨迹已确认：r11l将质心/交换/足迹约束写进规划器；sc25复用泵、步长和代码操作经验，重置后组合控制代码；tu93回读旧死亡转移修正守卫/巡逻者模型并分段执行通关。cd82在首次pin之前已将L1规则用于L2，后续用遮罩模拟校验目标再行动；m0r0从碰撞模型扩展到token和门。

因果范围要保留：cd82与m0r0首次通关早于本局任何成功记忆；不能把首次发现或全部分差归因于记忆。主动反思与裁剪后pin的独立贡献也没有分离。规则是模型假设，会冲突、修正或未正确落实为代码。m0r0存在引擎未显式RESET的软重置，动作摘要混入失败片段，因此不是纯成功路线或最短计划；没有看到直接照抄失败尾部的证据。

`zhuating/arc3-032-memory-full` v1最终ERROR，原计划为25题、每臂7254秒。实际manifest仅有baseline：25/25题均有可复算分数，均分38.077806，完成96/183关、4题全通、4747动作，CPU子进程exit_code为0。旧runner把退出前记录的`harness-game_1`、`harness-game_17`线程快照仍当作阻断条件，抛出`Arm baseline has undrained workers`，没有启动memory臂；最后模型服务已关闭。该故障不构成memory负证据，也不能称25题A/B已通过。

这次baseline仍提供了波动背景：与short重叠的10题均分为50.291923，高于short baseline的45.005966；m0r0和sc25在没有memory的另一轮也达到5关，而tr87从short的100降至4.761905。因预算、并发竞争和轨迹不同，这不是替代A/B对照。它说明short的全部分差不能直接归因于新增机制；五题正向结果与实际复用链仍支持进行一次正式探索性提交。

正式候选`zhuating/arc3-032-memory-submission` v1已GPU保存COMPLETE，报告passed：health200、两题均有真实非RESET动作和生成内容，官方未计分placeholder已生成。远端cell与冻结源码匹配。**北京时间2026-10-21 20:29:45真正提交成功，编号57481712；团队ccjjllt、提交者zhuating，来源v1的scriptVersionId为360713071。** 提交后独立读取列表已确认新编号；10月22日正式结果COMPLETE／30.20，低于009/31.16；不原样重推候选，保留009。保存通过证明能运行，不证明隐藏分数提高。

正式提交与补齐候选研究并行推进，不再把重新完成一轮full A/B设为提交或候选补跑的前置。研究侧已修正退出判断：保留退出前线程快照作为诊断，判断实际CPU进程及进程组退出；没有改变冻结solver或serving。`zhuating/arc3-032-memory-recovery` v1已COMPLETE，远端逐cell匹配，仅补缺失的25题memory候选，7254秒设置保持不变，外层上限14400秒。新会话与现有baseline的比较标为跨会话描述性证据；实际补跑49.21798分，详见上方。实际正式结果已低于009，开发池正向没有成为本次榜单提升。

补跑正向机制审阅中，r11l、vc33、s5i5共25次真实tool代码/stdout与完整transcript精确匹配，12条捕获规则对上真实模型回复；成功带记忆请求的数量与hash集合也一致。r11l把旧关质心/足迹约束写入搜索，L4实际16次点击过关，L6扩展L5染色井规则后全通；vc33将L4守恒水量与橙门条件旋转用于L5，后在L6/L7识别柱子污染水位读取，修改程序再执行并全通。s5i5虽实际回读L1经验，未构成完整L2程序；红点在step43已消失，首次pin在request65/nextaction47之后，不能倒置归因。summary.active=false是推理计时再次包装方法造成的identity诊断，实际请求已包含记忆；不是helper未运行。[完整机制审阅](../experiments/032-memory-analysis/recovery-mechanism-review.json)。

补跑退步审阅已核对实际request代码和执行输出：sc25的L1总成本126动作、baseline36，额外90动作在首条通关记忆产生前已发生；首次pin在request line109、step148/L3。摘要中的24是最后一次RESET后的成功尝试，不能当作L1完整成本。su15前三关更快，但L5双追兵未解；模型生成的`guarded()`只按固定tag与p/Y缺失判断，实际D1/W1等调用绕过条件，材料被吃甚至玩家消失后仍打印`ok`，后来才观察到失败并UNDO。baseline则通过gmove3模型和beam搜索实际7次点击通L5。这两题有真实回退，但未确证“旧错误记忆→坏行动”；它们分别暴露前置探索波动、当前关动力学模型和未落实的执行检查。[代码/输出原件索引](../experiments/032-memory-analysis/recovery-regression-review.json)。

来源：[完整分析](../experiments/032-memory-analysis/summary.md)、[cd82/m0r0轨迹审阅](../experiments/032-memory-analysis/cd82-m0r0-review.json)、[r11l/sc25/tu93轨迹审阅](../experiments/032-memory-analysis/r11l-sc25-tu93-review.json)、[full baseline独立评估](../experiments/032-memory-analysis/full-baseline-assessment.json)、[短跑记录](../experiments/032-launch.json)、[全池记录](../experiments/032-full-launch.json)、[保存记录](../experiments/032-save-launch.json)、[正式提交前版本核对](../experiments/032-before-formal-submit.json)、[提交后列表确认](../experiments/032-after-formal-submit.json)。

补跑原件：[启动记录](../experiments/032-recovery-launch.json)、[源码匹配](../experiments/032-recovery-source-check.json)、[冻结来源](../experiments/032-memory-recovery-source/preparation-manifest.json)。
