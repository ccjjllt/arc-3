# 007 — 代码状态保留：实现与运行进展

日期：2026-10-11（Asia/Shanghai）  
对应计划：[007-program-state](../plan/007-program-state.md)。  
状态：**007 v2已COMPLETE，两组完整跑完。baseline 46.3578分/51关/4全通；program_state 40.3235分/50关/2全通。实际保留并复用旧函数已确认，但单次A/B均分−6.0343，不晋升。**

## 研究已完成

005 tr87、006 baseline ar25与transient_history ar25分别有34/39/15个已保留函数在硬超时后被清空。底座未收到keepable_functions时用缺省空列表替代，再提交空函数集合。

这与普通Python异常不同：普通异常可返回有效namespace快照，执行过的新定义/删除应该保存。007仅区分缺键与有键，不把所有error都回滚。见 [研究与源码结论](../../research/007-program-state-design.md)。

## 代码完成

- 新增src/arc3_research/program_state.py，缺少keepable_functions时保留已有函数源码及附属import；有该字段时一律遵从原逻辑，包括合法空集合、有效异常快照、显式删除。
- 在提交点处理，不在tool结束后盲目恢复；原level/session作用域清理继续生效。不保留普通变量，不回滚真实游戏动作。
- 工具反馈明确本次失败调用的新定义/替换/删除未保存，原函数集合仍在。run_arm新增program_state独立组及program-state.json诊断。
- 不启用goal_evidence或transient_history，不改模型、serving、调度、deadline。

## 实际手动核对

真实隔离sandbox（无模型、无游戏动作）：先保存f/g及math import，再在尝试新定义后触发1秒timeout；修复组仍保留旧源码，下一sandbox调用g(2.9)=6，snippet变量未保留。正常del删除依赖链；普通ValueError附有效snapshot仍提交新定义；关闭补丁恢复原清空行为。

scope边界使用人工构造summary调用原方法核对，不能当作真实游戏重置复现。源码审查确认动作结果及dispatch仍走原路径。结构化证据：[007-manual-checks.json](../../experiments/007-manual-checks.json)。没有新增测试文件。

## Notebook与GPU启动

实际运行v2 Notebook为655880 bytes，SHA256：`e40a71efab35f5cd35832b8e853e68be4091675a0c5206dc258b29dc28614f17`。Kaggle COMPLETE、manifest completed，两组exit_code=0。固定12游戏、各3482秒、10路活跃、共享一次模型加载，Notebook硬限9000秒。嵌入源码全部与运行manifest一致，归档于[007-source](../../experiments/007-source)；启动与完成记录见[007-launch.json](../../experiments/007-launch.json)。这是公开环境的私有研究结果。

北京时间15:28:17的[v2推送后配额快照](../../experiments/007-quota-after-v2-push.json)为已用53183.6秒、预留0、余额15.2267778h。这是全账户余额，不等同于本次重试已经使用的GPU时长。

### v1失败与CPU输入诊断

v1曾成功推送，15 cells、651048 bytes，SHA256：`10e7f93b50c01b57e349b53f69d9b132b9a30e9f9311740f8107cd0b0609e2d1`。北京时间15:16:38的CLI状态为`KernelWorkerStatus.ERROR`。已取回的日志显示：运行约11.54秒时cp找不到canonical bundle路径，约11.89秒报FileNotFoundError，模型尚未加载，两组求解均未开始。日志保留于[runs/007-program-state-v1](../../runs/007-program-state-v1)，原Notebook保留于[experiments/007-attempts/v1](../../experiments/007-attempts/v1)。003/005/006历史原件未覆盖。

随后CPU diagnostic v1确认canonical原路径实际存在。CPU diagnostic v2使用本次准确的input_paths.py定位器，状态COMPLETE，全部输入包括model/draft index均通过，定位耗时0.030654496秒。结果见[input-paths.json](../../runs/007-input-inspection-v2/input-paths.json)。这是CPU输入可见性检查，不是模型加载或GPU求解结果；首次GPU运行缺失文件的原因仍未知，不能把后续成功检查解释为路径迁移。

新增src/arc3_research/input_paths.py按实际存在的文件定位输入，最多等待60秒。v2实际2.868秒找到扁平的dataset/competition路径，模型仍在嵌套路径，见[input-paths.json](../../runs/007-program-state/input-paths.json)。这与CPU检查布局不同，说明固定路径不可依赖；v1没有目录清单，不能据v2反推v1完整布局。构建器仅修改setup及5处路径引用，研究补丁、预算、serving/调度/deadline和大patch不变。模型789.94秒ready，随后两组完整执行。

v1推送前已重新核实以下两个其它项目Notebook均为COMPLETE。北京时间2026-10-11 15:15:40配额快照为已用53167.042秒、预留0、余额15.2313772222h（约15.23h），见[启动配额原件](../../experiments/007-quota-at-launch.json)。不能把这份全账户快照与此前余额之差归为007消耗，也不能将它当作v2的实时余额。

### 此前并发拒绝历史

首次尝试前的快照曾显示：已用37398.014769秒、余额19.61166h（未扣预留）、另有86184.393615秒即23.9401h预留。当时CLI确认以下其它项目Notebook为RUNNING：

- ccjjllt/arc2-011-s0-shared-model
- ccjjllt/p005-t0-single-state-pair

预留不是实际消费，也不能据此断言额度已经用完。本轮未停止或修改这些任务。用户当时选择并行启动007，但实际push返回`Maximum batch GPU session count of 2 reached`，没有成功启动；用户随后选择“保留就绪版本，稍后再启动”。该次失败记录见[007-launch-attempt.json](../../experiments/007-launch-attempt.json)，当时配额见[007-quota-before.json](../../experiments/007-quota-before.json)。这一暂缓状态已被用户本次“现在可以提交了”的明确指示取代；本次在确认空位后，按上述相同Notebook哈希成功推送v1。准备/启动记录由[007-preparation.json](../../experiments/007-preparation.json)及对应启动记录保存，未启用自动监控。

## 实际研究结果

| 指标 | baseline | program_state |
|---|---:|---:|
| 平均分 | 46.3578 | 40.3235 |
| 完成关卡 | 51/89 | 50/89 |
| 全通游戏 | 4/12 | 2/12 |
| Analyzer tokens | 2,107,894 | 2,159,836 |
| 预算内GPU利用率（时间加权） | 92.12% | 94.94% |

两组预算、ID/顺序、模型/环境/代码来源均核对一致，CPU进程隔离、cache flush成功。24条分数按原始动作数独立重算一致；deadline后真实动作/关卡均为0。每组只有1遍，公开诊断集、固定A先B后、共享调度，不能给显著性或因果提分结论。

候选3次缺失快照：re86首次0函数；ls20保21函数；re86后一次保17函数。3条反馈均进入下一模型请求。ls20立即复用旧函数，随后action334完成L3，但基线更早通过且总关卡更多；re86复用旧lines/Wpos成功，仍停在L6。代码完成与实际复用已验证，净研究效果未提升。baseline诊断为空是关闭补丁的设计，不代表没有timeout。

最大回退为零直接触发的tr87/sc25，合计均分贡献−9.0085；全部12游戏实际净差−6.0343。不能将零触发分差直接归因补丁，也不能把有触发分组当作随机因果对照。详细轨迹见[触发报告](../../research/007-intervention-analysis.md)。

会话7812.59秒（2.1702h），北京时间15:33:26—17:43:39，已关闭GPU服务。启动13.17min主要为权重加载；B整体输出和GPU利用率更高，不能用整体算力不足解释回退。账户快照余额11.6736h、预留0；全账户差额3.5532h不能当成本轮消耗。

产出：[逐游戏与结果解释](../../research/007-results-analysis.md)、[可复算comparison.json](../../experiments/007-analysis/comparison.json)、[效率报告](../../research/007-efficiency-analysis.md)、[配额原件](../../experiments/007-quota-after.json)。本次结果分析未运行新GPU作业，也未新增测试文件。

## 后续方向

007保留为独立候选，默认仍为baseline。本轮还定位tr87 L2的表示错误：B约2336.6秒/103237 tokens，A约213.8秒/14460 tokens。应优先在已保存帧上核对裁剪边界、符号编码和类别坍塌，再设计局部的观察证据辅助；不是立即重跑同配置。见[具体病例与下一方向](../../research/007-next-direction.md)。

下一轮交接已写入[008-observation-representation](../plan/008-observation-representation.md)。当前仅完成计划，尚未实现008候选或启动GPU。
