# 005 — sc25 / tn36 首关停滞与证据交付复盘

日期：2026-10-11（Asia/Shanghai）。范围：005 完整公开集 baseline 的 sc25、tn36，参照 003 baseline 的结果及 tn36 原始轨迹。仅 CPU 阅读日志和 harness；未读取游戏引擎源码，未执行轨迹里的 Python 代码，未写测试文件，未启动 GPU。

## 研究结论

两局都有真实动作探索和三次死亡重置，不能归为“只想不做”。也不能把长墙钟间隔当成持续占用 GPU 的无动作推理：两局较晚进入初始队列，中途各有约 52 分钟动作间隔，但该间隔后挂接的生成 tokens 只有数千。

**目前最具体、可用单一改动检验的缺口来自 tn36：同一 Python snippet 内先试一个控件，再执行别的动作时，原版自动提示只保留末动作的动画。模型又只打印了 no_op 和结算 diff，于是非末动作的暂态元数据没有自动进入模型上下文。** 该模型随后把“蓝圆已经试过，没有效果”当成前提，转向开关组合穷举。005 蓝圆那次的真实中间帧未保存在请求日志中，不能宣称其具体帧数、位移或颜色内容已知。

补充：独立CPU复现已完成，前缀及5个动作末帧均与005保存画面一致；按钮返回7帧、256暂态像素，后3探测无暂态。它不等于恢复005历史中间帧，详情见 [005-animation-replay](005-animation-replay.md)。

sc25 已多次读取并使用具体 timeline，主要可见问题是目标假设未收敛、局部重试条件与全局转移冲突、同色物体提取混淆。它不是上述缺口的同强度正例，可用于检查新增信息是否造成干扰。本轮不建议同时加卡关反思、调度修改或目标提示。

## 来源与定位口径

- 005 原始请求：`runs/005-full-baseline/baseline/sc25-635fd71a_p0_requests.jsonl`、`tn36-ef4dde99_p0_requests.jsonl`。
- 动作事件：同目录 `artifacts/*_p0_events.jsonl`；实际动作数、完成与死亡以这里和 benchmark 为准。
- 使用已修复的 `scripts/compact_requests.py`，产物位于 `runs/005-compact/`。sc25 保留 104 条事件（52 request + 52 response），tn36 保留 70 条（35 + 35）。没有改写 raw。
- 003 对照：`runs/003-goal-evidence-ab/baseline/tn36-ef4dde99_p0_requests.jsonl`，结合 `runs/004-reviewed-compact/`。本次没有读取 003 sc25 的完整请求，其机制不能据结果差异倒推。
- 下文 **raw 行号均为一基**，`messages[index]` 为零基。它们指该消息首次可见的请求快照，不能当成生成时间戳；显示 action 可能比真实 `action_num` 大 1。

```text
005 sc25 requests SHA256
9732f3f0e95cd27b7cd5aea2433c8167d7d23fecb3ddda7481253c96b7e2c1f3

005 tn36 requests SHA256
e0497c9e5c1db2460351cb4b584db681acb9c2344ab38edd52c7b0ea5512f455
```

## 1. 结果与计算曝光

| 游戏 / 运行 | 完成关 | 分数 | 动作数 | analyzer tokens | 首动作 / 末动作秒数 |
|---|---:|---:|---:|---:|---:|
| sc25 / 003 baseline | 4/6 | 47.62 | 371 | 158,928 | 36.0 / 4613.3 |
| sc25 / 005 baseline | 0/6 | 0.00 | 196 | 90,378 | 1036.9 / 5616.7 |
| tn36 / 003 baseline | 3/7 | 13.76 | 286 | 205,271 | 52.2 / 4437.0 |
| tn36 / 005 baseline | 0/7 | 0.00 | 188 | 126,087 | 1484.4 / 6435.1 |

秒数来自各自 `history.wallclock_seconds`，相对 game run；不是 GPU decode 时长。003 为 16 游戏池、4642 秒共享预算，005 为 25 游戏池、7254 秒。sc25 排序由第 6 个变为第 17 个，tn36 由第 9 个变为第 21 个；active streams 都为 10。005 还关闭了研究 warmup RESET。这里只能描述差异，不能将退化归因到某一个变化。

005 的两段大间隔：

| 游戏 | 相邻真实动作 | 墙钟间隔 | 下一动作挂接 generated_tokens |
|---|---:|---:|---:|
| sc25 | 107 → 108 | 3171.7s | 4703 |
| tn36 | 74 → 75 | 3113.1s | 6709 |

这与上下文裁剪后优先级 handover、重新排队的机制一致。源码 `tool_agent.py::_maybe_handover` 只在上下文变化后交回 slot，重算优先级；不能用这些间隔证明模型“空想 52 分钟”。末动作到取消之间，analyzer 与 history+final token 口径的残差分别只有 486、791；这些残差仍不是完整服务计费。

005 sc25 在真实动作 54、106、161 死亡，随后自动 RESET 55、107、162；tn36 在 61、123、185 死亡，自动 RESET 62、124、186。两局最终均是共享墙钟截止后的 `cancelled`，没有过关。

## 2. tn36：早期否定关键控件后转向组合穷举

### T1：非末动作只留下了结算反馈

005 **raw 11**，调用 `call_47eda6c967b54874830126f5`（assistant `messages[11]`、tool `[12]`）：

```python
probes = [(55,35,'blue blob'), (45,21,'T glyph black'),
          (45,36,'T glyph gray'), (20,20,'checker cell')]
for r,c,name in probes:
    before = current_frame
    res = action([{'action':'MOUSE','row':r,'col':c}])
    after = current_frame
    log.append((name, res.get('no_op'), res.get('gameplay_changed'),
                compact_diff(before, after)))
```

工具返回把蓝圆写为 `True, False`，结算 diff 只有 HUD 的 1 格变化。四个真实动作分别是动作 2–5；蓝圆是第一个，最后一个是棋盘 `(20,20)`。代码没有保存或打印每次 `res['animation']`，也没有在蓝圆之后立即读取动画。

该 snippet 后的 user prompt 列出四次动作，却没有暂态 cue。这里与 004 的“下一轮 user 已经有同一个 bbox 句”不同：**这个关键非末动作没有获得那条自动 cue**。这只是模型收到内容的事实，不证明该按钮在 005 当时产生了某段特定动画。

### T2：局部 no-op 被扩展为控件无效

005 **raw 17** 的推理将蓝圆写成 `The blue disc: tested no-op.`；**raw 21** 又明确推断 `no_op=True suggests truly nothing.`。原版 `no_op` 实际只描述结算帧内区变化，不包括已回到原色的暂态。

此后模型承认可能要“设置开关后执行”，但沿用蓝圆无效的判断，把十个可切换条/杆当成 1024 种候选目标配置。动作事件中，蓝圆区域 `(55,35)` 只被点击这一次；其后没有同一蓝圆的重试。这个统计来自实际坐标事件，不能从 API 名称频率推出。

### T3：没有执行控件的开关穷举

005 **raw 37** 将多个全同色配置排成 14 次点击；**raw 51**（调用 `call_fb21052d09904985ac8dad65`）固定 bars 为初态、用 Gray code 穷举 stems，stdout 为 `sweep done clicks 33`；**raw 59**（`call_2ffa84c353164cf4b9edfcd2`）又固定 stems 穷举 bars，返回 `bars sweep clicks 31 states 31`。

这些代码检查 `level_completed/game_over`，确实执行动作；没有发现程序执行语义。其间三次耗尽栏并 RESET，仍停在首关。不能从该轨迹直接断言“提醒一次就会过关”，但可以定位错误探索依赖的前提。

### T4：晚查动画只能得到最近开关的结果

005 **raw 61**，`call_757e073dadec4cfa949ff6c3`（tool `messages[38]`）：模型想到暂态可能包含反馈，终于读取 `last_animation_timeline/frames`。返回：

```text
action_num: 165
action_display: MOUSE(row=42, col=31)
timeline: {'error': 'No animation is available: the last executed action returned a single frame.'}
frames: 0
```

这个返回只涉及动作 165，不能用于否定动作 2 的暂态。历史保留了各动作的紧凑 metadata，但最后一段原始帧链已经被覆盖；模型没有通过 history 查询旧按钮 metadata。

### T5：003 的可比观察链

003 baseline **raw 11** 的蓝圆 `(55,37)` 是单独一次 snippet。stdout 同样写 `NO-OP`、结算 `changed 1`，但下一 user 给出 **7 帧 / 256 暂态格**。**raw 13** 立即读 timeline，出现 `Y>c / B>Y` 等位移事实；**raw 25** 在 RUN 后读取逐帧 yellowrows，修正为 bars 控制程序；**raw 31** 把 bars 配好再 RUN，真实动作 13 完成 L1。

003 goal_evidence **raw 13** 的同一坐标 `(55,35)` 也有 **7 帧 / 242 格** cue，随后读取实际帧；这证明该坐标曾是有信息的控件，却不提供 005 那次的具体帧内容。

003 两臂与 005 的初始可见 board_ascii 相同，第一次 `(14,31)` 后的可见 board_ascii 也相同。它提高了比较的相关性，不等于潜在状态或后续路径完全一致。003 成功链和 005 失败链的差别仍受随机生成、排序与曝光影响，没有候选干预的因果成绩。

## 3. sc25：动画已读，目标与局部代码仍未收敛

| 005 raw 定位 | 已收到的事实与代码 | 研究解释及边界 |
|---|---|---|
| **9**，`call_36be09d18a494e13886f63e6` | 初始 UP 结算不变；立即读 5 帧 timeline，看到四个白格依次 `W>N` 后返回。 | 此处自动 cue 和主动读帧都工作，不能归为 tn36 那种非末动作反馈缺口。 |
| **25**，`call_3c77a001b6574caaafce93a0`；**49**，`call_e09b220a3c8b4252a761cae9` | 完成四格图案后清盘，上方对象缩小；raw49 的 11 帧包含格子 `N/W>p`、上方 `b>p>b`、末尾 `b/S>c` 后恢复。 | 模型实际读到多阶段反馈，仍在“匹配→缩小→送到左端”等目标假说间反复。这里尚未找到短暂态元数据能直接补上的明确事实缺口。 |
| **45 / 47 / 63 / 77** | 多轮 LEFT/RIGHT 位置扫描，检查 completion；没有完成。 | 属于真实行动的目标探索，不能按低关数归为不行动。是否存在更好的目标判别实验尚未验证。 |
| **71**，`call_d00d6c7a17f44b11b1197422` | 明确写 `burn to reset`，最多 32 次 RIGHT，实际在循环第 25 次索引处 GAME_OVER。 | 模型有意识用动作耗尽栏换 RESET。它消耗动作但非程序死循环；是否应开放/使用 RESET 属于另一个干预，本轮不混改。 |
| **73**，`call_b9e257d134394d6ca1b53c65` | `setcell` 重试到某格等于 `N`。最后一格完成整体图案导致全格清空，重试又点击一次，留下一个多余绿色格。**raw97** `call_5cff641efc404bcca0f676ed` 再现，raw99 推理承认 retry 在 wipe 后多点了一次。 | 可见的局部目标与全局事件冲突。一次额外点击未导致立即死亡，不能据此解释全部 0 关；属于后续可研究的动作工具使用问题。 |
| **77**，`call_93d967cfb2174d4e85f6bcd6` | `info()` 把 rows17–23、cols16–43 内所有 `b/S` 视为运动对象。左侧固定 handle 同色也落入范围，扫描结果位置始终 `(17,16)`，只是长 pose 字符串变化。 | 物体提取混淆已能从代码和输出确定。模型仍会看其他 crop/图像，所以不能断言错误 helper 单独造成失败。 |

另有返回类型或缺字段错误（raw11 的 `res[0]`，raw69/87/91 对无动画字典取 `action/frames/steps`，raw79 对返回 None 的 helper 调 `.items()`）。模型有时自行恢复，不建议本轮据这些个例增加通用验证调用。

sc25 的 003 baseline 确实完成 4 关，但本次没有其完整请求对照，不能断言 005 只要继承某一个提示就能恢复这 4 关。若下一轮只修非末动作 metadata，sc25 可观察是否少丢事件、是否增加输出负担；未预设它会提高分数。

## 4. 原版数据通道：哪些覆盖，哪些仍可用

实际底座：`research/runtime-bundle/src/ARC3-Inference/`，与 005 arm metadata 的 tool_agent.py SHA256 一致。以下只检查 harness 如何处理公开观察，没有读取游戏规则。

| 位置 | 实际行为 | 实现含义 |
|---|---|---|
| `inference/framework/solver.py::_execute_action`，约 1271–1294 | 每个非 RESET 动作计算 `summarize_animation(chain)`；`animation_record` 每次执行都替换，单帧动作可清空。 | 原始历史帧链只有最近动作，不要声称通过 history 可恢复旧完整 timeline。 |
| 同文件约 **1330–1342** | 聚合 batch 之前，每个真实动作写入 `HistoryEntry.result`；保留 `executed/action_num/level/action_display/gameplay_changed/no_op/animation/automatic` 及终局 flags。 | **每个动作的紧凑动画 metadata 仍在 history，包含 batch 内非末动作。** 无需深入环境内部。 |
| `step_env`，**1158** 起 | `final_payload=dict(executed_payloads[-1])`，再加整个 batch 的计数/动作列表等。 | 单个 `action([...])` 返回聚合结果，animation 仍属于最后一动；只收集 action-call 返回列表不足以覆盖 batch 内每动。 |
| `tool_agent.py::_ascii_history_view_payload`，**2843** 起 | 将各 `HistoryEntry.result` 原样放入公开 Python history/transitions。 | 新摘要可从原模型已可访问的证据读取，不引入新权限或信息来源。 |
| `_handle_action`，**5862** | 每次 action-call 覆盖 `_last_animation_chain`。 | 多次 `action()` 的 Python snippet 也会覆盖早先帧链。 |
| `_summarize_step_sequence`，**3785** | `animation = executed_results[-1].get('animation')`。 | 下一 user opener 只自动描述 snippet 最后执行结果的动画。 |
| `_run_python_tool`，约 **5915–5932** | 有 stdout 就使用 stdout；只有无 stdout/无显式 result 时才回退 action result，多个 call 也只给 last_action_call_result。 | 模型选择只打印 no_op/diff 时，非末动画 metadata 虽在 history，但没有自动展示。 |
| `_append_action_viewer_event`，**825** 起 | action events 不保存 animation 字段。 | 仅凭下载的 005 events 无法重建早先按钮的帧数或轨迹。 |

“丢失”应精确表述为：原始旧帧链被覆盖、非末动作 metadata 未自动交付；不能说所有证据已从运行状态消失。

## 5. 建议的单一候选：补交非末动作暂态 metadata

建议优先研究这一窄候选，不同时修改调度、目标提示、动作停止规则或每轮反思。最低 hook 不需要改变 solver：

1. wrapper `ToolAgent._run_python_tool`，调用原函数前用已有 `load_runtime_state(state_path)` 记录 `before_step`。
2. 原调用完成后再次读取同一 runtime 的 history，只查看本 snippet 新增且实际 `executed=True` 的动作。用真实 `action_num` 去重，不按提交列表长度推算，不将跳过或拒绝动作列为执行。
3. 从 `HistoryEntry.result['animation']` 取 `frames/transient_pixels/transient_bbox`，附实际动作号、动作、level 及必要的 before/after level。只对非末真实动作中 `transient_pixels>0` 的事件新增短输出；末动作沿用原 cue，减少重复。
4. 将这些事实放进原工具 JSON 的独立字段，例如 `earlier_action_transients`，不依赖模型主动 print 或特殊 marker。保留原 stdout、dispatch flags 和全部真实动作行为，不多发 LLM 请求。
5. 识别 `automatic=True` 的 RESET：它不应使死亡前的最后一次玩家动作被误分类为普通中间动作。game_over/level_completed/run_complete 只作事实标识，不据其宣布机制或目标。

首版只用已经保存的 metadata，就能检验“被结算 NO-OP 掩盖的非末暂态是否被注意到”。这些 metadata 没有物体位移方向，不能伪装成完整时序事实。如果希望提供旧逐帧颜色/位置，需要在帧链覆盖之前增加更深的捕获，属于下一层实现，不要混进首次对照。

限制输出长度、记录遗漏计数而非无上限堆文本。日志应带 runtime/game、真实 step/level、哪些事件被交付、哪些因限长省略；是否被采用仍以之后的工具/推理人工判断，不以 API 名称频率判断。

可观察成功路径是：在类似 tn36 的早期多控件探测中，非末事件实际产生并被交付，模型随后将 no-op 限定为结算帧结果、重新检查有暂态的控件，再比较首次过关与总覆盖。这条路径需要真实运行检验，不能从 005 反向宣称“若补丁存在一定会过 L1”。若很多事件交付后仍不改变相关判断，或者正文膨胀伤害原本能解的游戏，应据结果暂停或收窄。

当前交付仅为研究与最低 hook 建议，尚未实现候选、未运行 006。
