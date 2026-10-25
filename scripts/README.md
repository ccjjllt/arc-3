# 脚本目录

从项目根目录运行。按实验编号浏览见[实验索引](../docs/experiments/README.md)。

## 通用入口

以下三个入口被历史构建与冻结来源记录引用，保留原路径和内容。

- [build_experiment.py](build_experiment.py)
- [build_submission.py](build_submission.py)
- [summarize_experiment.py](summarize_experiment.py)

## 结果与证据分析 · `analysis/`

- [analyze_005_results.py](analysis/analyze_005_results.py)
- [analyze_006_results.py](analysis/analyze_006_results.py)
- [analyze_007_results.py](analysis/analyze_007_results.py)
- [analyze_008_representation.py](analysis/analyze_008_representation.py)
- [analyze_010_animation_archive.py](analysis/analyze_010_animation_archive.py)
- [analyze_010_efficiency.py](analysis/analyze_010_efficiency.py)
- [analyze_010_results.py](analysis/analyze_010_results.py)
- [analyze_011_results.py](analysis/analyze_011_results.py)
- [analyze_011_timing.py](analysis/analyze_011_timing.py)
- [analyze_012_results.py](analysis/analyze_012_results.py)
- [analyze_012_timing.py](analysis/analyze_012_timing.py)
- [analyze_014_requests.py](analysis/analyze_014_requests.py)
- [analyze_014_results.py](analysis/analyze_014_results.py)
- [analyze_014_timing.py](analysis/analyze_014_timing.py)
- [analyze_016_results.py](analysis/analyze_016_results.py)
- [analyze_017_coverage.py](analysis/analyze_017_coverage.py)
- [analyze_018_results.py](analysis/analyze_018_results.py)
- [analyze_019_results.py](analysis/analyze_019_results.py)
- [analyze_020_results.py](analysis/analyze_020_results.py)
- [analyze_025_admission.py](analysis/analyze_025_admission.py)
- [analyze_026_results.py](analysis/analyze_026_results.py)
- [analyze_028_results.py](analysis/analyze_028_results.py)
- [analyze_030_results.py](analysis/analyze_030_results.py)
- [analyze_031_forks.py](analysis/analyze_031_forks.py)
- [analyze_031_natural.py](analysis/analyze_031_natural.py)
- [analyze_032_results.py](analysis/analyze_032_results.py)
- [analyze_033_results.py](analysis/analyze_033_results.py)
- [analyze_034_results.py](analysis/analyze_034_results.py)

## 手动 CPU 检查与预检 · `checks/`

- [check_010_animation_integration.py](checks/check_010_animation_integration.py)
- [check_010_notebook.py](checks/check_010_notebook.py)
- [check_011_notebook.py](checks/check_011_notebook.py)
- [check_012_current_data.py](checks/check_012_current_data.py)
- [check_012_notebook.py](checks/check_012_notebook.py)
- [check_014_cleanup.py](checks/check_014_cleanup.py)
- [check_014_notebook.py](checks/check_014_notebook.py)
- [check_014_request_deadline.py](checks/check_014_request_deadline.py)
- [check_014_scheduler_observer.py](checks/check_014_scheduler_observer.py)
- [check_014_session.py](checks/check_014_session.py)
- [check_015_native_values.py](checks/check_015_native_values.py)
- [check_018_grounding.py](checks/check_018_grounding.py)
- [check_019_preparation.py](checks/check_019_preparation.py)
- [check_021_checked_execution.py](checks/check_021_checked_execution.py)
- [check_022_community_bridge.py](checks/check_022_community_bridge.py)
- [check_022_expect_check.py](checks/check_022_expect_check.py)
- [check_023_stall_probe.py](checks/check_023_stall_probe.py)
- [check_026_fork.py](checks/check_026_fork.py)
- [check_026_probe_budget.py](checks/check_026_probe_budget.py)
- [check_034_executable_plan.py](checks/check_034_executable_plan.py)
- [check_035_aux_reasoning.py](checks/check_035_aux_reasoning.py)
- [check_036_main_reasoning.py](checks/check_036_main_reasoning.py)

## 专用 Notebook 与输入包构建 · `build/`

- [build_019_microbench.py](build/build_019_microbench.py)
- [build_020_submission.py](build/build_020_submission.py)
- [build_026_fork.py](build/build_026_fork.py)
- [build_029_submission.py](build/build_029_submission.py)
- [build_030_submission.py](build/build_030_submission.py)
- [build_031_submission.py](build/build_031_submission.py)
- [build_032_submission.py](build/build_032_submission.py)

## 实验输入准备 · `prepare/`

- [prepare_020_community.py](prepare/prepare_020_community.py)
- [prepare_028_inputs.py](prepare/prepare_028_inputs.py)
- [prepare_034_su15.py](prepare/prepare_034_su15.py)

## 前缀回放 · `replay/`

- [replay_024_level_stall.py](replay/replay_024_level_stall.py)
- [replay_026_prefix.py](replay/replay_026_prefix.py)
- [replay_028_prefix.py](replay/replay_028_prefix.py)

## 专项研究工具 · `research/`

- [research_017_snapshot.py](research/research_017_snapshot.py)
- [research_033_counterfactual.py](research/research_033_counterfactual.py)

## 通用日志与目录维护 · `tools/`

- [compact_requests.py](tools/compact_requests.py)
- [project_index.py](tools/project_index.py)

## 行为机制演示 · `demos/`

- [demo_020_behavior_mechanisms.py](demos/demo_020_behavior_mechanisms.py)

构建、分析和检查脚本可能写出本地产物；具体参数与输入要求见脚本说明。
