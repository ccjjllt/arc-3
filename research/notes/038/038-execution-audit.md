# 038：原主循环执行开销与兼容缺陷审计

2026-10-25。读取036完整两臂、25题×2的逐题请求日志，按arm/game/tool_call_id去重；执行两项保存观测上的CPU反例。未运行模型、GPU、游戏或网络，未修改solver模块。

**结论：先建立原样v83正式参考；后续最稳妥的小修是只读`history[*].step → history[*].frame.step`兼容别名。** 它能避免实际出现的接口误用，已有原代码反例通过；可回收开销很小，不能当作金牌幅度的能力改进。

| 036工具结果 | baseline | medium |
|---|---:|---:|
| 去重后的已交付工具结果 | 2291 | 2302 |
| error字段非空 | 226 | 190 |
| 被3072预算截断 | 3 | 2 |
| HistoryEntryView.step缺失 | 6 | 4 |

共4593条结果，仅5条工具截断（约0.109%），集中在lf52/m0r0/sp80；**不支持将扩大工具输出预算作为当前主要优化**。中间截断已经启用。缺响应或最后未再次进入模型上下文的工具可能未计入；这里不是完整HTTP调用计数。

10次`HistoryEntryView.step`失败覆盖ar25、ft09、g50t、su15、tu93、cd82、re86、wa30。现有`FrameView.step`确实存在，而`HistoryEntryView`只有action/frame/result；全部10例下一工具返回不再报错，多数仅改用`h.frame.step`，另有改enumerate/检查dir。对应纠错响应合计2282 completion tokens、740557 prompt tokens（含重复和缓存上下文），请求延迟之和43.346秒。它们不是可保证节省的GPU墙钟：不同游戏并发、修订也可能包含其它推理。失败调用自身生成14518 tokens不能全算可回收成本。

精确10例的原代码、错误/输出、下一次代码与输出、日志行号、chat_template_kwargs、usage及timing request_id见[案例表](../../../experiments/038-analysis/history-step-cases.json)。请求记录未包含的采样参数不作额外推断。

**CPU反事实已复现两个不同游戏。** 从036保存的intermediate_states观测数组恢复ar25的22动作切点与ft09的123动作切点，当前帧与当时请求图片逐像素匹配；所有历史帧和动作仅取到该切点，不执行环境。原失败代码再次产生同一AttributeError，安装实际新helper后原代码通过，stdout与显式`h.frame.step`修正对照逐字相同。已有action/frame/result、repr保持；step直接写入被拒绝；其它level/ascii/_grid等别名仍不存在；卸载恢复原失败。10次真实隔离sandbox调用，无模型/网络/游戏动作。

这里恢复了原片段读取的frame/action历史，未恢复它未读取的result字段或完整agent会话，因此只证明兼容修复。step是已有**动作后frame.step**，不是用户提示中加1后的“下一动作编号”。不能将缺frame自动补0或把整条历史项当frame。

[CPU报告](../../../experiments/038-analysis/history-step-cpu-counterexamples.json) · [实现](../../../src/arc3_research/history_step_compat.py)；实现由本轮构建代理编写，本审计只读验证。原类位于`python_tool_sandbox.py:182`；真实history frame step由`framework/solver.py:1256`构造。

**其它发现的优先级较低。** 20次30秒工具超时覆盖12款游戏，不能用20×30秒当作GPU净损失；其中部分代码含动作。14次禁止import time覆盖9款，既有真正计时搜索，也有`time.sleep(3)`、忙等6秒和未使用导入，直接放开整个模块未必提高效率。7次`KeyError: steps`覆盖5款，是已有空动画合同缺陷的新增病例；历史研究已显示通常很快恢复。NameError等多数涉及临时变量/模拟器本身，不能据此重开持久状态或任意常量捕获。

最新ouyangruize公开v10的cell5包含类似history/transition通用`__getattr__`别名，但同时放宽模块、捕获常量、剥注解、软超时、自动打印末表达式、序列化动画；其别名还暴露`_grid`。本轮不整体搬用。只读step别名有本地10例独立证据，适合单独候选，其它变更仍需要各自的效应证据。

完整计数、候选边界与源码定位见[审计JSON](../../../experiments/038-analysis/execution-audit.json)。本审计不能解释037隐藏正式分数为何回退，也没有新的公开榜得分。
