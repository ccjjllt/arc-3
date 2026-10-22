# ARC Prize 2026 · ARC-AGI-3 研究项目

以 dfranzen Milestone 2 v3 / Duck-TAAF / Qwen3.8-Flash-Next 为基线，研究交互游戏中的状态表示、经验复用、程序修复与受检执行。核心实现位于 `src/arc3_research/`，实验沿用三位编号。

## 当前进展

以下来自仓库截至 **2026-10-22** 的已保存记录：

| 项目 | 状态与结论 | 入口 |
|---|---|---|
| 正式最佳 · 009 v2 | submission 57101330，public **31.16** | [009 实验索引](docs/experiments/009.md) |
| 最近正式结果 · 032 | public 30.20，未刷新最佳；保留成功经验复用证据 | [032 结果](research/notes/032/032-results-analysis.md) |
| 当前研究 · 034 v5 | 已 COMPLETE；2次任务像素预测命中、2次失配，仍混淆对象；两题均分34.9206→20.1671，不扩大或正式提交 | [034 v5 结果](research/notes/034/034-v5-results-analysis.md) · [完成记录](experiments/034-v5-launch.json) |
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
