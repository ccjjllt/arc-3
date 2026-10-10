# 003 — Goal evidence 触发链复盘

日期：2026-10-11（Asia/Shanghai）。范围：审阅已完成的 003 GPU 运行、唯一 marker 的真实请求轨迹，以及最小诊断日志修补。本次没有启动 GPU，没有修改原运行 outputs，没有新增策略或测试文件。

## 结论

唯一 marker 的拒绝是正确的：它引用**刚刚已经成功的第 1 关**，当时真实 `current_frame` 已经是第 2 关。不是 step 编号差 1、JSON 类型错误、sandbox 未刷新或 hook 故障，也不是“预期目标达到但未过关”的反例。

003 实际向模型新增了初始 guidance 和可选事件报告约定；**反证提示没有触发过**。因此本轮差异只能解释为这份初始提示整体的单次实验结果，不能视为完成了事件反证机制的效果检验，也不能由 `nudge_count=0` 得出目标证据机制无效。

## 原始结果与定位

`runs/003-goal-evidence-ab/goal_evidence/goal-evidence.json`：

| 项目 | 原运行记录 |
|---|---:|
| guidance_count | 16 |
| marker_report_count | 1 |
| frame_validated_count | 0 |
| feedback_validated_count | 0 |
| nudge_count | 0 |

完整轨迹：`runs/003-goal-evidence-ab/goal_evidence/r11l-495a7899_p0_requests.jsonl`。第 23 行首次出现唯一 marker 的 tool reply（后续请求重复携带历史，不能重复计数）：

```text
tool_call_id = call_b0be66d224774304ac55016d
request event = request
analysis_step = 7
display action = 9
```

marker 为：

```json
{"goal":"place the middle (purple) bead exactly on the purple ring center","observed":true,"step":8,"level":1}
```

同一个 tool stdout 紧接着执行 `print(current_frame.level, current_frame.step)`，真实输出：

```text
2 8
```

`step=8` 匹配；`level=1` 与真实 `level=2` 不匹配。原日志没记录两侧值，只有 `unmatched_frame_claim`，需要完整轨迹才可确定这个原因。

## 前后证据链

1. 前一个 tool call `call_7da7ee9eb5b24ed78d70ab58` 的最后动作是 `MOUSE(row=21, col=15)`，stdout 明确为 `LEVEL COMPLETED`，其后打印 `lvl_done True over False`。
2. 下一条 user prompt 明确通知上一关完成、`current_frame` 是下一关起始棋盘，并写 `Current state: step 9, level 2`。这里 9 是底座显示层的加 1 编号。
3. 模型在 reasoning 中明确说 `Level 2! New board.`，并主动提出回顾第 1 关的完成证据。它生成的代码将 marker 的 `step` 和 `level` **硬编码**为 `8` 与 `1`，没有使用 guidance 示例中的 `current_frame.step/current_frame.level`。
4. 同一 snippet 随后打印真实帧为 `2 8`，并检查第 2 关 segmentation。

因此这不是无意把旧 `current_frame` 留在 sandbox。模型知道已经进入下一关，却将报告协议当成对成功目标的回顾。即便允许回顾旧帧，上一关本来就成功，也不满足“目标声明与未完成反馈冲突”的事件条件。

## 源码核对

底座使用本次已应用 Franzen patch 的源码，未更换版本：

- `inference/agent/python_tool_sandbox.py` 的 `_frame_from_payload` 对 `step/level` 使用 `int(...)`，本次 JSON 解码后也均为整数。
- 每次 `action()` 收到 host 的 `action_result` 后调用 `_refresh_state(reply['state'])`，覆盖 sandbox 的 `current_frame/latest_frame/history/...`。本次 marker 是新 snippet，初始化也会读取当前 runtime state。
- `inference/framework/solver.py` 的 `Frame.step` 与动作反馈的 `action_num` 都采用 `action_count`；`_build_user_prompt` 的显示 step 才加 1。hook 比较的是实际 `Frame.step`，所以没有使用显示编号导致偏移。
- 003 hook 将 marker 与 `_load_runtime_state(state_path)` 得到的**当前帧**比较。level 不同先记 `unmatched_frame_claim` 并退出，没有走到通关/终局检查。这解释了 `frame_validated_count=0`。

## session 日志缺陷

003 的每条事件都记录 `/kaggle/working/goal_evidence/artifacts`，确实无法单独从该字段区分游戏。原因是 `_session_runtime_dir` 是所有游戏共用的 artifacts **目录**；每个游戏实际使用不同的 `*_tool_runtime_state.json` 文件。

这次是诊断标识缺失，不是证据缓存跨游戏串用。solver 在 `_play_one` 中为每个游戏新建 `ToolAgent`，`_research_goal_evidence` 又保存在 agent 实例上，16 次 guidance 与逐游戏实例相符。

## 仅诊断修补，尚未进行新 GPU 运行

修改 `src/arc3_research/goal_evidence.py`：

- 增加 `diagnostics_version=2`。
- 透明 wrapper `_ensure_session`，只额外记完整 runtime 文件路径；事件增加 `state_path` 与原底座的 `dispatch_id`（如 `g15`），保留旧 session 目录字段。
- `unmatched_frame_claim` 增加精确 `reasons`、模型 observed 值、当前 `step/level`，以及最后动作与序列的完成/终局字段。
- 不修改 guidance、marker 格式、触发/拒绝条件、去重、工具输出、动作行为或模型调用数。

已通过真实 patched `ToolAgent` 和原 Python sandbox 做一次 CPU 手动重放：用合成 runtime `step=8, level=2`、已完成动作反馈，以及本次原样 marker，仍然不插入提示；新版日志准确记录 `reasons=["level_mismatch"]`、`current_step=8`、`current_level=2`、`feedback_level_completed=true`，并包含游戏文件名和 `g15`。这只是诊断重现，不是新的游戏实验。

原件与修补版本明确区分：

```text
003 实际运行 goal_evidence.py SHA256
685bb02f6618d8dc2e37814164ffeb716704cc901bd64b5c482d9e7551602fa9

本次诊断修补后本地 goal_evidence.py SHA256（未重新上 GPU）
317e773349b6794235899667a89a3962fd1c962e22731979ce1e8d34127b4a81

下载完成的 r11l 请求原件 SHA256
850c042fb685202cedd60010a8b1901a3aa47b9d16f035908b0555d70c1b50ae
```

未重写原 arm metadata、goal-evidence.json、Notebook 或已有请求日志。

## 下一轮研究应承接什么

本轮主要暴露的是**事件报告采用率与语义不匹配**：16 个游戏只出现 1 个报告，且它回顾已经成功的目标。尚不能判断稀少事件究竟来自目标误判少、模型没有采用可选约定、提示遗忘，还是模型没有在合适时点输出 marker；需要结合失败轨迹继续人工归因。

不要为了增加计数而放松帧匹配或把成功回顾当反证，也不要直接重跑同一机制并期待更多触发。下一轮若改事件获取方式，应单独立项、说明新的实际因子，并优先利用现有轨迹做 CPU 诊断，确认能够观测到所研究的失败事件后再投入 GPU。
