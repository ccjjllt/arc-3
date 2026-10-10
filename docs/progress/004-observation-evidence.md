# 004 — 观察证据使用（第一阶段）

执行：2026-10-11（Asia/Shanghai）  
对应计划：[004-observation-evidence](../plan/004-observation-evidence.md)  
状态：**CPU 归因完成。不实现 observation_evidence，不启动 GPU。** 保留 003 baseline。

## 代码完成

- 从 Kaggle 取回 003 的 su15 / tn36 / lf52 / sk48 两组 `*_p0_requests.jsonl` 与 `*_p0_events.jsonl`，放在 `runs/003-goal-evidence-ab/`（gitignore）。
- 增加手动工具 `scripts/compact_requests.py`，去掉重复历史；compact 写在 `runs/003-compact/`。
- **没有**新增 `src/arc3_research/observation_evidence.py`。
- **没有**新建 `notebooks/004-*`，**没有**覆盖 003 Notebook 或 `experiments/003-source/`。
- 003 目标 marker 保持关闭；warmup RESET 修复仍只存在于当前本地 `run_arm.py`，本阶段未上 GPU。

验证：人工阅读 compact 与 events；独立脚本重计 `last_animation_*` 次数；`python3 -m py_compile scripts/compact_requests.py`。没有测试文件。

## 运行完成

本阶段 GPU 作业数：**0**。未 `kaggle kernels push`，未正式提交比赛。配额仍以 003 后快照为准：剩余约 24.66h，10/17 刷新；执行下一 GPU 前重查。

## 效果结论

公开开发轨迹，不是隐藏榜。四局综合见 [004-observation-attribution](../../research/004-observation-attribution.md)。

| 游戏 | baseline | goal_evidence | 观察使用 | 004 候选会改过关？ |
|---|---|---|---|---|
| sk48 | 1.37、1/8、cancelled | 0.00、0/8、cancelled | 阶段 2 = 0；user cue 已给 bbox | 否 |
| lf52 | 7.73、3/10、cancelled | 10.91、3/10、cancelled | L1 读帧，之后吃 cue | 否 |
| su15 | 62.22、7/9、cancelled | 13.33、3/9、cancelled | 阶段 2 已密；单次分叉 | 否 |
| tn36 | 13.76、3/7、cancelled | 3.57、1/7、cancelled | 阶段 2 很密；卡在指令映射 | 否 |

阶段 1 已经提供动画 API 和「N 帧 / X 格 / bbox / 读 timeline」的用户提示。失败主要是目标假设、动力学和预算终止。把同类文字再写入工具返回，或再提醒看动画，都不构成新因子。

因此不晋升任何观察摘要补丁，不为该候选开 12 游戏 A/B。下一 GPU 选择：**25 游戏单遍 baseline**（计划表：约 2.17h，硬限 2.5h），补全公开能力/失败分布。另立项后再写计划。
