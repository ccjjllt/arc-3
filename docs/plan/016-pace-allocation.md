# 016 pace 单开关方案

日期：2026-10-17。与 015 并行，互不挤占配额。不占正式提交。

25 游戏沿用 005 顺序，baseline remaining/0 vs pace_1x remaining/1，各 7254s、10 流、1 pass、warmup0。配置见 experiments/016-pace-allocation.json。

共用一次模型加载，分开 CPU 进程，组间 cache flush，硬限 18000s、启动上限 1200s。诊断与 deadline 两臂相同。

首轮门槛：均分与加权覆盖为正、总关不降、至少两游戏新增关、非单游戏支撑。失败即不倒序、不晋升；通过才评估 tail→baseline 式倒序（pace→baseline）。
