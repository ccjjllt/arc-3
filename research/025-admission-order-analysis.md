# 025 首次入场排序：历史队列离线重算

日期：2026-10-19。CPU 只读重算，无 GPU、无模型调用。脚本 `scripts/analyze_025_admission.py`，派生数据 `experiments/025-admission-cpu/admission-recompute.json`。

## 方法

对 4 份历史完整队列（014 baseline / tail_80k，016 baseline / pace_1x 的 `scheduler-observer.json`，`events_dropped=0`），逐个 `selection` 事件重算：`snapshot=null` 的未入场候选把原 `2000000-100*idx` 换成 009 原版公式

`priority_value(PrioritySnapshot(level=1, actions=0, tokens=0.0, cost_multiplier=1.0, total_levels=number_of_levels), tail_lookup="remaining", normalize_score=True, 当时 tail_fraction)`

`total_levels` 取自同目录 `arm-metadata.json` 的 `game_results[].number_of_levels`；`tail_fraction` 由事件自带的 `clock_start/deadline/monotonic` 按 `0.2*(deadline-start)` 窗口重建（4 臂 `TAIL_FADE=1/FRACTION=0.2`）。已开局候选保留记录优先级。赢家取最大优先级，平局按小 token（堆序）。`cost_multiplier` 按交接要求传 `1.0`，不用 D-prime 的 `0.0`（原版会截断到 `pace=0.5`，把所有未入场初始值放大 2 倍）。

## 结果

| 臂 | selection 总数 | 新老混合竞争点 | 改选 |
|---|---|---:|---:|
| 014 baseline | 116 | 15 | 15（100%） |
| 014 tail_80k | 113 | 15 | 15（100%） |
| 016 baseline | 114 | 15 | 15（100%） |
| 016 pace_1x | 116 | 15 | 15（100%） |

* 60/60 个混合点全部改选：原 2M 波段恒选新游戏；真实初始值（6 关 1061 … 10 关 900，随总关数递减）远低于续跑局，续跑局跳过新局插队。其中 58 个改选提拔续跑局，2 个（两臂各一，均为 `m0r0` total=6，值 1061）在新局之间改排序。
* 全部改选点的 `tail_fraction>1`（fade 未激活，截断为 1），结论对 fade 重建不敏感。
* 被提拔的续跑局典型状态：`ar25 L6/actions 0`（014 tail_80k 15 次多为同一等待局）、`ar25 L4`（016 baseline 14 次）、`L5`（016 pace_1x 10 次）——多为刚进新关、动作为 0 的高价值局，符合“续跑刚进高权重关”的预期，而非 tokens 堆积局。
* 首次混合点均在 seq 74（10 并发下初始 10 局先跑，等待堆积满后开始竞争），早于 fade 区。

## 边界

这是历史选择点的静态重算，不是反事实仿真：真实改序会改变后续入场/过关轨迹，实际吞吐与饿死风险（零动作游戏数）只能由在线对照回答。若进 GPU：只包装 `_PriorityGate.acquire`，不动 `_enqueue_and_wait`/`_pump` 源码，按固定顺序装/逆序卸，并在配置中注册新 arm 名；用官方 25 题、10 并发验证。
