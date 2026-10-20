# 027 进展 — 已推送 RUNNING（teammateb额度）

日期：2026-10-20。状态：**已推送，RUNNING**。

- 配置：`experiments/027-tail-confirm.json`，候选→基线顺序，单tail参数。`validate_config` PASS。
- 构建：`notebooks/027-tail-confirm/experiment.ipynb`（16 cells，778700 bytes）。推送ID `qingyu1232/arc3-027-tail-confirm v1`（配置原写jiyujia，实际用teammateb推送，见下）。
- 推送：teammateb（qingyu1232）`kaggle quota`剩12.34h/30h；ccjjllt剩8.18h；jiyujia加速器统计剩1.85h不够5h硬限，故改用teammateb（与025先例一致）。`kaggle kernels push -t 18000`成功v1，状态RUNNING。启动记录`experiments/027-launch.json`。
- 配额口径说明：加速器统计（6h池）显示BLOCKED，但`kaggle quota`（30h池）显示teammateb/ccjjllt均够4.8h；以后推前以`kaggle quota`为准并双口径记录。
- 提交底座：009 v2离线构建通过；候选定制构建器未建（待复现收益）；未创建competition submission。
- 结果按预注册标准判定一次（主指标官方平均分 + vc33敏感性披露），不扩搜。
- 正式成绩仍为009 v2 / submission 57101330 / public 31.16。
