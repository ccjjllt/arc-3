# 018 派生证据（只读分析）

输入实验：`018-observation-grounding`；4 游戏，baseline → observation_grounding，每臂 1000 秒。

描述性 ΔAE=-3.227930，Δ覆盖=-2.976190，Δ关卡=+0。采用状态：`review_supplied`。

逐关复算、cap 修正及单局贡献在 comparison.json；工程检查在 validation.json；严格窗口 GPU 样本在 gpu-phases.json；deadline/调度在 timing.json；缓存和服务记录在 server-cache.json。

trajectory-index.json 指向每局去重调用原文和原始日志哈希/行号。导航标签只帮助定位，不是采用。复制 review-template.json 到独立文件，人工填写观察→编码→消费与具体纠错证据，再用 --reviews 读取；分数变化与采用门始终分开。

未执行模型、游戏、SDK、pickle 或日志代码；未调用网络/GPU。无直接CPU忙时数据。单次开发集结果不能证明隐藏分数或因果收益。
