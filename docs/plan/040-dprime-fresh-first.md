# 040：在009固定环境中改变逐题算力分配

2026-10-26。038原样v83正式27.73，低于009的31.16，且核心正式代码相同。本轮把候选改为实质调度变化，沿用009准确v2源码、Docker、模型、提示、采样、10streams、31920秒逐题预算和正式gateway。

唯一研究改动是公开D-prime的priority公式、逐关平均生成tokens的pace及0.4尾段fade。保留009原fresh-first：不替换`_PriorityGate.acquire`或`_HarnessGameSession.play`。公开fresh定价存在正常输入下长期压过新题的排名反例，本轮不引入它，也不加入新aging、停题阈值或其它接口小修。

CPU检查要覆盖公式与公开实现一致、实际runtime模块别名、安装/解除、真实gate竞争与fade；不能把CPU过关当作涨分。Notebook以普通源码单元交付，新增helper在benchmark恢复后、任何session创建之前安装。GPU保存检查沿用sb26/cd82各300秒真实推理与动作，并保存scheduler安装/完成快照；两题短测无法代表110题竞争。

本轮jiyujia GPU余额23.20h，zhuating7.48h；团队正式额度0。选择jiyujia启动一次必要GPU保存检查。保存通过、准确版本核验及提交额度可用后，正式验证一次。当前最佳009保留；不设置自动监控，按用户完成通知读取结果。

[配置](../../experiments/040-dprime-fresh-first.json) · [来源绑定边界](../../research/notes/040/040-scored-version.md) · [独立算法审查](../../research/notes/040/040-dprime-audit.md)

实际执行：21:41北京时间，jiyujia v1已启动GPU保存，14项远端核验通过；准确SHA及等待完成通知的后续动作见[进展](../progress/040-dprime-fresh-first.md)。

22:21结果更新：保存passed／平台COMPLETE；sb26完成4关，cd82为0关。pace2实例/4更新，priority_calls0，短测尚未验证调度重排收益。独立复核32项通过，保留准确v1等待团队正式额度，继续以进展记录为准。
