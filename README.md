# ARC Prize 2026 · ARC-AGI-3 研究项目

**034 v3正在运行：** 已实现紧凑事实包、辅助thinking关闭与工具交付、动作相关预测、累计3步短合同及退出；14个原生sandbox场景通过，A/B切点恢复hash一致。私有两题诊断已确认v3 RUNNING且远端源码精确一致，目前冷启动中，尚无新增得分结论。[实际进展](docs/progress/034-executable-plan.md) · [启动记录](experiments/034-v3-launch.json)。

**下一轮研究交接（10月22日16:27官方信息核验）：** [程序交付与完整得分验证方案](docs/handoff/034-next-round-research-plan.md)。保留009 v2／31.16，先验证紧凑辅助分支能否交付并执行当前短计划，再做完整25题同期对照；补充必要历史状态、预测器适用范围、误停恢复与9小时总截止。方案结合最新Notebook源码和前沿研究，尚未实施或启动新GPU实验。[本轮官方与源码快照](research/snapshots/2026-10-22-next-round/)

**034 v2已COMPLETE：** su15相同L5切点续跑，A新增0关、B新增1关；ft09均新增0关。但两次额外分支都仅返回推理、没有工具调用，验收程序与受检动作均为0；su15通关发生在普通主循环，不能归因于预期机制。会话58.30分钟、模型启动42.85分钟，服务已关闭。停止该版原样扩跑，先修代码交付；正式最佳仍009／31.16。[结果分析](research/034-v2-results-analysis.md) · [机制判断](experiments/034-v2-analysis/mechanism-assessment.json) · [完成记录](experiments/034-v2-launch.json)。

**10月22日研究交接：** [034 当前程序修复与执行核验](docs/handoff/034-executable-program-repair.md)。交接时重新读取官方规则、榜单与009/030/032正式成绩，并发现Heliosli公开Notebook已更新至v8：可参考其真实动作检查接线，但尚无目标模型提分证据。交接补齐自然合同建立、目标/计划确定消费、三态检查及9小时总预算边界；当时034/035为拟议实验，当前034实施状态见上方。[公开源码审计](research/snapshots/2026-10-22-candidates/source-audit.json) · [官方快照](research/snapshots/2026-10-22-handoff/read-manifest.json)。

**032正式结果已COMPLETE：30.20，较009的31.16低0.96，未刷新公开榜最佳。** submission57481712的10月22日08:43北京时间API原件已保存；009 v2／57101330继续保留。032公开短跑+25.655、全25题跨会话比较+11.140未迁移为此次正式提分；候选49.22仍低于历史005基线49.90。实际经验复用证据成立，但单轮公开均值和采用轨迹不足以证明稳定泛化收益。停止032 v1原样重提和扩大，保留其机制证据；后续优先研究当前任务程序由准确输入到目标计算、动力学与实际动作的纠错闭环。正式episodes为空、结果下载403，隐藏逐题与运行直接根因未能确认。[正式成绩原件](experiments/032-formal-result-snapshot.json) · [032研究结论](research/032-results-analysis.md) · [独立结果评估](experiments/032-memory-analysis/formal-result-assessment.json) · [全25题比较](experiments/032-memory-analysis/recovery-comparison.md) · [执行进展](docs/progress/032-033-memory-and-controller.md)。

031自然对照已COMPLETE：22.5092→23.2819（+0.7726），27→26关。r11l已有精确像素→搜索→执行→多过一关的完整正链；最大涨题ft09的收益尚不能归因于runs。冻结v2作为备选，不因032回退自动晋升或原样提交。[分析](experiments/031-natural-analysis/summary.md) · [独立深读](experiments/031-natural-analysis/decision-review.json)。

**正式最佳仍为009 v2 / submission 57101330 / public 31.16。** 030 submission 57447779已COMPLETE，public24.40，回退6.76；停止原样重提和扩大030。开发池单轮42.6134→47.1699未迁移为正式收益，同轮基线偏弱且增益集中；不能把采用或一次全池正收益等同于稳定提分。[回退分析](research/030-results-analysis.md)。隐藏逐题及运行日志不可得，直接根因尚不能确认。

10月21日11:58北京时间API历史快照：4566队，本队ccjjllt第393（teamId17139255），铜牌附近30.85、银牌附近32.22、金牌附近37.98；均为当时公开位置估算，最终看私榜及资格。10月21日20:29已使用当日一次正式提交；10月22日正式032为30.20，未超过009；余额另看最新账户查询，SDK通用配额口径存在冲突，不能当独立RTX余额。[榜单历史原件](research/snapshots/2026-10-21-handoff/) · [新提交接收原件](experiments/032-after-formal-submit.json)。截止北京时间11月3日07:59。

**历史结论：016已完成，015/016均未通过当轮预设标准。** 从020起主要按同预算官方分数与实际风险选择正式候选；关数、全通数和采用轨迹用于解释，不再套用“两游戏采用／去最大正向／所有指标同时不降”的通用否决条件。 016原ccjjllt会话因旧完成池误拒gave_up而中止；jiyujia修复轮完整完成。两者必须分开。

| 实验 | 已核实结果 | 当前判断 |
|---|---|---|
| 005全25 baseline | 49.8997，106/183关，9全通 | 公开研究参照；与009隐藏正式分数不同池 |
| 010旧动画检索 / 011倒序 | 初筛+3.8864，倒序−1.8637 | 整体增益未复现，不晋升 |
| 012显式数据缓存 | 45.0764→27.7582；0次get | 机制未形成复用链，不扩跑 |
| 014 tail | 47.1991→48.6390；110→108关，覆盖下降 | 未过门，不倒序 |
| 015原生值短筛 | 21.8289→33.2937；13→15关 | 新审计确认re86一次真复用，仍未达两游戏门，不进全池 |
| 016 pace全25 | 47.1340→47.4634；105→111关，全通8→7 | 去最大正向r11l后其余24局−1.5205，未过非单游戏门 |
| 018观察状态保真 | 67.0106→63.7827；22→22关，全通2→1 | 已COMPLETE；两游戏有具体纠错，但ar25仍转抄错误，不晋升/不扩跑 |
| 019 FP8 PLE | GPU v4已完成；10并发吞吐为BF16均值0.966倍，质量门未过 | 不进入游戏A/B，关闭本版 |
| 020 精确状态通道 | jiyujia v1 COMPLETE；41.2112→26.5081，44→36关，全通3→1 | 同预算明显回退，不提交原版 |
| 021 预测失配停批 | jiyujia v1 COMPLETE；36.9270→29.3560，41→38关，全通3→0 | 接口未被调用，不提交，不重复本前缀 |
| 027 tail确认 | 50.4293→44.4542；112→101关，全通8→7 | 014收益未复现，关闭该线 |
| 028 程序修复 | ft09真实代码执行且采用但关键像素仍错；tu93修复超时；三对均无新增关 | 关闭本版，不扩全池、不为导出故障重跑 |
| 030 关内持久Python | 开发池+4.5565，正式24.40／较009−6.76 | COMPLETE；保留009，停止扩大030；[回退分析](research/030-results-analysis.md) |
| 032 成功经验记忆 | 短跑+25.655、全池跨会话+11.140；正式30.20／较009−0.96 | COMPLETE；保留009，不原样重提/扩大v1；[研究结论](research/032-results-analysis.md) |
| 034 程序重算与受检执行 | v2两题相同前缀：su15新增0→1关，ft09均0；两个额外响应均无可执行代码、0受检动作 | COMPLETE；消费链未成立，不原样扩跑；先解决分支代码交付 |

[016完整分析](research/016-results-analysis.md)已复算50局并核对冻结源码、预算、缓存、排空和截止行为；会话内部4.2054h。015/016新审计覆盖18份请求、1281次去重Python调用：ft09外接框填色/转抄错误、tr87裁剪错位、ar25颜色与物理足迹边界均有纯CPU字面量证据。018已实际检验局部ASCII核对输入的短提示，局部纠错存在而整体回退；020改为复用008区域读取器直接交付程序输入；FP8作为支线，均不叠加018提示。[本地证据](research/017-local-evidence.md)、[018计划](docs/plan/018-observation-grounding.md)、[018进展](docs/progress/018-observation-grounding.md)。

**017深度研究完成：**刷新500队榜单、148文件清单及规则；审计19本公开Notebook；补读10/15 stop-and-report论文、OPINE-World v3消融及作者控制代码。现有底座已有自动续聊，选取016请求仅1次自然无工具stop，故不优先增加全局汇报；新验证API和整套Lexicon也缺足够采用证据。FP8 PLE有可核查权重/配置/loader路径，保留为独立吞吐与数值候选，不能把主机表减半当作释放显存或涨分。[Notebook审计](research/017-notebook-update.md)、[前沿研究](research/017-frontier-update.md)。

**GPU执行更新：**021 jiyujia v1已COMPLETE，两臂各1800秒、12游戏完整；会话70.11分钟，启动9.06分钟，GPU求解采样平均90.74%/95.51%、中位均98%。服务已关闭，[实际记录](experiments/021-launch.json)，[结果](research/021-results-analysis.md)。020 jiyujia v1同样COMPLETE，会话70.40分钟，启动9.55分钟，求解采样平均92.22%/90.81%、中位98.5%/98%，[记录](experiments/020-launch.json)。018会话内部43.13分钟。通用配额API增量不能当作本作业计费或剩余RTX额度。此段保留021等较早运行记录；最新正式提交见文首。

较早研究：003有效反证提示0次；006暂态交付后整体回退；007保留旧函数但净分回退；008有69份保存区域CPU核对，020已完成接入和一轮在线验证，整体回退。基线继续使用dfranzen Milestone 2 v3 / Duck-TAAF / Qwen3.8-Flash-Next。历史计划、结果和运行原件保留，不能把旧的“下一步/运行中/余额”当当前状态。

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
| [013 计划](docs/plan/013-research-next.md) / [013 进展](docs/progress/013-research-next.md) | 10/17赛情、12份Notebook、前沿与CPU审计；优先tail全25单因素，原生值采用筛选；未启动GPU |
| [014 计划](docs/plan/014-tail-allocation.md) / [014 进展](docs/progress/014-tail-allocation.md) | v1完成：47.1991→48.6390、110→108关；覆盖下降，未过门槛，不晋升/不倒序扩跑；转015 CPU集成 |
| [015 计划](docs/plan/015-native-adoption.md) / [015 进展](docs/progress/015-native-adoption.md) | 4游戏短筛已完成，涨分但仅一游戏确证复用，未过采用门 |
| [016 计划](docs/plan/016-pace-allocation.md) / [016 进展](docs/progress/016-pace-allocation.md) | jiyujia完整重跑已完成，+0.3293但非单游戏门失败，不晋升 |
| [017 计划](docs/plan/017-research-next.md) / [017 进展](docs/progress/017-research-next.md) | 最新赛情/数据、19本Notebook、前沿消融和1281调用审计；选择018 |
| [018 计划](docs/plan/018-observation-grounding.md) / [018 进展](docs/progress/018-observation-grounding.md) | 已完成四游戏短筛，均分−3.2279；具体纠错与新误编码并存，不晋升 |
| [019 计划](docs/plan/019-fp8-ple.md) / [019 进展](docs/progress/019-fp8-ple.md) | FP8 PLE独立系统候选，实际权重CPU预检与GPU微基准分开 |
| [021计划](docs/plan/021-checked-execution.md) / [021进展](docs/progress/021-checked-execution.md) / [021结果](research/021-results-analysis.md) | v1 同预算 −7.5710；停批接口未被调用，不提交 |
| [021实施交接](docs/handoff/021-implementation-handoff.md) / [020结果](research/020-results-analysis.md) | 020完整结果、实际采用、可复用代码与其余未完成接入 |
| [020原计划](docs/handoff/020-research-sprint.md) / [状态通道](research/020-state-channel.md) | 保留实验前优先级、正式提交节奏与真实sandbox消费证据 |
| [020执行与探索](research/020-behavior-mechanisms.md) / [社区验证](research/020-community-validation.md) | 独立行为机制、40家族代表、12开发/12预留/16冻结；未接入部分单独说明 |
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
- 10/20榜首68.91、第5名49.85、第19名37.98；4536队下估计金牌前19。本队ccjjllt第384名/31.16；最终以有效队数、私榜与奖牌分配为准。连续读取前500队，非全榜。
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
