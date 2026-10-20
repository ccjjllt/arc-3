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

## 2026-10-20 收敛重算（双 baseline only）
按评审意见收缩范围：只取 014 baseline + 016 baseline（arm-metadata 确认两臂调度策略完全一致：remaining/PACE=0/normalize=1/FADE=1/0.2/refresh=1/10流/0热身）。tail_80k 与 pace_1x 排除。

方法修正：
- 保真门：argmax(priority, token小者胜) 与记录 `selected` 行在 230/230 selection 事件全部一致（两臂 candidate_omitted 全 0），heap 规则复现通过。
- 初始优先级的旧 docstring 有误：底座为 `_PRIORITY_UNTRIMMED_BASE - (game_index*100 + pass_index)`（`tool_agent.py:2150`、`solver.py:598-601`），旧 docstring 的 `100*idx` 表述不完整；重算不受影响（null 直接替换）。
- 解释力声明：单决策反事实。首次改选后真实时钟/关卡/队列即分叉，不能由旧日志推算新策略整场分数。

结果：每臂 15 个混合决策，30/30 翻转，首次均在 seq 74（Late-run，前期是纯新游戏入场）。29 次是续跑游戏保住槽位（新游戏延后入场），1 次是新对新调换（014 seq74：m0r0 顶掉 lp85）。被保住的续跑多为深关卡低消耗态（如 ft09 L6 零消耗、cn04 L4）。
结论：改选机会存在且方向一致——009 值系统性偏向续跑、延后新游戏入场。是否涨分只能由官方 25 题 10 并发 A/B 回答（看聚合 RHAE、新题是否被饿死、续跑深关收益）。

## 2026-10-20 在线 A/B 结论：关线
官方 25 题、10 并发、等墙钟（7254s/臂），`qingyu1232/arc3-025-admission-order` v1，双臂 exit 0 跑满。
补丁在线生效：25/25 首次入场替换、0 fallback（`runs/025-admission-order/admission_009/admission-order.json`）。

| | baseline | admission_009 |
|---|---|---|
| mean score | 45.88 | 45.46（Δ-0.42） |
| levels | 106/183 | 103/183 |
| wins | 7 | 5 |
| tokens | 4.45M | 4.40M |

按预注册标准（聚合涨分 + 无新题饿死 + 无续跑回归）三项全不过：
- 无聚合涨分：Δ-0.42，且单局方差主导（±20~97 双向摆动，n=1/局），无信号。
- 续跑回归：m0r0 L6→L0（351→57 动作）、cn04 L5→L1、ar25 通关→L5、cd82 通关→L4、tn36 L6→L3、sk48 L4→L1。
- 饿死信号：m0r0/cn04 在 B 臂仅 57/56 动作（A 臂 351/272）；槽位分布上 m0r0 8→3、sk48 7→2 次选中。
B 臂也有大涨的局（vc33 +79、s5i5 +55、r11l +43），但双向巨幅摆动 + 均值持平 = 方差，不是策略红利。
结论：025 关闭正式候选，不进提交构建器。离线 30/30 翻转没有转化为在线收益；机制按设计运行了，但方向（系统性偏向续跑、延后新题）在此预算下不涨分且制造饿死。
