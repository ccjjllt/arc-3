# 032/033 研究执行进展

2026-10-21，北京时间。用户已授权直接执行，要求专注研究，不在门控/测试上反复；优先使用ccjjllt、jiyujia、qingyu1232配额。

## 研究状态

- 032候选补跑`zhuating/arc3-032-memory-recovery` v1已COMPLETE：49.21798分、108/183关、7全通，与已保存baseline38.07781/96关/4全通作跨会话描述性比较，+11.14017、13涨/8跌/4平。25题分数复算一致，CPU/GPU正常关闭，会话2.3495h。该结果仍低于005历史基线49.89969，不能宣称稳定增益；保留已提交冻结版本，等待57481712真实分数。23:20北京时间查询仍无publicScore。详见experiments/032-memory-analysis/recovery-comparison.md。
- 031自然对照已COMPLETE并完整下载。22.5092→23.2819，+0.7726；27→26关，3题涨/4题跌/3题平。独立深读确认r11l有runs→2950像素→225个解→实际10次计划点击→多过L2的完整正链；ft09最大增益不能归因为runs修正旧P4错误。031 v2保留为一次全池候选，先收032/033结果；若它们没有更强直接收益，就推进031全池，不再增加提示版本或短筛门槛。详见experiments/031-natural-analysis/decision-review.json。
- 032成功关卡文字记忆短对照已COMPLETE：45.00597→70.66115（+25.65519），40→53关、3→4全通，5题涨/5题平。记忆helper记录49次已通关事实、40条模型规则，415次实际成功请求含记忆。完整日志分析得到27个交付审阅窗口，五题的实际代码、行动与request payload已审：r11l规划约束复用、sc25重置后组合泵/步长控制、tu93回读死亡转移并修订巡逻模型等有真实行动链。交付计数不是收益；通关后主动总结与裁剪后pin两条干预尚未拆分，首次发现及全部分差不能归因于记忆。详见research/032-results-analysis.md与experiments/032-memory-analysis/。
- 032 full `zhuating/arc3-032-memory-full` v1最终ERROR。实际只有baseline完成：25/25题有分、均分38.077806、96/183关、4题全通、4747动作，官方分复算一致，CPU子进程exit_code为0。旧runner把退出前的两个残留线程名快照当成继续运行的阻断条件而误停，memory候选未启动、无候选数据；服务已关闭。因此这是编排故障，不是memory负结果，也没有完成25题A/B。该baseline在short重叠10题均分50.291923，m0r0/sc25另轮也达5关、tr87明显下跌，提示基线与轨迹波动；跨预算、跨会话差异不能当作memory处理效应。详见experiments/032-memory-analysis/full-baseline-assessment.json。
- 033已COMPLETE：zhuating补跑的全帧4096像素两次正确并交付，但rebuild错分任务布局为17行/14列、59个图案、2个普通格子；主循环未调用它，后续独立打印正确P4后也未重算旧目标。450秒、26动作、新增0关，本版不扩跑、不提交。初次jiyujia在冷加载13/38分片时退出，没有机制效果证据；其剩余0.25h不足重载，所以用zhuating补跑，恢复原009整模型预读、冻结研究代码不变。模型466秒就绪，会话975秒，服务已关闭。详见research/033-results-analysis.md。
- 032正式候选`zhuating/arc3-032-memory-submission` v1已GPU保存COMPLETE，报告passed：health200、sb26/cd82真实非RESET动作66/22、生成token36094/31921，官方未计分placeholder已生成，自己的服务已关闭。源码hash为d8829b5a07f07eba7dd52ade18724556bcf23a288d2271f2b2aaa6f5c6691028，远端cell与冻结版本匹配。北京时间2026-10-21 20:29:45已真正提交成功，编号**57481712**；团队ccjjllt、提交者zhuating、来源v1/scriptVersionId360713071。独立读取提交列表已确认，当前尚无publicScore，待评测；不重推或重新保存。正式最佳仍保留009/31.16；保存通过、开发集提升均不保证榜单提升或奖牌。证据见experiments/032-after-formal-submit.json。
- 033另做了纯CPU机制回放：同一冻结切点、原目标算法不变，只把bbox伪填色换为真实像素，A规则下由程序自动导出的2个点击完成L3；错误输入+A只点1次且未过关。说明准确输入进入目标程序的执行足以解决该切点；它是研究者干预，不计作模型收益。完整四条件结果见experiments/033-controller-analysis/counterfactual-ft09.json。

## 配额与排程

14:16左右启动前快照：ccjjllt余0h、jiyujia余0.74h、qingyu1232余2.28h，SDK reserved均0。是账号共享GPU余额，不保证具体型号。033单候选hard2580秒，实际450秒续跑含≤120秒修订，runner allowance600秒，配合小额jiyujia预算；032用较长窗口观察跨关和裁剪。详见experiments/032-resource-snapshot/。

已修复研究runner退出判断，并启动`zhuating/arc3-032-memory-recovery` v1，仅补缺失的25题memory候选；现已COMPLETE、远端源码逐cell匹配，冻结solver与7254秒设置保持不变，外层上限14400秒。12:33UTC附近CLI余额18.40h足够本次约2.3h补跑，SDK通用配额仍是另一冲突口径。启动记录见experiments/032-recovery-launch.json。补跑已收取，下一步结合真实轨迹审阅及032正式比赛分数判断。正式提交与候选补跑均不以重新跑完一轮full A/B为前置；新会话候选与既有baseline的比较须注明跨会话限制。只做维持实验可运行和结果可信所必要的修复，不新增测试套件、不反复容量/提示搜索。033本版已据真实轨迹停止扩跑，不把全帧复制正确当作语义程序已修好。

## 当前跟进状态

全池故障已经读取并定位；032正式v1比赛提交57481712已确认，等待评测。候选单臂补跑v1已完成，49.21798分；不把缺失候选数据写成负结果，不拿short的70.66115替代真实榜单分数。009/31.16继续保留。

补跑退步审阅：sc25首记忆前L1已比baseline多90动作；su15 L5生成的guard因tag名单/材料检查条件缺失，真实死亡仍报ok，随后才UNDO。现未确证旧记忆直接造成这两题回退。原始代码/stdout与首次pin位置见experiments/032-memory-analysis/recovery-regression-review.json。后续程序纠错研究可优先围绕实际执行的状态检查，不能把仅存在的guard函数当作已经生效。

补跑正向审阅：r11l真实复用质心/足迹搜索并在L4执行16click清关，L6扩展染色井规则全通；vc33复用守恒水量/门条件并在L6/L7修正pillar污染的读取程序后全通。25次tool代码/stdout、12条规则及三题成功记忆请求hash均与实际payload/transcript相符。s5i5的红点消失早于首次pin，不能倒置归因。见experiments/032-memory-analysis/recovery-mechanism-review.json。
