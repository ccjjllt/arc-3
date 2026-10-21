# 032/033 研究执行进展

2026-10-21，北京时间。用户已授权直接执行，要求专注研究，不在门控/测试上反复；优先使用ccjjllt、jiyujia、qingyu1232配额。

## 研究状态

- 031自然对照已COMPLETE并完整下载。22.5092→23.2819，+0.7726；27→26关，3题涨/4题跌/3题平。独立深读确认r11l有runs→2950像素→225个解→实际10次计划点击→多过L2的完整正链；ft09最大增益不能归因为runs修正旧P4错误。031 v2保留为一次全池候选，先收032/033结果；若它们没有更强直接收益，就推进031全池，不再增加提示版本或短筛门槛。详见experiments/031-natural-analysis/decision-review.json。
- 032成功关卡文字记忆短对照已COMPLETE：45.00597→70.66115（+25.65519），40→53关、3→4全通，5题涨/5题平。记忆helper记录49次已通关事实、40条模型规则，415次实际成功请求含记忆；这些是交付计数，具体复用及收益归因仍在并行审阅。已立即启动zhuating/arc3-032-memory-full v1的一次全25题比较，每臂7254秒、原009 warmup1/request_deadlinefalse，冻结helper不变，恢复原模型预读。详见experiments/032-full-launch.json。
- 033已COMPLETE：zhuating补跑的全帧4096像素两次正确并交付，但rebuild错分任务布局为17行/14列、59个图案、2个普通格子；主循环未调用它，后续独立打印正确P4后也未重算旧目标。450秒、26动作、新增0关，本版不扩跑、不提交。初次jiyujia在冷加载13/38分片时退出，没有机制效果证据；其剩余0.25h不足重载，所以用zhuating补跑，恢复原009整模型预读、冻结研究代码不变。模型466秒就绪，会话975秒，服务已关闭。详见research/033-results-analysis.md。
- 032正式候选`zhuating/arc3-032-memory-submission` v1已GPU保存COMPLETE，报告passed：health200、sb26/cd82真实非RESET动作66/22、生成token36094/31921，官方未计分placeholder已生成，自己的服务已关闭。源码hash为d8829b5a07f07eba7dd52ade18724556bcf23a288d2271f2b2aaa6f5c6691028。等待正在运行的全池结果后直接使用该版本正式提交，不重推。当前尚无新competition submission，正式最佳仍009/31.16。
- 033另做了纯CPU机制回放：同一冻结切点、原目标算法不变，只把bbox伪填色换为真实像素，A规则下由程序自动导出的2个点击完成L3；错误输入+A只点1次且未过关。说明准确输入进入目标程序的执行足以解决该切点；它是研究者干预，不计作模型收益。完整四条件结果见experiments/033-controller-analysis/counterfactual-ft09.json。

## 配额与排程

14:16左右启动前快照：ccjjllt余0h、jiyujia余0.74h、qingyu1232余2.28h，SDK reserved均0。是账号共享GPU余额，不保证具体型号。033单候选hard2580秒，实际450秒续跑含≤120秒修订，runner allowance600秒，配合小额jiyujia预算；032用较长窗口观察跨关和裁剪。详见experiments/032-resource-snapshot/。

下一步直接阅读真实轨迹与同预算分数。只做维持实验可运行和结果可信所必要的修复，不新增测试套件、不反复容量/提示搜索。记忆有直接收益就进入全池和真实提交；033先判断旧语义提取是否实际修好，不把全帧复制正确当作规则学会。

## 当前等待状态

用户表示全池出结果后再通知；已暂停主动跟踪，没有取消已运行GPU作业，没有创建定时监控。全池为zhuating/arc3-032-memory-full v1；正式候选zhuating/arc3-032-memory-submission v1已保存通过，尚未competition submit。收到通知后读取现有结果，按结果直接推进真实提交，不重推或重新保存。
