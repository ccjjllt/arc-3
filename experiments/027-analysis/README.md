# 027 analysis COMPLETE

日期：2026-10-20。状态：**qingyu1232/arc3-027-tail-confirm v2 已完成，候选失败，014尾部调度路线关闭。** 本文件替换启动前“配额封锁、未推送、无分数”的过时状态。

| 指标 | baseline | tail_80k |
|---|---:|---:|
| 25题平均分 | 50.4293 | 44.4542 |
| 完成关卡 | 112/183 | 101/183 |
| 全通 | 8 | 7 |
| 动作数 | 5458 | 4680 |

平均分差−5.9752；7题上涨、6题持平、12题下降；去掉vc33后其余24题仍平均下降4.8848分。只有动作变少不能证明效率改进，分析器token总量反而增加约2.74%。不做第三轮确认，不构建或提交027候选。

- 配置：[027-tail-confirm.json](../027-tail-confirm.json)，候选→基线，各7254秒，25题、10并发；硬限18000秒。
- v1臂名未被preflight接受，失败后v2改为 `tail_80k`。最终本地Notebook SHA256为 `094ad2b4ca649e5351fdeae309f2b6c664cf53ac9e93fa6655537d35c069b62f`。
- 实际会话内部15097.424秒，约4.194小时；两臂完整、服务已关闭。原件在本机 `runs/027-tail-confirm/experiment-manifest.json`。
- 逐题分析：[summary.json](summary.json)、[summary.md](summary.md)；结论：[027结果](../../research/027-tail-confirm-results.md)；启动与完成记录：[027-launch.json](../027-launch.json)。
- 正式最佳仍为009 v2／57101330／31.16；027没有新建submission。
- 下一轮采用[提分与提交交接](../../docs/handoff/029-score-and-submission-handoff.md)。10月20日实时确认zhuating CLI剩余30小时；SDK不同配额口径不能直接推断GPU封锁。旧“刷新后启动027”指令作废。
