# 028 最小修复案例 — CPU 钉死报告（GPU 未启动）

日期：2026-10-20。设计见 `research/028-minimal-repair-design.md`；本文件只记录**已运行的 CPU 证据**，不含任何模型修复结论。

执行更新：见[029交接](../docs/handoff/029-score-and-submission-handoff.md)。zhuating在10月20日19:44实查CLI剩余GPU 30小时；原ft09日志已在本机，且已补齐027的tu93当前失败原件。无需等待配额刷新。下表仅对应原三个历史切点，新增tu93尚未做恢复检查。

## 结论先行

- 三个候选切点全部通过 CPU 门：同版本 + 同 seed（0）+ 固定录像目录，两次回放全同；`step = 回放步数 + 1 + 死亡数` 精确对齐（死亡均为 0）；均为合法工具边界（前一 tool 已返回、下一请求未发出）。
- 主选：**ft09 cum27 / rec30（L3 step28）**。理由：run 中段（72 记录之第 30，还有后文可比）、42 消息全窗口、kept={} 干净、WOW 转抄 + 15 动作失败扫面 + 显式 mismatch 列表三者齐备。
- 备选：tr87 cum220 / rec104（L5 step221）。通过但较弱：是 run 末记录（无后文可比）、窗口被截断为 32 消息、kept={C, bg2} 有残留。仅当 ft09 fork 建不起时启用。
- 落选（保留作 fallback）：ft09 cum26 / rec22。有 WOW + 扫面，但显式 mismatch 列表尚未出现（在 rec30 的 tool msg32 才出现）。
- ID+data 比较：ft09 前 11 动作全为 ACTION6 但 11 个坐标互不相同；纯 ID 比较报"无分歧"——026 v6 的漏报机制在此复现为 demo。修复比较必须 ID+data。
- GPU：**0 次修复调用、0 秒**。修复链（发现→修程序→执行→验证→主模型使用）中只有"发现输入已钉死"完成，其余四环需 GPU，预算（≤2 次调用、总 ≤1h）原封未动。

## 切点证据（均来自实际运行 `scripts/replay_028_prefix.py`，python3.12）

| 切点 | 双次回放 | 步数规则 | 工具边界 | 失败证据（无答案） |
|---|---|---|---|---|
| ft09 cum26/rec22 | 全同 grid `6563f643eb5e` | replay(3,26,0) vs log(27,3) OK | request；11 tools 已返回；next=response | WOW 在码 + 15扫面已执行；无显式 mismatch |
| ft09 cum27/rec30 | 全同 grid `1ae3dee748dc` | replay(3,27,0) vs log(28,3) OK | request；15 tools 已返回；next=response | WOW + 扫面 + mismatch 列表（msg32）+ probe 点击（msg40） |
| tr87 cum220/rec104 | 全同 grid `c4db95c67c04` | replay(5,220,0) vs log(221,5) OK | request；末记录无 next；15 tools 已返回 | HITS []（tool msg30，紧贴最终 user msg31 之前） |

cum 重算（去重后累加 exec）：26 / 27 / 220，与切点一致。完整 JSON：`experiments/028-minimal-repair/replay-fidelity.json`。

## kept_functions（恢复保真用）

- ft09 rec30 窗口内 retention 全是"not retained"（cell_color、crop）→ kept={}。fork 恢复时历史不得声称函数可用（026 v4/v6 教训）。
- tr87 rec104 窗口内：C(rows) retained（msg18/22）、bg2 retained（msg24）；word2 等 not retained → kept 至少 {C, bg2}，且窗口外未知。另一处不一致风险，已在 `experiments/028-fork-inputs.json` 标注。

## 输入纪律（已执行）

fork 输入 `experiments/028-fork-inputs.json` 只含：原始画面（经回放 env 复得）、完整代码历史（as-logged 消息）、实际输出（as-logged tool 输出位置指针）。**未写**正确图案、像素差结论、未来盘面。026 式 `QUOTED_EVIDENCE` 本轮不存在。

## 边界

- 这是公开题研究钉死，不是隐藏 LB 结论；n=1 前缀，无方差声明。
- 修复能力问题（设计中的 Q1–Q3）**未回答**——需在完整输入、真实修复入口及恢复检查通过后，使用zhuating执行最多2次修复调用窗口。
- 本机 `python3` 为 3.9（不支持 `match` 语法），回放须用 `python3.12` 运行；已在脚本头与报告中注明。
