# 038：原样高分底座参考

2026-10-25。037正式26.71后，恢复The AGI Boys得分版v83的原样solver，固定同一Docker31401和5个输入版本，补上本队原样正式参考。上游35.35不是已在本队复现的分数；本队最佳仍009／31.16。

本地已构建并冻结25cells／676941字节，SHA256 `4711d9846e5d953cab075df1f78138e27eb39e277c8ce008b8ad349f87f4ad1f`。移除037的全部segmentation_runs安装单元；模型、服务、采样、调度、31920秒、120并发、10streams、warmup1及gateway与v83保持。复用已验证输入/save适配，两题300秒真实GPU保存检查配置已准备。

本地静态、配置和冻结副本检查通过；当前**未上传、未GPU运行、未正式提交**。本轮查询时GPU余额9.20h、今日提交额度0。下一步在平台额度允许时完成必要保存和准确版本提交，随后读取真实公开分数。只安排一次原样参考，不因未达到35.35就原样重复投。

[研究决策](../../research/notes/038/038-research-decision.md) · [配置](../../experiments/038-highscore-baseline.json) · [Notebook](../../notebooks/038-highscore-baseline/submission.ipynb) · [冻结核验](../../experiments/039-preparation/variant-build-review.json)
