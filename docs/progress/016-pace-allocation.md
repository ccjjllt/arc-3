# 016 pace 对照进展

更新：2026-10-18。状态：**jiyujia修复轮已COMPLETE，首轮门槛未通过，不晋升、不做同版倒序、不提交。** 对应[计划](../plan/016-pace-allocation.md)、[完整结果](../../research/notes/016/016-results-analysis.md)、[当前决策](../../research/notes/017/017-research-decision.md)。

| 指标 | baseline | pace_1x |
|---|---:|---:|
| 25游戏平均分 | 47.1340 | 47.4634 |
| 加权完成覆盖 | 50.1316 | 50.3452 |
| 总关卡 | 105/183 | 111/183 |
| 全通游戏 | 8 | 7 |

差值+0.3293；去除最大正向r11l后其余24游戏均差−1.5205，未通过非单游戏支撑门。两臂各7254秒、10流、单pass，唯一策略开关PACE 0→1，TAIL均remaining。50局复算一致，冻结源码、缓存、预算、worker排空有效，客户端账本无截止后新请求、动作或过关。GPU已停止，内部会话4.2054小时；不等于平台额度账单。

原ccjjllt首轮因complete_pool仅接受won/cancelled，误拒8个正常gave_up而在baseline后停止，pace未启动；该baseline50.4234/108关不是本次配对基线。修复后队员Notebook SHA `42b0ce493418…`，两臂于北京时间10/18 01:40–05:43完成。旧[启动记录](../../experiments/016-launch.json)的RUNNING是历史状态。

证据：[新manifest](../../runs/016-pace-allocation-jiyujia/experiment-manifest.json)、[复算与门槛](../../experiments/016-analysis/comparison.json)、[时序审计](../../experiments/016-analysis/timing.json)、[冻结构建](../../notebooks/016-pace-allocation-jiyujia/build-manifest.json)。

选取的大进退游戏在首次handover前已有不同轨迹；tr87在更多slot/tokens下仍少过两关，原始轨迹另确认字形裁剪错位，不能量化其对最终分差的贡献，也不能把分数差全归调度。下一研究转为[018观察状态保真](../plan/018-observation-grounding.md)。正式009/31.16保持不变。
