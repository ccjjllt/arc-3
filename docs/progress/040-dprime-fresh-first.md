# 040：D-prime保留新题优先，GPU保存运行中

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
