# 004 轨迹归因：tn36-ef4dde99

> **2026-10-11 复核说明：** 本文最初使用的 compact 按消息长度去重，在上下文裁剪处会漏消息。下文原始盘点数字和三阶段计数保留为旧口径，不再作为当前统计结论；统一以 [004-review-data](004-review-data.md) 的原始日志新统计为准。已有 episode 引文与事件定位保留，不能把旧摘录当成完整轨迹。004 候选未实现、未做反事实对照；表中评价只描述现有证据支持程度，不能证明候选有效或无效。

日期：2026-10-11。只读 003 compact JSON 与 events.jsonl；未读游戏引擎源码，未启动 GPU。  
编号一律用 compact JSON 的 `analysis_step` / `action`。events.jsonl 的 `analysis_step`/`action_num` 通常比 compact 少 1，仅作关卡完成/死亡对照。

Compact 形状：`records[].messages[]`，角色 `assistant` / `tool` / `user`。assistant 有 `reasoning`、`tool_calls[].code`、`reads_animation_api`；tool 有 `stdout`、`animation`、`mentions_animation`；user 有 `animation_lines` 与 `prefix`。

## 结论

tn36 不是“没看见动画”的游戏。基线已把 RUN 的暂态写进下一轮 user 提示（帧数、bbox、changed-and-changed-back 计数，并点名 `last_animation_timeline`），两组随后都大量读取 `last_animation_frames` / `last_animation_timeline`，并从中改写了 L1 的程序假设。基线据此过了 L1–L3，卡在 L4 的指令组合与预算；goal_evidence 过了 L1，卡在 L2 的字形→运动映射。失败中可见动力学/目标假设问题及预算终止，也有读取了帧却只提取部分相关事实的情况。**004 候选的过关效果未验证**：后期 RUN 经常与读帧在同一 snippet，首轮误解也在随后 cue 和查询后得到修正；这些事实降低了“缺少 API 入口”的解释力度，却不排除改变信息内容或交付时间的作用。保留 12/16 的观察提取不足线索，目前不据此单独启动 GPU。

## 两组完成关 / 分数与停止原因

来源：`runs/003-goal-evidence-ab/{baseline,goal_evidence}/benchmark.json` 与对应 `*_events.jsonl`。公开开发集，7 关。

| 组 | 分 | 完成关 | 动作 | 停止 | events 完成 | events 死亡 |
|---|---:|---:|---:|---|---|---|
| baseline | 13.76 | 3/7 | 286 | `cancelled`（预算） | L1@compact 10/14；L2@22/48；L3@34/119 | L3@33/110；L4@44/181、50/243 |
| goal_evidence | 3.57 | 1/7 | 109 | `cancelled`（预算） | L1@8/15 | L2@19/74 |

基线最终仍停在 L4、`NOT_FINISHED`、score 3。goal_evidence 停在 L2、score 1。两组都不是通关。

## 三阶段旧计数（以复核新统计为准）

阶段 1 = API/提示已经提供；阶段 2 = 模型读取动画 API；阶段 3 = 随后推理据所取事实更新假设。代码含 API 名只是查询代理指标，不能证明读取成功或提取充分。旧 `reads_animation_api` 还计入 `frame_diff`，不能直接作为阶段 2 统计。

| 量 | baseline | goal_evidence | 阶段 |
|---|---:|---:|---|
| user `animation_lines` 条数 | 42 | 17 | 1 |
| 其中点名 `last_animation_timeline` 的 RUN 暂态 cue | 全部 42 条均为此类 | 全部 17 条 | 1 |
| `reads_animation_api` 次（含 `frame_diff`） | 56 | 33 | 混合旧代理，不等于阶段 2 |
| 含 `last_animation_frames` | 43 | 28 | 2 |
| 含 `last_animation_timeline` | 4 | 9 | 2 |
| 仅 `frame_diff`、无 `last_animation_*` | 9 | 1 | 结算帧比较，不计阶段 2 |
| 含 `last_animation_*` 的唯一 `(analysis_step, action)` | 33 | 18 | 2 |
| 同一段代码里 `action(` 后又读 `last_animation_*` | 15 | 16 | 2 |
| `reasoning_mentions_animation` | 40 | 32 | 3 候选 |
| user cue 当回合未跟 `last_animation_*` | 11（见下） | 0 | — |

阶段 1 在首轮 user `prefix` 已声明 python 工具有 `current_frame` / `frame_diff` / `action`；`last_animation_*` 在沙箱里可用（两组代码实际调用成功）。更关键的阶段 1 事实：RUN 若终局棋盘不变，**下一轮 user 已经注入紧凑暂态**，不是空白。典型句：

> The last executed action (`MOUSE(row=55, col=37)`) animated over 7 frames and left the board area unchanged, but it was not a no-op: 256 cells changed and changed back around rows 13-59, cols 19-43. Whatever this action did is visible only there - read `last_animation_timeline` before concluding it failed.

基线 11 条 cue 当回合不再读 `last_animation_*`，对应的是已经在**上一回合同一 snippet** 里 `run()`/`action()` 后打印过帧的完成/死亡回合（例如 10/14 L1 完成、22/48 L2 完成、34/119 L3 完成）。不是把动画丢掉。goal_evidence 17/17 cue 当回合都读了。

tool 消息的 `mentions_animation` 两组都是 0：动画不在 `action()` 的默认 stdout 里，而在随后的 `last_animation_*` 打印中。这正是 004 候选想改的接缝，但 tn36 模型已经自己补上。

## 关键 episode 表

标签：观察遗漏 / 目标假设错误 / 动力学错误 / 记忆丢失 / 预算终止。一格可多标。004 列仅评价已有事实是否充分交付、提取或采用，不预测未经运行的过关结果。较早交付和减少查询可能改变时间成本，影响大小尚未验证。

### baseline

| step/action | 工具返回事实 | 随后推理/代码 | 标签 | 004 候选的现有证据支持 |
|---|---|---|---|---|
| 3/3 首次点蓝圆 | `action()` stdout：`MOUSE(row=55, col=37) -> NO-OP`，`changed 1`（只改 HUD 条）。下一 user cue：7 帧、256 cells changed and changed back，rows 13-59 cols 19-43。随后代码 `t = last_animation_timeline`：7 帧，step2 `Y>c 14, B>Y 14`；再 `fr = last_animation_frames` 裁切 rows 12–21 / 41–47。 | 推理：“yellow piece jumped down 4 rows … demo … T glyphs being a program … blue circle is a run button … drop the [piece] into the yellow U”。阶段 2+3 成立。 | 无失败。阶段 1 的 NO-OP 被下一轮 cue 纠正。 | **已有后续读帧与假设更新。** 提前交付可能省查询或改变探索，但没有运行对照，不能断言覆盖不变。 |
| 7/9 再 RUN | 同一 snippet：`action(MOUSE 55,37)` + `last_animation_frames`。stdout：`no_op True`；逐帧 `yellowrows` 从 `[13..16]` → `[17..20]` → …。user cue：298 cells changed back。 | “run animation is FIXED — the piece moved down twice … stems are NOT the command source; the BARS are the program”。阶段 3：用帧否定“茎=指令”。 | 无失败（L1 指令源修正）。 | **同一 snippet 已取得相关帧。** 重复事实的信息增量有限；摘要表示的作用未验证。 |
| 10/14 L1 完成 | `MOUSE(row=42, col=41)` 后 `run()`：`MOUSE(row=55, col=37) -> LEVEL COMPLETED`；`5-black run: ... completed True`。user cue：9 帧、314 cells，并 “You have completed the previous level”。 | “Confirmed: bars drive the run. 4 black bars → … No completion. Now try 5 black bars”。完成后来到 L2，开始拆双面板。未再读 `last_animation_*`（完成事实已在 `action()` 返回）。 | 无失败。 | **完成信号已明确。** 本行未显示通关判定需要额外摘要；后续影响未知。 |
| 12/16 L2 首次 RUN | `MOUSE(row=55, col=47) -> NO-OP`；`frames 6`；所有帧 `yellowrows` 相同 `[7..11, 24..27]`，highlight 沿 cols 37→42→47… 扫过程序区。user cue：405 cells, rows 24-62 cols 37-56。 | 下一回合：“All frames show the same yellow rows. So no movement.” 提取过粗（只盯 yellowrows），漏掉插座相对位移。随后 16/22 改读 timeline/帧后纠正。 | 观察提取不足 + 动力学推断错误；调用 API 已发生，但未取到相关位置事实。 | **保留观察提取不足线索。** yellowrows/highlight 没表达插座相对位移；局部位置时序可能提供不同信息。该线索尚不能证明可泛化提取方案或过关收益。 |
| 22/48 L2 完成 | 先读帧：socket 相对 `(24,45)` 在 col0 后 `shifted (-4 cols)` → “row1bar = left”；col1 无效果。随后 batch + `MOUSE(row=55, col=47) -> LEVEL COMPLETED`。 | 用逐帧 socket 位移标定指令，再写出完成程序。阶段 3 成功。 | 无失败。 | **已用具体位移标定指令并完成。** 候选能否减少标定成本未验证。 |
| 33/110 L3 死亡 | `batch of 11 actions, 3 executed ... stop_reason: game_over`。未读 `last_animation_*`。 | 已有路径假设 `[up, right×4, up]` 穿过 4×4 缺口，但一次 `setP` 点了 11 次把预算打穿。 | 预算终止；动力学/点击规划错误。 | **本次死亡发生在设置程序。** 本行未建立 RUN 动画摘要的直接收益证据；整个探索过程的反事实结果未知。 |
| 34/119 L3 完成 | reset 后 8 次点击命中 target，`MOUSE(row=58, col=58) -> LEVEL COMPLETED`。user cue：10 帧、646 cells，completed previous level。 | “Death cause: the budget bar was fully depleted”。然后重跑同一程序完成 L3。 | 前一格的预算死亡被正确归因。 | **已归因并重试成功。** 新摘要对前序探索或后续预算的影响未知。 |
| 44/181 L4 死亡 | 同一 snippet：`setP` 16 点 + `runP()` + `last_animation_frames`。stdout：`stop_reason: game_over`；帧里小 plug 停在 `(8-11, 45-48)`。 | “None of my 5 candidate combinations moved the small plug downward”。在读帧后仍判错“哪组字形=下”。 | 动力学错误 + 预算终止。阶段 2 真，阶段 3 失败。 | **已读帧但指令映射仍未确定。** 候选只能提供观察，不应宣布规则；表示是否有助于推断未验证。 |
| 50/243 L4 再死亡 | `MOUSE(row=58, col=58) -> GAME OVER`；`run no_op True ... gameover True`；帧 0 仍有两块黄物 `(24,28,40,45,16)` 与 `(8,15,45,52,56)`。user cue 给了 6 步动作列表。 | 预算条只剩 6，仍继续试指令。读了帧，没有完成。 | 动力学/目标假设错误 + 预算终止。 | **读帧后仍未完成。** 不能把这个结果当成新增摘要无效的对照。 |
| 61/286 预算截止 | 仍 `last_animation_frames`：robot2 RUN 时左精灵 `14→56→126→224`。 | 把 grow 写进世界模型，但 L4 未完成，run 被取消。 | 预算终止。阶段 2+3 仍在工作。 | **读帧与更新仍在进行。** 是否能更早收敛或减少查询成本未知。 |

### goal_evidence

| step/action | 工具返回事实 | 随后推理/代码 | 标签 | 004 候选的现有证据支持 |
|---|---|---|---|---|
| 5/5 首次 RUN | `probe(55,35)` stdout：`NO-OP`，HUD `changed 1`。user cue：7 帧、242 cells, rows 13-59 cols 19-43。随即 `last_animation_timeline`（step4 `Y>c 14, B>Y 14`）+ 两轮 `last_animation_frames` 裁切。 | “That's the yellow pieces moving down… Let me read the animation timeline.” 后：“Key observations from the animation”：cursor 扫 5 个 T，黄块下移 4 行后 revert。阶段 2+3 成立，与基线同类。 | 无失败。 | **已有后续读帧。** 更早交付可能改变查询成本；尚未验证行为和分数。 |
| 8/15 L1 完成 | 同一 snippet：`action(MOUSE 55,35)` + `last_animation_frames`。stdout：`LEVEL COMPLETED`，`level_completed: True`。user cue：9 帧、314 cells + completed previous level。 | “Mechanic: set switches … (B,B) = down, (B,w) = left; then click the blue ball … piece must land in the socket.” | 无失败。L1 指令编码与基线表述不同，但能完成。 | **完成事实已明确。** 额外摘要的增益未验证。 |
| 9/18 L2 首次有位移的 RUN | `last_animation_frames`：黄块 cols 45-48 → 49-52 然后 revert。user cue 给了 3 步点击 + RUN。 | “moved … RIGHT by one cell … cursor sweeps COLUMNS left→right”。阶段 3 开始改 L2 假设。 | 无失败（发现阶段）。 | **已采用位移事实。** 候选的额外信息和效果未知。 |
| 16/50 深读帧 | 多轮 `last_animation_frames` 与 `last_animation_timeline`。stdout 例：frame0 `cYBBYc` 在 row24；frame1 prongs 在底部；frame3 块在 rows 28-31。 | “HUGE INSIGHT! … the piece is FLIPPED VERTICALLY … TUMBLES/ROLLS”。又用 L1 history 对照杯口朝向，怀疑 flip 与完成条件冲突。尝试读“L1 最后一次动画”，但 `last_animation_frames` 已指向 L2 最后动作：“I need the animation frames of that action, but last_animation_frames now refers to the last action of level 2.” | 动力学错误（把过渡帧当成翻滚规则）；记忆丢失（L1 动画被 API 作用域盖住）。阶段 2 有多次查询，阶段 3 走偏；不能由查询次数判断提取是否充分。 | **保留表示误读与记忆线索。** 有逐帧 ASCII 不代表提取充分；更短时序表示或早期摘要是否减少误读、是否仍在历史中，均未验证。 |
| 19/74 L2 死亡 | 同一 snippet 点 3 次 + `MOUSE(row=58, col=46) -> NO-OP` + 逐帧黄块 bbox。user cue：6 帧、393 cells, rows 24-62 cols 37-56。events：该动作 `game_over`。 | 仍在调 timeline 的 `B>Y:2` 是不是 flip，与 frame1 字形不一致。下一回合 21/80：“Death frame: the bar is fully depleted … budget death”。 | 动力学错误 + 预算终止。 | **已观察死亡与部分位移。** 此次栏耗尽是事实；不能排除前序表示改变探索成本。 |
| 21/80 reset 后再测 | `bar [('B',1),('b',61)...]` 满条；`prog` 全灰；点 `(45,39)(48,39)` 后 RUN + `last_animation_frames`。user cue：377 cells, 程序区 bbox。 | “row-3 ⊥ → possibly UP”。帧显示无位移后放弃该假设。 | 动力学错误（继续穷举字形）。阶段 2 真。 | **观察到新假设被否定。** 更早或不同表示能否加快这一过程未知。 |
| 25/109–26/110 截止 | 25/109 仍读帧；26/110 推理：“D1 always moves DOWN regardless of orientation … piece … gone → off the board。” 未完成 L2。 | 阶段 3 部分收敛（D1=向下），但没有组成能进插座的程序。 | 目标假设/动力学错误 + 预算终止。 | **部分规则逐渐收敛但预算结束。** 候选是否改变收敛速度和最终覆盖未验证。 |

## 阶段判定（针对 004 问题）

1. **API/汇总提示已经提供。** 沙箱有动画入口；RUN 终局不变时，下一轮 user 已有 bbox、计数与读取提示。复制相同内容的信息增量有限，但不等价于提供了完整颜色或位置时序。
2. **已有多次读帧，充分性另判。** 原摘录的 33/18 唯一回合属于已被替代的旧统计，新数以复核为准。后期多个 episode 在同一 snippet 内动作后读帧；这支持“入口已被使用”，不支持“所有相关事实已经被取到”。12/16 的 yellowrows 提取漏掉插座相对位移就是反例线索。
3. **观察提取与规则外推可能同时出错。** 两组都从动画推断 RUN/程序条，基线又用插座位移标定 L2/L3。GE 的 flip/tumble 解读和基线 L4 指令映射仍不确定；仅凭“读过帧”不能把余下问题全部排除为观察问题，也不能断言摘要能解决它们。

## 对 004 实现的具体建议

**保留 12/16 作为观察提取不足的研究线索，暂不据此单独投入 GPU。** 下一步先明确如何从可见帧通用地提取插座相对位移，以及该事实与已交付内容有何差别；不能直接将它写成已证实的提分点。

若后续继续研究，tn36 给出这些实现约束和未解问题：

- 只改现有 python 工具返回，不新增 LLM 调用、不写 game-id 解法、不宣布“这是程序/这是目标”。
- 触发应贴近本游戏已经由 user cue 覆盖的条件：`action()` 报 NO-OP / 棋盘终局未变，但中间帧有 transient。把“N 帧、bbox、主颜色转移、可选每帧物体 bbox”接到**该次 `action()` stdout**，而不是下一轮 user 再提醒。
- 控制长度。GE 16/50 打印较多逐帧 ASCII 后仍产生可疑规则解释；这提示需要考察表示是否帮助提取，不能据此断言长输出必然有害或短摘要必然有益。
- 保留 `last_animation_frames` 入口。已有按需裁切适用于部分 episode；自动摘要是否减少查询成本、是否遗漏细节应分别记录。
- 12/16 的局部位置事实与已有 yellowrows/highlight 不等价。其他行已有更多帧事实，也仍需区分“收到”“正确提取”“用于规则推断”。目前没有 L2/L4 的候选对照成绩。

本轮只能保留可能影响查询成本或观察提取的假设。是否改变动作、推理时间或过关集合，均未验证。
