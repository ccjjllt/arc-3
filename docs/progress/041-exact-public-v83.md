# 041：最高公开得分v83原始23cells副本，正式0.00待诊断

2026-10-27。用户在040正式仍未提高后，明确要求明天用公开最高分Notebook直接提交一次，并在后续选择“我明天发消息后再提交”。本轮仅准备并保存原样副本，**未创建041正式提交、未创建定时任务**。

## 来源和范围

10月27日20:17北京时间，官方API按分排序第一仍为`romantamrazov/the-agi-boys-i-am-better`。最新源码为v86，全部cell sources与已确认得分v83逐字相同；API没有提供数值score字段，因此数值沿用此前UI准确绑定的**历史35.35／v83／scriptVersionId359573474**，不声称v86重新得分35.35。明天用户发消息后再核准来源与准确版本。

用户要求本次原样，因此采用已下载v83全部**23个cell source原值，包括Markdown，逐字保留**。没有过去038的两题保存适配，也没有040调度、039step或其它helper，没有增加任何源码单元；仅清历史输出、execution_count和执行metadata，设置必要的平台账号/私有/GPU/镜像及输入。v83下载metadata的isGpuEnabled=false与真实历史GPU证据不符，显式选RTX PRO6000；镜像31401／digest00377及五个输入版本固定。

上传文件23cells／651065字节，SHA256 `3efa7a1cc75156e62599daca754b6349f513ba7591a8d08da30fa4716c549d34`。原下载文件含历史输出的SHA为`8221f1e64ad7d4c8b3ecbbcbd83f68c9469707246484b0bbcaa5254da809905e`，整个JSON字节不相同，但23个source值逐个一致。

保留原生`%%writefile`，未为patch source额外加尾LF；不重现009v1的动态执行包装。原保存路径使用绝对Kaggle挂载位置，原运行为排除15题后的**10题、10并发、每题25分钟**。正式仍为完整gateway、1pass、120任务、10streams、31920秒和soft_end=None。原保存正常返回后生成官方未评分submission.parquet；实际成功性需后续日志验证。没有038的health硬断言、独立watchdog或自有进程清理，所以不据源码路径预判运行成功。

038已在同一正式solver/镜像下得27.73，本次不保证复现35.35，也不为这次再加优化。它是用户明确要求的一次全源码原样验证。

## 实际启动和后续

新派独立代理26项检查通过。使用已授权jiyujia配额，读取时剩10.46h；本人库存另有`jiyujia/vfarl-train100-32k-session-r3`运行中，没有更改或停止其它任务。检查041新slug不存在后push一次。

20:20北京时间，Kaggle接受 **jiyujia/arc3-041-exact-public-v83 v1，Notebook ID141162518**；回读RUNNING，15项检查通过，远端23sources同时与上传版和v83原件一致、镜像31401和五输入版本匹配。

等待用户通知保存完成后，读取原始demo输出、模型日志、benchmark和submission.parquet，确认运行与准确版本。**10月28日只在用户发消息之后**，再核对额度、最高来源和无重复提交，正式提交这个成功原样版本一次。若出现失败，先说明真实问题，不擅改原始源码或重复运行。

本轮曾尝试设置一次明日自动跟进，被自动审批拒绝：未来提交会消耗正式次数，用户此前约定不设自动化且没有明确自动执行授权。没有创建任何任务；用户随后明确选择明天自行发消息，因此不重试定时安排。

[运行页面](https://www.kaggle.com/code/jiyujia/arc3-041-exact-public-v83) · [启动记录](../../experiments/041-launch.json) · [远端核验](../../experiments/041-remote-source-check.json) · [独立26项检查](../../experiments/041-preparation/exact-source-review.json) · [源码归档](../../experiments/041-submission-source/) · [最新公开排序原件](../../research/snapshots/2026-10-27-exact-public/read-manifest.json)

## 10月28日保存核验与正式提交

用户明确通知可提交后，官方确认原样保存**COMPLETE／仍为v1**，全部23sources与原v83及冻结上传版一致，镜像31401和五输入版本等15项回读核验通过。重新按分排序，来源Notebook仍列第一；API不提供数值分，历史35.35和v83绑定沿用已有准确UI记录，不将最新排序当作新分数。

原始10题demo正常完成，1won、9gave_up，共45关；实际benchmark窗口1506.98秒，offline均分43.5808。10题均有真实非RESET动作和记录tokens，真实RTX、原harness patch应用成功、模型服务正常启动，原始submission.parquet已生成。早期ConnectionError在原900秒重试窗口内恢复；未见未捕获异常或OOM。原样没有自定义save-smoke-report和cleanup，不能沿用038／040特有的保存断言。root15项保存核验与新派独立代理31项复核均通过。

CLI实时额度剩1次、历史中没有041。直接对既有**jiyujia/arc3-041-exact-public-v83 v1**提交1次，未重跑GPU、未修改代码。北京时间**2026-10-28 08:55:18**，Kaggle接受唯一新提交 **57718364，PENDING**，提交者jiyujia、团队ccjjllt，描述绑定源码SHA256 `3efa7a1cc75156e62599daca754b6349f513ba7591a8d08da30fa4716c549d34`。今日剩0次。

**43.58是离线演示结果，041正式分数仍为空；当前正式最佳仍009／31.16。** 等用户完成通知后读取57718364，不设置自动监控、不重复提交。

[正式提交记录](../../experiments/041-formal-submission.json) · [平台接受列表](../../experiments/041-after-formal-submissions.json) · [初始回执](../../experiments/041-submission-detail-initial.json) · [保存分析](../../experiments/041-save-result.json) · [独立31项复核](../../experiments/041-save-independent-review.json) · [提交前源码核验](../../experiments/041-before-formal-source-check.json)

## 正式0.00：早结束迹象，不能确认根因

2026-10-28用户报告零分后，官方CLI与GetSubmission确认**57718364 COMPLETE／public0.00／最终文件3411字节**。第一次记录COMPLETE的查询时刻为01:28:47.852UTC，距00:55:18.977提交约**33分28.875秒**。这是含排队的完成时间上界，不是精确worker运行时长；可以确认它没有进行完整9小时评测。0分不得与离线43.58混淆。

客户端提交记录、v1与sourcehash正确，全部23cells确为原v83。提交使用-k/-v代码重跑接口，最终3411B与保存占位2648B不同，没有直接上传离线演示文件作为正式成绩的证据。原源码仅在not TRUE_SUBMISSION写占位，实际formal环境标记及其执行分支仍需正式日志确认。

当前更应怀疑正式冷启动／gateway scorecard提前结束。原版模型等待在12分钟时释放，未强制health200，首请求再给900秒重试；慢读模型或首次有效动作过迟可能触发游戏／HTTP窗口结束。新读取的[讨论751598](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/751598)也有多个参赛者报告相同3411B＋COMPLETE0分，而保存运行正常。署名María的[3545231更新](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/751598#3545231)称平台问题仍在调查，并请勿继续提供单个submissionID；API未独立验证其staff身份。

这些是诊断方向，不是041根因证明。本次episodes仍为空、下载403；没有正式模型加载时间、首动作、关闭原因或逐题日志，无法区分平台异常、原启动脆弱性或其它具体执行失败。没有把0分归因于模型解题能力或承诺重提即可恢复35.35。

保留009／31.16，暂不原样重复041；下一步先核查正式模型启动和首个／持续gateway动作。本次只做只读诊断与记录，未发外部消息、运行新GPU、提交或创建自动化。

[最终回执](../../experiments/041-formal-result-snapshot.json) · [诊断可用性](../../experiments/041-formal-diagnostics-availability.json) · [诊断事实与假设](../../experiments/041-zero-diagnosis.json) · [新代理源码审查](../../experiments/041-zero-source-review.json)
