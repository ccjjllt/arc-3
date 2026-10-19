# 026 失败前缀修复诊断：确定性回放与宿主修复分支（CPU 研究）

日期：2026-10-19。无 GPU、无模型调用。脚本 `scripts/replay_026_prefix.py`、`scripts/build_026_fork.py`、`scripts/check_026_probe_budget.py`；派生 `experiments/026-repair-cpu/`。本轮只交付 CPU 研究半边（回放＋分叉输入＋配额守卫）；A/B 对照仍需 GPU，见末节待办。

## 1. 切入点与证据（全部来自已落盘日志，无新采集）

| 前缀 | 切入 T（累计已执行动作 / step / 关） | 故障证据 |
|---|---|---|
| ft09 L3（015 baseline） | 11 / 12 / L3（rec 14） | L3 起模型的 legend 转抄把 `gWg/WOg/WWW` 写成 `WOW`（rec 18 起 tool stdout 的 target legend grid，analysis_step 5–10 在 L3 耗 91 动作；正确路径约 14）。B 在 L3 入口先做 0 动作重算。 |
| tr87 L5（016 pace_1x） | 132 / 133 / L5（rec 60） | 把 tile top 当 ink top，15 黑点裁成 11，轮盘搜索 `HITS []`（rec 104，analysis_step 17）。B 在 rec 60 状态先重跑裁剪＋搜索函数。 |
| m0r0 L1（016 baseline） | 22 / 23 / L1（rec 36） | 随后 18 步循环第 2 步预测 `(44,44)` vs 实际 `(44,34)`（rec 36 tool stdout `(1,'RIGHT',False,...)`），仍继续 16 步。B 在 T 点先做一步预测-实际比对。自然修模对照：同局 rec 78/88（L2）。 |
| r11l（016 baseline，正常对照） | 40 / 41 / L3（rec 110） | 第 111 行真实跨关。检验 B 不误伤正常通关。 |

## 2. 确定性回放（fidelity 门）

`benchmark.json` 的逐动作历史在离线 Arcade 从头执行，四局检查点（每条“executed N … step S, level L”用户消息去重后）**100% 对齐**：ft09 13/13，tr87 16/16，m0r0 50/50，r11l 32/32。对齐规则：关号精确相等；`step = 回放步数 + 1（初始项）+ 死亡次数`——四局死亡均为 0，故 `step = 回放步数 + 1`。结果：`experiments/026-repair-cpu/replay-fidelity.json`。四局环境均确定（ft09/m0r0/r11l 无随机；tr87 用 `random.Random(level_seed)` 分关播种），与 024 的 tt03 全局 `random` 问题无关。

## 3. 分叉输入（CPU 已建成）

每前缀 `experiments/026-repair-cpu/fork-<game>/` 含：`tool_runtime_state.json`（Frame/HistoryEntry 回放写出，`load_runtime_state` 往返校验通过）、`conversation.json`（切入记录消息）、`kept-functions.json`（prompt 中解析出的保留函数名）。见 `fork-manifest.json`。**已知缺口**：请求日志不保存 `_kept_functions` 源码，B 分支修复必须自包含（带数据参数重定义 helper），输出经 stdout（→`_history_messages`）或顶层 `def`（→`_kept_functions`）交回主循环；不假设普通全局变量跨回合存活（009 底座每 `python` 调用是全新子进程）。

## 4. 配额守卫（CPU 单元验证 14/14）

`src/arc3_research/probe_budget.py` 的 `ProbeBudget`/`run_probe_batch`：每次真实下发前 `request()`，配额耗尽/过关/死亡返回带 `stop_reason`（`probe_budget_reached`/`boundary_*`）的正常字典并截断剩余批次，**不抛未捕获异常**（否则整段 stdout 与已定义函数被丢弃）。K=0 为纯重算。覆盖：12 步计划取 3、K=0 零下发、关卡/死亡边界优先、欠配额无截断、非法配额构造期拒绝、交接字段形状。修复了 024 `stall_probe.py` 的事后扣减缺陷（整批 `step3()` 一次下发绕过 3 步窗口）。

在线接线（二选一，GPU 时定）：(b) 宿主把探测拆成单动作 `step_env` 调用、每次查守卫——记账精确，推荐；(a) 装 `action_guard_hook` 按位置否决——在拒绝/无效动作处记账有偏差。两种都不改求解器源码。

## 5. 待办（需 GPU，约 1h 预算）

同一切入状态、共享剩余预算：A 臂原策略直跑；B 臂先跑 0 动作重算（仅确认失败时才申请至多 3 真实探测），再继续原循环（独立 Arcade 实例或 `/flush_cache` 隔离）。判据：B 是否真正改变随后动作并恢复通关；r11l 对照是否零误伤。若无增量恢复或频繁误伤，停掉该实现，不做在线触发器。

## 2026-10-20 评审修正
1. 停止路径：`ProbeBudget.stop_payload()` 普通 dict 不能终止模型 Python 循环；v1 的 guard 从未真正接线（构造了但没调用）。改为 K=0 重算：`install_zero_env_guard` 包 analyzer 实例 `_action_guard_hook`（每轮 analyze 重新抓取，无需底座补丁，与计时/观察器补丁无安装顺序耦合），拒绝走 solver 守卫路径（`solver.py:1047-1073` → 拒绝 payload `1136-1155` → 沙箱不可捕获异常，中断片段但保留 stdout 与已保留函数）。纯 Python 重算不经过该 hook，保持允许。`probe_budget.py` 与模块 docstring 中"永不抛异常/会丢输出"的旧说法已更正。
2. 切点边界：ft09 cut（cum 11 / rec 14）经核对是合法工具边界——rec14=request、rec15=同会话response（21 条消息完全相同）、rec16 前 21 条与 rec14 一致并新起 assistant turn；第 7 个 tool（含 6 动作批）已返回，无在途 Python、无局部状态可泄漏。m0r0 批内切点暂缓（只恢复消息/函数恢复不了循环位置，且整段 tool 输出已含后 16 步）。
