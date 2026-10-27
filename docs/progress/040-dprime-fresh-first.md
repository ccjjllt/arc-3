# 040：D-prime保留新题优先，正式提交待评分

2026-10-26 21:41北京时间。用户授权继续优化后，新派实现与独立审查代理，以实际最高分009v2为固定底座，构建并启动一次新候选。当前最佳仍009／31.16，040尚无正式提交或公开分数。

## 候选范围

D-prime替换priority_value、ProgressPace，并启用mean-token pace、queue refresh、0.4尾段fade。使用公开源码已有PRICE_FRESH=False选项，保持009的`gate.acquire`与`session.play`原对象，保护未开始题的初次准入。独立原函数反例表明True可能让已停滞短题持续压过未开始长题；这不是兼容bug，因此没有默默修改公开公式或新增aging参数。

保留009准确v2源码、Docker `57e612b4…`、模型、提示、采样、10streams、120任务、1pass、31920秒逐题上限、原gateway及soft_end行为。两个数据集显式固定/1，五个输入版本ID与已验证公共栈一致。没有加入037像素字段、039step或其它求解干预。

公开D-prime当前v2源码SHA与昨日快照完全一致；历史卡片33.55尚未绑定具体得分版本，040也保留了原fresh-first，所以它是独立待测候选，不是33.55全本复现。[来源边界](../../research/notes/040/040-scored-version.md)

## 已完成的验证

- 实际冻结runtime的14项CPU检查通过，包括32,400组公开公式整数优先级逐项精确一致、先unpickle再安装后新建PaceTracker、真实gate线程重排、0.4fade及恢复原方法。没有模型、GPU或游戏动作。
- 独立代理22项预发布检查通过：四个安装单元位于配置后、bm.run前；反向移除安装与save快照钩子后，正式代码与009逐字相同；manifest与冻结依赖哈希一致。
- 上传后官方API回读29cells逐字相同，14项源码、版本、GPU/私有/断网、009镜像、五个输入ID等检查全部通过。

本地Notebook29cells／688885字节，SHA256 `8e742d69135c687896365dd6d8a4388b4f33d54eda87760b35301ded4481ae47`。helper SHA256 `484d1e08b8de491a108ed3057b75f8a7b4a5994d01bd5f8476374d8d849640fc`。所有来源固定在[提交源码归档](../../experiments/040-submission-source/)。

## 实际启动

使用用户已授权的jiyujia账号，查询时GPU剩23.20h，主账号7.48h。本人保存Notebook列表没有已确认运行的任务，3个旧ref不可查询，交互session并未被完整列出。新slug直接pull403不能判断存在性；再次本人列表32项中无040，确认无已知同名版本后push一次。

Kaggle已接受 **jiyujia/arc3-040-dprime-fresh-first version1，Notebook ID140991585**，21:41回读**RUNNING**。平台超时32400秒保持正式9小时target，save自身3600秒watchdog，模型就绪后仅sb26/cd82并发2、各300秒真实动作和生成；仅save通过后才写官方未评分占位输出，并清理本次拥有的模型进程。

两题短测、尤其仅2并发而gate有10slots，可能尚未触发context trim和优先级竞争；`priority_calls=0`本身不能判为失败。会读取真实snapshot的active／price_fresh／pace实例与更新／priority_calls；CPU真实gate检查负责兼容证据，正式分数负责提分判定。

当前团队正式额度0，**未创建040正式提交**。等待用户完成通知后读取本次save report、benchmark和dprime快照；运行及准确版本检查通过且额度可用时，只提交该成功版本一次。不重复push、不设置自动监控或连续轮询。

[运行页面](https://www.kaggle.com/code/jiyujia/arc3-040-dprime-fresh-first) · [启动记录](../../experiments/040-launch.json) · [远端核验](../../experiments/040-remote-source-check.json) · [CPU原件](../../experiments/040-preparation/dprime-cpu-check.json) · [独立审查](../../experiments/040-preparation/builder-review.json) · [计划](../plan/040-dprime-fresh-first.md)

## 保存完成，保留准确v1等待正式额度

2026-10-26 22:21北京时间，用户通知完成后官方API确认**COMPLETE，仍为version1**。29cells再次逐字匹配，009镜像、五个输入版本、GPU/私有/断网等14项回读核验通过。保存报告passed，真实RTX PRO6000，health200在838.15秒就绪，总检查1159.04秒，输出已写、模型拥有进程组已清理。

两题300秒短测：sb26有73次非RESET动作、记录33069个动作挂接/序列化最终tokens、完成4关；cd82有38次非RESET动作、同口径32805 tokens、完成0关。两题按预算cancelled，正常结束。这些数字不代表隐藏正式分数；sb26 solver_note的33928与保存的动作挂接33069不同，不把后者称为完整模型生成总量。

helper安装与最终快照均active、price_fresh=False、fade0.4，实际创建2个PaceTracker并更新4次；fresh_priced=0。**priority_calls=0，此次短测没有触发D-prime优先级评分/重排**，因此不能据它声称调度已经提高吞吐或分数。兼容证据来自既有实际CPU gate检查，正式收益仍需隐藏评分。日志末尾SIGQUIT出现在本次主动SIGTERM清理阶段；没有Notebook traceback，不能把正常清理信号当作中途模型崩溃。

root完成23项保存复算，最新派独立代理另完成32项复核，全部通过。benchmark hash、冻结manifest、运行报告source hashes均一致。

团队查询仍为今日已用1、累计5、剩0。状态**READY_AWAITING_TEAM_SUBMISSION_QUOTA，未创建040正式提交**。保留已通过的jiyujia版本1，下一次用户触发检查且额度恢复时，核对版本、源码和无重复提交后直接正式提交一次；不重跑保存，不设置自动监控。当前正式最佳仍009／31.16。

[保存结果](../../experiments/040-save-result.json) · [完成后源码核验](../../experiments/040-postsave-source-check.json) · [输出下载清单](../../experiments/040-save-output-manifest.json) · [新代理独立复核](../../experiments/040-save-independent-review.json)

## 2026-10-27正式提交已接受

用户明确通知有额度并要求submission。实时CLI确认今日已用0、剩1，团队历史不存在040；官方回读仍为准确jiyujia v1／COMPLETE，29cells及镜像、五输入版本等14项全部通过。本轮新派独立代理复核冻结hash、保存passed及price_fresh=False，无阻断。

直接提交现有成功版本，CLI执行1次并正常退出。北京时间**2026-10-27 09:51:24**接受唯一新提交 **57685414，PENDING**，提交者jiyujia、团队ccjjllt，描述绑定SHA256 `8e742d69135c687896365dd6d8a4388b4f33d54eda87760b35301ded4481ae47`。今日剩0次，040尚无公开分；最佳仍009／31.16。

等待用户完成通知后读取该ID正式结果，不重复提交或GPU保存、不设置自动轮询。

[正式提交记录](../../experiments/040-formal-submission.json) · [平台接受列表](../../experiments/040-after-formal-submissions.json) · [初始回执](../../experiments/040-submission-detail-initial.json) · [提交前源码核验](../../experiments/040-before-formal-source-check.json) · [本轮独立复核](../../experiments/040-formal-independent-review.json)
