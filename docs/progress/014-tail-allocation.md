# 014 全25调度对照进展

日期：2026-10-17。状态：**jiyujia/arc3-014-tail-allocation v1已COMPLETE；47.1991→48.6390（+1.4399），110→108关、7→8全通。加权完成覆盖下降，未通过晋升门槛；不提交当前tail、不启动同版倒序确认。** 对应[计划](../plan/014-tail-allocation.md)、[结果分析](../../research/014-results-analysis.md)。

## 完成结果与下一步

22:06北京CLI核实COMPLETE，50局得分独立复算一致。两臂25游戏版本/顺序、7254秒预算、10活跃流、共用源码一致，唯一环境差异为tail开关；缓存backend确认两次、独立CPU进程、无遗留worker，最终GPU服务进程组已停止。

- 平均AE：47.1991428→48.6390449；覆盖上限50.7665224→50.4649351；110→108/183关。11游戏得分上升、7持平、7下降。
- 最大正向vc33贡献均值+3.1611，去掉该局后其余24游戏差−1.7929；当前正差不能作为稳定提分或隐藏榜预测。
- GPU求解均值92.80%/92.91%，中位数均99%；无截止后动作或客户端新chat/HTTP，但baseline服务端有两条截止后约0.079/0.552秒入队，明确保留此边界。
- 当前正式57101330仍为31.16，未新建submission。014是公开集OFFLINE研究入口，不能直接作为正式提交。下一步先完成015完整ToolAgent/SDK的CPU集成，再视合同结果决定最多1h自然采用筛选。

证据：[复算JSON](../../experiments/014-analysis/comparison.json)、[逐游戏表](../../experiments/014-analysis/comparison.md)、[时间/资源审计](../../experiments/014-timing-analysis.json)、[完成快照](../../experiments/014-completion.json)、[审查结论](../../experiments/014-results-review.json)。原始选择性下载产物在`runs/014-tail-allocation/`；本次分析没有执行日志中的代码或读取pickle。

## 实现与检查

- 显式、受限的arm_environment覆盖在harness导入前生效；baseline=remaining、tail=1，PACE0。动态policy在真实harness preflight中已核对。
- deadline补丁36项真实harness/人工反馈检查通过；调度observer18项真实gate/线程检查通过；session runner49项受控流程检查通过。
- 完整三补丁preflight通过，无网络/模型/动作，逆序卸载恢复原函数。完整harness CPU验证使用本机Python3.13；Notebook/IPython打包验证用3.12，不能据此声称远端依赖已运行验证。
- 原生Notebook 34 cells、27代码cells、17个helper经真实IPython写出hash匹配，继承patch正文一致、git apply stat通过。
- 已修复原stop_group只看leader退出的清理盲点；50项真实人工进程组检查通过，覆盖孤儿子进程、忽略TERM后KILL、旁路进程不受影响和重复清理不再发信号。[清理记录](../../experiments/014-cleanup-checks.json)。

机器证据：[deadline](../../experiments/014-deadline-checks/report.json)、[scheduler](../../experiments/014-scheduler-checks/report.json)、[session](../../experiments/014-session-checks.json)、[preflight](../../experiments/014-preflight-checks.json)、[Notebook](../../experiments/014-notebook-checks.json)。

## 资源

原账号早期准备时GPU余额约29.31h、预留0，此次改用真实队员jiyujia账号。队员17:04北京启动前额度30h、已用0、预留0；17:08排队时仍未使用或预留GPU。刷新时间10/24 08:00北京。本轮预计4.3h，平台硬限5h，两组共用一次模型启动。余额为全账户快照，不按其它作业消耗分摊。[队员启动前配额](../../experiments/014-jiyujia-quota-before.json)、[最新状态快照](../../experiments/014-jiyujia-status.json)、[原账号历史快照](../../experiments/014-quota-before.json)。

完成后实测：会话内部15132.38秒（4.2034h），模型就绪533.74秒；账号已用17245.729秒（4.7905h）、预留0、剩余25.2095h。额度与内部时钟差约35.22分钟，未核实该差额归属，不将其全算成模型加载或平台开销。

## 并行的015

原生普通值交接已完成独立CPU原型：56项人工合同、16次真实sandbox子进程检查通过。尚未完整ToolAgent/SDK集成，也没有模型采用或提分证据；不进入014Notebook。[015说明](../../experiments/015-native-values/README.md)。

014完成结果已追加到本文件，正式009保持不变。当前版本不启动确认轮。

## 上传审批历史

冻结Notebook SHA256为`5c473c7a1a54d05169f9ea3f5d06808229ac9f99fba097c7662683e0b6b7f3d2`，35份源码/检查产物已归档于[014-source](../../experiments/014-source/source-hashes.json)。自己的Kaggle Notebook搜索未发现同名014。上传命令在进程创建前被自动审批拒绝：实验运行授权已被识别，但源码上传到第三方的授权不够明确。已向用户提出针对这份冻结私有Notebook的上传/启动授权问题；没有通过其他接口重试或绕过。见[拒绝记录](../../experiments/014-launch-blocked.json)、[导出结构检查](../../experiments/014-export-review.json)。

## 队员账号实际启动

随后用户确认是真实队员账号，保存token后明确要求：“我加好了你看看，然后用队员的账号训练吧。” CLI验证ACCESS_TOKEN对应用户名jiyujia；同名Notebook不存在，配额充足。此次标准CLI push通过审批并返回v1上传成功；早期拒绝记录保留为历史，不再是当前阻塞。

- 实际Notebook：[jiyujia/arc3-014-tail-allocation](https://www.kaggle.com/code/jiyujia/arc3-014-tail-allocation)，id_no 139197335，v1。
- 上传目录：[014-tail-allocation-jiyujia](../../notebooks/014-tail-allocation-jiyujia/kernel-metadata.json)。仅外部metadata.id改为队员账号；Notebook正文及冻结hash不变。内嵌config的原kernel_id只作来源记录，求解代码不读取它。
- 远端回读的34个cells与本地正文一致（按CLI规则合并source行数组、清空outputs后比较全部Notebook字段）；附件、私有、断网与RTX PRO6000机型一致。[远端核验](../../experiments/014-jiyujia-remote-check.json)、[启动记录](../../experiments/014-jiyujia-launch.json)。
- 17:08北京状态QUEUED，无失败信息、无日志、GPU已用/预留0；这还不是模型成功加载或两臂完成的证据。

凭据继续存于用户目录，不写入仓库。后续操作直接用原生CLI按命令选择队员token：

```bash
KAGGLE_API_TOKEN="$HOME/.kaggle/access_token_teammatea" kaggle kernels status jiyujia/arc3-014-tail-allocation
KAGGLE_API_TOKEN="$HOME/.kaggle/access_token_teammatea" kaggle kernels logs -f jiyujia/arc3-014-tail-allocation
```
