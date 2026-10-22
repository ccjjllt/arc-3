# 004 — sk48 轨迹归因（003 baseline vs goal_evidence）

> **2026-10-11 复核说明：** 本文最初使用的 compact 按消息长度去重，在上下文裁剪处会漏消息。下文原始盘点数字和三阶段计数保留为旧口径，不再作为当前统计结论；统一以 [004-review-data](004-review-data.md) 的原始日志新统计为准。已有 episode 引文与事件定位保留，不能把旧摘录当成完整轨迹。004 候选未实现、未做反事实对照；表中评价只描述现有证据支持程度，不能证明候选有效或无效。

日期：2026-10-11（Asia/Shanghai）。范围：只读 003 已下载 compact 请求与 action/analysis 事件；**未读游戏引擎源码**，未启动 GPU，未覆盖 003 notebook。

输入：

- compact：`runs/003-compact/baseline__sk48-d8078629_p0_requests.compact.json`（67 request / 65 records）、`runs/003-compact/goal_evidence__sk48-d8078629_p0_requests.compact.json`（30 request / 28 records）
- 事件：`runs/003-goal-evidence-ab/{baseline,goal_evidence}/artifacts/sk48-d8078629_p0_events.jsonl`（只取 `type=action|analysis` 的元数据；未把整盘 ascii 当作机制依据）
- 停止口径：`runs/003-goal-evidence-ab/{baseline,goal_evidence}/run.log`、`experiments/003-analysis/summary.md`

下文 `analysis_step` / `action` 均指 compact JSON 字段（`action` 是底座显示步，与 events 的 `action_num` 可差 1）。引用的 stdout / reasoning 来自同一 compact 记录。

## 结论

sk48 上 baseline 过了第 1 关（1.37、1/8），goal_evidence 一关未过（0.00、0/8）；两组都是墙钟预算取消，不是通关或 game_over。动画 **API 与 user-prompt 紧凑时序事实已经全程提供**（阶段 1）：有暂态时 user 提示写明帧数、changed-and-changed-back 格数和 bbox，并指向 `last_animation_timeline`。两组代码对 `last_animation_timeline` / `last_animation_frames` 的读取次数都是 **0**（阶段 2 未发生）。compact 里标成 `reads_animation_api` 的调用（baseline 2、goal_evidence 6）全部是 `frame_diff()`，比较的是结算帧，不是动画帧。

模型偶尔会把 **user 提示里的 bbox/格数** 写进推理（baseline `analysis_step=4 action=4` 的 36 格、`analysis_step=13 action=41` 的 8 格 N 闪烁），这是阶段 1 文本被采用，不是阶段 2 读帧。第 1 关实际过关来自结算状态上的「一臂贯穿同带三块」，不是读了 9 帧/108 格的通关动画。随后卡关是 **目标假设**（图例空心=钩住/收集；HUD 左右序=胜利条件）和 **动力学**（level 2 自建 sim 与真实块位移不一致），最后是预算终止。

004 候选（把局部时序事实注入现有 Python 工具返回）**效果未验证**。原版已提供帧数、格数和 bbox；复制同一句话新增的信息有限，但这不等于逐步颜色/位置事实已经交给模型。没有主动读帧是采用不足的线索，自动交付可能绕过该步骤，也可能引入噪声。当前 episode 尚未建立收益证据，暂不据此实现补丁或追加 GPU；这不是无效结论。

## 两组完成关 / 分数与停止原因

| 臂 | 分数 | 关卡 | 环境动作 | 分析步 | 停止 |
|---|---:|---|---:|---:|---|
| baseline | 1.37（复算 1.3656） | 1/8 | 112 | compact 1–30 | `state=cancelled`；`per-level=87/61,25/177,...`；analyzer note tokens=171039，history 记账 156178 |
| goal_evidence | 0.00 | 0/8 | 61（含 1 次 warmup RESET） | compact 1–19 | `state=cancelled`；`per-level=61/61,0/177,...`；analyzer 133440，history 100819 |

- baseline events：`action_num=87`、`analysis_step=22`、`ACTION4`/`RIGHT`、`level_completed=True`、`score=1`、进入 level 2；其后 25 个环境动作停在 level 2。对应 compact 过关后的 user 提示是 `analysis_step=23 action=88`（显示步 88、level 2）。
- goal_evidence events：全程 level 1、`score=0`、无 `level_completed`。`action_num=1` 是 `RESET`（`run.log`：`warmup RESET issued before the analyzer is reachable`），这是 003 已知的非确定性 warmup 差异，不是观察 API 缺陷。
- 两组 `game_over`/`done`/`run_complete` 均为 false。停止原因是共享墙钟预算取消（summary 记 `cancelled | unknown`），不是内部步数条耗尽后的自动失败。

## 三阶段旧计数（以复核新统计为准）

阶段定义：**(1)** 动画 API / 提示已经提供；**(2)** 模型代码真正读取相关动画帧（`last_animation_timeline` 或 `last_animation_frames`）；**(3)** 之后的假设因这些帧而更新。user 提示里的紧凑暂态句属于阶段 1，被推理引用仍不是阶段 2。

| 项 | baseline | goal_evidence | 说明 |
|---|---:|---:|---|
| user-prompt 动画线索 | **18** | **13** | 与 inventory hint 一致。有暂态时固定句式：`animated over F frames. C cells changed and changed back around rows r0-r1, cols c0-c1. last_animation_timeline shows them.` |
| reasoning 提到 animation/transient | **7** | **4** | compact `reasoning_mentions_animation`；多数在复述 user 线索或声称「去看动画」，而不是读了 timeline |
| compact `reads_animation_api` | **2** | **6** | `scripts/tools/compact_requests.py` 的 CODE_HINT **包含 `frame_diff`**。两组这些调用全部是 `frame_diff()` |
| 代码含 `last_animation_timeline` / `last_animation_frames` | **0** | **0** | 阶段 2 = 0 |
| 因 **动画帧** 更新假设 | **0** | **0** | 无读帧，故无阶段 3 |
| 因 **user 线索** 更新/偏转假设 | 2 次采用、其余忽略 | 1 次口头打算、未执行 | 见 episode B3、B5；G2 |

阶段 1 的具体来源（不是新能力）：

- 系统/工具说明里已有 `last_animation_frames`（短动画各帧的 `.ascii/.segmentation`）和 `last_animation_timeline`（逐步 `old>new @(row,col)`）。user 提示在有暂态时点名 timeline。
- `action()` 的 JSON 里已有 `animation: {frames, transient_pixels, ...}`。compact 里几乎只有第一次打印完整 `r` 时看得见：baseline `analysis_step=2 action=2` stdout：`'animation': {'frames': 2, 'transient_pixels': 0}`。后续批次只打印 `no_op`/`tok`/`blk`，工具返回里的 animation 字段被丢掉。
- user 线索量级（只统计「changed and changed back」句）：baseline 8–108 格、2–9 帧；goal_evidence 8–88 格、2–3 帧。最大 bbox：baseline 通关 `rows 36-60, cols 27-46`（108 格、9 帧，含 HUD 行）；垂直拖曳 88 格 `rows 27-36, cols 12-46`（baseline）和 `rows 17-26, cols 12-46`（goal_evidence）。

## 关键 episode

004 列只记录现有证据是否已被采用、是否存在未交付或未提取的事实，以及仍未知的作用。未做反事实对照，不能从原轨迹确定换一种工具返回后的下一步行为或过关结果。复制 bbox、提前交付、提供额外颜色/位置时序是不同变量，需要分别说明。

### baseline

| ID | compact step/action | 工具返回事实（引用） | 随后推理/代码 | 标签 | 004 候选的现有证据支持 |
|---|---|---|---|---|---|
| B1 | `analysis_step=2 action=2` | stdout：`RIGHT -> effect`，`board_changed True`，`animation: {frames: 2, transient_pixels: 0}`；`frame_diff`：`changed_cell_count 12`，尾迹 `w/g` appeared 于 `[38,23]` 一带 | 代码：`r = action([{'action':'RIGHT'}]); d = frame_diff()`（compact `reads_animation_api=True`，实为 `frame_diff`）。无 `last_animation_*`。下一 user **没有** changed-and-changed-back 句（`transient_pixels=0`，与 Franzen「无往返暂态则沉默」一致） | 无失败；结算帧已足够看见尾迹伸长 | **本次不触发暂态候选。** 工具已有 animation 摘要且 transient_pixels=0。 |
| B2 | `analysis_step=3 action=3` | stdout：`DOWN -> NO-OP (executed, no change inside the board area)`，`True False False`，`cells 0` | 下一轮把 DOWN 解释成边界/方向阻塞，改试 UP。仍是 `frame_diff`，不是动画帧 | dynamics error（一次空操作探测） | **本次未见可注入暂态。** 该观察不提供候选增益证据。 |
| B3 | `analysis_step=4 action=4` | 上一动作 UP 的 user 线索：`animated over 2 frames. 36 cells changed and changed back around rows 33-38, cols 12-28` | reasoning（`reasoning_mentions_animation=True`）：「the animation showed 36 cells changed and changed back around rows 33-38, cols 12-28 — meaning during the animation, the trail disappeared there and reappeared。」随后代码只打 segmentation，**不**读 timeline | 阶段 1 文本被采用；阶段 2 仍未发生 | **已采用汇总线索。** 重复相同 bbox 信息增量有限；更具体的时序事实是否改变理解未验证。 |
| B4 | `analysis_step=9 action=19` | 本 turn 无新动画线索（inspection）。stdout 量 bar 仍 64：`bar53 nonblack 64` | reasoning：「use the animation timeline of the touch. That's long gone (only last animation is retained).」改用系统实验，未 UNDO、未读任何 timeline | memory loss（早先 R 接触的暂态已不可得）+ goal-hypothesis error（图例空心=进度/附着，反复改写） | **保留记忆线索，效果未知。** 事后无法重新读取这段旧动画；若从早期动作就注入摘要，它是否保留在对话、是否被后续采用，现有轨迹不能回答。 |
| B5 | `analysis_step=13 action=41` → `14/42` | 批次 stdout：5×RIGHT 后 `N` 仍 `(37, 42)`，`leg N False`，trail `(17, 46)`。user：`RIGHT animated over 3 frames. 8 cells changed and changed back around rows 36-41, cols 42-45`。下一动作 LEFT stdout：`N': (37, 36)`（N 被拉左 6 列） | rec22 reasoning 直接引用 8 格线索：「the animation for the last RIGHT showed "8 cells changed and changed back around rows 36-41, cols 42-45" — that's N's area, suggesting N flickered」。ascii 结算帧：`38 wwgwwgNNNNwB`（尾迹跨过 N 但 N 仍 16 像素）。仍把 `leg N False` 当成「未钩住」。LEFT 之后才承认 N 在动 | observation miss（未读 8 格的 old>new）**叠加** goal-hypothesis error（图例=钩住）。8 格线索已被引用，缺的是目标定义 | **存在未读时序线索。** bbox 已被引用，但不等于已读取 old>new。LEFT 的结算位移支持 N 随臂移动；提前提供时序事实能否修正图例解释未验证。 |
| B6 | `analysis_step=15 action=44` | 无动画 user 句。history 结算帧：`8 RIGHT ... {'R': True}`，R 在第一次贯穿后已空心 | 「Let me look at the animation of the moment R got marked... I can inspect history entries!」代码：`for i in range(8,13): f = history[i].frame` — 读的是 **history 结算帧**，不是 `last_animation_*` | goal-hypothesis error | **保留旧证据检索线索。** 本轮只查看 history 结算帧；更早生成的摘要是否能保留相关暂态事实未验证。 |
| B7 | `analysis_step=19 action=63` | 批次最后 DOWN：`tok 30`，`b': (37, 42)`（b 被扫到 D 带）。user：`DOWN animated over 2 frames. 88 cells changed and changed back around rows 27-36, cols 12-46` | 下一轮按既定计划 LEFT/DOWN，reasoning **不引用**这 88 格。结算 `rd()` 已显示 b 下移 | 阶段 1 线索被忽略；但结算帧已含目标转移。不算「最终帧掩盖了唯一证据」 | **结算帧已有相关位移。** 重复 bbox 增量有限；不同时间或内容的交付效果未知。 |
| B8 | `analysis_step=23 action=88`（events：`action_num=87` 过关） | 第 4 次 RIGHT：`LEVEL COMPLETED`，`level_completed True`；第 3 次已 `leg N True`。user：`animated over 9 frames. 108 cells changed and changed back around rows 36-60, cols 27-46`（bbox 含 HUD 行 54–60）并声明已进入 level 2 | rec38：「the animation showed 108 cells changing and the level completed」。随后用结算盘 + HUD 序 `R,O,b,N` 规划 level 2 换序，**不**读 9 帧 timeline | 过关成功。对 level 2 的目标迁移是 goal-hypothesis（HUD 左右序=必须的贯穿顺序），不是观察遗漏 | **完成事实已明确。** 本行未见补充通关动画的直接信息需求；对后续关卡的影响未验证。 |
| B9 | `analysis_step=30 action=113` | 批次 `DOWN`+5×`RIGHT`：`level_completed False`。真实：`tok 24 {'b': (19, 24), 'N': (25, 36), ...}`；期望：`b` 仍在 `(25, 36)`。user：最后 RIGHT `3 frames, 8 cells ... rows 24-29, cols 48-51` | 自建 `sim2` 与真实不一致（`b` 被带到 row 19）。修 transitions 索引后 `bad 0`，但没有时间再执行修正计划。events 最后一动 `action_num=112`，仍 level 2 | dynamics error + budget termination | **已有明确模型失配。** 结算坐标足以发现 sim 错误；额外时序证据对修正速度和后续覆盖的影响未知。 |

### goal_evidence

| ID | compact step/action | 工具返回事实 | 随后推理/代码 | 标签 | 004 候选的现有证据支持 |
|---|---|---|---|---|---|
| G0 | events `action_num=1` RESET；compact 从 `analysis_step=1 action=2` 起 | RESET：`board_changed False` | warmup 消耗 1 动作，之后才 RIGHT | 运行时差异，不是观察缺陷 | **不是本候选处理的事件。** warmup RESET 属于已识别的运行差异。 |
| G1 | `analysis_step=2 action=3` | 完整 `print(r)`：`animation: {frames: 2, transient_pixels: 0}`；`frame_diff` `changed_cell_count` 对应尾迹伸长 | 与 B1 相同，`reads_animation_api` 实为 `frame_diff` | — | **本次不触发暂态候选。** transient_pixels=0。 |
| G2 | `analysis_step=3 action=4` | UP stdout：`frame_diff` `changed 120`，token `M` `from [36,11] to [30,11]`，尾迹整段上移。user：`36 cells changed and changed back around rows 33-38, cols 12-28` | reasoning：**在动作前**写「Let me look at the animation frames of the last action」；代码却是 `d = frame_diff()`，没有 `last_animation_*`。结算帧已经显示头+尾上移 6 | observation miss（口头阶段 2，实际未读帧）。假设更新来自 `frame_diff` 结算位移 | **存在 API 采用不足。** 实际用的是结算 diff；自动提供具体时序事实可能绕过主动查询，是否影响后续行为未验证。 |
| G3 | `analysis_step=12 action=21` | UP stdout：`targets` 中 `b` 从右墙带到 `(19, 42)`（随臂上移）。user：`88 cells changed and changed back around rows 17-26, cols 12-46` | 下一长推理（rec15）讨论 HUD 空心与目标，**不引用** 88 格。crop 结算帧已显示 b 随臂 | 同 B7：大暂态被忽略，结算帧足够 | **结算帧已有相关位移。** 未建立额外时序摘要的增益证据。 |
| G4 | `analysis_step=13 action=22` | `MOUSE(row=21, col=43) -> NO-OP`，`chg 0` | 把 MOUSE 当分离/选择；确认无效后继续用 LEFT/RIGHT 搬块 | dynamics error（探测无效动作）+ goal-hypothesis error（在找「放下」机制） | **本次未见可注入暂态。** 目标解释是否改变不能由本行推断。 |
| G5 | `analysis_step=14 action=34` | 12 动作后：N 仍在右墙 `(31,42)`，HUD `R/N/b` 均无空心。user：最后 RIGHT `3 frames, 8 cells ... rows 30-35, cols 42-45` | 计划「钩 N 则 HUD N 应亮」失败。继续改写收集顺序/左右墙/竖排序 | goal-hypothesis error | **目标假设有未解释反馈。** 8 格汇总提示已提供，但具体时序内容是否有区分力尚未核对。 |
| G6 | `analysis_step=19 action=62` | 6 动作后仍 level 1。history 结算：初始 `R@(19,42), b@(25,42), N@(31,42)`，HUD 序 R,N,b。`bar53 init 64 now 45` | 「The light appeared and disappeared over the animation... Let me look at the animation timeline of the step-9 RIGHT... I can't — too old (`last_animation_frames` is for the last action only).」**知道 API 存在仍不读当前最后一次动画**。随后 ~34k reasoning 无 tool call（compact rec27 只有 assistant+user） | goal-hypothesis error + memory loss（step 9 的灯）+ budget termination | **保留记忆与采用线索。** 当前 API 无法读取 step 9；早期摘要可能留在历史，也可能被裁剪或忽略，效果未知。 |

## 对 004 实现的研究判断

sk48 尚未建立局部时序摘要能增加通关的证据，但保留了采用不足、旧暂态不可再查及目标解释不确定的线索。不以本游戏单独决定新增 GPU 实验，也不把未读 API 当成自动交付无效的证明。

1. **已提供的是汇总线索。** B3/B5 引用了帧数、格数与 bbox；它们不包含完整 old>new 或物体位移序列。B7/G3 的结算帧已经显示相关位移，单纯复制这些汇总信息的增量有限。
2. **主动查询采用不足。** 旧计数为两组 0 次 `last_animation_*`，当前结论以复核新统计为准。自动把真实时序事实交付到上下文可能绕过查询步骤；需要先明确它提供了哪些原上下文没有的事实，再判断是否值得实现。
3. **目标与动力学问题确实可见。** B5 的 N 被拉走但 `leg N False`，B8→B9 与 G5–G6 将 HUD 顺序用于目标推断，B9 的 sim 与真实坐标不一致。观察补丁不能直接宣布这些规则，但可能影响模型如何推断；当前没有验证这种影响。
4. **旧摘录提供的量级。** 有暂态时 8–108 格、2–9 帧；常见小事件 8–12 格，大事件 40–88 格；通关 108 格/9 帧且 bbox 可碰到 HUD。这些是已有 episode 的观察值，完整分布以复核为准。不要按 game id 写解法。
5. **003 因果范围。** sk48 的 goal_evidence 未记录 marker，反证 nudge 没有发生；初始 guidance、生成随机性、warmup RESET 和共享调度对差异各有多大贡献尚未区分。

当前选择仍是保留 baseline、补齐公开能力分布。这里是资源优先级判断，不是候选效果已被否定。
