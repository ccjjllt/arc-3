# 004 — 观察证据使用（第一阶段）

执行及复核：2026-10-11（Asia/Shanghai）  
对应计划：[004-observation-evidence](../plan/004-observation-evidence.md)  
状态：**CPU 归因及原始轨迹复核完成。本轮暂不实现 observation_evidence，GPU 作业数为 0。** 下一轮另见 [005](005-full-baseline.md)。

## 代码完成

- 从 Kaggle 取回 003 的 su15 / tn36 / lf52 / sk48 两组 requests/events，保存在 runs/003-goal-evidence-ab/（gitignore）。
- 增加 scripts/compact_requests.py。复核修复按历史长度切片导致的裁剪漏数，改为消息内容对齐和工具调用 ID 去重；保留每条事件的 response usage、finish_reason 与原始行号。
- 动画 user 提示改为提取 text part，避免保留整段 base64；分开记录代码内容引用、AST 语法引用与工具返回，不能把名称出现等同于成功读帧。
- 新结果写入 runs/004-reviewed-compact/；原始轨迹及旧 runs/003-compact/ 保留。恢复了旧输出漏掉的 25 个调用；新输出覆盖 raw 快照可见的全部 682 个唯一工具调用和 1405 条事件。
- 未新增 observation_evidence.py 或 004 Notebook，未覆盖 003 Notebook/源码归档。

手动核对：逐文件对照 raw 的调用 ID 集合、user cue、上下文裁剪边界、新增帧引用及 stdout。没有新增测试文件。详细原始定位、计数及限制见 [复核记录](../../research/004-review-data.md)。最后一次生成内容若未进入后续请求快照，不能仅靠 requests 文件保证完整可见。

## 运行完成

004 的 GPU 作业数：**0**，无正式比赛提交。下一轮 005 推送前已另查账户配额：剩余 24.5969h，10/17 00:00 UTC 刷新；本轮没有把该额度用于观察候选。

## 研究结果与效果边界

以下是 003 已发生的公开开发结果，不是 004 新实验，更不是隐藏榜。综合解释见 [004-observation-attribution](../../research/004-observation-attribution.md)。

| 游戏 | baseline | goal_evidence | 当前可支持的观察 |
|---|---|---|---|
| sk48 | 1.37、1/8 | 0.00、0/8 | 无可见动画 API 代码引用；曾使用 user cue，自动呈现的价值未验证 |
| lf52 | 7.73、3/10 | 10.91、3/10 | 有真实读帧和 cue 使用；后续相机/目标与预算问题 |
| su15 | 62.22、7/9 | 13.33、3/9 | 已有观察采用，两条路径明显不同；单次分差不能因果归因 |
| tn36 | 13.76、3/7 | 3.57、1/7 | 多次观察；部分 yellowrows 提取遗漏 socket 相对变化 |

四游戏两组均 cancelled。未实现、未运行的观察候选，其过关效果均为**未知**。已有帧数/bbox 提示不等于完整时序事实；当前证据不足以优先启动该候选 A/B，但没有证明其无效。各 trace 的旧计数已标注，修正计数以复核记录为准。

## 后续方向

继续保留 003 baseline，先做 [005 全25游戏单遍基线](../plan/005-full-baseline.md)：补全能力和失败分布，预计约 2.2h、硬限 2.5h。保留 tn36 相对位移遗漏和 sk48 主动查询不足作为后续线索；等全量结果形成后，选择具备具体观察事实和可测行为变化的一个候选。
