# 003 — 强基线复现与首轮目标假设实验

日期：2026-10-10（Asia/Shanghai）  
状态：**已完成运行与分析**；结果见 [对应进展](../progress/003-next-experiment.md)。保留本文件的原实验假设与执行修订，下一轮见 [004](004-observation-evidence.md)。  
继承：[001](001-baseline.md)、[002](002-strategy-improvement.md)。

## 2026-10-10 执行调整：30h 每周 GPU 配额

用户要求尽可能提高 GPU 利用率。首轮改为一次加载模型、两个独立 CPU harness 进程的 16 游戏对照筛选：baseline 与 goal_evidence 各 4642 秒（沿用原版 532min×16/110），10 条 active streams，预计约2.8h，Notebook硬上限10800秒。GPU权重不重载，组间尝试清空prompt cache；独立进程隔离调度时钟、import-time开关与agent记忆。其余9个公开游戏用于后续扩展。

本轮只实现目标证据反馈单因子，不同时加入动画干预或新调度。模型主动报告当前观察符合候选目标、且真实环境未过关时，返回短反证提示；记录采用与触发率。没有额外LLM调用。16游戏是依据已读轨迹选择的开发筛选集，不称未见验证集。顺序A/B仍有编译内核热身等顺序影响，一次比较不能证明显著提升。

本次自有launcher替换了原版benchmark执行段，因此CLI可以直接设10800秒；下文“保持32400秒”的要求仅适用于未修改的原版入口。先用本次筛选决定是否值得花更多配额执行下文完整25游戏复现与独立重复。具体配置：[003-goal-evidence.json](../../experiments/003-goal-evidence.json)。

## 1. 要回答的问题

在原版模型、推理栈、算力和动作接口不变的条件下，**区分“转移模型正确”与“胜利条件正确”，并保留可反驳的目标证据，能否增加首次未解关的通过率和后段关卡覆盖？**

先完整复现 baseline，复核我们自己的失败是否与公开日志一致。若失败类型不同，就据实调整实验，不强推现有假设。

已有证据而非本项目强模型成绩：

- 原版公开 v3 100 条轨迹 46.4930，固定完成集合上限 49.1227。
- sk48：自建模型预测匹配仍未过关，目标假设有误的典型。
- lf52：最终帧相同不代表没有信息，动画可能揭示机制。
- tn36：成功轨迹使用动画；适合检查新增提示是否损伤原有能力。
- 本项目仅手动运行过合法随机策略 25×80 动作，0 关完成，不能作为强基线效果。

## 2. 可直接接手的资产

| 资产 | 路径 |
|---|---|
| 已经 CLI pull 的原版 | `research/notebooks/cli-baseline/arc-agi-3-milestone-2-solution.ipynb` |
| 对应 CLI metadata | `research/notebooks/cli-baseline/kernel-metadata.json` |
| MCP v3 metadata | `research/notebooks/dfranzen__arc-agi-3-milestone-2-solution.metadata.json` |
| 作者原始输出 | `research/notebooks/dfranzen-v3-output/benchmark.json`、`*.log`、三个选取的 `*_requests.jsonl` |
| 全部公开环境 | `research/data/extracted/environment_files/` |
| 版本及人工观察 | `research/data-inventory.json`、`research/overview/data-findings.md` |
| 研究依据 | `research/overview/notebook-findings.md`、`research/overview/frontier-findings.md` |

当前源码可提取修改，但未解包为本项目正式 solver。不要将 research 中第三方源码误称为我们的算法实现。

## 3. 实验 E0：同等每游戏预算的强基线

准备 `notebooks/001-baseline/`，按 README 的复制和 metadata 修改步骤生成自己的私有 Notebook。删除原作者 `id_no`，使用自己的 owner/slug。保留模型、两份 dataset、Docker、RTX 和断网设置。

**开发运行配置需明确：**

原版 v3 的 Customization hook 默认 `bm.n_passes = 4`；正式比赛分支自动设为 1。原版公开运行的 4 遍不是四次独立 9 小时。

第一次开发复现设 `bm.n_passes = 1`，保留原版按 110 个隐藏游戏归一化的开发时间预算，以及 10 个 active slots。源码当前在 demo 分支计算：

```python
bm.solver.concurrency = 25 * bm.n_passes
bm.solver.max_runtime_s_per_game = 532*60 * bm.solver.concurrency // 110
```

单遍大约 7254 秒 solver 预算，加加载/收尾，预计约 2.2–2.5 小时；这是根据源码估算，记录实际值。CLI Notebook 上限仍用 32400 秒，**不要仅把 CLI timeout 改成两小时**：原版要求 target.max_runtime_s=32400，内部 solver 自行缩放。不要把“四遍预算”全部给单遍然后称为公平提升。

第一次完整 25 游戏跑完后，在独立 session 复跑一遍原版以了解我们运行条件下的波动；固定可设置的随机种子，保存剩余非确定性说明。不把两遍挑更高者当 baseline。

人工确认：scorecard/benchmark 非空，运行确实是公开 OFFLINE，日志显示全部游戏尝试，动作接口含运行时可用动作，保存最终停止原因。这是手动研究检查，不创建测试文件。

## 4. 实验 E1：最小目标假设修改

只改 agent 提示及少量状态记录，不改模型、serving、调度公式、动作 batch 停止行为。

新增机制：

- 当动作效果已被模型预测但预期目标没有带来过关时，将当前目标记录为尚未支持/已被反驳。
- 仅保留 2–3 个竞争目标，各记录一条支持证据和下一次可区分它们的观察。
- 临时目标来自实际帧，不写入“sk48 要如何解”“lf52 的某颜色一定是什么”等人工答案。
- 对最终帧不变但有 transient animation 的转移，提供其证据引用供模型按需读取；原版已有动画 API，不再另建重复观察系统。
- 短提示只在上述有信息的事件发生时插入；其他回合沿用原版，不每轮生成长表格。

拟改动：

- `inference/agent/prompts.py`：目标假设与反例的简短提示。
- `inference/agent/tool_agent.py`：已有动作/关卡反馈位置挂接目标状态，不改变真实 API 的动作计数。
- 如需要持久引用，再添加 `inference/agent/evidence_memory.py`；如果没有裁剪后遗忘证据，此项留到 E2。

先保持 Python 函数保留、推理历史、关闭旧 world-model 摘要等设置与基线相同。

## 5. 开发集与留出

先用 sk48、lf52、tn36 及一个原版稳定成功游戏做轨迹诊断。这几个游戏已通过公开日志参与了选题，不能称为未见留出。

随后用全 25 游戏单遍和 E0 对照。对未用于改提示的游戏报告单独结果；若做机制家族留出，应先固定分组、再调参。公开游戏已经存在于网上，即使留出也不能排除基础模型见过资料；真正陌生泛化仍依赖 Kaggle 隐藏集。

固定比较项：相同硬件、底座、serving、动作接口、每游戏归一化规则及总墙钟预算。输出 tokens 是资源结果；不要一边改缓存一边强行固定 tokens 抵消收益。

## 6. 手动实验表

| ID | 核心变量 | 数据 | 预算估计 | 主要目的 |
|---|---|---|---|---|
| E0a | 原版，demo 1 pass | 25 游戏 | 约 2.2–2.5h | 建立我们的真实基线 |
| E0b | 原版独立运行 | 25 游戏 | 同 E0a | 估计运行波动 |
| E1a | 目标候选+反证事件 | 全集，诊断游戏单列 | 同 E0a | 增加首次未解关覆盖 |
| E1b | 同一修改独立运行 | 25 游戏 | 同 E0a | 看收益是否重复出现 |
| E2 | 裁剪后证据检索或调度之一 | 依 E1 失败选择 | 同 E0a | 只再改变一个机制 |
| K1 | 选定候选正式提交 | 隐藏 110 | Notebook≤9h | 验证 public LB 迁移 |

资源依据：MCP 本轮返回 GPU 总配额 30h、已用约 2.35h、未预留，表面剩余约 27.65h，刷新为北京时间 10/17 08:00。它不是专用 RTX 随时可用保证，也可能随账户其他任务变化。执行前重查实际 quota；不据此启动收费外部算力。优先完成 E0/E1，不把全部配额耗在很多 seed 或量化组合上。

## 7. 观察与判断

每个游戏/独立运行至少保存：

```text
run_id, source_hash, notebook_version, model_versions, wheel_versions
game_id, game_version, seed, pass_id, scheduling_pool_id
levels_completed, total_levels, completion_weight_ceiling
official_score, action_counts_by_level, resets, game_overs
wall_seconds, generated_tokens, prefill_tokens, cached_tokens
stop_reason, trace_paths, change_summary
```

手动标签：目标错误、控制错误、规则遗漏、观察/动画遗漏、记忆丢失、规划失误、计算不足。目标正误由回放与后续反馈人工判断；不要让模型自报成功代替真实过关。

成功证据须包括：新增过关在多个游戏/独立运行出现，且没有用大量额外时间换来；原来稳定成功的游戏没有明显回退。若只增加内部模型拟合率、漂亮摘要或 tokens/s，不能据此宣称获益。

如果 E1 只改善诊断游戏，先归为定向开发收益；如果新机制引入更多无效探测，撤回它。保留失败轨迹，以决定下一轮研究对象。

## 8. 本轮结束时写什么

新建 `docs/progress/003-next-experiment.md`，按次序记录：

1. 实际修改的代码、版本、文件/产物路径。
2. 已运行和未运行的实验；排队/失败/超时单独写。
3. 每次运行完整结果与代表性轨迹，public demo 和 Kaggle LB 分开。
4. 当前支持/反驳了哪个假设，以及下一轮只改什么。
5. 不写未经实际运行支持的“提升 X 分”“可以拿金牌”。

终局安排建议：10/10–10/13 建立 E0；10/14–10/21 主攻机制假设与证据；10/22–10/28 完整预算验证和隐藏反馈；10/29–11/2 UTC 留给稳定候选和最终两份选择。日期是研究排期，不是已创建自动任务。
