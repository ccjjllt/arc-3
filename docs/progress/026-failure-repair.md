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

* 待推送：`kaggle kernels push -p notebooks/026-failure-repair -t 7200`（ccjjllt 身份；本地已验证凭证即此身份，配额剩 16.59h）。
* 回收后比对：B 是否改变后续动作并通关、r11l 对照是否零误伤；增量无效或频繁误伤即停。
