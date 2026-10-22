# 004 — lf52-271a04aa 轨迹归因

> **2026-10-11 复核说明：** 本文最初使用的 compact 按消息长度去重，在上下文裁剪处会漏消息。下文原始盘点数字和三阶段计数保留为旧口径，不再作为当前统计结论；统一以 [004-review-data](004-review-data.md) 的原始日志新统计为准。已有 episode 引文与事件定位保留，不能把旧摘录当成完整轨迹。004 候选未实现、未做反事实对照；表中评价只描述现有证据支持程度，不能证明候选有效或无效。

日期：2026-10-11。只读 003 compact 请求与 events；未读游戏引擎源码，未启动 GPU。  
来源：`runs/003-compact/{baseline,goal_evidence}__lf52-271a04aa_p0_requests.compact.json`，`runs/003-goal-evidence-ab/{baseline,goal_evidence}/artifacts/lf52-271a04aa_p0_events.jsonl`，arm-metadata / benchmark。

引用用 compact JSON 的 `analysis_step` / `action`。模型自称的 peg / lock / ferry / key / shake 只当作轨迹里的工作假说，不是引擎规则。

## 结论

两组都完成 **3/10** 关后因共享墙钟预算取消（`soft_deadline_fired`），不是通关。baseline **7.73** 分、动作 `[15, 57, 116, 23]`；goal_evidence **10.91** 分、动作 `[10, 65, 58, 49]`。覆盖相同，分差来自 L3 动作效率（116 vs 58）；GE 已碰到 3/10 的完成覆盖上限。动画 API 与 user-prompt 暂态句已经大量存在（user cue 38 / 48）。模型在 L1 会读 `last_animation_timeline` / `last_animation_frames`，并把“选中环 + 灰色幽灵”更新成跳跃预览；L2 起几乎不再读帧，改看 settled ascii、`frame_diff` 和下一条 user cue。Harness 在 settled 不变时打印 `NO-OP (executed, no change inside the board area)`，同一回合的下一条 user 句却写 `left the board area unchanged, but it was not a no-op`（16 格 / 3 帧）。模型下一轮通常把这解释成 shake / 非法跳跃，这表明已有 cue 被采用，但不排除更早交付或不同表示的作用。L4 停在相机滚动坐标、锁与钉子目标假说和预算。**004 候选的关卡效果未验证**。帧数 / 格子数 / bbox 已在下一条 user prompt 中，但它们不等于完整的逐步颜色或位置事实。现有摘录尚未建立值得立即开 GPU 的收益证据，保留观察交付与解释问题供后续研究。

## 两组完成关 / 分数与停止原因

| | baseline | goal_evidence |
|---|---|---|
| 分数 | 7.7320 | 10.9091 |
| 关卡 | 3 / 10 | 3 / 10 |
| 完成覆盖上限 | 10.91 | 10.91 |
| `actions_per_level` | `[15, 57, 116, 23, 0…]`（合计 211） | `[10, 65, 58, 49, 0…]`（合计 182） |
| 记录 tokens | 176,221（analyzer 179,731） | 238,898（analyzer 247,596） |
| compact 请求 | 109 req / 105 records | 137 req / 131 records |
| 状态 | `cancelled`；`stop_reason` 缺省 | 同左 |
| 预算 | 共享 4642s，`soft_deadline_fired=true` | 同左 |

Events 过关动作（`level_completed=true`，随后 `level` +1）：

- baseline：L1→L2 `action_num=15` `analysis_step=9` `MOUSE(row=44, col=43)`；L2→L3 `72` / `24` `MOUSE(row=52, col=51)`；L3→L4 `188` / `49` `MOUSE(row=48, col=26)`。停在 L4、`action_num=211`、`analysis_step=67`。
- goal_evidence：L1→L2 `10` / `6` `MOUSE(row=43, col=42)`；L2→L3 `75` / `34` `MOUSE(row=53, col=51)`；L3→L4 `133` / `51` `MOUSE(row=49, col=25)`。停在 L4、`action_num=182`、`analysis_step=76`。

GE 分数碰到上限，是少动作，不是多过关。两边最后都在 L4 画格子 / 滚屏，没有 `won`。

## 三阶段旧计数（以复核新统计为准）

阶段 1 = API/提示已经提供；阶段 2 = 模型代码真正读了相关动画对象；阶段 3 = 随后推理根据这些证据改了假说。compact 的 `reads_animation_api` 把 `frame_diff` 也算进去，与“读了相关帧”不是同一件事。

| 阶段 | 口径 | baseline | goal_evidence | 例子 |
|---|---|---:|---:|---|
| 1 已提供 | user 消息 `animation_lines` 非空 | **38** | **48** | “animated over N frames. X cells changed and changed back around rows … cols … `last_animation_timeline` shows them.”；其中 **not-a-no-op** 句 baseline 2、GE 4 |
| 1 已提供 | python 全局 `last_animation_timeline` / `last_animation_frames`；`action()` 返回里已有 `animation: {frames, transient_pixels, transient_bbox}` | 全程 | 全程 | baseline `analysis_step=2` 自己写了 `print({k:v for k,v in r.items() if k!='animation'})`，把已有字段滤掉 |
| 2 真正读帧 | 代码含 `last_animation_timeline` 或 `last_animation_frames` | **5 次 / 4 个 (step,action)**：`(2,2)(3,4)(4,5)(11,22)`；**0 次 frames** | **4 次 / 3 个**：`(3,3)(5,5)(15,26)`；其中 2 次同时读 **frames** | 见下表 |
| 2 对照 | compact `reads_animation_api`（含 `frame_diff`） | **9** | **24** | 与 inventory hint 一致；GE 多出来的几乎全是 `frame_diff`，不是时间线 |
| 2 对照 | 同 step 有 user cue 且读了 timeline/frames | 4 / 38 cue | 3 / 48 cue | L2 之后 cue 仍在发，代码不再查时间线 |
| 3 由时间线/帧更新 | 上述 2 的每次读是否改了假说 | **4/4 step 都更新**（`(11,22)` 第一次 KeyError 后重读成功） | **3/3 step 都更新** | 选中+幽灵；跳跃位移；钉子变灰+钥匙从底部升起 |
| 3 仅由 user cue、未读 API | 随后推理引用 16 格 / shake | 少（早期改读 API） | 多次 | GE `(38,79)` “shake animation (16 cells…) — no legal moves” |

User cue 量级（决定 004 长度阈值，不是预设开关）：帧数 `{2,3,6,7,8,16,19,20,22}`；格子数 4–3568。baseline 中位数 6 帧；GE 中位数 3 帧。≤3 帧的 cue：18 / 27。≤16 格：12 / 14。≥16 帧或 ≥1000 格的是过关/重置/相机滚动，不是局部暂态。

## 关键 episode 表

标签允许叠加。004 候选 = 把来自真实 `last_animation_frames` / 动作元数据的**紧凑局部时序事实**写入**现有 python 工具返回**（观察事实，不宣布胜利规则，不另加“请看动画”）。

| 臂 | step / action | 工具返回事实（引 stdout） | 随后推理 / 代码 | 标签 | 004 候选的现有证据支持 |
|---|---|---|---|---|---|
| B | `2` / `2` | stdout：`[action] MOUSE(row=13, col=12) -> NO-OP (executed, no change inside the board area)`，`no_op: True`。下一 user：`animated over 6 frames and left the board area unchanged, but it was not a no-op: 48 cells … rows 16-23, cols 15-22`。同 step 第二段代码 `print(last_animation_timeline)` → 6 步 `W>b`/`b>W` 闪。 | “clicking at (13,12) caused an animation at cell (rows 18-21, cols 17-20) — a flash outline”。随后继续 probe 时间线。 | observation miss（当回合被 NO-OP 带偏，下一 snippet 已读时间线） | **已在后续查询中采用时间线。** 更早交付可能改变查询成本或路径，但尚无对照结果。 |
| B | `4` / `5` | `MOUSE(row=19, col=18) -> effect`；timeline step1 `W>G:16`（环），step2 `w>g`/`g>w` 在 rows 18-21, cols 29-32。 | “selected … ghost preview of a move appears at (1,3)”。 | 无失败（阶段 2+3 成功） | **已采用相关事实。** 额外摘要的信息增量和效果未验证。 |
| B | `11` / `22` | 上一动作 19 帧 / 175 格。第一次 `last_animation_timeline` 因 `ch[:220]` 对 dict 切片 KeyError；重读得到 steps 9–13 `N>g`，14–19 `S>p` 从 rows 63 升到 51。 | “pegs turned to 'g' … purple object slid in from the bottom”。接着 `MOUSE(row=56, col=7)`。 | goal-hypothesis error（把死局钥匙当过关物去点） | **已读取帧序列，目标解释仍有问题。** 不足以证明不同摘要无效；本行未建立增益证据。 |
| B | `12` / `23` | `MOUSE(row=56, col=7)` 20 帧 / 3568 格（整屏 `S>B`）。 | “Whoa — the board RESET to the initial level-2 state … clicking the purple object restarted the level”。 | goal-hypothesis error | **超出局部事件的初始范围。** 3568 格整屏变化提示需要压缩取舍，未验证任何输出方案的收益或伤害。 |
| B | `67` / `212` | `MOUSE(row=26, col=50)` 后 user cue 16 帧 / 1701 格。未读 timeline。 | “THE CAMERA SCROLLED! … 1701 cells changed”。随后画 pegs/ferries，分析被取消打断。 | dynamics error（滚屏坐标）；budget termination | **滚屏与预算线索。** 未建立局部摘要可解决该问题的证据，也没有反事实结果。 |
| GE | `3` / `3` | 打印 `last_animation_timeline` 与 `last_animation_frames`：2 帧；step2 `w>g`/`g>w` 在 (18,30) 一带。 | “cell (row1,col3) … gray plus-outline (g) marker … distance 2 to the right”。 | 无失败（阶段 2+3） | **已采用相关时序事实。** 额外摘要的效果未验证。 |
| GE | `5` / `5` | frames 0–7 ascii：plus 从 ci=1 移到 ci=3。timeline 多步 `W>N`/`N>w`。 | “The animation shows a plus traveling from the left … landing at ci=3”。随后写成跳跃序列并执行。 | 无失败；这是 GE 比 baseline 更早钉死 peg-solitaire 的关键读帧 | **已读帧并更新假设。** 更早或不同表示的交付收益未知。 |
| GE | `11` / `20` | 一批 6 次点击，stdout：`batch of 6 actions, 5 executed … stop_reason: no_op_action`，`no_op: True`。User：`MOUSE(row=16, col=38) … 3 frames … not a no-op: 16 cells … rows 15-18, cols 36-41`。 | 下一轮：`clicking an already-selected peg deselects it`；batch 被 NO-OP 截断，第 6 次没执行。 | observation miss（当回合 NO-OP/batch stop） | **已发生的批次截断不变。** 只追加文本不能补执行已跳过的第 6 次点击；随后动作、时间成本和最终覆盖仍可能改变，未验证。 |
| GE | `15` / `26` | 读 timeline 19 步：1–8 跳跃，9 `N>g:24`，14–19 钥匙从 row 63 升到 51。 | “The key rises up from the bottom”。接着点 `(58,6)`。 | goal-hypothesis error | **已读取时间线。** 目标解释与额外证据表示的作用尚未区分。 |
| GE | `17` / `28` | 点钥匙后 settled 回到 L2 开局。 | “Clicking the key UNDID everything! … key = UNDO button … deadlock … fail/stuck”。 | goal-hypothesis error（已修正“钥匙=过关”，仍未钉死 L2 目标） | **观察到目标解释修正。** 未建立额外摘要的增益证据。 |
| GE | `30` / `56` | 未读 timeline。User cue 此前 16 格暂态。 | “Clicking the peg on the lock produced a small animation (16 cells …) … shake/invalid”。 | 无失败（阶段 3 来自 user cue，跳过阶段 2） | **已采用 user cue。** 复制相同线索的信息增量有限；丰富时序内容与不同交付时间的效果未知。 |
| GE | `37` / `78` | stdout：`MOUSE(row=49, col=25) -> NO-OP`，`no_op: True`。User：`not a no-op: 16 cells … rows 48-51, cols 23-28`。 | `(38,79)`：“only a shake animation (16 cells changed and reverted) — no legal moves”。 | observation miss（当回合）+ 已恢复 | **已有 cue 后恢复。** 不能据此断言更早纠正对后续路径没有影响。 |
| GE | `58` / `141` | `MOUSE(row=61, col=37) -> NO-OP`，`frame_diff` `noop changed 1`。User：16 格 rows 60-63, cols 35-40。 | “shake animation … peg at (9,5) has NO legal jumps”。随后陷入相机/世界宽度。 | observation miss（已恢复）+ dynamics error + goal-hypothesis error | **暂态汇总已被解释。** 地图与目标仍不确定；摘要的增益未验证。 |
| GE | `75`–`76` / `178`–`183` | 又一次 `NO-OP` + 16 格 cue；`frame_diff` 找 ghost 得到 `{}`。未读 timeline。最后在 `SC=15` 重画格子，预算取消。 | 长段滚屏模运算；“bar INCREASED”；“wires … lock can travel INSIDE the panel”。 | dynamics error；memory loss（反复重估 scroll）；budget termination | **坐标、记忆与预算线索。** 现有摘录不足以确定新增时序表示能否改变后续规划。 |

## 对 004 实现的研究判断

原版已在 `gameplay_changed is False` 时提示读取 timeline，后续若干步骤也采用了 16 格 / 3 帧 cue。单纯复制这句话的信息增量有限；但把相同事实更早交付，以及加入原 cue 没有的逐步颜色/位置事实，是不同假设，尚未检验。

两组覆盖相同，分差可由已完成 L3 的动作数解释；这个评分分解不能推出新候选无效。当前不单靠 lf52 启动新 A/B，先补完整 baseline。

若后续继续研究工具返回，保留以下设计线索，均不是已验证实现：

1. **交付时点。** `[action] … -> NO-OP` 与随后 user 的 not-a-no-op 句之间存在表达差异。`action()` 字典已有 `animation`，模型有时只打印 `no_op`；需区分改变表达、提前交付和增加时序信息各自的作用。
2. **局部量级。** 旧摘录包含 4/8/16/48 格的小事件，也包含 175/275/1000+/3568 格的入场、重置或滚屏。原先提出的 `frames ≤ 8`、`transient_pixels ≤ 80` 只是待考察条件，不能由几个 episode 当成适用阈值。
3. **信息增量。** bbox/帧数/格数与逐步颜色、位置序列不可等同。只有在明确哪些额外事实有区分力后，才决定是否输出及如何限长；不宣布 “illegal jump” 或 “win”，保留按需原帧。
4. **不混改 batch 行为。** GE `(11,20)` 的第 6 次点击已被截断，事后文本不能补执行它；这不限制随后策略可能改变。修改 `no_op_action` 是另一条干预。
5. **可观察采用。** 记录 game/runtime、真实 step/level、交付事实及后续代码/推理。只看到插入成功不等于证据被使用。

现有事实支持：模型既有主动读帧，也有直接使用 user cue；L4 仍存在目标、相机坐标和预算问题。它们不足以证明局部时序摘要有效，也不足以证明无效。
