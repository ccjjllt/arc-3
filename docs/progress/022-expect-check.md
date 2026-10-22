# 022 — 已有预测值接入动作

日期：2026-10-19。状态：**v1 COMPLETE，接口零调用，路线暂停。** 39.6825→42.8571，只是 m0r0 多一关；266 条候选请求没有 `expect=`，没有 `checked_trace`。详见 [022结果](../../research/notes/022/022-results-analysis.md)。这是 3 个游戏、每臂 600 秒的接入探针，不是 12 游戏扩跑。

调用从 `pred` / `extract` / `scope` 改成模型已经算好的值：

```python
action(step, expect=pred, read=reader)
```

`reader(frame)` 必须返回和 `pred` 相同的值。一次失配抛出 `PredictionMismatch`，停掉本段剩余动作，并把 `checked_trace` 交给下一轮。换关、`game_over`、`done` 不算失配。普通 `action(...)` 不打印这条记录，避免给没进入检查的代码加输出。

本地 sandbox 已确认：普通批次不变、预测一致时返回原来的动作结果、第 2 步失配后第 3 步不送出、下一次调用可以按修正后的 expect 继续、过关和 `game_over` 不记成失配、点击坐标保留、缺 `read` 不降级执行、未声明像素不停、声明了的边缘会停。报告在 `experiments/022-expect-check-cpu/report.json`。这还不是模型自己走出这条链。

跑完后只看请求里有没有 `expect=`、有没有 `checked_trace`、失配后下一轮是否改了规则，以及相对 baseline 的动作和 token。若仍是零调用，这条近期路线暂停。
