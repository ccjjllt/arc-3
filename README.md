# ARC Prize 2026 · ARC-AGI-3 研究项目

目标：争取竞赛奖牌，优先冲击金牌与终局奖金。初始赛情快照：**2026-10-10**；最新项目进展：**2026-10-13，Asia/Shanghai**。

**009 v2正式评测已COMPLETE：31.16分，10/13公开榜快照第247名/4221队。** 当前金牌附近第18名36.98、前五门槛42.66；最终看私榜和有效队数。submission 57101330，原生Notebook和冻结源码未变。首次提交链路已打通，见[009进展](docs/progress/009-baseline-submission.md)。

**010 v1已完成：公开同池26.0501→29.9365（+3.8864），关卡34→37/91，全通2→1。** 4局实际使用旧动画，28次非latest命中；最大涨分m0r0没有查询，新API独立收益和稳定性尚未确认。保留候选，不晋升正式版本。实测会话2.1266h，GPU预算内90.60%/93.09%；010完成时账户余额约5.40h（历史快照），10/17 08:00北京刷新。见[010结果](research/010-results-analysis.md)、[采用分析](research/010-intervention-analysis.md)、[010进展与下一步](docs/progress/010-retrievable-animation.md)。

**011 v1倒序确认已COMPLETE：baseline 33.9794→候选32.1157（−1.8637），关卡42→41/91，全通2→2。** 24局分数独立复算一致，两臂各3482秒，源码/预算/缓存/正常退出有效，无截止后动作或客户端新模型请求。010总体正向收益未复现，冻结候选不晋升，暂不全25扩跑或正式提交。实际2.10445h，GPU已停止；共享余额约3.29h，10/17 08:00北京刷新。见[011进展](docs/progress/011-animation-confirmation.md)、[综合结果](research/011-results-analysis.md)。随后转入计算值直接跨snippet交接，已有两种游戏的误写证据；实现进展见下方012，尚无提分证据。设计见[下一候选报告](research/011-evidence-reuse-next.md)。

**012 v1已COMPLETE，筛选未通过：baseline45.0764→current_data27.7582（−17.3182），关卡51→38/97，全通3→1。** 26局独立复算一致，无截止后动作；候选2次put/1次stored、0次get，模型没有形成数据复用链，当前版本不晋升。实际2.26747h、GPU已停；共享余额0h，10/17 08:00北京刷新。后续先验证模型实际采用，再进入完整得分A/B。见[012进展](docs/progress/012-current-data.md)、[综合结果](research/012-results-analysis.md)。

**008 CPU原型已完成：69份区域表示与保存帧核对一致，但尚未在线接入或验证提分。** 正确裁剪重现pink匹配1/4→4/4、yellow显式D4分类9→7；截断诊断漏掉2个完全遗漏的断开组件，长面板分槽仍未解决。见[008进展](docs/progress/008-observation-representation.md)。

当前决策：继续以 **dfranzen Milestone 2 v3 / Duck-TAAF / Qwen3.8-Flash-Next** 为baseline。003目标marker未形成有效反证反馈；006历史暂态真实交付，但整体没有收益，两个候选均不晋升。

**006已完成：baseline 28.3856分/36关/3全通，transient_history 21.9216分/31关/1全通。** 补丁101次附加246条记录，抽检证实进入模型并有引用，但首关病例未在本轮触发，零附加游戏也出现较大正负变化。不能将单次分差全归因提示。005全25 baseline仍为49.8997分/106关/9全通，和006诊断12游戏不可直接比。

006和007均未显示净提分。**007 v2已完成：baseline 46.3578分/51关/4全通，program_state 40.3235分/50关/2全通，均分−6.0343，不晋升。** 真实轨迹确认两次保住并复用旧函数，但最大回退发生在零直接触发的tr87/sc25，不能把全部分差归因补丁。会话2.1702h，求解GPU约92.12%/94.94%；007完成时账户余额11.6736h（历史快照）。007之后转入tr87的图案裁剪/编码研究；008 CPU结果与009正式提交状态见上方最新进展。详见[007进展](docs/progress/007-program-state.md)与[结果分析](research/007-results-analysis.md)。本项目最新正式public LB为31.16，详见009；没有私榜成绩。

## 研究入口

| 文档 | 内容 |
|---|---|
| [001 计划](docs/plan/001-baseline.md) / [001 进展](docs/progress/001-baseline.md) | 赛制、数据、评分版本、基线选择与实际手动观察 |
| [002 计划](docs/plan/002-strategy-improvement.md) / [002 进展](docs/progress/002-strategy-improvement.md) | 公开源码、原始轨迹与前沿论文形成的研究方向 |
| [003 计划](docs/plan/003-next-experiment.md) / [003 进展](docs/progress/003-next-experiment.md) | 已完成16游戏A/B：49.25 vs 46.88，实际2.743h |
| [004 计划](docs/plan/004-observation-evidence.md) / [004 进展](docs/progress/004-observation-evidence.md) | CPU归因及原始轨迹复核；暂缓观察候选，未消耗GPU |
| [005 计划](docs/plan/005-full-baseline.md) / [005 进展](docs/progress/005-full-baseline.md) | 已完成：49.8997分/106关/9全通，实际2.1927h |
| [006 计划](docs/plan/006-transient-history.md) / [006 进展](docs/progress/006-transient-history.md) | 已完成：28.3856 vs 21.9216，候选不晋升 |
| [007 计划](docs/plan/007-program-state.md) / [007 进展](docs/progress/007-program-state.md) | v2完成；真实保留/复用已验证，但均分−6.0343，不晋升；进入已有帧的CPU表示研究 |
| [008 计划](docs/plan/008-observation-representation.md) / [008 进展](docs/progress/008-observation-representation.md) | CPU原型及保存帧核验已完成；未在线接入、无提分证据 |
| [009 计划](docs/plan/009-baseline-submission.md) / [009 进展](docs/progress/009-baseline-submission.md) | 正式57101330 COMPLETE，public LB 31.16，公开榜快照247名 |
| [010 计划](docs/plan/010-retrievable-animation.md) / [010 进展](docs/progress/010-retrievable-animation.md) | v1完成：26.0501→29.9365，34→37关、全通2→1；真实采用已核实，尚不晋升 |
| [011 计划](docs/plan/011-animation-confirmation.md) / [011 进展](docs/progress/011-animation-confirmation.md) | v1完成：33.9794→32.1157、42→41关；整体增益未复现，暂不晋升 |
| [012 计划](docs/plan/012-current-data.md) / [012 进展](docs/progress/012-current-data.md) | v1完成：45.0764→27.7582、51→38关；0次get、无复用链，不晋升 |
| [数据研究](research/data-findings.md) | 25 游戏 / 183 关、SDK、真实动作接口与手动实验 |
| [Notebook 研究](research/notebook-findings.md) | 版本、得分证据、源码差异、依赖及原始运行记录 |
| [前沿研究](research/frontier-findings.md) | 一手论文/官方报告、可迁移机制、协议与资源限制 |

```text
docs/
├── plan/
│   ├── 001-baseline.md
│   ├── 002-strategy-improvement.md
│   ├── 003-next-experiment.md
│   ├── 004-observation-evidence.md
│   ├── 005-full-baseline.md
│   ├── 006-transient-history.md
│   └── 007-program-state.md
└── progress/
    ├── 001-baseline.md
    ├── 002-strategy-improvement.md
    ├── 003-next-experiment.md
    ├── 004-observation-evidence.md
    ├── 005-full-baseline.md
    ├── 006-transient-history.md
    └── 007-program-state.md
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
- 10/13 榜首67.49、第5名42.66、第18名36.98；4221队下金牌约前18。本队247名/31.16，最终以有效队数、私榜与Kaggle奖牌分配为准。
- 两次里程碑奖金截止已过；终局前五奖金分别 $40k/$15k/$10k/$5k/$5k。奖金规则及模型许可未决事项见 001。
- 已定位评分版本冲突：Kaggle data 文字落后于随比赛提供的 SDK；研究以实际 scorecard 和版本记录为准。

## Kaggle MCP：查询信息

前期已成功调用 `mcp__kaggle__*`。10/11 MCP曾传输失败并改用已配置CLI；10/13 MCP已恢复，可读取当前比赛、榜单、提交和Notebook信息。工具输入通常嵌套在 `request` 中。没有在 README 中保存凭证。

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

### 正式提交（通用命令；009已实际执行）

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

已完成的私有Notebook：[ARC3 003 Goal Evidence AB](https://www.kaggle.com/code/ccjjllt/arc3-003-goal-evidence-ab)。以下命令记录复现方法，不表示应立即原样重跑。本地已补诊断/token统计并关闭研究warmup RESET，这些修改从005开始使用；003实际源码已归档于`experiments/003-source/`，原Notebook不变。

```bash
# 003 已归档；以下记录历史运行命令，不重新构建或原样重跑。
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


## 已完成005实验：全25游戏，实际2.1927h

已实际推送私有 [ARC3 005 Full Baseline v1](https://www.kaggle.com/code/ccjjllt/arc3-005-full-baseline)。以下是历史构建/启动记录，不表示需要原样重跑。构建器现在要求显式配置，输出目录默认 notebooks/<配置id>；复用旧配置时应另设 --output-dir，避免覆盖研究原件。

```bash
kaggle quota
python3 scripts/build_experiment.py --config experiments/005-full-baseline.json
kaggle kernels push -p notebooks/005-full-baseline -t 9000 --accelerator NvidiaRtxPro6000
kaggle kernels status ccjjllt/arc3-005-full-baseline
kaggle kernels logs -f ccjjllt/arc3-005-full-baseline
```

结果已取回，以下保留下载/复算命令：

```bash
kaggle kernels output ccjjllt/arc3-005-full-baseline \
  -p runs/005-full-baseline \
  --file-pattern '(benchmark.json|arm-metadata.json|experiment-manifest.json|gpu-utilization.jsonl|run.log|serve.log|summary.json|summary.md)$'
python3 scripts/summarize_experiment.py \
  baseline=runs/005-full-baseline/baseline/benchmark.json \
  --source-kind local-experiment --output-dir experiments/005-analysis
```

单组解题预算7254秒，保留10路活跃和一次模型加载；每10秒GPU采样覆盖启动、解题、收尾。计划与进展中保留“代码完成”和“效果待测”的区别。全25分数不能直接与003的16游戏均分比较；分析时单列原16与新增9，不把调度池变化当作策略提升。


005结果复算与研究入口：

```bash
python3 scripts/analyze_005_results.py --output-dir experiments/005-analysis
```

[分组与逐游戏结果](research/005-results-analysis.md)、[GPU效率](research/005-efficiency-analysis.md)、[首关失败机制](research/005-stagnation-traces.md)、[暂态CPU复现](research/005-animation-replay.md)。005嵌入源码按运行哈希保存于 experiments/005-source/；后续本地代码变化不能当成已运行的005源码。


## 已完成006：非末动作暂态保留A/B

已推送 [ARC3 006 Transient History v1](https://www.kaggle.com/code/ccjjllt/arc3-006-transient-history)。以下记录历史构建/启动命令，不表示需要原样重跑：

```bash
python3 scripts/build_experiment.py --config experiments/006-transient-history.json
kaggle kernels push -p notebooks/006-transient-history -t 9000 --accelerator NvidiaRtxPro6000
kaggle kernels status ccjjllt/arc3-006-transient-history
kaggle kernels logs -f ccjjllt/arc3-006-transient-history
```

结果已下载，以下保留复算方法和干预诊断文件：

```bash
kaggle kernels output ccjjllt/arc3-006-transient-history \
  -p runs/006-transient-history \
  --file-pattern '(benchmark.json|arm-metadata.json|transient-history.json|experiment-manifest.json|gpu-utilization.jsonl|run.log|serve.log|summary.json|summary.md)$'
python3 scripts/summarize_experiment.py runs/006-transient-history \
  --reference baseline --source-kind local-experiment \
  --output-dir experiments/006-analysis
```

状态、真实代码完成与结果边界见 [006进展](docs/progress/006-transient-history.md)。真实结果为整体回退；已区分附加、进入模型、实际采用与得分。006嵌入源码归档在experiments/006-source/。


006完整A/B复算：

```bash
python3 scripts/analyze_006_results.py --output-dir experiments/006-analysis
```

[006数值研究](research/006-results-analysis.md)、[干预轨迹](research/006-intervention-analysis.md)、[零触发对照](research/006-zero-trigger-traces.md)、[GPU效率](research/006-efficiency-analysis.md)。


## 007 已完成：函数快照缺失时保留旧代码

[ARC3 007 Program State v2](https://www.kaggle.com/code/ccjjllt/arc3-007-program-state)两组完整运行，各12游戏/3482秒。结果46.3578→40.3235，关卡51→50，全通4→2，不晋升。实际触发3次，其中2次保留非空函数集合并被成功复用；这一行为证据不等于净提分。

v1在模型加载前因固定输入路径不可见失败。v2按实际挂载定位输入，2.868秒完成定位：dataset/competition是扁平路径，模型为嵌套路径。CPU检查与GPU会话布局不同，排查经过与原件已归档。v2实际源码在experiments/007-source/，运行输出在runs/007-program-state/。

以下为已完成运行的获取与手动分析命令，不需要重复push：

```bash
kaggle kernels status ccjjllt/arc3-007-program-state
kaggle kernels output ccjjllt/arc3-007-program-state \
  -p runs/007-program-state --file-pattern '.*\.(json|jsonl|log|md)$'
python3 scripts/summarize_experiment.py runs/007-program-state \
  --source-kind local-experiment --reference baseline \
  --output-dir experiments/007-analysis/summary
python3 scripts/analyze_007_results.py
```

[007结果](research/007-results-analysis.md)、[真实触发与复用](research/007-intervention-analysis.md)、[GPU效率](research/007-efficiency-analysis.md)、[下一研究方向](research/007-next-direction.md)。007结束后的GPU账户快照余额11.6736h，预留0；该会话2.1702h。009保存后的快照余额8.63h，见009进展。配额共享，全账户差额不能全部归为本次实验消耗。下一步优先CPU分析已有帧的表示错误，未创建测试文件或新GPU作业。

008的CPU研究已完成，见[008进展](docs/progress/008-observation-representation.md)；独立原型尚未在线接入。009正式提交与008分开，见[009进展](docs/progress/009-baseline-submission.md)。既有007结论及运行原件保持不变。
