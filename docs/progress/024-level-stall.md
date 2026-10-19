# 024 — 未过关满 64 步后的一次探索

日期：2026-10-19。状态：**v1 COMPLETE。窗口打开 3 次，关卡没有增加。不扩跑 GPU。** RTX 97887 MiB。ih01 仍是 0/7，tt03 两臂都是 2/3。详见 [024结果](../../research/024-level-stall-results.md)。不扩大，不提交。

触发是同一关累计 64 个已执行动作仍未过关。画面变化、失败和 RESET 都不清零；过关才清零。每一关只打开一次，接下来 3 个动作记在窗口里。没有新的动作接口，也没有常驻提示。

ih01 和 tt03 的失败原因、回放开火位置见 [024记录](../../research/024-level-stall.md)。CPU 单元检查是 `experiments/024-level-stall-cpu/unit-report.json`，回放是同目录的 `replay-report.json`。

对照是这两局、每臂 1800 秒。模型读到了提示：ih01 把它当成死亡预算来检验，tt03 继续原来的收集走法。停批接口和 FP8 没有改。

追加（同日 CPU，不开新 GPU）：ih01 已单列——7 关上界只有加热格达标（L1 2/100 … L4 4/100），0/7 是天花板，不再当提分目标；tt03 的 Arcade seed 被丢弃、刷怪走全局 `random`，同 py_seed 全同、换 seed 即分叉，022/024 的关数差不可比。证据见 `experiments/024-level-stall-cpu/ih01-solvability-report.json`、`tt03-seed-report.json`，结论见 [024记录](../../research/024-level-stall.md) 末节。下轮选关须先过 CPU 门：可解＋确定性 RNG＋固定预算失败可复现＋同 seed 重跑同向增益。
