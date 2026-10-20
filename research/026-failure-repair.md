# 026 失败前缀修复诊断：最终报告（保留为诊断，不进候选）

**问题**：在记录的失败状态给模型一条宿主重算的证据，能否让它自行纠正并恢复通关？
**结论**：不能（有效零结果）。026 保留为诊断结果，不建在线触发器、不占正式候选名额。

## 1. 有效实验 v6（2026-10-20，`jiyujia/arc3-026-failure-repair` v6）

3 个合法工具边界切点（前一 tool 已返回、下一请求未发出）：ft09 L3（cum 11/rec 14，legend 误转抄）、tr87 L5（cum 132/rec 60，裁剪误识）、r11l L3（cum 40/rec 110，正常对照）。m0r0 暂缓：切点在 18 动作批调用内部，恢复不了循环位置且整段 tool 输出已含未来。双臂 exit 0（A 621s / B 483s），执行链完整：重算送达（B prompt 命中）、turn 正常（0 个 400）、恢复未被清空。

- ft09：A/B 首个后 T 动作完全相同（4 个同坐标 MOUSE），同 +1 关、同分 28.57。重算被送达但零利用——交付≠使用。
- tr87：首动作仅差一个方向键，双双 +0 关、同分。不同错误机制同样无恢复。
- r11l 对照：B +12 vs A +1 动作，同关同分，无误伤。

预注册标准（B 改变后续动作并恢复通关 + 对照干净）未达成。这是“交付与使用”缺口的又一次受控复现（017 行为证据同指向）。

## 2. 切点与回放（CPU，`scripts/replay_026_prefix.py`）

`benchmark.json` 逐动作历史离线重放，四局检查点 111/111 精确对齐（ft09 13、tr87 16、m0r0 50、r11l 32；`step = 回放步数 + 1 + 死亡数`，四局死亡为 0）。四局环境确定（tr87 用 `random.Random(level_seed)` 分关播种），与 024 tt03 全局 `random` 问题无关。产物 `experiments/026-repair-cpu/`（fork 态、会话、保真度）。

## 3. 三次 void 的机制教训（均有实证，非推测）

1. **v4：恢复被静默清空**。恢复写在 play() 之前，首个 analyze() 内 `_ensure_session`（`tool_agent.py:3605`）因目录不符清掉历史与函数——B prompt `HOST RECHECK` 0 命中。修复：显式 `_ensure_session(state_path)` 之后再恢复（真机双向验证：seed 后保留、seed 前恢复必清空；`scripts/check_026_fork.py` 钉住顺序断言）。
2. **v4：K=0 guard 名存实亡**。沙箱只对封闭 stop_reason 集（reset_not_first/stale_state/known_death/repeated_action_in_state/known_noop）抛不可捕获中断（`python_tool_sandbox.py:513-533`），自定义 `probe_budget_reached` 直接穿透（30 个后 T 动作照常执行）。专用预算停止需底座支持（blocked）；且概念上 K=0 约束的是修复（宿主纯重算），续跑必须能自由动作才能观测恢复。
3. **v5：图片占位 400**。恢复历史的 `<fork-stripped>` image_url 被原样发给 SGLang（`Non-base64 digit found`），analyzer 连败 11 次、6/6 fork 零续跑。修复：build 期直接删图片段（无 image-only 消息），`no image parts` 门进 CPU 检查。

`ProbeBudget` 预下发记账保留（`src/arc3_research/probe_budget.py`，14/14 CPU 验证），但停止语义以第 2 条为准：普通返回 dict 不能终止模型循环。

## 4. 边界

- 单固定顺序 pair、熟悉前缀，非隐藏分、非因果证明；n=1/局，方差声明同 025。
- 在线触发合同未建：若将来重启，需先解决专用预算停止的底座支持，并与诊断同执行路径；仍靠人工定点则永久保留为诊断。
- 输入清单：`docs/handoff/025-026-input-manifest.md`；启动记录：`experiments/026-launch.json`。
