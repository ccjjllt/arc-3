# 026 — 失败前缀修复分支进展

日期：2026-10-19。状态：**notebook 已构建，待推送**。`ccjjllt/arc3-026-failure-repair`，RTX PRO 6000。计划见 [025/026 交接](../handoff/025-research-handoff.md)，CPU 研究见 [026 修复诊断](../../research/026-failure-repair.md)。

## 设计（相对交接的偏差已记录原因）

* 双臂 `repair_A` / `repair_B`，同 4 官方前缀、同切入 T、同额外预算（30 动作 / 250s），标准 `summarize_experiment --reference repair_A` 对比。`experiments/026-failure-repair.json`。
* A 从回放态新鲜继续；B 多一条宿主证据重核 opening 消息（0 env 动作，`ProbeBudget(0)` 构造保证）。会话注入被 dropped：Kaggle 1MB payload 上限装不下 16–75MB 的请求日志；A/B 共享精确状态与预算，对比仍是单因素的。A-vs-原始轨迹只作保真诊断。
* 不新增模型可调工具/提示前缀；修复只走 stdout 文本与顶层 def。`src/arc3_research/failure_repair.py`、`probe_budget.py`。
* fork 输入 `experiments/026-fork-inputs.json`（7.5KB）：切入点 + 引用的失败签名 + 切入前动作序列。

## CPU 验证（均已通过，无 GPU/模型）

* `scripts/replay_026_prefix.py`：四前缀 111/111 检查点精确对齐。
* `scripts/check_026_probe_budget.py`：14/14（配额、截断、边界、K=0）。
* `scripts/check_026_fork.py`：20/20（重核裁决内容、宿主可见性、payload 体积）。
* `validate_config` + preflight 兼容（新 arm 冻结 remaining/pace0；preflight 只验模块与预算器，无全局 hook）。

## GPU

* v1 ERROR：回放键名不匹配（`KeyError: action`），已修消费侧双格式兼容。
* v2 ERROR：repair_A 成功（4 forks 回放精确），但空历史冷启动下模型把 250s 花在重探索上（0–2 个后 T 动作，~35k tokens），repair_B 没跑到（臂间 cache-flush 偶发失败）。教训：原 run 首动作耗时 50–1853s，250s 上限对冷启动根本不够；且“同状态不同知识”的对比测的是探索速度而非修复。
* v3（RUNNING）：warm restart——录制的纯文本会话恢复（图片剥离，163KB 打包），B 追加宿主重核；kept={} 双臂一致（源码未落盘，只能自包含重定义，已记录）。若 B 在同状态下更快恢复通关且 r11l 干净，则有效。
