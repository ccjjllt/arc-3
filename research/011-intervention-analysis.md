# 011：旧动画交付、实际采用与晋升判断

日期：2026-10-13。**本次仍不晋升正式 solver。** 011 证明旧帧能被取回、进入后续请求并用于修正局部理解；没有重复出稳定的净通关收益。尤其 tn36 本次零 archive 查询仍完成 4 关，而 baseline 为 1 关，不能把两轮重复的 +3 关解释为“历史检索重复产生 +3 关”。总分复算见 [011 结果报告](011-results-analysis.md)，这里仅审查采用链。

| 交付指标 | 010 | 011 |
| --- | ---: | ---: |
| 实际动作 capture / available | 2,290 / 2,290 | 2,517 / 2,517 |
| 原始返回帧数 | 8,030 | 9,067 |
| list / get | 19 / 29 | 19 / 25 |
| get 命中 / miss | 28 / 1 | 25 / 0 |
| nonlatest 命中 | 28 | 22 |
| 不同命中引用 / 重复命中 | 13 / 15 | 14 / 11 |
| 任意查询游戏 / 实际 get 游戏 | 4 / 4 | 5 / 4 |

011 的 25 次命中分布为 bp35 17、m0r0 4、sp80 3、su15 1；另 sc25 只有一次 list。3 次 latest 命中全部在 bp35，不能把全部 get 都称为旧信息恢复。两轮环形日志都完整保留全部查询。011 峰值存储 JSON 38,995,852 bytes，capture/query 的线程 CPU 分别 4.197/0.557 秒；10,225,768 response JSON bytes 是 IPC 数据量，不是模型 prompt 或完整端到端成本。

精选 3 局共 29 个含 API 的 Python 调用，均按 tool_call_id 对齐到原始 requests 中的 assistant 调用和 tool 返回。一个 Python 调用可能发多次 list/get。字段、来源 hash 与摘录分别在 [query-index.json](../experiments/011-intervention-analysis/query-index.json)、[selected-evidence.json](../experiments/011-intervention-analysis/selected-evidence.json)、[source-hashes.json](../experiments/011-intervention-analysis/source-hashes.json)。只读解析，没有执行日志代码或新增运行。

## su15：有局部采用，不能把后续净多一关归因给它

候选完成 action 6 后，list 显示真实引用 1–6，再读取旧 action 3 的 5 帧，观察紫色块中间移动及短暂遮挡；发生在 L1 尚未完成时。随后提出短距离点击假设，先有一次无效探测，再按新的观察推进，action 13 完成 L1。[候选 events L15、L17、L23](../runs/011-animation-confirmation/retrievable_animation/artifacts/su15-1944f8ab_p0_events.jsonl)，对应 API requests L23/L25。

这条“读取→解释→新探测→后续通关”的时间链成立。但 action 3 当时的原 latest/settled 输出已经显示位移；模型在首次查询前也已经写出“三步移动”。新增读取主要细化了中间过程，不能说原接口无法学习该机制。baseline 未安装 archive，也在 action 8 完成 L1，比候选少 5 次动作。[baseline events L15](../runs/011-animation-confirmation/baseline/artifacts/su15-1944f8ab_p0_events.jsonl)。

候选之后在 action 34/55/72 完成 L2/L3/L4，没有再调用 archive；baseline 本局完成 3 关。因此有真实局部采用，但单次 L1 查询的独立贡献尚未从后续实验、轨迹和资源分配中分离，不能直接宣称它带来第 4 关。

## bp35：恢复镜头运动和死亡过程，调用最多仍停 L2

候选 action 17 后找回 action 16 的 47 帧，先把玩家屏幕位置变化理解为“上去又回来”，随后通过粗粒度图及跨帧匹配修正为镜头滚动。这是旧帧提供了可辨别的局部证据。之后又读取一段上升/滚动动画，action 33 完成 L1。[events L26–28、L42–44](../runs/011-animation-confirmation/retrievable_animation/artifacts/bp35-0a0ad940_p0_events.jsonl)，API requests L29–37、L49/L51。

L2 里查询死亡前后的帧，排除 HUD 像素污染，比较角色、障碍及水域变化；不是所有重复 get 都是原样空读。不过该局 17 次命中后仍只完成 1 关；baseline 也是 1 关，但 L1 只用 16 动作，候选用了 33，AE 为 2.2222→0.8999。011 的查询比 010 更早：010 bp35 的 +1 关发生在首次 archive 读取之前，011 则有读取后通过 L1 的链，仍没有新增完成关卡的对照收益。

另有 **3 次调用方 IndexError**，尽管 archive get 全部 hit：一次差分下标越界；两次用预想帧数筛选记录再无条件取 `[0]`，找不到匹配项。后者实际存在 raw 帧数和原 latest 去重帧数差异，模型列出 refs 后自行纠正；不是 archive 丢帧或 silently fallback。见 requests L81/L107/L127、events L66/L101/L114。它说明“命中率 100%”并不意味着模型侧使用无摩擦。

## m0r0：查询发生在前三关之后，关键纠正还依赖稳定历史

候选已于 action 26/66/138 完成 L1/L2/L3。到 action 159 才首次查询，并四次读取 action 150/154 的 8 帧，恢复“先正常移动、进入异常区域、闪烁、最后返回同一位置”的时序。[events L215–216](../runs/011-animation-confirmation/retrievable_animation/artifacts/m0r0-492f87ba_p0_events.jsonl)，requests L195–203。

模型据此修正过纯平移解释，但又提出弹出、传送、连锁反应等假说。到 events L223，比较既有 L4 初始 history 才发现返回位置正是初始态，纠正了先前把首次移动后的位置误记为初始位置的问题。旧动画提供了异常事件过程；“固定落点是初始态”的决定性对应来自稳定历史对照，不能全归给 archive。

后续有新规划和动作，但预算结束仍未完成 L4；本局 baseline 完成 5 关，候选 3 关。前三关早于所有 archive 查询，不得算作查询收益。这与 010 相反：010 m0r0 是最大加分游戏，却完全没有调用新 API，进一步显示单游戏分差和工具调用之间没有简单对应关系。

## 合并判断

sp80 的计数也不支持把已过关归功查询：011 唯一完成的 L1 在 action 10，第一次 get 正是读取 action 10 且标记 nonlatest，因此旧帧读取晚于这次完成；最终 baseline 3 关、候选 1 关。该时间关系由 benchmark 完成边界及完整 archive ledger 可直接核对，本次未扩大下载其请求轨迹。

010 的 tn36、011 的 bp35/su15 都有真实信息读取和局部规则采用，故结论不是“工具无用”或“零采用”。但 011 全池 AE 33.9794→32.1157、42→41 关；010/011 的简单平均差 +1.0113 仍是两个固定顺序会话的描述量。加上 tn36 在零查询条件下重复出现相同关卡优势，目前缺少将可重复净收益连到旧帧使用的证据。

保留模块和案例，正式 solver 继续使用原基线。本次材料优先支持后续研究精确引用、计算结果复用和规则验证；不支持为追求晋升而继续叠更多帧、自动摘要或修改调度后仍将总结果归因给 010。
