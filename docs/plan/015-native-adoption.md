# 015 原生值采用筛选方案

日期：2026-10-17。承接 013 采用门槛与 015 原型 56 项、完整集成 28 项 CPU。只做小规模自然采用筛选，不占正式提交。

固定 4 游戏 ft09/re86/bp35+ar25 控制，baseline→native_values 各 1000s、10 流、1 pass、warmup0，调度冻结 remaining/0。配置见 experiments/015-native-adoption.json。

两臂共用一次模型加载，分开 CPU 进程，组间 cache flush 确认。硬限 5400s、启动上限 1200s；启动挤占即停，不缩短比较。被动 timing/scheduler/deadline 诊断两臂相同。

衡量：原始 benchmark、native-values.json（commits/字节/拒绝/CPU）、request 日志自然“计算→原名消费”链、正确重算一致性、陈旧误用、GPU 采样。至少两个非同游戏自然采用且可审，才考虑全池 A/B；否则停止。4 游戏结果不宣称提分或隐藏泛化。
