# 005 — 全25游戏单遍基线与失败分布

日期：2026-10-11（Asia/Shanghai）  
对应进展：[005-full-baseline](../progress/005-full-baseline.md)。  
继承：[003结果](../progress/003-next-experiment.md)、[004归因](../progress/004-observation-evidence.md)。

## 研究背景与目标

004在CPU上检查了四个游戏，没有建立足够证据支持立即追加观察摘要补丁。复核发现压缩工具在上下文裁剪时漏消息，以及文档存在未经实验支持的“不会改变过关”表述；修复后仍保留“不为证据不足的候选消耗GPU”的资源决策，不把它升级为候选已被证明无效。

本轮选择25游戏单遍baseline，补齐此前未用本项目launcher运行的9个游戏，并取得完整25游戏共享调度池的失败分布。这是新工作负载的基线画像，不是验证004候选无效，也不是003的严格重复。

研究问题：

1. 原基线在全部25游戏/183关上实际完成哪些关卡、哪些机制仍卡住？
2. 新增9个游戏的瓶颈是否与四个深读游戏不同，能否提出更有价值的机制假设？
3. 在完整调度池、修复多余RESET后，得分、覆盖、动作和推理预算如何分配？

## 实验配置与预算

配置：[005-full-baseline.json](../../experiments/005-full-baseline.json)。

- 所有游戏使用下载清单中的完整版本ID，不只依赖短前缀。
- 单组`baseline`，每游戏1遍；不启用goal_evidence或observation_evidence。
- 沿用原版模型、量化、SGLang/Pennyroyal、上下文、优先级调度和10路active streams。
- solver预算为`532*60*25//110 = 7254`秒，约120.9分钟。
- 整个Notebook硬上限9000秒（2.5h），按上次启动实测估计约2.2h。只加载一次模型，结束后关闭服务。
- 配额查询时剩余24.5969h；即使达到硬上限，本轮之外仍约22.0969h，实际以账户最新计费为准。原始快照：[005-quota-before.json](../../experiments/005-quota-before.json)。
- 本轮是私有公开集研究Notebook，不消耗正式比赛提交次数，不读取隐藏环境。

新增9个游戏：cn04、dc22、ka59、re86、s5i5、sb26、sp80、tr87、vc33。结果分别报告全25、原16、新9；不同调度池下的原16只能描述性对照，不能把分数差全归因于RESET修复。

## 实际需要修改的代码

1. `scripts/build_experiment.py`：显式`--config`，以实验ID产生新目录和Kaggle slug；单组/多组summary输入动态生成，不能覆盖003。
2. `src/arc3_research/session_runner.py`：预算除以实际arm数量，保留清理余量；新增轻量后台10秒GPU采样，覆盖加载、解题、收尾，不只记录解题阶段。
3. `src/arc3_research/run_arm.py`：继承003分析后已做的研究模式warmup RESET关闭；baseline分支保持目标干预关闭。无需另写算法。
4. 生成`notebooks/005-full-baseline/`，保存构建hash、原始来源和配额快照。推送硬限9000秒。

## 手动执行与观察

人工核对Notebook metadata、25个版本、7254秒单组预算、9000秒硬限和保留的底座源码；不新增测试文件。

运行时看加载/服务是否成功、是否确实进入25游戏baseline；将异常与真实低分分开。结束后取回benchmark、arm metadata、服务日志与GPU采样；汇总保留action-history、analyzer、server三种tokens口径，不能将未跟踪字段0当成无消耗。

得分、完成权重、关卡/游戏覆盖是主要结果；GPU utilization与吞吐只判断资源利用。对新的瓶颈人工读代表性轨迹，再决定下一轮实现。一次公开集运行不能证明隐藏泛化或获得奖牌。

## 接手者必须继承的结论

- 003的目标反证提示没有触发，初始指导版未晋升，不能据此判反证机制无效。
- 004已有N帧/格数/bbox提示不等于完整时序事实；“已经提供API”“代码引用API”“执行成功并更新假设”应分开。
- 历史裁剪后的完整新compact以`runs/004-reviewed-compact/`为准；旧compact保留为研究原件，计数与反事实结论已经修正。
- 单次路径分叉无法区分初始指导影响、生成随机性、调度和运行差异；保留负结果，不择优删游戏。

结果写同名progress，分开记录代码完成、运行完成与效果结论。
