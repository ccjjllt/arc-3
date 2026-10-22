# 003 — 真实 A/B 结果与测量核查

分析日期：2026-10-11（Asia/Shanghai）。这份分析只读取已经完成的 Kaggle 003 输出，**没有启动新 GPU 作业**。每组是同一批 16 个公开开发游戏的单遍结果，不是比赛隐藏集成绩，也不是独立重复实验。

## 结论

本轮 baseline 为 **49.2502 分、72 关**，goal_evidence 为 **46.8783 分、68 关**，后者低 **2.3719 分、4 关**。两组均完整通过同样的 5 个游戏。

更重要的是，goal_evidence 实际只记录了 16 次 guidance、1 次 marker report，且该 marker 被帧匹配检查拒绝；**frame_validated、feedback_validated、nudge 都是 0**。本轮实际检验的是“增加目标指导文字、模型极少主动报告目标”的实现，而没有观察到计划中的短反证反馈被执行。因此，不能把分数变化归因于反证提示，也不能据此断言目标反证研究方向失败。

总分差对单个游戏敏感：su15 从 7 关下降至 3 关，单游戏低 48.8889 分，对 16 游戏均值贡献 -3.0556 分。仅作敏感性分析，去掉 su15 后其余 15 个游戏均值差变成 +0.7292；**正式结果仍保留全部 16 个游戏的 -2.3719 分，不能删除失败游戏后宣称提升**。

不建议原样扩大此版本。唯一marker的完整轨迹已确认它回顾已完成的上一关，当前帧已进入下一关，拒绝正确，**没有帧绑定故障**，详见[触发复盘](003-intervention-postmortem.md)。下一轮应重新研究信息如何进入模型的实际工作流，并补齐诊断与尾部token观测；不放宽正确的拒绝条件，也不原样重跑。

## 数据与复算方法

- 原始数据：[baseline benchmark](../../../runs/003-goal-evidence-ab/baseline/benchmark.json)、[goal_evidence benchmark](../../../runs/003-goal-evidence-ab/goal_evidence/benchmark.json)。两份均包含 16 条 `game_runs`，同一游戏各出现一次，完整 game_id 一一对应。
- 配置证据：[experiment-manifest](../../../runs/003-goal-evidence-ab/experiment-manifest.json)、[baseline metadata](../../../runs/003-goal-evidence-ab/baseline/arm-metadata.json)、[goal_evidence metadata](../../../runs/003-goal-evidence-ab/goal_evidence/arm-metadata.json)。
- 采用证据：[baseline intervention](../../../runs/003-goal-evidence-ab/baseline/goal-evidence.json)、[goal_evidence intervention](../../../runs/003-goal-evidence-ab/goal_evidence/goal-evidence.json)。
- 已人工调用 [汇总脚本](../../../scripts/summarize_experiment.py)：`python3 scripts/summarize_experiment.py runs/003-goal-evidence-ab --reference baseline --source-kind local-experiment --output-dir experiments/003-analysis`。
- 派生产物：[summary.json](../../../experiments/003-analysis/summary.json)、[summary.md](../../../experiments/003-analysis/summary.md)、[diagnostics.json](../../../experiments/003-analysis/diagnostics.json)。后者保存输入 SHA256、逐游戏 token 缺口、截止时间检查、配置一致性和 leave-one-game-out 敏感性结果。

汇总工具已经补充 schema_version=2：保留原 `generated_tokens` 的 history+final 口径，新增 `action_attached_generated_tokens`（仅 history）、`analyzer_reported_generated_tokens`（显式字段或严格匹配的 solver_note）与 `unattached_generated_tokens`（analyzer 减 history+final，已记入 final 的不重复算缺口）。另记录 analyzer 计数覆盖了多少 run，并读取 arm metadata 作为截止上下文。人工重跑后两组得分不变，尾部缺口与独立计算一致；输入文件 SHA256 均保持不变，下载目录里的原 summary 未覆盖。

以 `final_score` 为原始得分，并用所附 TAAF 公式独立复算：已完成关卡的单关得分 `min(115, (baseline_actions/actions)^2*100)`，以关卡序号 1…n 加权，再受已完成关卡权重上限约束。32 条运行的原分与复算均一致；`sum(actions_per_level) == len(history)` 全部成立。两组 `game_weights=null`，此处均值是同一 16 游戏的普通均值。

完成覆盖上限（completion ceiling）为 `100*k*(k+1)/(n*(n+1))`，其中 k 是已完成关卡数。它固定当前完成集合，只表示改善动作效率可达到的理论上限；不是已经拿到的分数。

## 汇总

| 指标 | baseline | goal_evidence | B − A |
|---|---:|---:|---:|
| 游戏数 / 每游戏遍数 | 16 / 1 | 16 / 1 | 相同 |
| 平均分 | 49.250188 | 46.878290 | -2.371897 |
| 平均完成覆盖上限 | 52.507215 | 49.302850 | -3.204365 |
| 上限与实分差距 | 3.257027 | 2.424559 | -0.832468 |
| 完成关卡 / 总关卡 | 72 / 121 | 68 / 121 | -4 |
| 完整通关游戏 | 5 | 5 | 0 |
| 截止时取消游戏 | 11 | 11 | 0 |
| 动作数 | 3,226 | 3,169 | -57 |
| benchmark 记账 generated tokens | 2,810,615 | 2,813,917 | +3,302 |
| analyzer 自报 tokens（solver_note） | 2,856,116 | 2,922,797 | +66,681 |
| benchmark 未归属的 analyzer tokens | 45,501 | 108,880 | +63,379 |
| 请求的单组有效预算（秒） | 4,642 | 4,642 | 0 |
| benchmark JSON 起止时长（秒） | 4,681.097 | 4,648.515 | -32.582 |

均值下降主要伴随覆盖下降，动作效率差距反而缩小。但这是不同完成集合下的描述，不能说效率模块得到因果改善。6 个游戏分数较高、5 个相同、5 个较低；完成关卡数增加的仅 2 个、下降的 3 个，其余 11 个相同。

### 逐游戏得分、覆盖与完成关卡

下表顺序沿用实验输入，B 是 goal_evidence。每游戏只运行一次。

| 游戏 | A 分数 | B 分数 | Δ 分数 | 完成关卡 A → B / 总数 | A 上限 | B 上限 |
|---|---:|---:|---:|---|---:|---:|
| sk48 | 1.3656 | 0.0000 | -1.3656 | 1 → 0 / 8 | 2.7778 | 0.0000 |
| lf52 | 7.7320 | 10.9091 | +3.1771 | 3 → 3 / 10 | 10.9091 | 10.9091 |
| bp35 | 2.2222 | 2.2222 | 0.0000 | 1 → 1 / 9 | 2.2222 | 2.2222 |
| wa30 | 2.2222 | 13.3333 | +11.1111 | 1 → 3 / 9 | 2.2222 | 13.3333 |
| g50t | 2.6825 | 10.7143 | +8.0317 | 1 → 2 / 7 | 3.5714 | 10.7143 |
| sc25 | 47.6190 | 38.9264 | -8.6927 | 4 → 4 / 6 | 47.6190 | 47.6190 |
| ls20 | 34.0685 | 35.7143 | +1.6458 | 4 → 4 / 7 | 35.7143 | 35.7143 |
| su15 | 62.2222 | 13.3333 | -48.8889 | 7 → 3 / 9 | 62.2222 | 13.3333 |
| tn36 | 13.7582 | 3.5714 | -10.1868 | 3 → 1 / 7 | 21.4286 | 3.5714 |
| m0r0 | 66.5169 | 71.4286 | +4.9117 | 5 → 5 / 6 | 71.4286 | 71.4286 |
| cd82 | 75.6165 | 82.5484 | +6.9320 | 6 → 6 / 6 | 100.0000 | 100.0000 |
| tu93 | 71.9770 | 67.3513 | -4.6257 | 8 → 8 / 9 | 80.0000 | 80.0000 |
| ar25 | 100.0000 | 100.0000 | 0.0000 | 8 → 8 / 8 | 100.0000 | 100.0000 |
| lp85 | 100.0000 | 100.0000 | 0.0000 | 8 → 8 / 8 | 100.0000 | 100.0000 |
| ft09 | 100.0000 | 100.0000 | 0.0000 | 6 → 6 / 6 | 100.0000 | 100.0000 |
| r11l | 100.0000 | 100.0000 | 0.0000 | 6 → 6 / 6 | 100.0000 | 100.0000 |

两组全通的游戏都是 cd82、ar25、lp85、ft09、r11l。新版本未新增完整通关。诊断关注游戏中，sk48 退了 1 关，lf52 关卡覆盖相同，tn36 退了 2 关；不能认定已有重点机制瓶颈被突破。

### 逐游戏 tokens

“记账”指 `sum(history.generated_tokens) + final_generated_tokens`；“自报”指原始 `solver_note` 的 analyzer 累计计数。两种值都保留，不擅自改写原始 benchmark。

| 游戏 | A 记账 | B 记账 | A 自报 | B 自报 |
|---|---:|---:|---:|---:|
| sk48 | 156,178 | 100,819 | 171,039 | 133,440 |
| lf52 | 176,221 | 238,898 | 179,731 | 247,596 |
| bp35 | 180,624 | 180,439 | 186,514 | 216,708 |
| wa30 | 156,422 | 200,529 | 156,422 | 200,529 |
| g50t | 172,628 | 170,353 | 175,313 | 170,353 |
| sc25 | 158,928 | 167,220 | 158,928 | 167,220 |
| ls20 | 207,912 | 188,100 | 207,912 | 188,100 |
| su15 | 239,090 | 218,558 | 239,090 | 218,558 |
| tn36 | 202,589 | 149,968 | 205,271 | 149,968 |
| m0r0 | 231,909 | 249,967 | 231,909 | 278,471 |
| cd82 | 144,787 | 121,122 | 144,787 | 121,122 |
| tu93 | 223,225 | 242,233 | 239,098 | 245,021 |
| ar25 | 138,249 | 153,717 | 138,249 | 153,717 |
| lp85 | 135,117 | 132,266 | 135,117 | 132,266 |
| ft09 | 105,112 | 82,595 | 105,112 | 82,595 |
| r11l | 181,624 | 217,133 | 181,624 | 217,133 |

记账总量只高 0.1175%，自报总量却高约 2.3347%。原实现只在动作执行时把新生成 tokens 归属到动作；`_finish_if_needed()` 调用 `finish_game()` 没有传入最后一次动作后的剩余 tokens。因此 32 条记录的 `final_generated_tokens` 全为 0，尾部生成会落入缺口。对应源码：[solver.py](../../runtime-bundle/src/ARC3-Inference/inference/framework/solver.py) 的 `_play_inner`、`_finish_if_needed` 和动作记账部分。

A 有 6 个游戏自报大于记账，差 45,501，占自报 1.5931%；B 有 5 个，差 108,880，占自报 3.7252%。例如 B 的 sk48 最后一次动作约在第 3,743.68 秒，直到结束没有新动作，尾部 32,621 tokens 没有落到动作记录。**不能据 2.81M 记账总量近似相等就断言两组实际模型计算量完全相同**。自报值也不是 server billing token 的独立校验，应保留这一限制。

`uncached_input_tokens` 两组全为 0；动作包装器当前硬编码传入 0，因此这不表示真实 prefill 成本为零。

## 截止、超时与收尾

两组都按 4,642 秒共同截止，metadata 的 `soft_deadline_fired=true`；每组最后有 11 个 `cancelled`，没有 `crashed`、`not_started`、强制进程退出或遗留 worker。两组进程均 exit_code=0。这里的 cancelled 是预算耗尽停止，不是 11 个程序异常。

run.log 中 A 有 7 条 `analyzer request timed out`，B 有 6 条，均出现在最后的集中收尾区域；对应 read timeout 范围 A 为 7.27–74.73 秒、B 为 0.86–86.55 秒，明显小于常规 analyzer_timeout=900 秒，与截止剩余时间截断相符。日志未对每条 timeout 稳定附 game_id，不能精确把所有请求超时归属到某游戏；需要逐请求轨迹时再核对请求文件，不能根据相邻日志行武断对应。

为排查 A 比 B 多出的收尾时间是否带来额外得分，人工用 `started_at + history.wallclock_seconds` 对齐共同截止，并按 `actions_per_level` 恢复已完成关卡的结束动作：**两组截止后的记录动作均为 0，截止后完成关卡均为 0**。最后记录动作最大时间：A 约 4,641.24 秒，B 约 4,640.07 秒，都在有效预算内。

benchmark JSON 时长 A 超预算约 39.10 秒，B 超约 6.51 秒；metadata 的 `benchmark_wall_seconds` 再多约 3 秒，因为包含诊断输出。额外墙钟主要是请求取消和收尾，本轮没有观察到借此多执行游戏动作。它仍会消耗真实会话时间，不能完全忽略预算成本。

原始 benchmark 不含明确 `stop_reason`，通用汇总将未胜利原因保留为 unknown；本报告结合 metadata、状态和时序，才将这 22 条归类为共同截止取消。保留两个证据层次，避免把所有未来 `cancelled` 自动推断成相同原因。

server.log 启动时出现 `sitecustomize` 缺少 `wrapt` 的非致命提示，随后完成模型加载、warmup 和全部运行，未观察到 OOM 或 server 崩溃。它不能解释某一组的游戏分数差异。两次 `Cache flushed successfully!` 均可在 server.log 确认，不能仅凭 HTTP 200 推断清缓存成功。

## 实验是否可比

本轮可以作**同一配置、同一开发集、等墙钟的描述性筛选**，但不构成独立配对的因果估计。

已核对相同的字段：完整游戏版本与顺序（SHA256 相同）、OFFLINE 模式、16 游戏并发任务、10 条 active streams、1 pass、4,642 秒预算、900 秒 analyzer_timeout、source_sha256、environment；同一已加载模型 server。CPU 进程 PID 不同，每组独立初始化，组间 prompt cache 已清。

仍需继承的限制：

1. 顺序固定为 baseline → goal_evidence，模型权重和编译 kernel 共用。第二组有热身顺序优势，清 prompt cache 不会重置全部硬件与服务状态。
2. 采样温度 0.7，未建立每请求相同随机种子或独立重复；服务侧自身有 seed 也不等于两个游戏轨迹被成对固定。一次游戏对比不能估计运行间方差。
3. 每组 16 个游戏共享 10 条 streams 和共同截止，调度会把某游戏进展转化成其他游戏的算力机会，逐游戏结果非独立，等总预算不等于等逐游戏 tokens。
4. 首个 warmup RESET 落到不同游戏：A 的 bp35，B 的 sk48。实际动作计数已经包括它；这是一项较小但真实的执行差异。
5. 这 16 个游戏根据已有公开轨迹选题，不能当未见验证集。更不能将此次 16 游戏 49.25 分与作者 25 游戏 × 4 遍 46.49 分直接比较并声称复现更强。
6. intervention 事件只记录共享 artifacts 目录，缺少 game_id；唯一 marker 的 step=8、level=1 和目标文本不足以在该 JSON 内独立证明归属。不能从事件日志计算可靠的逐游戏采用率。

## 对 30h 周额度的含义

manifest 记录整个研究 runner 用时 **9,875.01 秒，即 2.7431 小时**，其中模型 ready 花 526.54 秒；两组请求的有效研究预算共 9,284 秒。一次加载服务两组，启动费用得到摊薄，且 `gpu_server_stopped=true`。

这不是 Kaggle 账户最终计费快照：Notebook 安装阶段、runner 之前或之后仍可能占用 GPU。也不能用 16 个并发 game 的 wallclock 相加估算 GPU 消耗。下一轮优先提高“每次模型计算能检验研究假设”的比例；此轮 nudge=0 比盲目增加运行时长更值得先处理。

## 下一步建议

1. 保留 baseline 作为当前参考实现，不把 goal_evidence v1 提升为默认 solver。本次没有提升证据。
2. 先离线检查唯一 unmatched marker 的原始请求和帧，区分模型不采用、帧绑定不匹配、记录粒度缺失。简化报告方式并按 game/session 标识事件；用人工回放已存在输出确认预期反馈路径能够发生，不消耗新 GPU。
3. 补记最后一个动作后的生成 tokens，保留 analyzer 总计作交叉核对。此项只修正实验观测，不应宣传为策略提升，也无需新增测试文件。
4. 下一次小实验必须同时报告“指导次数、marker 采用、frame 匹配、真实 nudge、后续关卡变化”。若预算很小，先确认机制实际被采用，再考虑扩展全部公开游戏或独立复跑；保留 su15、tn36 的回退轨迹和 wa30、g50t 的改善轨迹进行比较。
5. 后续如观察到明确机制采用和跨游戏覆盖收益，再在预算内交换 A/B 顺序或独立复跑；当前单轮数据不足以支持隐藏榜单收益、奖牌或奖金预测。
