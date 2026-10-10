# 004 — 观察证据使用：四游戏综合归因

日期：2026-10-11（Asia/Shanghai）。范围：003 已完成的 baseline 与 goal_evidence 在 **su15、tn36、lf52、sk48** 的请求轨迹。未启动 GPU，未读游戏引擎源码。逐游戏笔记：[sk48](004-trace-sk48.md)、[lf52](004-trace-lf52.md)、[su15](004-trace-su15.md)、[tn36](004-trace-tn36.md)。规格：[004 计划](../docs/plan/004-observation-evidence.md)。

独立复核：从 compact JSON 重计 `last_animation_timeline` / `last_animation_frames` / user cue 次数，并抽查过关动作、NO-OP 后的暂态句、su15 环推动推理、tn36「bars are the program」推理。sk48 B5 的「N flickered」就在 compact `analysis_step=13 action=41` 的 reasoning 里，同轮 user 已给 8 格 bbox；下一轮 LEFT 后 N 从 `(37,42)` 到 `(37,36)`，图例仍 False。结论（未读 timeline、目标仍绑图例）成立。

## 决定

**不实现 `observation_evidence`，不构建 004 Notebook，不 push GPU。** 四局都没有规格要求的那种反复出现、且靠「把局部时序事实塞进现有 Python 工具返回」就能改过关结果的可见转移缺陷。下一轮 GPU 更符合 004 表中的 **25 游戏单遍 baseline**（约 2.17h / 硬限 2.5h），用来补全公开能力与失败分布。执行前重查配额。

保留 baseline。003 的 goal_evidence v1 仍不晋升、不原样重跑。

## 三阶段对照

阶段 1 = 动画 API / 用户提示已经提供；阶段 2 = 代码真正读了 `last_animation_timeline` 或 `last_animation_frames`；阶段 3 = 随后假设因这些帧而更新。`frame_diff` 比较结算帧，不算阶段 2。

| 游戏 | 分数 A→B | 关 A→B | 阶段 1 user cue A/B | 阶段 2 `last_animation_*` A/B | 主要失败 |
|---|---|---|---:|---:|---|
| sk48 | 1.37→0.00 | 1→0 / 8 | 18 / 13 | **0 / 0** | 目标假设（图例/HUD）+ 动力学（L2 sim）+ 预算 |
| lf52 | 7.73→10.91 | 3→3 / 10 | 38 / 48 | 5 timeline+0 frames / 4+2 | L1 会读帧；L2 后吃 user cue；L4 相机/目标 + 预算 |
| su15 | 62.22→13.33 | 7→3 / 9 | 62 / 51 | 4+3 / 19+2 | 阶段 2 已密；分差是单次路径分叉 + 预算 |
| tn36 | 13.76→3.57 | 3→1 / 7 | 42 / 17 | 4+43 / 9+28 | 阶段 2 很密；L2/L4 指令映射 + 预算 |

有暂态时，**下一轮 user 提示已经写出**帧数、changed-and-changed-back 格数、bbox，并点名 `last_animation_timeline`。`action()` 字典里也常有 `animation: {frames, transient_pixels, transient_bbox}`，模型经常只打印 `no_op` 或把它滤掉。这是规格里「已经提供动画 API/提示」，不能再包装成新能力。

## 候选假设为何不成立

规格候选：最终帧变化很小、中间动画有额外信息时，把紧凑局部时序事实放进**现有 Python 工具返回**，可能比要求模型主动查询更容易被采用。

实际轨迹：

1. **通道已经存在。** 与候选同级的 bbox/格数/帧数已经在下一轮 user 提示里。tn36 / lf52 的 RUN 或 shake 还会写 “left the board area unchanged, but it was not a no-op”。再把同一句话塞进 stdout，是换通道重复阶段 1。
2. **sk48 是阶段 2=0 的游戏，也不是正例。** 它从不调用 `last_animation_*`。有暂态时 user 句仍在发；模型有时引用 bbox，有时忽略，过关靠结算帧上的贯穿。缺的是图例/HUD 目标定义，004 禁止替模型宣布胜利规则。把 bbox 从 user 复制到 stdout 不会变成读帧。
3. **会读帧的游戏，失败在阶段 3。** su15 用 `last_animation_frames` 推出环推动色块；tn36 用逐帧位移推出 RUN/程序条。之后卡在粉环追逐、字形→运动、预算。goal_evidence 的 su15 甚至读得更勤（21 次 vs 6 次）却少过 4 关。
4. **NO-OP 标签 vs 暂态** 在 lf52/tn36/su15 反复出现，但下一轮 cue 已被用来纠正「不是空操作」。列出的 episode 没有一格会因为工具返回里多一段逐步 `old>new` 而改过关集合。
5. **su15 大分差不是干预效应。** 两边都 `cancelled`。GE 在第 2 关耗尽底栏 RESET，停在第 4 关；baseline 用更短路径到第 8 关。规格写明单次差异不能当成提示导致下降。

因此：不为凑实验实现该候选，也不再加「请看动画」。

## 若以后仍改工具返回，轨迹只给量级

不作为本轮实现依据：

- 局部 shake / 环：约 3–6 帧，8–48 或 ~113 格。
- 拒绝闪烁：约 13 帧，~120–155 格。
- 通关/滚屏/钥匙入场：数百到 3568 格，不要注入。
- 已有 `animation` 摘要不够区分「只有环」和「环带着物体」；有区分力的逐步位移，模型在关键步已经自己 `print`。
- 不要改 `no_op_action` 截断，那是另一条干预。

## 下一 GPU

004 表两条不同时做。本轮没有「已有具体观察遗漏证据、候选策略准备好」的 12 游戏 A/B 条件。剩下 9 个公开游戏从未用本项目 launcher 跑过。**优先 25 游戏单遍 baseline**，硬限 2.5h，沿用 003 的共享加载、独立 CPU 进程、warmup RESET 关闭、10 路活跃。目标是公开失败分布，不是验证未实现的观察摘要。
