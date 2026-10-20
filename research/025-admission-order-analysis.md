# 025 首次入场排序：从离线重算到在线 A/B 的完整结论

**问题**：新游戏首次入场用 009 快照值代替 2M 波段，能否涨分？
**结论**：不能。关闭正式候选，不进提交构建器。正式基线保持 009 v2 / submission 57101330 / public 31.16。

## 1. 在线 A/B（2026-10-20，`qingyu1232/arc3-025-admission-order` v1）

官方 25 题、10 并发、等墙钟（7254s/臂），双臂 exit 0 跑满。候选补丁在线生效：25/25 首次入场替换、0 fallback（`runs/025-admission-order/admission_009/admission-order.json`）。

| | baseline | admission_009 |
|---|---|---|
| mean score | 45.88 | 45.46（Δ-0.42） |
| levels | 106/183 | 103/183 |
| wins | 7 | 5 |
| tokens（action-attached） | 4.449839M | 4.404089M（-1.03%） |
| tokens（analyzer-report总量） | 4.528520M | 4.600032M（+1.58%） |

预注册标准（聚合涨分 + 无新题饿死 + 无续跑回归）三项全不过：
- 无聚合涨分：Δ-0.42，且单局方差主导（±20~97 双向摆动，n=1/局），无信号。
- 续跑回归：m0r0 L6→L0（351→57 动作）、cn04 L5→L1、ar25 通关→L5、cd82 通关→L4、tn36 L6→L3、sk48 L4→L1。
- 分配不足（原“饿死”口径修正）：两臂均为25/25游戏有动作，无零动作游戏，最小动作基线37（r11l）、候选51（r11l）；m0r0/cn04在B臂仅57/56动作（A臂351/272），槽位选中m0r0 8→3、sk48 7→2。属分配不足而非饿死，归因需等待时间/占用时段证据。
- Token口径修正：报告原4.45M→4.40M为action-attached口径；计入未挂接部分后analyzer总量反而+1.58%。不得称节省总token。

B 臂也有大涨的局（vc33 +79、s5i5 +55、r11l +43），但双向巨幅摆动 + 均值持平 = 方差，不是策略红利。标准对比：`experiments/025-analysis/summary.{json,md}`（`summarize_experiment.py --reference baseline`）。

## 2. 离线重算（2026-10-19/20，CPU 只读）

范围经评审收敛：只取 014 baseline + 016 baseline（arm-metadata 确认两臂调度策略完全一致：remaining/PACE=0/normalize=1/FADE=1/0.2/refresh=1/10 流/0 热身；tail_80k 与 pace_1x 因属其他策略而排除）。脚本 `scripts/analyze_025_admission.py`，派生 `experiments/025-admission-cpu/admission-recompute.json`。

- 保真门：argmax(priority, token 小者胜)与记录 `selected` 行在 230/230 selection 事件全一致（两臂 `candidates_omitted` 全 0），heap 规则复现通过。
- 方法：仅 null（未入场）候选替换为 009 值 `priority_value(PrioritySnapshot(1,0,0,1.0,N), remaining/normalize/当时 tail_fraction)`，`cost_multiplier=1.0`；已开局保留记录值；同堆平局规则。
- 结果：每臂 15 个混合决策，30/30 翻转，首次均在 seq 74。29 次续跑保位、1 次新对新调换（014 seq74：m0r0 顶掉 lp85）。被保住的多为深关低消耗态。
- 解释力：单决策反事实。首次改选后真实时钟/关卡/队列即分叉，不能由旧日志推算新策略整场分数——这正是必须跑在线 A/B 的原因。

## 3. 候选实现（`src/arc3_research/admission_order.py`）

只动首次 `acquire`：包 `_HarnessGameSession._queue_position`（per-session，16 流无竞态），经 gate 自身 `_snapshot_priority(now)` 求值（与已开局同一调用，公式零漂移）；失败回退 2M 波段并计数。候选先于计时/观察器安装、逆序卸载。预注册的饿死/回归门写在 `experiments/025-admission-order.json` 的 `selection_note` 中。

## 4. 边界与教训

- 离线 30/30 翻转没有转化为在线收益；机制按设计运行了，但方向（系统性偏向续跑、延后新题）在此预算下不涨分且制造饿死。
- 附带纠错：旧 docstring 的 `2000000-100*idx` 表述不完整，底座实为 `_PRIORITY_UNTRIMMED_BASE - (game_index*100 + pass_index)`（`tool_agent.py:2150`、`solver.py:598-601`）。
- 输入清单（含 runs/ 大文件哈希）：`docs/handoff/025-026-input-manifest.md`。
