# 015 采用筛选进展

日期：2026-10-17 夜启动，10-18 回包。状态：**jiyujia/arc3-015-native-adoption-screen v1 COMPLETE；21.8289→33.2937（+11.4647），13→15 关，但未过自然采用门，不进全池 A/B。** 对应[计划](../plan/015-native-adoption.md)、[决策](../../research/015-016-research-decision.md)、[结果](../../research/015-results-analysis.md)。

- 集成新增 src/arc3_research/native_values.py：成功无动作整命名空间原子提交，动作/RESET/跨关/错误/超时失效，32 名/64KiB/16 层/4096 节点，exact builtins only。prompt 只纠正短期寿命，不新增 API。
- CPU：原型 56 项 + 集成 28 项（7+21）通过；修复 NV_LIMITS 缺失与执行器 bootstrap 绑定。无模型/HTTP/引擎动作回放。
- Notebook 冻结 sha be0250cd7944，35 cells，私有/断网/RTX PRO 6000。实际 slug 为 arc3-015-native-adoption-screen，用该 slug 查状态/日志/输出。
- 正式 009/31.16 不变；本任务 OFFLINE，不提交。结果已按“两游戏自然采用”门判定未通过，不进入全池 A/B。

证据：[启动](../../experiments/015-launch.json)、[配置](../../experiments/015-native-adoption.json)、[CPU](../../experiments/015-native-values/)。

10/18深度复核补充：re86原始107→109行确认一次成功普通值复用，后续同名SH仍有失效；仍没有第二游戏采用链。ft09/ar25涨分不能归因到原生值，观察提取/程序状态及前序耗时有直接证据。见[017本地审计](../../research/017-local-evidence.md)。
