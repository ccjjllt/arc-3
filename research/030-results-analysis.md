# 030 关内持久Python：全池正收益，推进真实提交

2026-10-21，北京时间。执行版本 `zhuating/arc3-030-capability-comparison` v2；模型与服务沿用009，唯一能力变化是当前关内保留真实Python计算状态。**决定直接推进候选自身保存运行及真实提交，不追加一轮全池确认。** 新正式submission尚未创建。

## 同预算结果

两臂各25题、7254秒、10 streams、1 pass，候选先、基线后，共用一次模型加载。两臂完整结束、无crashed／not_started、无残留工作线程，缓存清理均由服务日志确认。研究模型进程组已关闭。

| 指标 | baseline | persistent_python | 候选减基线 |
|---|---:|---:|---:|
| 官方公式平均分 | 42.613362 | 47.169880 | **+4.556518** |
| 完成关卡 | 103/183 | 102/183 | −1 |
| 全通 | 5 | 8 | +3 |
| 动作 | 5377 | 4643 | −734 |
| 记录生成token | 4,332,548 | 4,408,842 | +76,294（+1.76%） |
| 分析器报告token | 4,461,854 | 4,532,258 | +70,404 |

记录token与分析器token是两种记账口径，不能相加；超时请求未返回完整usage的成本也不能默认零。两臂包含相同被动计时／调度观察器及研究deadline修正；正式版本继承009原请求行为，不悄悄带入研究hooks。

12题正向、10题负向、3题不变。最大正向r11l +78.0594，其次cd82 +68.5469、cn04 +52.3810、su15 +44.4952；去最大正向后其余24题平均仍+1.4939。明显回退包括vc33 −78.5714、tn36 −59.1984、sp80 −42.8571、ka59 −35.2535。总关数下降不能略去，但官方平均分和全通的净提升足以取得下一份隐藏集证据，不要求所有辅助指标同时上升。

此处只有一轮描述性对照，不能证明统计显著性、全部分差均由持久变量造成，或隐藏榜一定上涨。既有027基线50.43不是本轮对照，不能混用。完整逐题／逐关见 [精确报告](../experiments/030-analysis/report.md) 与 [JSON](../experiments/030-analysis/report.json)。

## 机制实际发生

实际2259次Python调用、3283次action调用；helper报告10次状态丢失，结束后worker为0。状态丢失提示可能在后续调用重复出现，不能拿提示条数代替实际丢失次数。

已读取真实请求发现：cn04的普通列表sols跨调用直接被render；普通sols_found／SHAPE随后用于目标计算和实际动作。tu93更直接：path列表定义后，即使中间一次import失败，后续新调用仍分别读取path[:8]与path[8:]执行真实动作，并在该序列中通关。这超出原有函数源码保留；静态AST命中不是单独证据。[采用复核](030-persistent-python-adoption.md)保存原请求位置、实际stdout和边界，不把通关后新帧失配误报为旧计划失败。

## GPU与来源

会话内部15402.75秒（约4.2785h），模型ready834.66秒。求解阶段GPU采样均值候选92.33%／基线91.74%，中位99%／98%；这些不是全会话平均值，也不是Kaggle逐作业计费。结果后CLI余额24.08h属于当时快照。

远端latest在下载前后均核对为v2；29个cell类型及源码与冻结版本逐项相同。Kaggle序列化令原文JSON字节hash不同，未把它冒充相同字节；CLI的版本路径不能锁输出。[下载原件hash](../experiments/030-analysis/output-manifest.json)、[版本及完整440文件索引核验](../experiments/030-analysis/remote-version-and-output-index-after-completion.json)、[GPU分阶段采样](../experiments/030-analysis/gpu-utilization.json)。

## 正式推进

`zhuating/arc3-030-persistent-submission` **v1已推送，正在候选自身保存运行**。Notebook SHA256 `cf08d5876048343b86102917e171d77b2c27b8e65de431afc7fb22d76befb95a`，helper SHA256 `084c3d46e855a32b0482b49139f7135b2c5a8174c9d51eeeeb60c49d91a6428e`；嵌入helper与研究v2一致。保留009动态live gateway、31920秒solver、9小时限制、模型及服务；不装028或研究hooks。

该运行沿用既定两题300秒真实模型保存流程。保存结果不是正式分数；成功后使用同一准确版本真正competition submit，记录ID再跟进COMPLETE。不要再push此slug覆盖v1。原009 v2／57101330／public31.16保留。[当前保存／提交记录](../experiments/030-submission-launch.json)。031只是备用，当前不占GPU。
