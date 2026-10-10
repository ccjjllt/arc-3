# 004 — sk48 轨迹归因（003 baseline vs goal_evidence）

日期：2026-10-11（Asia/Shanghai）。范围：只读 003 已下载 compact 请求与 action/analysis 事件；**未读游戏引擎源码**，未启动 GPU，未覆盖 003 notebook。

输入：

- compact：`runs/003-compact/baseline__sk48-d8078629_p0_requests.compact.json`（67 request / 65 records）、`runs/003-compact/goal_evidence__sk48-d8078629_p0_requests.compact.json`（30 request / 28 records）
- 事件：`runs/003-goal-evidence-ab/{baseline,goal_evidence}/artifacts/sk48-d8078629_p0_events.jsonl`（只取 `type=action|analysis` 的元数据；未把整盘 ascii 当作机制依据）
- 停止口径：`runs/003-goal-evidence-ab/{baseline,goal_evidence}/run.log`、`experiments/003-analysis/summary.md`

下文 `analysis_step` / `action` 均指 compact JSON 字段（`action` 是底座显示步，与 events 的 `action_num` 可差 1）。引用的 stdout / reasoning 来自同一 compact 记录。

## 结论

sk48 上 baseline 过了第 1 关（1.37、1/8），goal_evidence 一关未过（0.00、0/8）；两组都是墙钟预算取消，不是通关或 game_over。动画 **API 与 user-prompt 紧凑时序事实已经全程提供**（阶段 1）：有暂态时 user 提示写明帧数、changed-and-changed-back 格数和 bbox，并指向 `last_animation_timeline`。两组代码对 `last_animation_timeline` / `last_animation_frames` 的读取次数都是 **0**（阶段 2 未发生）。compact 里标成 `reads_animation_api` 的调用（baseline 2、goal_evidence 6）全部是 `frame_diff()`，比较的是结算帧，不是动画帧。

模型偶尔会把 **user 提示里的 bbox/格数** 写进推理（baseline `analysis_step=4 action=4` 的 36 格、`analysis_step=13 action=41` 的 8 格 N 闪烁），这是阶段 1 文本被采用，不是阶段 2 读帧。第 1 关实际过关来自结算状态上的「一臂贯穿同带三块」，不是读了 9 帧/108 格的通关动画。随后卡关是 **目标假设**（图例空心=钩住/收集；HUD 左右序=胜利条件）和 **动力学**（level 2 自建 sim 与真实块位移不一致），最后是预算终止。

004 候选（把局部时序事实注入现有 Python 工具返回）**不会改变下表任一 listed episode**。同一条「N 帧、X 格 changed and changed back、bbox」已经出现在下一轮 user 提示里；模型有时用它、有时忽略它，但从未去读帧。把同一句话再放进 stdout，不会补上未读的帧，也不会修正图例/HUD 目标假设。不要再加一条「请看动画」提醒。

## 两组完成关 / 分数与停止原因

| 臂 | 分数 | 关卡 | 环境动作 | 分析步 | 停止 |
|---|---:|---|---:|---:|---|
| baseline | 1.37（复算 1.3656） | 1/8 | 112 | compact 1–30 | `state=cancelled`；`per-level=87/61,25/177,...`；analyzer note tokens=171039，history 记账 156178 |
| goal_evidence | 0.00 | 0/8 | 61（含 1 次 warmup RESET） | compact 1–19 | `state=cancelled`；`per-level=61/61,0/177,...`；analyzer 133440，history 100819 |

- baseline events：`action_num=87`、`analysis_step=22`、`ACTION4`/`RIGHT`、`level_completed=True`、`score=1`、进入 level 2；其后 25 个环境动作停在 level 2。对应 compact 过关后的 user 提示是 `analysis_step=23 action=88`（显示步 88、level 2）。
- goal_evidence events：全程 level 1、`score=0`、无 `level_completed`。`action_num=1` 是 `RESET`（`run.log`：`warmup RESET issued before the analyzer is reachable`），这是 003 已知的非确定性 warmup 差异，不是观察 API 缺陷。
- 两组 `game_over`/`done`/`run_complete` 均为 false。停止原因是共享墙钟预算取消（summary 记 `cancelled | unknown`），不是内部步数条耗尽后的自动失败。

## 三阶段计数

阶段定义：**(1)** 动画 API / 提示已经提供；**(2)** 模型代码真正读取相关动画帧（`last_animation_timeline` 或 `last_animation_frames`）；**(3)** 之后的假设因这些帧而更新。user 提示里的紧凑暂态句属于阶段 1，被推理引用仍不是阶段 2。

| 项 | baseline | goal_evidence | 说明 |
|---|---:|---:|---|
| user-prompt 动画线索 | **18** | **13** | 与 inventory hint 一致。有暂态时固定句式：`animated over F frames. C cells changed and changed back around rows r0-r1, cols c0-c1. last_animation_timeline shows them.` |
| reasoning 提到 animation/transient | **7** | **4** | compact `reasoning_mentions_animation`；多数在复述 user 线索或声称「去看动画」，而不是读了 timeline |
| compact `reads_animation_api` | **2** | **6** | `scripts/compact_requests.py` 的 CODE_HINT **包含 `frame_diff`**。两组这些调用全部是 `frame_diff()` |
| 代码含 `last_animation_timeline` / `last_animation_frames` | **0** | **0** | 阶段 2 = 0 |
| 因 **动画帧** 更新假设 | **0** | **0** | 无读帧，故无阶段 3 |
| 因 **user 线索** 更新/偏转假设 | 2 次采用、其余忽略 | 1 次口头打算、未执行 | 见 episode B3、B5；G2 |

阶段 1 的具体来源（不是新能力）：

- 系统/工具说明里已有 `last_animation_frames`（短动画各帧的 `.ascii/.segmentation`）和 `last_animation_timeline`（逐步 `old>new @(row,col)`）。user 提示在有暂态时点名 timeline。
- `action()` 的 JSON 里已有 `animation: {frames, transient_pixels, ...}`。compact 里几乎只有第一次打印完整 `r` 时看得见：baseline `analysis_step=2 action=2` stdout：`'animation': {'frames': 2, 'transient_pixels': 0}`。后续批次只打印 `no_op`/`tok`/`blk`，工具返回里的 animation 字段被丢掉。
- user 线索量级（只统计「changed and changed back」句）：baseline 8–108 格、2–9 帧；goal_evidence 8–88 格、2–3 帧。最大 bbox：baseline 通关 `rows 36-60, cols 27-46`（108 格、9 帧，含 HUD 行）；垂直拖曳 88 格 `rows 27-36, cols 12-46`（baseline）和 `rows 17-26, cols 12-46`（goal_evidence）。

## 关键 episode

004 列回答的是：把「变化区域 / 颜色或位置的暂态顺序 / 帧索引」写入**现有 python 工具返回**（不另调 LLM、不报胜利规则）会不会改变该 episode 的下一步代码或假设。提醒「请看动画」不算改变。

### baseline

| ID | compact step/action | 工具返回事实（引用） | 随后推理/代码 | 标签 | 004 会改变？ |
|---|---|---|---|---|---|
| B1 | `analysis_step=2 action=2` | stdout：`RIGHT -> effect`，`board_changed True`，`animation: {frames: 2, transient_pixels: 0}`；`frame_diff`：`changed_cell_count 12`，尾迹 `w/g` appeared 于 `[38,23]` 一带 | 代码：`r = action([{'action':'RIGHT'}]); d = frame_diff()`（compact `reads_animation_api=True`，实为 `frame_diff`）。无 `last_animation_*`。下一 user **没有** changed-and-changed-back 句（`transient_pixels=0`，与 Franzen「无往返暂态则沉默」一致） | 无失败；结算帧已足够看见尾迹伸长 | **否**。工具里已有 animation 摘要且暂态为 0 |
| B2 | `analysis_step=3 action=3` | stdout：`DOWN -> NO-OP (executed, no change inside the board area)`，`True False False`，`cells 0` | 下一轮把 DOWN 解释成边界/方向阻塞，改试 UP。仍是 `frame_diff`，不是动画帧 | dynamics error（一次空操作探测） | **否**。无暂态可注入 |
| B3 | `analysis_step=4 action=4` | 上一动作 UP 的 user 线索：`animated over 2 frames. 36 cells changed and changed back around rows 33-38, cols 12-28` | reasoning（`reasoning_mentions_animation=True`）：「the animation showed 36 cells changed and changed back around rows 33-38, cols 12-28 — meaning during the animation, the trail disappeared there and reappeared。」随后代码只打 segmentation，**不**读 timeline | 阶段 1 文本被采用；阶段 2 仍未发生 | **否**。004 会重复 user 句；模型已经用了这句，且选择不读帧 |
| B4 | `analysis_step=9 action=19` | 本 turn 无新动画线索（inspection）。stdout 量 bar 仍 64：`bar53 nonblack 64` | reasoning：「use the animation timeline of the touch. That's long gone (only last animation is retained).」改用系统实验，未 UNDO、未读任何 timeline | memory loss（早先 R 接触的暂态已不可得）+ goal-hypothesis error（图例空心=进度/附着，反复改写） | **否**。004 只覆盖**最近一次**动作的暂态，恢复不了 step 9 的接触动画 |
| B5 | `analysis_step=13 action=41` → `14/42` | 批次 stdout：5×RIGHT 后 `N` 仍 `(37, 42)`，`leg N False`，trail `(17, 46)`。user：`RIGHT animated over 3 frames. 8 cells changed and changed back around rows 36-41, cols 42-45`。下一动作 LEFT stdout：`N': (37, 36)`（N 被拉左 6 列） | rec22 reasoning 直接引用 8 格线索：「the animation for the last RIGHT showed "8 cells changed and changed back around rows 36-41, cols 42-45" — that's N's area, suggesting N flickered」。ascii 结算帧：`38 wwgwwgNNNNwB`（尾迹跨过 N 但 N 仍 16 像素）。仍把 `leg N False` 当成「未钩住」。LEFT 之后才承认 N 在动 | observation miss（未读 8 格的 old>new）**叠加** goal-hypothesis error（图例=钩住）。8 格线索已被引用，缺的是目标定义 | **否**。user 已给 bbox/格数；颜色序列最多确认「闪过 N」，不能解释图例为何不亮。钩住是 LEFT 的结算位移证明的 |
| B6 | `analysis_step=15 action=44` | 无动画 user 句。history 结算帧：`8 RIGHT ... {'R': True}`，R 在第一次贯穿后已空心 | 「Let me look at the animation of the moment R got marked... I can inspect history entries!」代码：`for i in range(8,13): f = history[i].frame` — 读的是 **history 结算帧**，不是 `last_animation_*` | goal-hypothesis error | **否**。要的是旧步图例，004 只附最近动画 |
| B7 | `analysis_step=19 action=63` | 批次最后 DOWN：`tok 30`，`b': (37, 42)`（b 被扫到 D 带）。user：`DOWN animated over 2 frames. 88 cells changed and changed back around rows 27-36, cols 12-46` | 下一轮按既定计划 LEFT/DOWN，reasoning **不引用**这 88 格。结算 `rd()` 已显示 b 下移 | 阶段 1 线索被忽略；但结算帧已含目标转移。不算「最终帧掩盖了唯一证据」 | **否**。注入同一 88 格 bbox 只是重复被忽略的 user 句；下一步不依赖中间闪烁 |
| B8 | `analysis_step=23 action=88`（events：`action_num=87` 过关） | 第 4 次 RIGHT：`LEVEL COMPLETED`，`level_completed True`；第 3 次已 `leg N True`。user：`animated over 9 frames. 108 cells changed and changed back around rows 36-60, cols 27-46`（bbox 含 HUD 行 54–60）并声明已进入 level 2 | rec38：「the animation showed 108 cells changing and the level completed」。随后用结算盘 + HUD 序 `R,O,b,N` 规划 level 2 换序，**不**读 9 帧 timeline | 过关成功。对 level 2 的目标迁移是 goal-hypothesis（HUD 左右序=必须的贯穿顺序），不是观察遗漏 | **否**。stdout 已有 `LEVEL COMPLETED` 与新块坐标；108 格句已在 user 提示 |
| B9 | `analysis_step=30 action=113` | 批次 `DOWN`+5×`RIGHT`：`level_completed False`。真实：`tok 24 {'b': (19, 24), 'N': (25, 36), ...}`；期望：`b` 仍在 `(25, 36)`。user：最后 RIGHT `3 frames, 8 cells ... rows 24-29, cols 48-51` | 自建 `sim2` 与真实不一致（`b` 被带到 row 19）。修 transitions 索引后 `bad 0`，但没有时间再执行修正计划。events 最后一动 `action_num=112`，仍 level 2 | dynamics error + budget termination | **否**。失败是 sim 与结算块坐标不一致，8 格闪烁改变不了这条 |

### goal_evidence

| ID | compact step/action | 工具返回事实 | 随后推理/代码 | 标签 | 004 会改变？ |
|---|---|---|---|---|---|
| G0 | events `action_num=1` RESET；compact 从 `analysis_step=1 action=2` 起 | RESET：`board_changed False` | warmup 消耗 1 动作，之后才 RIGHT | 运行时差异，不是观察缺陷 | **否** |
| G1 | `analysis_step=2 action=3` | 完整 `print(r)`：`animation: {frames: 2, transient_pixels: 0}`；`frame_diff` `changed_cell_count` 对应尾迹伸长 | 与 B1 相同，`reads_animation_api` 实为 `frame_diff` | — | **否** |
| G2 | `analysis_step=3 action=4` | UP stdout：`frame_diff` `changed 120`，token `M` `from [36,11] to [30,11]`，尾迹整段上移。user：`36 cells changed and changed back around rows 33-38, cols 12-28` | reasoning：**在动作前**写「Let me look at the animation frames of the last action」；代码却是 `d = frame_diff()`，没有 `last_animation_*`。结算帧已经显示头+尾上移 6 | observation miss（口头阶段 2，实际未读帧）。假设更新来自 `frame_diff` 结算位移 | **否**。36 格句出现在**下一** user 提示；本 turn 真正用的是 `frame_diff`。004 若写入本次 stdout，最多重复下一句已经提供的 bbox，不改变「用结算 diff、不读帧」 |
| G3 | `analysis_step=12 action=21` | UP stdout：`targets` 中 `b` 从右墙带到 `(19, 42)`（随臂上移）。user：`88 cells changed and changed back around rows 17-26, cols 12-46` | 下一长推理（rec15）讨论 HUD 空心与目标，**不引用** 88 格。crop 结算帧已显示 b 随臂 | 同 B7：大暂态被忽略，结算帧足够 | **否** |
| G4 | `analysis_step=13 action=22` | `MOUSE(row=21, col=43) -> NO-OP`，`chg 0` | 把 MOUSE 当分离/选择；确认无效后继续用 LEFT/RIGHT 搬块 | dynamics error（探测无效动作）+ goal-hypothesis error（在找「放下」机制） | **否**。无暂态 |
| G5 | `analysis_step=14 action=34` | 12 动作后：N 仍在右墙 `(31,42)`，HUD `R/N/b` 均无空心。user：最后 RIGHT `3 frames, 8 cells ... rows 30-35, cols 42-45` | 计划「钩 N 则 HUD N 应亮」失败。继续改写收集顺序/左右墙/竖排序 | goal-hypothesis error | **否**。8 格线索已在 user 提示；模型要的是 HUD 灯，结算 HUD 已是否定结果 |
| G6 | `analysis_step=19 action=62` | 6 动作后仍 level 1。history 结算：初始 `R@(19,42), b@(25,42), N@(31,42)`，HUD 序 R,N,b。`bar53 init 64 now 45` | 「The light appeared and disappeared over the animation... Let me look at the animation timeline of the step-9 RIGHT... I can't — too old (`last_animation_frames` is for the last action only).」**知道 API 存在仍不读当前最后一次动画**。随后 ~34k reasoning 无 tool call（compact rec27 只有 assistant+user） | goal-hypothesis error + memory loss（step 9 的灯）+ budget termination | **否**。004 不能复活 step 9；当前最后一次 UP 的 12 格线索已在 user 提示里，本 turn 也没读 |

## 对 004 实现的具体建议（就 sk48：**明确反对**用本游戏当正例）

sk48 **不支持**「最终帧变化很小、中间动画含模型没收到的转移事实，因此要把局部时序塞进工具返回」这条主假设。

1. **阶段 1 已经在做 004 候选的文本形态。** 有往返暂态时，user 提示已经给出帧数、格数、bbox，并点名 `last_animation_timeline`。这不是「再提醒一次」，是已经提供的紧凑事实。模型在 B3/B5 引用过它，在 B7/G3 忽略过它；忽略时结算 `rd()`/`frame_diff` 已经给出块的新位置。
2. **采用瓶颈在阶段 2，不是通道。** 两组 0 次 `last_animation_*`。goal_evidence 甚至写明 API 名字然后说「太旧了」——对**当前**最后一次动画同样没读。把同一 bbox 句从 user 提示复制到 stdout，不会变成读帧。禁止再加「请看动画」。
3. **本局反复缺陷是目标假设与动力学，不是被最终帧抹掉的暂态。** 图例空心与真实附着脱节（B5：N 被拉走但 `leg N False`）；HUD 左右序被当成胜利条件（B8→B9，G5–G6）。level 2 的失败是 sim 与真实 `b` 坐标不一致（B9）。这些都不能靠「变化区域 + 暂态顺序」在工具返回里宣布——004 计划也禁止替模型宣布胜利规则。
4. **若其他游戏（非 sk48）仍要做最小注入**，sk48 只提供量级，不提供开关借口：有暂态时 8–108 格、2–9 帧；常见小事件 8–12 格（钩/缩一格）；大事件 40–88 格（整臂竖移）；通关 108 格/9 帧且 bbox 可碰到 HUD。不要在 `transient_pixels=0` 时输出（B1/G1 已是这种沉默）。不要按 game id 写解法。
5. **goal_evidence 臂在 sk48 上 0 次 marker。** 本局差异是过关与否和 warmup RESET，不能写成 003 反证机制的效果。

**Listed episode 的 004 列全部为否。** 综合结论交给 Task 6；就 sk48 单独而言，不建议为这个游戏实现 `observation_evidence`。
