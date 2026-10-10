# 001 — 赛制、数据与强基线研究结果

日期：2026-10-10（Asia/Shanghai）  
对应计划：[001-baseline](../plan/001-baseline.md)  
状态：赛制/数据/接口研究完成；强模型 GPU 复现尚未执行，交接给 003。

## 1. 实际完成的工作与文件

| 工作 | 产出 | 完成边界 |
|---|---|---|
| 比赛信息 | `research/snapshots/` 的比赛、页面、榜单、讨论 JSON | 读取时点快照；榜单仅前20 |
| 数据获取 | `research/data/arc-prize-2026-arc-agi-3.zip` 与 `extracted/` | 已下载并检查，非仅浏览网页 |
| 资产/版本 | `research/data-inventory.json` | 148文件、31wheel、25游戏版本及183关 |
| SDK与评分审读 | `research/data/sdk_inspection/`、`research/data-findings.md` | 检查通用接口和评分实现，没有读机制源码来解题 |
| 手动观察代码 | `research/data/manual_probe.py` | 只经 observation/action 接口运行合法随机策略 |
| 真实运行产物 | `research/data/manual-probe-20261010-valid-scorecard/` | observations/events/scorecard、初始帧及拼图 |
| 强基线源码与依赖 | `research/notebooks/cli-baseline/` 等 | 下载并阅读，未在我们的GPU上运行 |
| 交接文档 | README、001/002/003 plan及001/002 progress | MCP/CLI命令、研究决策和下一步实验 |

未创建自有测试文件、测试套件、CI 或门控流程。数据包自带的上游测试文件未运行。手动观察脚本是研究实验，不是算法效果测试套件。

## 2. 实测结果

有效实验：环境 seed=0；每个游戏的策略 RNG 都初始化为 20261010；每游戏 80 次 action；只从当前 `available_actions` 选择，点击坐标均匀随机，GAME_OVER 后 RESET。

| 指标 | 实测 |
|---|---:|
| 公开游戏 / 关卡 | 25 / 183 |
| 实际动作 | 2000，含11次关卡RESET |
| 完成关卡 / 游戏 | 0 / 0 |
| SDK0.9.8本地scorecard | AE=0.0，非空，含25游戏 |
| 最终帧完全未变 | 504/2000（25.2%） |
| 一次动作最多返回动画帧 | 42 |
| 初始允许点击的游戏 | 19/25，其中6个仅点击 |

结果只能说明合法随机策略在该单 seed、小预算条件下未通关，以及接口可运行。不能从 0 分推出世界模型、LLM 或主动探索的效果；也不能把帧未变等同于内部状态未变。

人工查看了 25 游戏初始帧拼图，确认细小对象、分区/网格和边缘 UI 广泛存在；图像不是环境规则说明。具体逐游戏数据见 [数据研究](../../research/data-findings.md)。

## 3. 问题及处理

- 初次运行带 `ONLY_RESET_LEVELS=true`，得到空 scorecard。通用 SDK 显示首次 reset 未产生 full_reset，离线计分没有登记首个 play；取消变量后相同观察策略重跑，获得有效计分。两次产物分目录保存，没有用空 scorecard 的0分充当结果。
- 官方 Random 示例未按每个游戏合法动作限制；本轮改用独立合法动作观察脚本，未冒称复现官方 Random。
- 官方 ReasoningAgent 使用外部模型 API，动作 schema也不覆盖全部按钮，不能原样作为本场离线解法。
- macOS 无法直接安装比赛目录里全部 Linux cp312 wheel；使用独立临时 Python3.12环境固定核心 SDK，依赖差异已记录。未声称本地运行验证了 Kaggle serving。
- 评分页面与提供 SDK 不一致：实际0.9.8执行代码为每关最高115%且有完成权重 cap。隐藏部署版本尚未实证，保留原始动作以便重算。
- CLI 带版本 `/3` 的 pull 返回403，不带版本成功；内容与 MCP v3逐cell一致。README如实写明验证范围。

## 4. 代码完成与研究效果分开说明

**代码/资产完成**：数据清单、手动观察脚本、版本与原始证据归档；公开强基线已下载并选定。没有实现新的正式参赛 solver。

**研究结论**：方向键中心的旧模板不足以覆盖动作空间；多帧动画必须可供推理读取；评分重视后续关卡；dfranzen是比从零智能体更有竞争价值的起点。

**效果未证实**：没有自己的强基线分数；没有新记忆、目标候选或调度机制的增益；没有push或正式提交。本轮未消耗Kaggle GPU运行额度。

## 5. 后续交接

执行 [003](../plan/003-next-experiment.md) 的单遍开发复现，保存我们自己的真实结果，再逐项改变机制。不得将上述随机0分和第三方46.49公开demo分混为同一个实验系列。接手者优先读README、实际Notebook Customization hook以及data-findings中的reset/评分版本说明。

