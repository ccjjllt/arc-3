# 039：历史步号兼容修复

2026-10-25。本轮新审计在036两臂25题的4593条去重工具结果中发现10次HistoryEntryView缺少step，涉及8游戏。全部下一调用自然恢复，后续纠错响应合计2282 completion tokens；这是有界的小开销，未测线上得分增益。

候选只在原隔离Python的HistoryEntryView上增加只读`step`属性，返回既有`entry.frame.step`；空frame仍AttributeError。不改提示、repr、帧数据或动作处理。两例原失败代码CPU复现通过，实际helper输出与显式frame.step修正逐字相同，卸载还原原错。

已构建并冻结29cells／682888字节，SHA256 `ac9f48b8827f566ada2a6fea9cf8032a26637ccb3f7a804d48cb1f27807d9e20`。去掉四个安装cells后，其余运行代码与038逐字一致；旧037精确像素字段未安装。静态、配置、冻结检查通过。

当前**未上传、未GPU运行、未正式提交**。优先取得038原样v83参考，再安排本候选的必要运行检查和正式比较；不以CPU反例成功声称提分。

[研究决策](../../research/notes/038/038-research-decision.md) · [补丁](../../src/arc3_research/history_step_compat.py) · [Notebook](../../notebooks/039-history-step/submission.ipynb) · [CPU反例](../../experiments/038-analysis/history-step-cpu-counterexamples.json)

2026-10-26更新：038原样正式27.73，未刷新009的31.16。复核后039降为低优先级兼容备选，不机械晋级为下一次正式提交；当前证据只支持消除少量可自行恢复的接口错误，没有实质新增过关证据。优先核验D-prime调度的准确得分版本和独立移植范围。039仍未上传、GPU运行或正式提交。[结果分析与优先级](../../research/notes/038/038-formal-results-analysis.md)
