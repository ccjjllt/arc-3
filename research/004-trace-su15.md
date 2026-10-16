# 004 轨迹归因 — su15-1944f8ab

> **2026-10-11 复核说明：** 本文最初使用的 compact 按消息长度去重，在上下文裁剪处会漏消息。下文原始盘点数字和三阶段计数保留为旧口径，不再作为当前统计结论；统一以 [004-review-data](004-review-data.md) 的原始日志新统计为准。已有 episode 引文与事件定位保留，不能把旧摘录当成完整轨迹。004 候选未实现、未做反事实对照；表中评价只描述现有证据支持程度，不能证明候选有效或无效。

日期：2026-10-11（Asia/Shanghai）。范围：003 已完成的 baseline 与 goal_evidence 各一次 `su15-1944f8ab` 请求轨迹与事件日志。未读游戏引擎源码；只依据 compact JSON 的 user/assistant/tool 消息、工具 stdout，以及 `events.jsonl`。未启动 GPU，未覆盖 003 notebooks。

输入：

- `runs/003-compact/baseline__su15-1944f8ab_p0_requests.compact.json`
- `runs/003-compact/goal_evidence__su15-1944f8ab_p0_requests.compact.json`
- `runs/003-goal-evidence-ab/baseline/artifacts/su15-1944f8ab_p0_events.jsonl`
- `runs/003-goal-evidence-ab/goal_evidence/artifacts/su15-1944f8ab_p0_events.jsonl`

盘点（已核对 compact 字段）：baseline 62 条 user-prompt animation cues、25 次 reasoning 提及、19 次 animation-API 读取（`reads_animation_api` / CODE_HINT）；goal_evidence 51 / 38 / 22。其中真正访问 `last_animation_timeline` 或 `last_animation_frames` 的次数是 baseline 6、goal_evidence 21。

## 结论

su15 是 003 最大单游戏分差来源（62.22 → 13.33，−48.89），但这只是**单次对照中的差异**，尚不能区分初始 guidance、生成随机性和运行条件的影响，也不能证明提示没有影响。两组都在共享墙钟预算上 `cancelled`，都没有通完全部 9 关。

第一阶段已经很满：几乎每次鼠标动作后，用户提示都会写清「N 帧、X 格 changed and changed back、bbox，并点名 `last_animation_timeline`」；`action()` 的 stdout 里也常有 `animation: {frames, transient_pixels, transient_bbox}`。第二阶段两边都会读动画，goal_evidence 甚至更勤（21 次 `last_animation_*` vs 6 次）。第三阶段在关键发现上成立：baseline 用帧作物推出「收缩环把紫块推向点击点」，goal_evidence 用 timeline 步 2 的 `B>M`/`M>B` 推出块平移，后又用 8 帧作物确认粉环在动画中吞点。

列出的失败包含目标假设、动力学和预算问题，若干关键步骤已经读取动画。**这不等于所有相关事实都被充分提取，也不等于自动交付摘要无效。** 004 候选未做反事实实验，目前不能确定它会否改变后续行为或完成关卡；本游戏尚未提供足以立即实现并投入 GPU 的收益证据。

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

两边停因都是**预算终止**（`cancelled` + 墙钟用尽），不是 `won`。分差来自 goal_evidence 在第 2 关耗掉 37 步（含一次耗尽底栏后的 RESET）后卡在第 4 关粉环，而 baseline 用更短路径过了前 7 关、卡在第 8 关。这是一次轨迹分叉；是否由初始 guidance 引起、是否可复现，尚无证据区分。两边都因预算终止也不能排除提示通过路径或 token 消耗影响覆盖。

从工具 stdout 可见的可观察对象（不推断引擎规则）：可点格子、收缩/膨胀白环、可拖的色块与点、同色合并、底栏每步缩短、UNDO、RESET；较晚关出现会移动并「吃」棋子的粉环/入侵者。胜利在轨迹里表现为 `level_completed` 与盘面进入下一关，而不是模型打印的目标句。

## 三阶段旧计数（以复核新统计为准）

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

标签可叠用。004 列记录已收到/采用的事实、可疑的提取或交付缺口，以及效果仍未知的部分。更早看见同样的 timeline 可能影响查询成本与探索路径，但没有反事实运行不能判断实际收益。

| 臂 | step / action | 工具返回或用户提示中的事实 | 随后推理 / 代码 | 标签 | 004 候选的现有证据支持 |
|---|---|---|---|---|---|
| B | `analysis_step=2` `action=2` | stdout：`MOUSE(row=30, col=30) -> NO-OP`；`animation: {'frames': 5, 'transient_pixels': 113, 'transient_bbox': [22, 22, 38, 38]}`。随后代码 `t = last_animation_timeline` 打印步 1–5 的 `B>W`/`W>B` 与收缩 bbox。 | 「113 transient pixels in bbox rows 22-38… expanding ring/explosion」「clicking creates an expanding-then-contracting white ring」。阶段 2+3 已成立。 | （发现，非失败） | **已读取并采用时间线。** 复制同一 dict 的信息增量有限；更早交付的时间与路径影响未知。 |
| B | `analysis_step=4` `action=6` | 第三次点击 stdout：`(53,10) noop=False … tpix=120 … moved: 1`。`frame_diff`：`p` 从 `[58,3]` 到 `[52,9]`，`W` 十字消失。接着 `last_animation_frames` 作物：紫块随环从 `BBBpWp` 一带移到环心。 | 「The animation shows the ring contracting … pushing/carries the purple square up along the diagonal to the click point。」随后沿对角线点到蓝盘，action 13 过第 1 关。 | （发现） | **已采用具体时序事实。** 候选是否更省查询或更稳地提取这些事实未验证。 |
| B | `analysis_step=8–10` `action=15–17` | 用户 cue：5 帧、113 格 changed-and-back，board unchanged。代码只跑 `frame_diff()`（空 moved），**没有** `last_animation_*`。 | 「Clicking the disc did nothing (only the ring animation).」「The yellow HUD square is not draggable」。随后用 `frame_diff` 发现 S 点可拖、两点合并成 M。 | 轻度 observation miss（跳过 timeline）；对本关结果的因果贡献未知 | **相关时序未直接查询。** 模型借 cue 作出“只有环”的解释，随后从结算帧发现合并；更早提供时序事实能否改变探索未知。 |
| B | `analysis_step=19` `action=36` | `last_animation_timeline`：`MOUSE(row=26, col=54) 13` 帧；步 5–12 在 `(25,53)(25,54)(26,53)` 上 `M>W`/`W>M` 闪烁；步 13 `B>M`/`B>S` 把物体放回原位。 | 「the merge FAILED and everything reverted」「grabbed THREE objects」。之后改用方形 ±8 抓取模型继续合并，并过第 3 关。 | 曾有 dynamics error（抓取半径），已被 timeline 纠正 | **已读回滚并改写计划。** 额外摘要的收益未验证。 |
| B | `analysis_step=30` `action=56` | timeline 10 帧：`P>B`/`B>P`、`M>p`、步 10 `Y>g` 与 `b>g`。 | 「the pink object seems to be moving down and left」；怀疑粉物冲向蓝盘、目标变灰。第 4 关仍过了（action 63）。 | 部分 dynamics error（粉物语义未一次钉死） | **已读时间线且本关完成。** 不能据此确定不同表示对效率或后续覆盖的影响。 |
| B | `analysis_step=68` `action=127` 起，第 8 关 | 用户 cue：10 帧、110 格、board unchanged。代码 `last_animation_frames` 10 帧作物：钻石 `N` 与入侵者 `P` 相邻，中间白爆发，随后分开。 | 「They ended up apart … creatures don't eat each other; instead there's a white flash (probably the bump/knock animation).」其后大量 UNDO（本局共 24 次）尝试把 O 送进盘、躲开入侵者。`analysis_step=77`：`the O in the disc is NOT protected — the invader ate it`；`how can the level ever be completed??` | goal-hypothesis error；dynamics error；budget termination | **碰撞帧已读，规则仍不明确。** 需要区分提取到的事实是否充分与规则外推错误，现有轨迹没有候选对照。 |
| G | `analysis_step=2–5` `action=2–5` | 多次 `tl = last_animation_timeline`。点击蓝球：5 帧 `c>W`/`b>W` 再回去。点击白十字：`noop False`，紫块移位。点击空点/紫块：`noop True` + 同样白环。 | 「pulse ring」；一度假设「只有点白十字才有效」「紫块是进度标记」。第 1 关仍在 `analysis_step=8` 用沿轨 3 步一跳完成（action 12）。 | 早期 goal-hypothesis error，已自行纠正 | **已有多次查询与自我修正。** 本次完成是在原反馈下发生的，不排除新增表示改变路径。 |
| G | `analysis_step=11` `action=15` | 先打印残缺 timeline，再重拉全量：步 2 `B>M: 2, M>B: 2`。 | 「the block shifted by 1 cell left (2 cells gained on the left, 2 lost on the right). So the block moved left by exactly 1 in one animation frame.」阶段 3 成立。随后又误推「跳到点击格 / 最近物体」。 | 先更新、后 dynamics error | **已采用位移事实。** 后续规则外推仍出错，不能单凭此断定摘要没有作用。 |
| G | `analysis_step=16–20` `action=23–27` | 13 帧拒绝：目标格 `M>W`/`W>M` 闪烁后回滚；另一次 `'M>b'/'S>b'`。stdout `frames 13`、`noop True`。 | 「denied/invalid animation」「blinking = invalid move」。又把底栏 `W>B` 多格读成「拒绝罚 8 格」，`analysis_step=21`：「ALERT: The bar is now only 18 wide」。 | dynamics error（惩罚/reach 模型） | **已读闪烁回滚。** 关于栏罚的推断仍有错误；何种表示能减少误读尚未验证。 |
| G | `analysis_step=28–29` `action=35–38` | 批动作 stdout：`MOUSE(56,15), MOUSE(50,47) \| stop_reason: game_over`；`bar []`。用户提示已 RESET，并写 fatal 动画 5 帧、114 格 rows 42–58 cols 39–55。**未**读 `last_animation_timeline`。 | 「Diagnosis: the bar was fully depleted … budget death, as intended. The level reset」。随后用 37 步重打第 2 关并在 action 49 过关。 | budget termination；exploration 过贵。observation miss 很弱：死因按 BAR RULE 已判对 | **已识别此次死亡原因。** 事后文本不改变已耗尽的栏；若更早的反馈改变探索成本，后续 RESET 次数仍可能不同，未验证。 |
| G | `analysis_step=40–41` `action=74–75` | timeline 5 帧 + `last_animation_frames` 作物；随后 8 帧作物：粉环逐帧左移，第 7 帧 `P` 盖住原 `S`。 | 「the ring moves left … and consumes objects it overlaps. It's a hazard.」阶段 3 成立。 | （发现） | **已读取并更新危害物假设。** 额外摘要的增益未验证。 |
| G | `analysis_step=51–63` 第 4 关 | `analysis_step=52` `action=93`：`MOUSE(33,12) -> NO-OP`，用户 cue 13 帧、155 格 unchanged。未读 timeline。推理仍写出「probably a rejection flash」。`analysis_step=60` 从最终物体推断「D was eaten during k4's animation while the ring was moving from col 42 to col 34」。最后一批 stdout：`p 9 … M 4 … g 69`（球已灰）、`bar 18`，仍在第 4 关直到 cancelled。 | 反复 UNDO（25 次）重排合并与躲环；把环当成每步 col−4 的追逐物，仍被中途扫食。 | dynamics error；goal-hypothesis error（灰球/送子）；budget termination | **保留时序提取与规则线索。** 拒绝和吞点已有部分证据；是否更早、完整地交付位移事实能改善躲避与合并规划未知。 |

阶段 2 有、阶段 3 无（或很弱）的例子，单独计数：baseline 在 `analysis_step=3` 打印了 `last_animation_frames` ascii 后仍说「the crosshair does NOT move」，下一轮才靠另一次作物改成「环推动」——延迟一拍，不是忽略。goal_evidence 多次把 timeline 当 no-op 确认，同时用错误 reach/栏罚模型，属于读了事实、更新错动力学。

## 对 004 实现的建议

**su15 尚未提供必须实现观察摘要的充分证据，也没有提供候选无效的反事实证据。** 当前不据此追加 GPU，保留可见线索。

理由与规格对齐：

1. 原版已经提供帧数、格数、bbox 和 timeline 提示。复制这些汇总内容的信息增量有限，但不等于已经提供候选中的完整局部时序。003 的特殊 marker 采用少，也不能直接外推为其他证据交付方式无效。
2. 收缩环载物、闪烁回滚和粉环逐帧吞点等关键步骤确实有 API 查询及后续假设更新。查询较多而过关较少不证明观察已充分，也不能定位唯一瓶颈；两臂的关卡经历与探索路径不同，原始计数亦需复核。
3. 未直接读取动画的若干步骤从 cue 推断 no-op/拒绝。解释是否完整、提前交付具体序列是否改变行为，现有轨迹没有对照答案。旧 7/10 cue 数仅作历史记录，新口径见复核表。
4. GE 在 L2 耗尽底栏后 RESET，随后停在 L4；baseline 到 L8 后停下。这描述了差异发生的位置，不能判断初始 guidance、随机生成或调度各自造成了多少差异。两边预算终止并不排除干预通过探索成本影响覆盖。

若后续找到可重复的证据交付或提取缺口（包括已调用 API 却未提取相关事实的情况），以下旧摘录量级可作设计线索，不能直接当作收益依据：

- 常见脉冲：5 帧，~113 暂态格，约 17×17 bbox。
- 拒绝闪烁：13 帧，~120–155 格，物体在目标格 `M>W`/`W>M` 后回滚。
- 载物/危害：5–12 帧，逐步 `B>p`/`p>B` 或粉环每帧移 1 格。
- 工具返回里**现有**的 `animation.frames / transient_pixels / transient_bbox` 不够区分「只有环」和「环带着物体走」；有区分力的是逐步颜色计数和物体位移，而那正是模型在关键步已经 `print` 的 `last_animation_timeline['steps']`。
- 若仍实现，可考察逐步物体位移/闪烁回滚，并控制重复和长度；旧摘录 stdout 约 300–5500 字符，完整分布以复核为准。「最终 `gameplay_changed` 为假或 `no_op`、`frames>=5`」只是待考察条件。不得宣布胜利规则或按 `su15` 硬编码，保留按需原帧，单独说明新事实与交付时点。

本笔记不启动 GPU，不修改 `src/`，不覆盖 003。
