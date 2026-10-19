# 023 — 卡关后一次规则／目标探索

日期：2026-10-19。状态：**v3 COMPLETE，触发 0 次。** RTX 97887 MiB。配对均分 15.61→40.08，完成关 7→12，但 `stall-probe.json` 的 events 为空，分数差不能归到探索。详见 [023结果](../../research/023-stall-probe-results.md)。v2 探索臂崩溃，不能并进对照。停批接口和 FP8 没有改。

v3 的触发是同一关连续 4 个已执行、画面没有进展的批次。这个条件在社区失败局上对不上，已由 [024](024-level-stall.md) 改成按未过关的动作数计数。023 的内核不再上传。

CPU 检查见 `experiments/023-stall-probe-cpu/report.json`。对照是 m0r0、r11l、sb26，每臂 600 秒。社区这次跑完、并且确认 RTX 空闲之后再上传。
