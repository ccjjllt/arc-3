# 项目目录约定

本次整理日期：2026-10-22。项目按实验编号保留研究全过程；统一入口为[全部实验索引](experiments/README.md)。

## 文件放置

| 内容 | 位置 | 约定 |
|---|---|---|
| 可复用实现、运行时组件 | `src/arc3_research/` | 按功能命名 |
| 实验计划、实际进展、交接 | `docs/plan/`、`docs/progress/`、`docs/handoff/` | 沿用三位实验编号 |
| 研究分析与结论 | `research/notes/NNN/` | 保留原文件名；跨实验笔记按文件名前三个数字归组 |
| 数据、Notebook、前沿总览 | `research/overview/` | 通用资料与编号笔记分开 |
| 官方快照与第三方源码 | `research/snapshots/`、`research/notebooks/` | 按来源与日期保存原件 |
| 实验配置、冻结源码、审计记录 | `experiments/NNN-*` | 保留既有物理路径和原件字节 |
| 构建或上传的 Notebook | `notebooks/NNN-*` | 保留版本、账号与上传证据 |
| 原始请求、模型输出、运行日志 | `runs/NNN-*` | 本地保存，Git 忽略 |
| 分析、检查、构建、准备、回放脚本 | `scripts/` 下对应用途子目录 | 从项目根目录调用 |

新增实验后执行 `python3 -B scripts/tools/project_index.py`，刷新实验、脚本与资料导航。索引由当前实际文件生成，实验状态以进展和原始运行记录为准。

## 历史路径迁移

| 原路径 | 当前路径 |
|---|---|
| `research/NNN-*.md` | `research/notes/NNN/NNN-*.md` |
| `research/*-findings.md` | `research/overview/*-findings.md` |
| `scripts/analyze_*.py` | `scripts/analysis/analyze_*.py` |
| `scripts/check_*.py` | `scripts/checks/check_*.py` |
| `scripts/build_NNN_*.py` | `scripts/build/build_NNN_*.py` |
| `scripts/prepare_*.py` | `scripts/prepare/prepare_*.py` |
| `scripts/replay_*.py` | `scripts/replay/replay_*.py` |
| `scripts/research_*.py` | `scripts/research/research_*.py` |
| `scripts/compact_requests.py` | `scripts/tools/compact_requests.py` |
| `scripts/demo_*.py` | `scripts/demos/demo_*.py` |
| 原完整 `README.md` | [历史操作手册](archive/project-history-2026-10-22.md) |

`scripts/build_experiment.py`、`scripts/build_submission.py`、`scripts/summarize_experiment.py` 保持原位和原内容。冻结 JSON、Notebook、源码归档中的旧路径属于当时的来源记录，仍按原件保存；本次更新了维护中的脚本入口、Markdown 链接与命令。

历史记录需要定位单个旧路径时，可查[完整文件迁移映射](archive/path-migration-2026-10-22.json)。

## 清理范围

本次删除 115 个可再生成的 Python 字节码缓存文件（2,939,550 bytes，约 2.8 MiB）和 2 个无内容的旧运行目录。原始 `requests.jsonl`、运行日志、冻结源码副本和上传故障证据均有复核用途，予以保留。两个下载 ZIP 仍含解包目录未保留的条目，保留原件。

继续使用 `.gitignore` 排除本地运行输出、下载数据、虚拟环境、缓存和凭证。临时草稿或编辑器备份不进入版本库。
