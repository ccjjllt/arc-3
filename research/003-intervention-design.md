# 003 — Goal evidence 最小干预实现

日期：2026-10-10（Asia/Shanghai）。实现文件：`src/arc3_research/goal_evidence.py`。研究计划对应 `docs/plan/003-next-experiment.md`；本文件记录 hook 与可复核实现细节，实际 GPU 结果仍以对应 progress 为准。

## 本轮只改变一个因子

原版已经有局部转移模型、动画读取与跨关提示。本轮不再增加动画提示、不改动作停止行为、不加额外模型调用。唯一变量是：将**模型自报的真实帧目标条件**与**环境返回的通关反馈**明确分开，在两者冲突时给一次短提示。

这里没有自动判断像素所代表目标的算法。`observed=True` 仍是模型声明，不能因此说目标条件真的成立；真实反馈只说明该时点没有过关。提示明确保留这个条件：如果观察正确，那么这个条件尚不足以构成胜利规则。

## 已核对的实际底座接口

从 dfranzen 原版 Notebook 的 source bundle 解包并应用其 cell 2 全量 patch 后，直接读取并导入：

`research/runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py`

精确接口：

```python
ToolAgent._build_user_prompt(
    self, action_num, *, valid_actions, current_frame=None,
    history_entries=None, previous_step_summary=None,
) -> str

ToolAgent._run_python_tool(self, state_path, arguments) -> _ToolDispatchResult
```

`_ToolDispatchResult` 是 frozen dataclass，字段为 `content`、`step_executed`、`made_progress`。修改输出使用 `dataclasses.replace`，后两个字段保持原值。

`_last_action_call_result` 提供 `executed/action_num/level_completed/game_over/run_complete`；序列摘要的跨关字段实际叫 `level_transition`，不是 `level_completed`。`Frame.step` 和动作反馈 `action_num` 都来自 solver 的 `action_count`；不是 user prompt 为显示而加 1 的 step。

## Hook 行为

1. `_build_user_prompt`：每个新游戏 session 只追加一次说明。模型只在自己候选的胜利条件已经出现在真实 `current_frame` 时，任选输出一行：

   ```python
   import json
   print("GOAL_EVIDENCE " + json.dumps({
       "goal": "当前候选胜利条件的简短描述",
       "observed": True,
       "step": current_frame.step,
       "level": current_frame.level,
   }))
   ```

   不要求每轮摘要；不把模拟器状态、中间子目标列为事件。

2. `_run_python_tool`：先完整执行原函数，再查看现有 stdout 中的精确 marker。只读取原工具已公开使用的 runtime frame 的 `step/level`，不读取环境源码、隐藏状态或规则。无 marker 的调用原样返回。

3. 引用当前帧、存在对应真实 action feedback、未通关/死亡且该工具无错误时，附加短 `goal_evidence` 输出：区别转移预测与胜利条件，最多保留两个目标及各一条证据，选择一项能区分它们的短观察/探测。真实动作仍完全由原智能体决定。

4. 同关同一目标文字只提示一次。目标文字最多保留 240 个字符。不改 system prompt，不改变已有记忆段落开关、不重写长期摘要。

## 运行与开关

```python
from arc3_research.goal_evidence import install_goal_evidence

# 在导入原 ToolAgent 之后、创建本 arm agents 之前调用。
patch = install_goal_evidence(enabled=(arm == "goal_evidence"))

# bm.run 结束后保存，runner 可在 finally 中执行以保留失败诊断。
(arm_output / "goal-evidence.json").write_text(
    json.dumps(patch.snapshot(), indent=2), encoding="utf-8"
)
```

首轮 runner 让 baseline 与 intervention 使用不同 CPU 子进程、共享同一个 SGLang GPU 服务，避免重复加载模型与不同 arm 的 Python session 污染。模块也支持 `patch.set_enabled(False/True)`，只能在一组 benchmark 完成之后切换，并创建新游戏 sessions。关闭时 prompt 和 dispatch 都直接返回原函数结果。

诊断 JSON 包含逐事件 `session/epoch/kind`，以及 `guidance_count`、`marker_report_count`、`frame_validated_count`、`feedback_validated_count`、`nudge_count`。这些计数分别回答：说明是否发出、模型是否采用报告格式、帧引用是否匹配、是否有对应动作反馈、最终插入几次提示。它们都不是通关成绩。

## 已手动验证

没有创建测试文件，没有调用 GPU 或模型。

- 使用已有 `/private/tmp/arc3-data-inspection-venv/bin/python` 直接导入已应用 patch 的真实 `ToolAgent`，用 `inspect.signature` 核对两个接口。
- 对真实 class 的 prompt 手动开关：关闭结果与原结果相同；启用只在 session 首次追加；再次关闭恢复原文本。
- 使用真实 Python sandbox、临时合成 `Frame(step=5, level=1)` 和明确标注的合成动作反馈，执行报告代码：首次补充提示，第二次同目标不重复，`step_executed/made_progress` 未改动。
- 手动执行普通 stdout、过时 step、`observed=False`、已通关、game over、缺对应动作反馈这六种输入，均无额外提示或 sandbox 错误。

这些检查说明 hook 能执行，不能说明研究假设有效。合成帧与反馈不是 ARC 游戏成绩。

## 尚未验证与读数方法

- 未验证模型会采用 marker，也未验证它是否准确识别候选目标；必须结合真实轨迹人工判断。
- 若 `marker_report_count=0`，只检验了初始提示的影响，没有检验反证事件机制；不能把无收益直接解释为目标证据无价值。
- 若 marker 被原工具输出长度裁剪，当前 hook 看不到它。不要为此在本轮改变原输出预算；若普遍发生，再作为下一轮独立问题处理。
- 一次提示后原版长上下文裁剪可能丢掉报告约定。本轮不混入额外记忆恢复因子。
- 文字去重不能识别语义相同的改写目标，也不负责断言目标真假。
- 未进行 GPU paired run、完整 25 游戏、隐藏评测。未产生涨分或比赛奖牌概率结论。

判读顺序：先看是否真实发出/采用事件，再人工读新增通关或失败轨迹，最后比较同条件完成关卡、动作与时间。动画机制保留给之后的独立实验。
