# ARC Prize 2026 · ARC-AGI-3 研究项目

以 dfranzen Milestone 2 v3 / Duck-TAAF / Qwen3.8-Flash-Next 为基线，研究交互游戏中的状态表示、经验复用、程序修复与受检执行。核心实现位于 `src/arc3_research/`，实验沿用三位编号。

## 当前进展

以下来自仓库截至 **2026-10-30** 的已保存记录：

| 项目 | 状态与结论 | 入口 |
|---|---|---|
| 正式最佳 · 009 v2 | submission 57101330，public **31.16** | [009 实验索引](docs/experiments/009.md) |
| 新候选已正式提交 · 043 v1 | submission **57789256**，**PENDING**；H3真实触发11次，两份请求/后续动作核验通过；离线49.30／49关，今日剩0次 | [043进展](docs/progress/043-inference-audit.md) · [正式记录](experiments/043-formal-submission.json) |
| 最新正式结果 · 042 v1 | submission **57767406**，COMPLETE／**26.09**，较最佳低5.07；本次非零，未证实启动修复净收益，停止原样重提 | [042进展](docs/progress/042-startup-ready.md) · [正式记录](experiments/042-formal-submission.json) |
| 原样正式零分 · 041 v1 | submission **57718364**，COMPLETE／**0.00**，3411B；提交后约33分29秒内已结束，优先排查正式启动/scorecard早停，原因未证实 | [041进展](docs/progress/041-exact-public-v83.md) · [诊断证据](experiments/041-zero-diagnosis.json) |
| 最近正式结果 · 040 v1 | submission **57685414**，public **26.54**，较009低4.62；停止本版重提 | [040进展](docs/progress/040-dprime-fresh-first.md) · [正式记录](experiments/040-formal-submission.json) |
| 最新正式结果 · 038 | submission 57650170，public **27.73**，较009低3.43；核心正式代码与009相同，结束原样重提 | [结果与下一步](research/notes/038/038-formal-results-analysis.md) · [038进展](docs/progress/038-highscore-baseline.md) |
| 已准备备选 · 039 | step兼容修复本地冻结，收益证据较小，降为低优先级；优先核验D-prime准确得分版本及调度差异 | [039](docs/progress/039-history-step.md) |
| 历史正式结果 · 037 | submission 57615378，public **26.71**，较009低4.45；保留009，停止原样重提 | [037进展与结果](docs/progress/037-highscore-pixels.md) · [正式原件](experiments/037-formal-result-snapshot.json) |
| 历史正式结果 · 032 | public 30.20，未刷新最佳；保留成功经验复用证据 | [032 结果](research/notes/032/032-results-analysis.md) |
| 最新结果 · 036 | 完整25题39.4358→40.6409（+1.2051）、97→100关；去最大涨题后−2.3161，不直接晋级正式候选 | [036结果](research/notes/036/036-results-analysis.md) · [进展](docs/progress/036-main-reasoning-medium.md) |
| 已完成 · 035 | low真实生效，但A/B/C均分18.2540、新增关及程序动作均0；执行停损，结束独立辅助分支 | [035结果](research/notes/035/035-results-analysis.md) · [进展](docs/progress/035-auxiliary-reasoning.md) |
| 已完成 · 034 v9 | 程序动作仍0，A/B均分20.2479→18.2540，差−1.9939；执行停损，停止合同调参，不扩池或正式提交 | [v9结果](research/notes/034/034-v9-results-analysis.md) |
| 已完成 · 034 v8 | 四份源码全交付，但三份弃权／一份无效ready，程序动作0；两题均分差0，不扩池或正式提交 | [v8结果](research/notes/034/034-v8-results-analysis.md) |
| 已完成 · 034 v7 | 零动作反馈真实送达并缩短代码，但全部被提取合同拒收，程序动作0；同期两题均分−5.5556，不扩池 | [034 v7 结果](research/notes/034/034-v7-results-analysis.md) |
| 已完成 · 034 v6 | 两题均分+5.5556，但辅助程序均在动作前失败，新增关来自普通主循环，不扩池 | [034 v6 结果](research/notes/034/034-v6-results-analysis.md) |
| 已完成 · 034 v5 | 2次局部任务像素预测命中，仍混淆对象；两题均分34.9206→20.1671，不扩大或正式提交 | [034 v5 结果](research/notes/034/034-v5-results-analysis.md) |
| 已完成 · 034 v4 | 程序已交付，但两次受检动作均 mismatch；不扩大或正式提交该版 | [034 v4 结果](research/notes/034/034-v4-results-analysis.md) |

实验状态、公开开发池结果与隐藏正式分数分别记录；历史文档中的“下一步”“运行中”和余额应按其记录日期理解。

## 从这里开始

- [全部实验索引](docs/experiments/README.md)：按编号查看计划、进展、研究笔记、配置、运行记录和 Notebook。
- [脚本目录](scripts/README.md)：构建、分析、检查、输入准备和回放入口。
- [研究资料](research/README.md)：分析笔记、第三方 Notebook、官方快照与本地数据。
- [目录约定与整理记录](docs/project-layout.md)：文件放置规则、历史路径迁移和清理范围。
- [历史操作手册](docs/archive/project-history-2026-10-22.md)：完整旧首页、早期结论、Kaggle 查询与运行命令。

## 目录

```text
src/arc3_research/      核心实现与运行时组件
scripts/
  analysis/            结果、时序、采用证据分析
  checks/              手动 CPU 检查与预检
  build/               专用 Notebook / 输入包构建
  prepare/             实验输入准备
  replay/              已保存前缀的本地回放
  research/            专项研究工具
  tools/               通用日志与目录维护工具
  demos/               行为机制演示
docs/
  experiments/         按实验编号生成的统一导航
  plan/                实验设计
  progress/            实际执行与结论
  handoff/             研究交接
  archive/             历史操作手册
research/
  notes/NNN/           按编号归档的研究笔记
  overview/            数据、Notebook 与前沿研究总览
  snapshots/           官方/API/讨论的时间快照
  notebooks/           第三方源码与元数据
  data/                本地数据（Git 忽略）
  runtime-bundle/      基线运行时（Git 忽略）
experiments/           实验配置、冻结源码与审计原件
notebooks/             已构建或上传的 Notebook
runs/                  本地原始运行输出（Git 忽略）
```

`experiments/`、`notebooks/` 和 `runs/` 保留原路径，便于冻结源码哈希、输入打包和历史分析复核；按编号浏览请使用实验索引。

## 常用本地入口

在项目根目录执行；现有 SDK 使用 Python 3.10+ 语法，本机可用 `python3.12`：

```bash
# 查看通用构建器和最新分析器的参数
python3.12 -B scripts/build_experiment.py --help
python3.12 -B scripts/build_submission.py --help
python3.12 -B scripts/analysis/analyze_034_results.py --help

# 新增实验文件后刷新目录导航
python3.12 -B scripts/tools/project_index.py
```

通用构建器 `build_experiment.py`、`build_submission.py` 和 `summarize_experiment.py` 保留在 `scripts/` 根目录。其余工具使用上方分类路径；[完整脚本列表](scripts/README.md)包含所有入口。

沿用现有验证方式：执行针对性的 CPU 检查、阅读日志和回放，不新增测试套件或 CI。下载数据、环境缓存和原始运行输出不提交到 Git；凭证保存在仓库外。
