# 030 关内持久Python执行进展

2026-10-20 21:05，北京时间。用户已授权实际GPU研究、尽快确认提分并正式提交，并单独授权每15分钟自动续接，直到本轮submission评测完成。

`zhuating/arc3-030-capability-comparison` **v2已真正进入求解**，真实单张RTX PRO6000、97887MiB。候选persistent_python先跑，原baseline随后跑；各25题、7254秒、10 streams，共用一次模型加载。日志已观察候选运行120秒；尚无030均分或新正式submission。求解预算合计约4小时，最终时间以真实日志为准。

Notebook SHA256 `265ed9a9b84f118190a4262b96f85c6204be031de613f64a6fd4ca755ab8a994`，冻结源 `experiments/030-capability-source-v2/`，状态入口 [launch](../../experiments/030-capability-launch.json)，完整本地日志 `runs/030-capability-comparison/live-notebook-v2.log`。v1因1200秒启动分配不足退出，没有运行求解；v2修复wrapper签名、放宽启动等待至1800秒，未缩短任一臂预算。v2全量模型预读458.31秒，首臂开始时会话约835秒。

028已完成真实模型修复诊断，三对均无新增关卡，关闭本版；不重复GPU，不混入030。[028结果](../../research/028-program-repair-results.md)。030不新增模型API，直接让模型的普通变量／搜索队列在同一关存活，换关／超时／结束清理。

本聊天自动续接 **arc3** 已ACTIVE，每15分钟检查；无变化保持安静，收到实际结果继续分析，出现有意义增益即推进候选自己的必要Kaggle保存流程及真正competition submit，记录ID并跟进COMPLETE。原最佳009 v2／57101330／public31.16保留。自动审批最初拒绝持久任务；用户随后明确授权，创建已成功。

结果分析入口：`python3.12 -B scripts/analyze_030_results.py --root runs/030-capability-comparison --output-dir experiments/030-analysis`。用真实官方均分、逐题/关卡、token成本和变量复用轨迹判断，不套新的多条件晋升门或新增测试套件。若030明确负面，再用已准备的独立031精确分割runs短研究；031尚未启动GPU。

zhuating CLI在20:54读到剩余28.28h，属于历史快照，不据此推导本作业计费。实际生成利用率证据见 [GPU说明](../../research/030-gpu-utilization-notes.md)。下一次031已停用与SGLang分片预读重复的整目录model precache，保留分片预读、wheel预缓存及全部推理数值参数；当前030源码不因此改变，下一次效果未实测。
