# 004 轨迹归因 — su15-1944f8ab

日期：2026-10-11（Asia/Shanghai）。范围：003 已完成的 baseline 与 goal_evidence 各一次 `su15-1944f8ab` 请求轨迹与事件日志。未读游戏引擎源码；只依据 compact JSON 的 user/assistant/tool 消息、工具 stdout，以及 `events.jsonl`。未启动 GPU，未覆盖 003 notebooks。

输入：

- `runs/003-compact/baseline__su15-1944f8ab_p0_requests.compact.json`
- `runs/003-compact/goal_evidence__su15-1944f8ab_p0_requests.compact.json`
- `runs/003-goal-evidence-ab/baseline/artifacts/su15-1944f8ab_p0_events.jsonl`
- `runs/003-goal-evidence-ab/goal_evidence/artifacts/su15-1944f8ab_p0_events.jsonl`

盘点（已核对 compact 字段）：baseline 62 条 user-prompt animation cues、25 次 reasoning 提及、19 次 animation-API 读取（`reads_animation_api` / CODE_HINT）；goal_evidence 51 / 38 / 22。其中真正访问 `last_animation_timeline` 或 `last_animation_frames` 的次数是 baseline 6、goal_evidence 21。

## 结论

su15 是 003 最大单游戏分差来源（62.22 → 13.33，−48.89），但是**单次运行波动**，不能当作 goal-evidence 提示导致退步的因果证明。两组都在共享墙钟预算上 `cancelled`，都没有通完全部 9 关。

第一阶段已经很满：几乎每次鼠标动作后，用户提示都会写清「N 帧、X 格 changed and changed back、bbox，并点名 `last_animation_timeline`」；`action()` 的 stdout 里也常有 `animation: {frames, transient_pixels, transient_bbox}`。第二阶段两边都会读动画，goal_evidence 甚至更勤（21 次 `last_animation_*` vs 6 次）。第三阶段在关键发现上成立：baseline 用帧作物推出「收缩环把紫块推向点击点」，goal_evidence 用 timeline 步 2 的 `B>M`/`M>B` 推出块平移，后又用 8 帧作物确认粉环在动画中吞点。

列出的失败主要是目标假设错误、动力学错误和预算终止，不是「最终帧几乎不变、中间动画有事实、但模型完全没看见」。004 候选（把紧凑局部时序事实注入现有 Python 工具返回）**不会改变下表任一 listed episode 的结果**。不要把「再提醒看动画」做成新因子；本游戏单独也不构成必须实现该候选的证据。

## 两组完成关、分数与停止原因

来源：`runs/003-goal-evidence-ab/{baseline,goal_evidence}/benchmark.json` 的 `su15-1944f8ab` 条，以及对应 `events.jsonl`。

| | baseline | goal_evidence |
|---|---:|---:|
| `final_score` | 62.2222 | 13.3333 |
| 完成关 / 总关 | 7 / 9 | 3 / 9 |
| `state` | cancelled | cancelled |
| 历史动作数 | 143 | 126 |
| `actions_per_level` | [13, 21, 14, 15, 6, 12, 5, 57, 0] | [12, 37, 19, 58, 0, 0, 0, 0, 0] |
| `final_wallclock_seconds` | 4643.4 | 4642.2 |
| 事件中 `GAME_OVER` | 无 | action 36 / `analysis_step` 28，随后 `RESET` |

关卡切换（events `level_completed` 为真的动作；`level` 字段是完成后的新关号）：

- baseline：L1→2 于 action 13 `MOUSE(row=18, col=45)`；L2→3 action 34；L3→4 action 48；L4→5 action 63；L5→6 action 69；L6→7 action 81；L7→8 action 86。之后 57 个动作停在第 8 关。
- goal_evidence：L1→2 于 action 12 `MOUSE(row=19, col=44)`；L2 在 action 36 `MOUSE(row=50, col=47)` 进入 `GAME_OVER`，同批 `RESET`；L2→3 action 49；L3→4 action 68。之后 58 个动作停在第 4 关。

两边停因都是**预算终止**（`cancelled` + 墙钟用尽），不是 `won`。分差来自 goal_evidence 在第 2 关耗掉 37 步（含一次耗尽底栏后的 RESET）后卡在第 4 关粉环，而 baseline 用更短路径过了前 7 关、卡在第 8 关。这是一次轨迹分叉，不是可复现的干预效应。

从工具 stdout 可见的可观察对象（不推断引擎规则）：可点格子、收缩/膨胀白环、可拖的色块与点、同色合并、底栏每步缩短、UNDO、RESET；较晚关出现会移动并「吃」棋子的粉环/入侵者。胜利在轨迹里表现为 `level_completed` 与盘面进入下一关，而不是模型打印的目标句。

## 三阶段计数表

阶段定义按 004 规格：**(1) API/提示已经提供**；**(2) 模型真正读取相关帧**；**(3) 模型据此更新假设**。第 1 阶段的存在不能算新能力。

| 阶段 | baseline | goal_evidence | 证据口径 |
|---|---:|---:|---|
| 1 已提供：user animation cue | 62 | 51 | compact `user.animation_lines` 非空 |
| 1 已提供：最终帧不变但有暂态（「not a no-op / board area unchanged」或 fatal 专句） | 7 | 10 | 用户提示已给出帧数、格数、bbox，并命令读 `last_animation_timeline` |
| 1 已提供：python 全局 / action 元数据 | 有 | 有 | 提示列出 `last_animation_timeline`、`last_animation_frames`；模型 `print(r)` 可见 `animation: {frames, transient_pixels, transient_bbox}` |
| 2 读取：CODE_HINT（含 `frame_diff` / `r.get('animation')`） | 19 | 22 | 与盘点 hint 一致 |
| 2 读取：`last_animation_timeline` 或 `last_animation_frames` | 6 | 21 | 真正读帧/时间线。baseline 步 2,3,4,19,30,68；GE 步 2–5,10,11×2,13–17,19–21,23,25,26,40×2,41 |
| 2 在「最终帧不变」cue 之后读了 `last_animation_*` | 3 / 7 | 5 / 10 | 未读的不变 cue，模型多用空 `frame_diff` + 用户提示里的环描述下结论 |
| 3 假设更新（读后改写机制） | ≥4 次明确 | ≥6 次明确 | 见下表；另有多次读了但只确认 no-op |
| 3 读了但未改写 / 误读 | 有 | 有 | 例如把 13 帧闪烁的底栏缩短当成「拒绝罚 8 格」；粉环轨迹在最终帧上拟合，忽略中途扫过 |

用户 cue 例句（阶段 1，已是紧凑时序事实，不是「请看动画」空话）：

- baseline `analysis_step=2` `action=2`：`The last executed action (\`MOUSE(row=30, col=30)\`) animated over 5 frames and left the board area unchanged, but it was not a no-op: 113 cells changed and changed back around rows 22-38, cols 22-38. Whatever this action did is visible only there - read \`last_animation_timeline\` before concluding it failed.`
- goal_evidence `analysis_step=29` `action=38`（GAME_OVER 后）：`That fatal action animated over 5 frames, and inside it 114 cells changed and changed back around rows 42-58, cols 39-55. Those cells are in neither \`history[-3].frame\` nor \`history[-2].frame\` - read \`last_animation_timeline\` to see what happened between them.`

动画帧数量级（用户 cue「animated over N frames」）：baseline 62 条中 44 条为 5 帧，其余 4–13 帧（10 帧 6 次、12 帧 6 次、13 帧 1 次）；goal_evidence 51 条中 41 条为 5 帧，13 帧拒绝闪烁 4 次。暂态格数大约 64–260，常见 ~113。这些是若实现 004 时应用的真实量级，不是预设开关。

## 关键 episode 表

标签可叠用。004 列只回答：**把紧凑局部时序事实注入当时那次 Python 工具返回，会不会改变这一行的后续行为/关卡结果**。不把「模型可能更早看见同样的 timeline」算改变，除非现有证据显示它当时没采用、且采用会改动作。

| 臂 | step / action | 工具返回或用户提示中的事实 | 随后推理 / 代码 | 标签 | 004 会改变？ |
|---|---|---|---|---|---|
| B | `analysis_step=2` `action=2` | stdout：`MOUSE(row=30, col=30) -> NO-OP`；`animation: {'frames': 5, 'transient_pixels': 113, 'transient_bbox': [22, 22, 38, 38]}`。随后代码 `t = last_animation_timeline` 打印步 1–5 的 `B>W`/`W>B` 与收缩 bbox。 | 「113 transient pixels in bbox rows 22-38… expanding ring/explosion」「clicking creates an expanding-then-contracting white ring」。阶段 2+3 已成立。 | （发现，非失败） | **否**。已经查询 timeline 并更新假设。注入工具返回只是重复用户提示 + 已打印的 dict。 |
| B | `analysis_step=4` `action=6` | 第三次点击 stdout：`(53,10) noop=False … tpix=120 … moved: 1`。`frame_diff`：`p` 从 `[58,3]` 到 `[52,9]`，`W` 十字消失。接着 `last_animation_frames` 作物：紫块随环从 `BBBpWp` 一带移到环心。 | 「The animation shows the ring contracting … pushing/carries the purple square up along the diagonal to the click point。」随后沿对角线点到蓝盘，action 13 过第 1 关。 | （发现） | **否**。这正是候选想自动提供的「颜色/位置暂态顺序」，但模型已经从 `last_animation_frames` 读到并采用。 |
| B | `analysis_step=8–10` `action=15–17` | 用户 cue：5 帧、113 格 changed-and-back，board unchanged。代码只跑 `frame_diff()`（空 moved），**没有** `last_animation_*`。 | 「Clicking the disc did nothing (only the ring animation).」「The yellow HUD square is not draggable」。随后用 `frame_diff` 发现 S 点可拖、两点合并成 M。 | 轻度 observation miss（跳过 timeline）；不是本关失败原因 | **否**。空 `frame_diff` + 用户 cue 已足够得出「只有环」。004 的环膨胀收缩摘要不会让他们更早发现合并；合并来自最终帧 `appeared M / disappeared 2 S`。 |
| B | `analysis_step=19` `action=36` | `last_animation_timeline`：`MOUSE(row=26, col=54) 13` 帧；步 5–12 在 `(25,53)(25,54)(26,53)` 上 `M>W`/`W>M` 闪烁；步 13 `B>M`/`B>S` 把物体放回原位。 | 「the merge FAILED and everything reverted」「grabbed THREE objects」。之后改用方形 ±8 抓取模型继续合并，并过第 3 关。 | 曾有 dynamics error（抓取半径），已被 timeline 纠正 | **否**。13 帧回滚已被读取并改变了计划。 |
| B | `analysis_step=30` `action=56` | timeline 10 帧：`P>B`/`B>P`、`M>p`、步 10 `Y>g` 与 `b>g`。 | 「the pink object seems to be moving down and left」；怀疑粉物冲向蓝盘、目标变灰。第 4 关仍过了（action 63）。 | 部分 dynamics error（粉物语义未一次钉死） | **否**。已经读了 10 帧时间线；L4 结果未因缺摘要而失败。 |
| B | `analysis_step=68` `action=127` 起，第 8 关 | 用户 cue：10 帧、110 格、board unchanged。代码 `last_animation_frames` 10 帧作物：钻石 `N` 与入侵者 `P` 相邻，中间白爆发，随后分开。 | 「They ended up apart … creatures don't eat each other; instead there's a white flash (probably the bump/knock animation).」其后大量 UNDO（本局共 24 次）尝试把 O 送进盘、躲开入侵者。`analysis_step=77`：`the O in the disc is NOT protected — the invader ate it`；`how can the level ever be completed??` | goal-hypothesis error；dynamics error；budget termination | **否**。碰撞动画已被读。卡住的是胜利条件与入侵者吃子，不是未注入暂态事实。 |
| G | `analysis_step=2–5` `action=2–5` | 多次 `tl = last_animation_timeline`。点击蓝球：5 帧 `c>W`/`b>W` 再回去。点击白十字：`noop False`，紫块移位。点击空点/紫块：`noop True` + 同样白环。 | 「pulse ring」；一度假设「只有点白十字才有效」「紫块是进度标记」。第 1 关仍在 `analysis_step=8` 用沿轨 3 步一跳完成（action 12）。 | 早期 goal-hypothesis error，已自行纠正 | **否**。阶段 2 已密；过关不依赖额外工具返回。 |
| G | `analysis_step=11` `action=15` | 先打印残缺 timeline，再重拉全量：步 2 `B>M: 2, M>B: 2`。 | 「the block shifted by 1 cell left (2 cells gained on the left, 2 lost on the right). So the block moved left by exactly 1 in one animation frame.」阶段 3 成立。随后又误推「跳到点击格 / 最近物体」。 | 先更新、后 dynamics error | **否**。平移事实已被采用；后续错在规则外推，不是没看见帧。 |
| G | `analysis_step=16–20` `action=23–27` | 13 帧拒绝：目标格 `M>W`/`W>M` 闪烁后回滚；另一次 `'M>b'/'S>b'`。stdout `frames 13`、`noop True`。 | 「denied/invalid animation」「blinking = invalid move」。又把底栏 `W>B` 多格读成「拒绝罚 8 格」，`analysis_step=21`：「ALERT: The bar is now only 18 wide」。 | dynamics error（惩罚/reach 模型） | **否**。闪烁回滚已被读。004 不会禁止错误的栏罚解释。 |
| G | `analysis_step=28–29` `action=35–38` | 批动作 stdout：`MOUSE(56,15), MOUSE(50,47) \| stop_reason: game_over`；`bar []`。用户提示已 RESET，并写 fatal 动画 5 帧、114 格 rows 42–58 cols 39–55。**未**读 `last_animation_timeline`。 | 「Diagnosis: the bar was fully depleted … budget death, as intended. The level reset」。随后用 37 步重打第 2 关并在 action 49 过关。 | budget termination；exploration 过贵。observation miss 很弱：死因按 BAR RULE 已判对 | **否**。注入 fatal 动画（多半是合并脉冲）不能把空栏变回有栏，也不能避免 RESET 成本。 |
| G | `analysis_step=40–41` `action=74–75` | timeline 5 帧 + `last_animation_frames` 作物；随后 8 帧作物：粉环逐帧左移，第 7 帧 `P` 盖住原 `S`。 | 「the ring moves left … and consumes objects it overlaps. It's a hazard.」阶段 3 成立。 | （发现） | **否**。已经读帧并改写成危害物。 |
| G | `analysis_step=51–63` 第 4 关 | `analysis_step=52` `action=93`：`MOUSE(33,12) -> NO-OP`，用户 cue 13 帧、155 格 unchanged。未读 timeline。推理仍写出「probably a rejection flash」。`analysis_step=60` 从最终物体推断「D was eaten during k4's animation while the ring was moving from col 42 to col 34」。最后一批 stdout：`p 9 … M 4 … g 69`（球已灰）、`bar 18`，仍在第 4 关直到 cancelled。 | 反复 UNDO（25 次）重排合并与躲环；把环当成每步 col−4 的追逐物，仍被中途扫食。 | dynamics error；goal-hypothesis error（灰球/送子）；budget termination | **否**。13 帧拒绝已从 `no_op`+用户 cue 正确判出。中途吞点最终也从盘面推出。缺的是在预算内同时完成合并链并躲开环，不是缺一段工具返回摘要。 |

阶段 2 有、阶段 3 无（或很弱）的例子，单独计数：baseline 在 `analysis_step=3` 打印了 `last_animation_frames` ascii 后仍说「the crosshair does NOT move」，下一轮才靠另一次作物改成「环推动」——延迟一拍，不是忽略。goal_evidence 多次把 timeline 当 no-op 确认，同时用错误 reach/栏罚模型，属于读了事实、更新错动力学。

## 对 004 实现的建议

**就 su15 列出的 episode：反对把本游戏当作「必须实现观察摘要」的充分证据。明确反对再加一条「请看动画」式提示。**

理由与规格对齐：

1. 阶段 1 已经包含候选想提供的摘要句（帧数、changed-and-back 格数、bbox、点名 timeline）。再注入同级文字是重复，且 003 已证明「多一段指导文字」不必进入行为。
2. 当中间帧真正改变假设时（收缩环载物、13 帧闪烁回滚、粉环逐帧吞点、钻石/入侵者碰撞），模型**已经会**调用 `last_animation_timeline` / `last_animation_frames`。阶段 2 在 goal_evidence 上甚至更密，却少过 4 关——说明瓶颈在阶段 3 的规则外推和预算，不在「没入口」。
3. 真正符合「最终帧变化很小、中间有信息」的 cue（baseline 7、GE 10）里，未读 `last_animation_*` 的几次，模型仍用空 `frame_diff` + 用户 cue 得出正确的 no-op/拒绝；004 不会改动作。
4. 分差是单次波动：GE 第 2 关耗尽底栏 RESET，第 4 关与粉环赛跑；baseline 用更短合并路径冲到第 8 关后被入侵者吃子。两边停因都是预算终止。

若 Task 6 在**其他游戏**上找到反复出现的、且模型**不查询** timeline 的可见转移缺陷，su15 只提供量级，不提供本游戏的必做理由：

- 常见脉冲：5 帧，~113 暂态格，约 17×17 bbox。
- 拒绝闪烁：13 帧，~120–155 格，物体在目标格 `M>W`/`W>M` 后回滚。
- 载物/危害：5–12 帧，逐步 `B>p`/`p>B` 或粉环每帧移 1 格。
- 工具返回里**现有**的 `animation.frames / transient_pixels / transient_bbox` 不够区分「只有环」和「环带着物体走」；有区分力的是逐步颜色计数和物体位移，而那正是模型在关键步已经 `print` 的 `last_animation_timeline['steps']`。
- 若仍实现：只附加逐步物体位移/闪烁回滚，长度远小于现有 stdout（本轨迹 300–5500 字符），去重重复环事件，条件限制在「最终 `gameplay_changed` 为假或 `no_op` 但 `frames>=5`」。不宣布胜利规则，不按 `su15` 硬编码，不开 003 marker。保留按需原帧。不要复制用户提示里已经出现的那句 bbox 摘要。

本笔记不启动 GPU，不修改 `src/`，不覆盖 003。
