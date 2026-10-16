# 012 — 计算值交接进展

日期：2026-10-13。状态：**012 v1已COMPLETE，但筛选未通过：baseline45.0764→current_data27.7582（−17.3182），51→38关/97，全通3→1。** 模型只有2次put、1次存入，0次get/context，预期的数据复用链没有发生。冻结候选不晋升、不正式提交。对应[计划](../plan/012-current-data.md)。

## 完成结果与决策

| 指标 | baseline | current_data |
|---|---:|---:|
| 13游戏等权平均分 | 45.076431 | 27.758211 |
| 完成关卡 | 51/97 | 38/97 |
| 全通 | 3 | 1 |
| 动作 | 2633 | 2356 |
| analyzer生成tokens | 2,364,169 | 2,378,190 |

26局分数由原始逐关动作数独立重算完全一致。各3772秒、源码/环境/缓存清理/独立进程和退出状态符合冻结配置；截止后动作/关卡均0。候选却有tn36/lf52两次新模型请求在截止后约0.6秒发出，未产生后续动作，作为取消边界问题单独保留。不是运行崩溃，也不能把全部退分归因新API。[结果复算](../../experiments/012-analysis/comparison.md)、[独立复核](../../experiments/012-results-review.json)、[计时报告](../../research/012-timing-analysis.md)

唯一使用者ft09第一次保存list[tuple]被拒绝；第二次在action28后存入181字节候选解，下一模型段承认选错组合，手写更正并行动，没有get。成功写入后到下一段之间尚无动作，不能说失效过早阻止读取。其余12局含cd82全零调用。[采用分析](../../research/012-intervention-analysis.md)

实际北京时间17:21:25→19:37:28，8162.91秒（2.26747h），model-ready560.59秒，GPU服务已停止。共享余额已为0h，10/17 08:00北京刷新；账户同时存在其它新作业，余额变化不等同012耗时，不作计费分摊。[完成记录](../../experiments/012-completion.json)、[配额快照](../../experiments/012-quota-after.json)

**停止当前版本扩跑，正式基线保持009/31.16。** 后续先以最小真实模型试验验证采用，再进入完整多游戏A/B；CPU检查不能替代模型主动读取与消费的证据。不因一次tuple拒绝就假定放宽类型可提分，也不强行把错误假说变成持久事实。[综合结论与下一步](../../research/012-results-analysis.md)

## 工程与CPU证据

模块[current_data.py](../../src/arc3_research/current_data.py)已冻结为`0d6f825d65cb091203e590cc6777d402f5cf1a6fa5cdd3b92f3d0c5f29f05c4c`。接口为`current_data.put/get/context`，仅独立current_data臂安装；未叠加未获晋升的010动画。

- [真实SDK与sandbox最终检查](../../experiments/012-current-data/cpu-20261013T083909Z/summary.json)：53项通过（含基础通信检查，并非53个独立游戏）。覆盖值精确复制、跨snippet、普通变量仍不持久、原函数保留、两个真实session隔离、无操作动作、实际RESET和ft09实际L1→L2后失效、旧绑定拒绝，以及真实硬超时后已确认值保留（请求0.5秒，底座最小执行限1秒）。HTTP请求和模型调用为0。
- [72项受控检查](../../experiments/012-current-data/module-checks/report.json)：默认容量、严格JSON、复制隔离、128会话淘汰不复活、画面完全相同但动作数增加的失效、A→B→A不复活、异常/计时故障下原动作返回与异常identity保真。人工carrier和真实类wrapper，不冒称真实SDK动作或并发压力。
- [两病例最终比较](../../experiments/012-current-data/check-cases/comparison.json)：cd82程序算出30像素/bbox，后续snippet直接得到9×14；ft09从分割结果算出逻辑列2并索引回原位置。baseline纯函数重算、候选计算、host确认及get四方hash一致。[病例说明](../../research/012-current-data-cases.md)

早期CPU目录保留开发记录：第一次使用sandbox不允许的globals导致探针失败；第二次把游戏报告no-op误当完整画面不变（HUD会变）；首次超时探针被禁止import time而实际只是普通异常。最终版本分别修正为直接名称检查、真实no-op与受控同帧分开验证、while循环触发明确`Tool timed out after 0.5s`（文案为请求值，实际底座最小限1秒），并在首个stored响应后发送第二写入作为确认已消费的证据。不能把早期通过项数当最终超时证据。

CPU只证明通道保真，没有模型自动采用、策略纠错、token节省或提分证据。没有生产并发压力、真实死亡自动RESET或长期RSS验证；已取回的Python局部别名不会自动失效。

## 打包与试验前设计（历史记录）

原生Notebook29 cells、22代码cells、13个helper经真实IPython写出后hash匹配，继承patch正文与末尾LF校验通过，无新增exec/compile/eval外壳。SHA256：`6789f075141fb81cd82b958eb8a851a726720c231efd4d99d477fd78c72dd7dc`。[Notebook核验](../../experiments/012-notebook-checks.json)

新13游戏A/B配置已准备：baseline→current_data，各3772秒，预计2.3h、硬限9900秒，两臂相同计时。相比011只为新候选加入cd82病例，未调整调度。下一轮要回答模型是否实际使用以及是否有净关卡收益；正式基线仍保留009/31.16。

## 上传与远端核验（历史记录）

初次上传命令被自动审批在进程创建前拒绝，要求明确授权012上传及共享GPU使用。用户答复“授权上传并启动012”后执行成功，返回Kernel version1。没有绕过审批或占用正式比赛submission名额。

[私有012 Notebook](https://www.kaggle.com/code/ccjjllt/arc3-012-current-data)已回拉，29个cell类型和正文与冻结版本一致，私有/GPU/断网/RTX PRO 6000配置正确；远端docker_image_pinning_type返回null，不能据此声称实际镜像pin已核验。启动前共享余额3.29h。[启动记录](../../experiments/012-launch.json)、[远端源码比对](../../experiments/012-remote-source-check.json)、[独立审查](../../experiments/012-current-data/review.json)、[冻结源码](../../experiments/012-source/source-hashes.json)

16:56时读取平台状态仍为QUEUED，当时尚未确认实际GPU分配或模型health。排队期间日志stream接口返回HTTP500，本地读取器已退出；这不是Notebook执行失败的证据，也没有取消远端作业。现已由完成产物确认两臂实际执行结束。[当时启动核验](../../experiments/012-launch-validation.json)
