# 043：低频推理复核，真实GPU验证中

2026-10-30。用户授权继续优化并争取一次提分submission。正式最佳仍为009 v2／31.16；042已完成26.09。今天团队尚有1次正式机会。目标是完成有依据的新候选验证后提交，不能预先保证超过31.16。

## 本轮选择和历史排重

最新公开Notebook排序没有核实到替代当前最高来源的新第一名。新发现的[ondrewsha Stack S9](https://www.kaggle.com/code/ondrewsha/arc-agi-3-stack-s9)有若干实质改动。其v2头部自报v1得32.16，但未独立绑定平台分数；这个分数对应整个组合，不能归给H3，也不是本队可复现承诺。

最初检查的“超时不清空已保留函数”确有代码缺陷，却已在007做过同语义真实A/B：12题46.3578→40.3235、51→50关，保留和复用真实发生仍无净提升。因此取消该候选，没有为它启动GPU。重新下载036/r11l一份41MB日志发现两次超时清空14/19函数，但这不能推翻007负结果。[排重和真实轨迹证据](../../experiments/043-preparation/trace-evidence.json)

043只移植S9 **H3v2.1**：关卡累计30k生成tokens、20k生成tokens无真实动作、或3条新“不可能”措辞触发推理复核；至少间隔12k tokens，普通关卡复核最多2次，连续无动作阶段单独限次。追加真实动作覆盖表；不强制执行动作、不改动作预算。没有移植HF、RESETC、H1记忆或SCH调度。

这区别于023/024的画面no-op或64已执行动作触发。H3的stale-summary判断避免把旧executed_count误认为刚刚执行了动作。原提示全文、采样、模型、服务启动参数、10streams和调度保留，默认full续接保证追加文本实际进入请求。

## 证据边界和选择取舍

无动作长规划并不必然无效：005归档有19段≥20k的动作前区间，其中11段所在关最终完成；036/r11l两段21,849／26,449 tokens的长规划也最终完成了该关。T3正则还可能匹配“not impossible”或局部约束，而不是全局不可解。覆盖表按完整画面状态计数，包含HUD差异，不是规则正确性证明。

轨迹审查代理偏向只保留T2；源码与公开方案审查代理偏向完整H3。主代理选择保留已公开H3原阈值与功能，不根据一两条轨迹另造参数，以便验证其完整机制；保留这一分歧和所有反例。没有把它认定为已验证提分方案。[停滞证据](../../experiments/043-preparation/stagnation-evidence.json) · [设计审查](../../experiments/043-preparation/h3-design-review.json)

## 实现、预算与冻结

基于042准确冻结源码，只新增H3模块与安装单元，以及保存阶段的预算/观察/检查。H3功能正文逐字保留S9 cell20（去除Notebook入口，增加准确来源说明）。CPU43项通过，包括三种触发、真实动作/stale、关卡切换、12k冷却、两次上限、真实Frame/动作映射、32独立实例并发和正常提示不变。独立最终产物39项通过。它们是CPU和源码证据，不是模型采用或分数证据。

- Notebook25cells／679045B，SHA256 `16cc3e6684ce9fba5880fa73e9491ce746e4c8699e1312d10508e65c270bb3ab`。
- Helper SHA256 `c4e0ef0323d09409b3639d94aabae11ac65418cbe24647dfb7a6177727130a8e`。
- 正式：原90min模型就绪门、32400秒平台预算、原31920秒逐题上限；镜像31401、五输入版本、断网RTX与042相同。
- 保存：原10游戏×25min；只在保存分支限制模型启动45min、总80min。watchdog只终止本次创建的模型进程组并失败退出。名义最坏45+25=70min，保留额外收尾余量。
- 账号CLI：jiyujia剩1.53h GPU，zhuating仅0.09h，不使用后者运行；周额度10月31日北京时间08:00刷新。挂载和其他会话仍可能消耗实际余量。

保存阶段的只读observer记录H3追加提示和位置，返回原提示对象。至少一次自然触发、标记文本实际存在、10题有模型生成和非RESET动作、全部终态及模型ready检查通过后，才写原协议placeholder。正式没有这个保存observer；gateway调用和输出所有权保持。

[CPU检查](../../experiments/043-preparation/inference-audit-cpu.json) · [独立冻结审查](../../experiments/043-preparation/final-artifact-review.json) · [构建源码](../../scripts/build/build_043_inference_audit.py) · [冻结原件](../../experiments/043-submission-source/)

## 已启动准确v1

2026-10-30 **09:08北京时间**回读：`jiyujia/arc3-043-inference-audit`，version1，Notebook ID **141592243**，**RUNNING**。push只执行一次。远端25cells全部源码与类型、GPU、镜像及输入等14项一致。账号完整返回60个已有Notebook列表中没有043，避免覆盖或重复运行。正式今日仍剩1次，尚未使用。

完成后下载 `startup-readiness.json`、`inference-audit-install.json`、`inference-audit-events.jsonl`、`inference-audit-save-check.json`、`benchmark.json`、`serve.log`、Notebook日志、`submission.parquet`；再依据事件选择1–2份对应逐题request日志，确认追加文本真正进入模型请求，并查看后续真实动作与进度。原就绪报告继承042标签，但由043当前版本执行，不能拿旧042输出替代。

验证正常后，重新核对准确v1源码和提交额度/排重，按用户授权提交一次；若存在异常、提示未送达或明显持续无动作，需要先诊断。短保存结果不构成完整配对A/B，不能把相对历史demo的分差宣称净收益。按此前用户通知完成的工作方式，不创建自动监控或自动重试。

[运行页面](https://www.kaggle.com/code/jiyujia/arc3-043-inference-audit) · [启动记录](../../experiments/043-launch.json) · [远端源码核验](../../experiments/043-remote-source-check.json)

## 真实保存通过，已正式提交

2026-10-30 10:08北京时间回读。准确v1 **COMPLETE**，远端25cells与冻结源码一致，14项身份/环境检查通过。模型在554.943秒（约9分15秒）健康就绪；日志先ready，再安装H3、启动benchmark及RESET，实际RTX与原补丁正常。

10题1pass结束，**1 won／9 gave_up，共49关、1365次非RESET动作、875495记录生成tokens，离线均分49.304978**。benchmark耗时1524.050秒。8项在线保存检查全过，两份日志无致命异常和audit/coverage skipped。11次自然复核覆盖7个实例：5次impossible、5次level-tokens、1次stagnation。没有将重复出现于请求历史的marker误计为新触发。

两份真实逐题请求完成定点检查：

- r11l request第55行包含event3完整提示及动作覆盖表；第57行出现模型对复核的回应并实际MOUSE(row35,col45)。提示后11.388秒有动作，124.245秒后L2完成，最终4关。
- re86 request第65/71/101行分别匹配event0/4/6。唯一stagnation提示在第101行，第103行先做BFS计算，第105行执行65动作并完成L5。提示后75.936秒有动作、90.615秒后过关，未严格遵循“1–2步探测”字面要求。最终5关。

以上证明实际交付和后续进展，不是净提分或因果证据；最后一条tr87复核接近截止且没有后续动作，不能说11次全部有效。离线49.30与042的49.56不是同期配对试验，不据此估计组件效果。

2648B submission.parquet头尾PAR1、SHA与原offline placeholder一致；正式仍用-k/-v1运行Notebook，由gateway产生计分输出。独立新代理审核根输出和两份请求后确认没有阻塞。

提交前额度1次且无043历史记录，**10:07:54北京时间正式提交一次**：**submission57789256，scriptVersionId363656590，PENDING**。CLI成功后已从提交列表与详情确认接收，今天剩0次，尚无公开分数。最佳仍009／31.16，等待用户完成通知，无监控或重复提交。

[保存结果](../../experiments/043-save-result.json) · [提示与动作证据](../../experiments/043-prompt-action-verification.json) · [独立审核](../../experiments/043-save-independent-review.json) · [输出哈希清单](../../experiments/043-save-output-manifest.json) · [正式提交记录](../../experiments/043-formal-submission.json) · [准确版本](https://www.kaggle.com/code/jiyujia/arc3-043-inference-audit?scriptVersionId=363656590)
