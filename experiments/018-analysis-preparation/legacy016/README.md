# 018 派生证据（只读分析）

输入实验：`016-pace-allocation-jiyujia`；25 游戏，baseline → pace_1x，每臂 7254 秒。

描述性 ΔAE=+0.329342，Δ覆盖=+0.213564，Δ关卡=+6。采用状态：`not_applicable_legacy_fixture`。

逐关复算、cap 修正及单局贡献在 comparison.json；工程检查在 validation.json；严格窗口 GPU 样本在 gpu-phases.json；deadline/调度在 timing.json；缓存和服务记录在 server-cache.json。

trajectory-index.json 指向每局去重调用原文和原始日志哈希/行号。导航标签只帮助定位，不是采用。复制 review-template.json 到独立文件，人工填写观察→编码→消费与具体纠错证据，再用 --reviews 读取；分数变化与采用门始终分开。

**本目录仅为旧实验兼容演练，不是018结果。**

未执行模型、游戏、SDK、pickle 或日志代码；未调用网络/GPU。无直接CPU忙时数据。单次开发集结果不能证明隐藏分数或因果收益。
