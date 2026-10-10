# 004 — lf52-271a04aa 轨迹归因

日期：2026-10-11。只读 003 compact 请求与 events；未读游戏引擎源码，未启动 GPU。  
来源：`runs/003-compact/{baseline,goal_evidence}__lf52-271a04aa_p0_requests.compact.json`，`runs/003-goal-evidence-ab/{baseline,goal_evidence}/artifacts/lf52-271a04aa_p0_events.jsonl`，arm-metadata / benchmark。

引用用 compact JSON 的 `analysis_step` / `action`。模型自称的 peg / lock / ferry / key / shake 只当作轨迹里的工作假说，不是引擎规则。

## 结论

两组都完成 **3/10** 关后因共享墙钟预算取消（`soft_deadline_fired`），不是通关。baseline **7.73** 分、动作 `[15, 57, 116, 23]`；goal_evidence **10.91** 分、动作 `[10, 65, 58, 49]`。覆盖相同，分差来自 L3 动作效率（116 vs 58）；GE 已碰到 3/10 的完成覆盖上限。动画 API 与 user-prompt 暂态句已经大量存在（user cue 38 / 48）。模型在 L1 会读 `last_animation_timeline` / `last_animation_frames`，并把“选中环 + 灰色幽灵”更新成跳跃预览；L2 起几乎不再读帧，改看 settled ascii、`frame_diff` 和下一条 user cue。Harness 在 settled 不变时打印 `NO-OP (executed, no change inside the board area)`，同一回合的下一条 user 句却写 `left the board area unchanged, but it was not a no-op`（16 格 / 3 帧）。模型下一轮通常把这解释成 shake / 非法跳跃，并不需要再提醒“请看动画”。L4 停在相机滚动坐标、锁与钉子目标假说和预算。**把紧凑时序事实注入现有 python 工具返回，不会改变下表任一列出 episode 的关卡结果**：等价的帧数 / 格子数 / bbox 已在下一条 user prompt 里，剩余失败不是“没看见暂态”。

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

## 三阶段计数表

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

| 臂 | step / action | 工具返回事实（引 stdout） | 随后推理 / 代码 | 标签 | 004 会改变？ |
|---|---|---|---|---|---|
| B | `2` / `2` | stdout：`[action] MOUSE(row=13, col=12) -> NO-OP (executed, no change inside the board area)`，`no_op: True`。下一 user：`animated over 6 frames and left the board area unchanged, but it was not a no-op: 48 cells … rows 16-23, cols 15-22`。同 step 第二段代码 `print(last_animation_timeline)` → 6 步 `W>b`/`b>W` 闪。 | “clicking at (13,12) caused an animation at cell (rows 18-21, cols 17-20) — a flash outline”。随后继续 probe 时间线。 | observation miss（当回合被 NO-OP 带偏，下一 snippet 已读时间线） | **否**。已经读了 timeline；004 最多让第一段 stdout 少一次误判，不改变 L1 探索路径。 |
| B | `4` / `5` | `MOUSE(row=19, col=18) -> effect`；timeline step1 `W>G:16`（环），step2 `w>g`/`g>w` 在 rows 18-21, cols 29-32。 | “selected … ghost preview of a move appears at (1,3)”。 | 无失败（阶段 2+3 成功） | **否**。时间线已被采用。 |
| B | `11` / `22` | 上一动作 19 帧 / 175 格。第一次 `last_animation_timeline` 因 `ch[:220]` 对 dict 切片 KeyError；重读得到 steps 9–13 `N>g`，14–19 `S>p` 从 rows 63 升到 51。 | “pegs turned to 'g' … purple object slid in from the bottom”。接着 `MOUSE(row=56, col=7)`。 | goal-hypothesis error（把死局钥匙当过关物去点） | **否**。帧序列已被读到；错的是目标，不是没看见动画。 |
| B | `12` / `23` | `MOUSE(row=56, col=7)` 20 帧 / 3568 格（整屏 `S>B`）。 | “Whoa — the board RESET to the initial level-2 state … clicking the purple object restarted the level”。 | goal-hypothesis error | **否**。整屏重置不是“局部时序事实”；004 若倾倒 3568 格会更糟。 |
| B | `67` / `212` | `MOUSE(row=26, col=50)` 后 user cue 16 帧 / 1701 格。未读 timeline。 | “THE CAMERA SCROLLED! … 1701 cells changed”。随后画 pegs/ferries，分析被取消打断。 | dynamics error（滚屏坐标）；budget termination | **否**。全屏滚动不是局部转移；预算到时。 |
| GE | `3` / `3` | 打印 `last_animation_timeline` 与 `last_animation_frames`：2 帧；step2 `w>g`/`g>w` 在 (18,30) 一带。 | “cell (row1,col3) … gray plus-outline (g) marker … distance 2 to the right”。 | 无失败（阶段 2+3） | **否**。 |
| GE | `5` / `5` | frames 0–7 ascii：plus 从 ci=1 移到 ci=3。timeline 多步 `W>N`/`N>w`。 | “The animation shows a plus traveling from the left … landing at ci=3”。随后写成跳跃序列并执行。 | 无失败；这是 GE 比 baseline 更早钉死 peg-solitaire 的关键读帧 | **否**。已经读了帧。 |
| GE | `11` / `20` | 一批 6 次点击，stdout：`batch of 6 actions, 5 executed … stop_reason: no_op_action`，`no_op: True`。User：`MOUSE(row=16, col=38) … 3 frames … not a no-op: 16 cells … rows 15-18, cols 36-41`。 | 下一轮：`clicking an already-selected peg deselects it`；batch 被 NO-OP 截断，第 6 次没执行。 | observation miss（当回合 NO-OP/batch stop） | **否（结果）**。下一 user cue 已被用来纠正；batch 在工具返回写出之前已经停。004 若只追加文本、不改 `no_op_action`，第 6 次点击仍不会在当回合发出。 |
| GE | `15` / `26` | 读 timeline 19 步：1–8 跳跃，9 `N>g:24`，14–19 钥匙从 row 63 升到 51。 | “The key rises up from the bottom”。接着点 `(58,6)`。 | goal-hypothesis error | **否**。已读时间线。 |
| GE | `17` / `28` | 点钥匙后 settled 回到 L2 开局。 | “Clicking the key UNDID everything! … key = UNDO button … deadlock … fail/stuck”。 | goal-hypothesis error（已修正“钥匙=过关”，仍未钉死 L2 目标） | **否**。 |
| GE | `30` / `56` | 未读 timeline。User cue 此前 16 格暂态。 | “Clicking the peg on the lock produced a small animation (16 cells …) … shake/invalid”。 | 无失败（阶段 3 来自 user cue，跳过阶段 2） | **否**。事实已在 prompt 里并被采用。 |
| GE | `37` / `78` | stdout：`MOUSE(row=49, col=25) -> NO-OP`，`no_op: True`。User：`not a no-op: 16 cells … rows 48-51, cols 23-28`。 | `(38,79)`：“only a shake animation (16 cells changed and reverted) — no legal moves”。 | observation miss（当回合）+ 已恢复 | **否**。恢复用的是已有 user cue，不是缺事实。 |
| GE | `58` / `141` | `MOUSE(row=61, col=37) -> NO-OP`，`frame_diff` `noop changed 1`。User：16 格 rows 60-63, cols 35-40。 | “shake animation … peg at (9,5) has NO legal jumps”。随后陷入相机/世界宽度。 | observation miss（已恢复）+ dynamics error + goal-hypothesis error | **否**。shake 已被 cue 解释；L4 卡住的是地图与目标。 |
| GE | `75`–`76` / `178`–`183` | 又一次 `NO-OP` + 16 格 cue；`frame_diff` 找 ghost 得到 `{}`。未读 timeline。最后在 `SC=15` 重画格子，预算取消。 | 长段滚屏模运算；“bar INCREASED”；“wires … lock can travel INSIDE the panel”。 | dynamics error；memory loss（反复重估 scroll）；budget termination | **否**。缺的不是 16 格 bbox，是坐标与目标。 |

## 对 004 实现的具体建议或明确反对

**反对把“再提醒看动画”当新因子。** User cue 已经在 `gameplay_changed is False` 时写出 “read `last_animation_timeline` before concluding it failed.” L2 之后这条仍在发，模型仍不查时间线，但会把 16 格 3 帧当成 shake。再写一遍同一句话没有增量。

**lf52 列在表里的 episode，004 候选都不会改变关卡结果。** 不支持单靠本游戏去开 GPU。覆盖已经相同；分差是 L3 动作数。

若仍要做“注入现有 python 工具返回”，本轨迹只支持一个很窄的缺口，且要和 user cue **去重**：

1. **只在当回合工具 stdout 里补事实**，因为冲突发生在这里：`[action] … -> NO-OP (executed, no change inside the board area)` 与随后 user 的 not-a-no-op 句。`action()` 字典里已经有 `animation: {frames, transient_pixels, transient_bbox}`，模型经常只 `print(no_op)` 或直接滤掉 `animation`（baseline `analysis_step=2`）。
2. **条件从本轨迹量级来，不要做复杂开关**：仅当 settled 不变、暂态存在、且局部——例如 `frames ≤ 8` 且 `transient_pixels ≤ 80`（覆盖 4/8/16/48 格的环与 shake）。**不要**注入 175 / 275 / 1000+ / 3568 格的过关、钥匙入场、重置、滚屏。
3. **输出只要 bbox + 帧数 + 格子数 + 是否回到原色**，不要逐格列表，不要宣布 “illegal jump” / “win”。保留按需 `last_animation_frames`。
4. **不要在本候选里改 `no_op` / `stop_reason: no_op_action`。** GE `(11,20)` 的 6 连击在工具文本写出前就已经停。改 batch 停条件是另一条干预，不是“紧凑观察事实”。
5. 事件日志仍要记 game/runtime、真实 step/level、事实、是否交给模型；采用与否看**之后的代码/推理**，不看模型自评。

本游戏对 004 的证据是：**阶段 1 已经很吵；阶段 2 在 L1 有效、之后稀疏；阶段 3 经常直接吃 user cue。** 真正反复出现、可用可见转移描述的，是 “NO-OP 标签 vs 16 格 3 帧 shake”，但下一轮 prompt 已经把这件事说完，并且模型采用了。剩下的 L4 失败是目标假说、动力学/相机和预算。
