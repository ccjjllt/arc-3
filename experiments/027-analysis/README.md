# 027 analysis — BLOCKED ON GPU QUOTA (no scores)

日期：2026-10-20。状态：**未运行，无分数**。本目录暂只记录 CPU 预检证据与配额快照；任何平均分、胜负题、完成度结论都必须等 GPU 会话 COMPLETE 后再写。

- 配置：`experiments/027-tail-confirm.json`（候选→基线，7254s/臂，hard_limit 18000s）。
- 构建：`notebooks/027-tail-confirm/experiment.ipynb`，16 cells，778700 bytes，SHA `55b47c45…c8a7`（两输出目录可复现一致）；`validate_config` PASS。
- 提交底座：009 v2 离线构建复验通过（25 cells，SHA `203da467…5dd5`，`/tmp/arc3-009-check`）；候选定制构建器**未建**（按计划：只有复现收益才建）。
- 配额（分进程实测，刷新 2026-10-24T00:00Z）：jiyujia 剩 ~6649s（1.85h）；ccjjllt、qingyu1232 均已超 21600s 额度。027 需 18000s 硬限 → **三账号均不可跑**。证据：`runs/027-tail-confirm-cpu-preflight/quota-snapshot.json`。
- 推送：**未推送**（故意）。kernel `jiyujia/arc3-027-tail-confirm` 无版本。
- 正式基线不变：009 v2 / submission 57101330 / public 31.16。**未伪造任何 submission.parquet 或分数。**
- 恢复命令（刷新后）：`kaggle kernels push -p notebooks/027-tail-confirm`，随后按预注册标准判定（主指标官方平均分 + vc33 敏感性披露，只确认一次）。
