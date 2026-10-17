# 015 采用筛选进展

日期：2026-10-17 夜。状态：**jiyujia/arc3-015-native-adoption-screen v1 RUNNING；完整集成 28 项 CPU 已通过，GPU 采用结果未回。** 对应[计划](../plan/015-native-adoption.md)、[决策](../../research/015-016-research-decision.md)。

- 集成新增 src/arc3_research/native_values.py：成功无动作整命名空间原子提交，动作/RESET/跨关/错误/超时失效，32 名/64KiB/16 层/4096 节点，exact builtins only。prompt 只纠正短期寿命，不新增 API。
- CPU：原型 56 项 + 集成 28 项（7+21）通过；修复 NV_LIMITS 缺失与执行器 bootstrap 绑定。无模型/HTTP/引擎动作回放。
- Notebook 冻结 sha be0250cd7944，35 cells，私有/断网/RTX PRO 6000。实际 slug 为 arc3-015-native-adoption-screen，用该 slug 查状态/日志/输出。
- 正式 009/31.16 不变；本任务 OFFLINE，不提交。回包后按“两游戏自然采用”门判是否进入全池 A/B。

证据：[启动](../../experiments/015-launch.json)、[配置](../../experiments/015-native-adoption.json)、[CPU](../../experiments/015-native-values/)。
