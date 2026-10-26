# 038 正式结果：27.73，原样底座复现结束

2026-10-26，北京时间。用户通知运行结束后，官方CLI列表和GetSubmission均确认 submission **57650170，COMPLETE，public 27.73**，提交者jiyujia、团队ccjjllt。038相对009最佳31.16低3.43，相对037的26.71高1.02；相对上游v83历史显示35.35低7.62。最佳仍为009。这里的差值是各一次运行的描述，不是组件因果效应。

## 结果改变了什么

038完成了本队原样v83正式参考，不能把上游35.35继续当作已复现的起点，也没有依据再原样重复提交。它没有带来相对009的新求解算法。此前的两题GPU保存通过只证明模型和动作链可运行，不能据此预测隐藏正式分数。

实际009v2的SHA256为`203da467cb0534fdf50b5683a55a524e647023e0d490524c59f2fda9a73b5dd5`，038v1为`51e11dc5d8d1a0a4852db9208b81dd2a1a453bfef4cf59f05092d64e3a3c06e8`。两份均25cells；代码单元仅0、18不同。核心harness patch、模型/提示/采样/调度环境、依赖安装命令、模型启动器、target、gateway与benchmark入口源码逐字相同。

隔离求值已检查过的配置cell18，在正式分支得到完全相同的1pass、120并发、31920秒逐题上限、900秒analyzer timeout、关闭请求日志，正式demo排除列表均为空。009初始n_passes4与038初始1均被正式分支覆盖为1；038的demo排除15题不会作用于正式游戏列表。没有因此减少正式题目覆盖的源码证据。

已知部署差异为Docker：009使用`57e612b4…`，038使用`00377cd1…`；038数据集显式固定/1并回读版本ID，009历史metadata使用裸slug。不能把这些已知差异直接解释成退分原因；历史实际挂载版本、启动耗时、吞吐、隐藏题轨迹及平台状态尚未形成可识别的对照。[逐cell审计与配置原件](../../../experiments/038-analysis/038-vs009-runtime-audit.json)

## 诊断边界

038的episodes接口仍返回空列表，submission下载接口HTTP403，没有取得逐题完成关卡、tokens、模型就绪时间、截止覆盖或正式运行日志。GetSubmission的提交文件3814字节不能反推出题数或正常完成程度。当前既不能判定平台故障，也不能排除平台或随机轨迹影响。

只读刷新[平台慢读讨论751598](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/751598)后，比昨日快照新增11条顶层消息，仍有用户报告同版本0分、慢加载及system error。新消息主要为参赛者自报，不是对038的工程诊断，不据此替038申请重评或断言本次有相同故障。[当日原件](../../snapshots/2026-10-26-result-review/topic-751598.json)

## 下一候选的优先级

1. 保留009为当前最高实测版本，结束038原样重提路线。固定它的环境用于下一项变化，仍须承认31.16也是一次历史结果，不能保证复现。
2. 优先核验公开D-prime的准确得分版本，再只移植调度机制，保留10streams、模型与提示。已有源码的实质变化包括动作/token衰减、逐关pace、tail fade和未开始游戏定价，可能影响多题算力分配。昨日公开卡片33.55尚未与具体版本准确绑定；本轮页面读取超时，未解决此问题，所以它是待审候选，没有本队净收益证据，不能宣称可得33.55。来源：[tantan D-prime](https://www.kaggle.com/code/tantan0327/arc3-franzen-dprime)、[已存差异](../../snapshots/2026-10-25-strategy/notebook-sources/tantan0327__arc3-franzen-dprime/franzen.diff)。不能把此算法等同于已停损的027 tail_80k。
3. 039降为低优先级兼容备选。10次step错误全部下一调用恢复，纠错响应合计2282 completion tokens、43.346秒请求延迟之和；CPU反例支持修复正确性，尚不足以支持为它单独消耗下一次正式机会。

036固定完成关卡后的动作效率上限空间约2.15，且16/25题已到当前进度上限；这只描述该开发轨迹，支持将主要研究目标转向增加关卡覆盖，不预测隐藏分数。[条件上限计算](../../snapshots/2026-10-25-strategy/036-headroom-calculation.json)

本轮只完成正式结果读取、源码/配置审计和候选优先级调整，没有启动新GPU运行或新正式提交。

[正式记录](../../../experiments/038-formal-submission.json) · [最终回执](../../../experiments/038-formal-result-snapshot.json) · [诊断可用性](../../../experiments/038-formal-diagnostics-availability.json) · [新代理独立复核](../../../experiments/038-formal-result-independent-review.json)
