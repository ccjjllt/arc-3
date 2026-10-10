# ARC Prize 2026 · ARC-AGI-3 研究项目

目标：争取竞赛奖牌，优先冲击金牌与终局奖金。研究截止快照：**2026-10-10，Asia/Shanghai**。

当前决策：以 **dfranzen Milestone 2 v3 / Duck-TAAF / Qwen3.8-Flash-Next** 为强离线基线，主攻**目标与机制发现、突破首个未解关、后续关卡迁移**。003已完成：16游戏baseline **49.25分/72关**，goal_evidence **46.88分/68关**，反证提示实际触发0次，因此保留baseline、不晋升该改进版。程序实测2.743h，解题阶段GPU采样均值约91%/92%；10/11查询剩余配额约24.66h。详见[003进展](docs/progress/003-next-experiment.md)。这些是公开开发分，尚无本项目隐藏榜单成绩。

## 研究入口

| 文档 | 内容 |
|---|---|
| [001 计划](docs/plan/001-baseline.md) / [001 进展](docs/progress/001-baseline.md) | 赛制、数据、评分版本、基线选择与实际手动观察 |
| [002 计划](docs/plan/002-strategy-improvement.md) / [002 进展](docs/progress/002-strategy-improvement.md) | 公开源码、原始轨迹与前沿论文形成的研究方向 |
| [003 计划](docs/plan/003-next-experiment.md) / [003 进展](docs/progress/003-next-experiment.md) | 共享一次模型加载的16游戏A/B，预计2.8h，硬上限3h |
| [004 下一轮计划](docs/plan/004-observation-evidence.md) | 先用现有轨迹研究实际证据使用，再选择≤2.5h实验；尚未启动GPU |
| [数据研究](research/data-findings.md) | 25 游戏 / 183 关、SDK、真实动作接口与手动实验 |
| [Notebook 研究](research/notebook-findings.md) | 版本、得分证据、源码差异、依赖及原始运行记录 |
| [前沿研究](research/frontier-findings.md) | 一手论文/官方报告、可迁移机制、协议与资源限制 |

```text
docs/
├── plan/
│   ├── 001-baseline.md
│   ├── 002-strategy-improvement.md
│   ├── 003-next-experiment.md
│   └── 004-observation-evidence.md
└── progress/
    ├── 001-baseline.md
    ├── 002-strategy-improvement.md
    └── 003-next-experiment.md
research/
├── snapshots/          # Kaggle MCP 比赛/讨论快照
├── notebooks/          # 第三方公开代码、metadata、选取的原始输出
├── data/               # 实际数据包、解包文件、手动运行记录
├── data-inventory.json
└── *-findings.md
```

计划和进展使用相同编号与主题。专注研究，不新增测试文件或 CI；所有验证由人工执行命令/Notebook、阅读日志与回放完成。代码完成和效果结论分开记录。

## 已核验的比赛事实

- [比赛](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview)：交互游戏；25 个公开开发游戏、110 个隐藏评测游戏，隐藏集 55/55 对应 public/private LB。
- 截止：**北京时间 2026-11-03 07:59**；每天最多 1 次正式提交，最终可选 2 份。
- Notebook 最多 9h，评测断网。当前强基线使用 RTX PRO 6000。
- 10/10 榜首 62.96、第 5 名 40.97。4090 队规模条件下金牌名次估计约前 18，但最终以有效队数、最终私榜与 Kaggle 奖牌分配为准。
- 两次里程碑奖金截止已过；终局前五奖金分别 $40k/$15k/$10k/$5k/$5k。奖金规则及模型许可未决事项见 001。
- 已定位评分版本冲突：Kaggle data 文字落后于随比赛提供的 SDK；研究以实际 scorecard 和版本记录为准。

## Kaggle MCP：查询信息

本轮已成功调用 `mcp__kaggle__*`。工具输入通常嵌套在 `request` 中。没有在 README 中保存凭证。

```javascript
await tools.mcp__kaggle__get_competition({
  request: { competitionName: "arc-prize-2026-arc-agi-3" }
});
await tools.mcp__kaggle__list_competition_pages({
  request: { competitionName: "arc-prize-2026-arc-agi-3" }
});
await tools.mcp__kaggle__get_competition_leaderboard({
  request: { competitionName: "arc-prize-2026-arc-agi-3" }
});
await tools.mcp__kaggle__search_notebooks({
  request: {
    competition: "arc-prize-2026-arc-agi-3",
    sortBy: "ScoreDescending",
    pageSize: 20
  }
});
await tools.mcp__kaggle__get_notebook_info({
  request: {
    userName: "dfranzen",
    kernelSlug: "arc-agi-3-milestone-2-solution"
  }
});
await tools.mcp__kaggle__list_competition_topics({
  request: {
    competitionName: "arc-prize-2026-arc-agi-3",
    sortBy: "Recent"
  }
});
await tools.mcp__kaggle__get_forum_topic({
  request: { forumTopicId: 744792, includeComments: true }
});
await tools.mcp__kaggle__get_accelerator_quota({ request: {} });
```

返回值常在 `content[].text` 中保存 JSON，先解析后挑需要字段。榜单/文件/话题分页必须处理 `next_page_token`；本地 `get_competition_leaderboard.json` 只保存第一页 20 队，不是完整榜单。

其它已发现工具：`list_competition_data_files`、`get_competition_data_files_summary`、`list_models`、`get_model`、`download_notebook_output`、`search_competition_submissions`。使用前读取当前 schema；具体 metadata 与 source 查询范围见研究笔记。搜索按 score 排序不等于工具返回了可追溯的当前版本分数；votes、作者标题、公开游戏分数和 LB 分数必须分开。

## Kaggle CLI：下载与 Notebook 运行

本机已实测 `kaggle --version` 为 **2.2.4**。以下命令在项目根目录执行。

### 已实际验证的只读命令

```bash
kaggle --version
kaggle competitions download arc-prize-2026-arc-agi-3 -p research/data
kaggle kernels pull dfranzen/arc-agi-3-milestone-2-solution -p research/notebooks/cli-baseline -m
```

CLI 的 `owner/slug/3` pull 本轮返回 403；不带版本成功，已将内容逐 cell 与 MCP v3 比对一致。固定的是已保存文件和 hash，不假设以后 latest 仍是同一版：

```text
MCP current_version_number: 3
CLI ipynb SHA256:
88a379f17c3a4ba8c98715fc23155346ccd6eb289bdafebadfc61a3178f9d9bd
```

原版 metadata 是下载参考，**不是我们自己的 push 身份**。MCP 的 `dataset_data_sources` 等字段也不能直接作为 CLI metadata 使用。

### 准备我们自己的私有运行目录（待执行示例）

将 `YOUR_KAGGLE_USERNAME` 换成自己的 Kaggle 用户名。这些步骤只复制到新目录并修改 metadata，保留研究原件：

```bash
mkdir -p notebooks/001-baseline
cp research/notebooks/cli-baseline/arc-agi-3-milestone-2-solution.ipynb notebooks/001-baseline/
cp research/notebooks/cli-baseline/kernel-metadata.json notebooks/001-baseline/
export ARC3_OWNER='YOUR_KAGGLE_USERNAME'
python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path("notebooks/001-baseline/kernel-metadata.json")
meta = json.loads(path.read_text())
meta.pop("id_no", None)
meta["id"] = os.environ["ARC3_OWNER"] + "/arc3-001-baseline"
meta["title"] = "ARC3 001 Baseline"
meta["is_private"] = True
meta["enable_gpu"] = True
meta["enable_internet"] = False
meta["machine_shape"] = "NvidiaRtxPro6000"
meta["docker_image_pinning_type"] = "original"
path.write_text(json.dumps(meta, indent=2) + "\n")
PY
```

保留原版两份 dataset、两份 model、competition_sources、Docker 镜像；新建运行需在日志中确认镜像/依赖确实按预期解析。当前模型来源：

```text
dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1
dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1
```

CLI 2.2.4 源码核对：`id_no` 会被提交为旧 Notebook ID；新 fork 必须移除。CLI 未显式设置 `enable_internet` 的实现默认值与部分文档不同，所以始终显式设为 false。`docker_image_pinning_type` 当前支持 original/latest，不使用猜测值。

### Push、看状态、取日志/输出

以下是未修改原版入口的通用示例。003已实际push私有研究Notebook（3h自有launcher），尚未正式提交比赛：

```bash
kaggle kernels push -p notebooks/001-baseline -t 32400 --accelerator NvidiaRtxPro6000
kaggle kernels status "$ARC3_OWNER/arc3-001-baseline"
kaggle kernels logs "$ARC3_OWNER/arc3-001-baseline"
kaggle kernels output "$ARC3_OWNER/arc3-001-baseline" -p runs/001-baseline
```

`push` 创建并运行 Notebook，消耗运行资源；它与提交比赛计分是两步。默认 v3 的开发模式跑 25 游戏 ×4 遍；第一次开发运行建议按 [003](docs/plan/003-next-experiment.md) 调整为单遍并保持时间缩放。正式比赛模式由平台 `KAGGLE_IS_COMPETITION_RERUN` 设置，勿为本地模拟手工伪造。

遇到输出很多时可用 `--file-pattern` 只取 benchmark、scorecard、log 和指定回放。保留 push 返回的 URL、版本号、source hash、输入版本及实际 GPU 信息。

### 正式提交（待有候选结果时执行）

用实际运行版本替换下面的 1：

```bash
kaggle competitions submit arc-prize-2026-arc-agi-3 \
  -k "$ARC3_OWNER/arc3-001-baseline" \
  -v 1 \
  -f submission.parquet \
  -m "001 baseline; record exact source and model versions"
```

正式 rerun 通过 ARC gateway 自动生成 `submission.parquet`，不要手工伪造分数表，也不要把本地公开开发集分数当正式提交分数。提交每天最多 1 次；同一轮完整结果写入对应 progress。输出文件名仍应在实际 baseline/gateway 路径中确认。

## 已完成的手动工作与效果边界

- 下载并检查比赛数据与 wheel，手动运行 25 游戏 ×80 动作，得到有效本地 scorecard：**2000 动作，0 关完成，AE=0.0**。这是随机策略接口观察。
- 阅读公开强实现、获取作者原始 benchmark/部分 requests logs，并独立重算 100 条轨迹；这是第三方记录分析，不是我们的 GPU 重跑。
- 已完成003的真实GPU对照：baseline49.25，目标证据版46.88，后者未晋升；没有证明新的反证机制有效，因为有效提示触发0次。详见003结果与复盘。

参考：[Kaggle CLI 官方 metadata](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md)、[ARC 文档](https://docs.arcprize.org/)、[比赛 Code](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/code)、[比赛 Models](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/models)。

## 已完成003实验：共享加载，最多3h

已完成的私有Notebook：[ARC3 003 Goal Evidence AB](https://www.kaggle.com/code/ccjjllt/arc3-003-goal-evidence-ab)。以下命令记录复现方法，不表示应立即原样重跑。本地已补诊断/token统计并关闭研究warmup RESET，均未重新上GPU；003实际源码已归档于`experiments/003-source/`，原Notebook不变。

```bash
python3 scripts/build_experiment.py
kaggle kernels push -p notebooks/003-goal-evidence-ab -t 10800 --accelerator NvidiaRtxPro6000
kaggle kernels status ccjjllt/arc3-003-goal-evidence-ab
kaggle kernels logs -f ccjjllt/arc3-003-goal-evidence-ab
kaggle kernels output ccjjllt/arc3-003-goal-evidence-ab \
  -p runs/003-goal-evidence-ab \
  --file-pattern '(benchmark.json|arm-metadata.json|goal-evidence.json|experiment-manifest.json|gpu-utilization.jsonl|run.log|serve.log|summary.json|summary.md)$'
python3 scripts/summarize_experiment.py runs/003-goal-evidence-ab \
  --reference baseline --source-kind local-experiment --output-dir runs/003-analysis
```

源数据、模型权重和Pennyroyal运行时沿用基线；10路活跃请求、复用GPU权重、独立CPU会话及等量预算运行成功。[得分分析](research/003-results-analysis.md)、[GPU效率](research/003-efficiency-analysis.md)、[零触发复盘](research/003-intervention-postmortem.md)已完成；原件在`runs/003-goal-evidence-ab/`，校正后的派生汇总在`experiments/003-analysis/`。
