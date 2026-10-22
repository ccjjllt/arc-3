# 003 — GPU 利用率、运行开销与下一轮预算

日期：2026-10-11（Asia/Shanghai）。仅分析已经完成的 003 输出；本次没有启动 GPU、没有创建测试文件。机器可读结果与方法存于 [`experiments/003-efficiency.json`](../../../experiments/003-efficiency.json)。

## 结论

**本轮共享模型的执行方式达到了节省配额的目的，暂时没有证据支持优先重写 serving 或增加并发。** 实测 session 2.7431 小时，其中 94.02% 是预先分配的解题窗口，加载约 8.78 分钟，其他收尾约 64 秒。两组各有 16 个游戏，实际 decode 平均约 9 条运行请求，接近 10 条上限；没有长时间卡在空队列、模型重载或错误重试的迹象。

更值得立即处理的是**统计完整性与实验噪声**：原 action-history token 汇总漏掉没有落到动作的推理；公开实验已等待 server ready，却仍给一个不确定的游戏额外 RESET。两项都能先在 CPU 上修好，不必再烧一轮 GPU 排查。

本轮目标提示的研究效果不由吞吐或 GPU utilization 判断。B 输出更多 tokens、吞吐略高，并不等于更会解题；完整效果应读取对应研究结果分析。

## 时间与配额

依据 `runs/003-goal-evidence-ab/experiment-manifest.json`，从北京时间 **10 月 10 日 21:19:31 至 10 月 11 日 00:04:06**：

| 阶段 | 秒 | 分钟 | 占 session |
|---|---:|---:|---:|
| 依赖准备、权重加载、CUDA graph 与 ready 等待 | 526.54 | 8.78 | 5.33% |
| A+B 预定解题窗口，4642 秒 × 2 | 9284.00 | 154.73 | 94.02% |
| 两组窗口外 CPU 启停、deadline drain、结果落盘 | 59.25 | 0.99 | 0.60% |
| 外层收尾与 server 关闭 | 5.22 | 0.09 | 0.05% |
| **合计** | **9875.01** | **164.58** | **100%** |

“预定解题窗口”包含模型推理、CPU 工具、游戏调度等待等，不代表每一秒都是 GPU kernel 运算时间。

服务日志能单独解释 startup 的 417.34 秒：主模型权重 263.60 秒、draft 权重 0.82 秒、target verify CUDA graph 144.89 秒、draft decode graph 7.07 秒、draft extend graph 0.96 秒；其余 109.20 秒包括安装、分布式/模型初始化、warmup、其他 graph 与 ready 开销。不要把所有 526.54 秒都称作“读模型文件”。

A 父进程计时 4688.13 秒，B 4655.12 秒；相对于 4642 秒窗口分别多 46.13、13.12 秒。`bm.run` 调用计时分别为 4684.23、4651.73 秒，其超额部分为 42.23、9.73 秒。两组都正常结束，没有被父进程 hard timeout，没有残留 worker 线程、没有强退 CPU 进程。11 个 `cancelled` 是按预算结束的未通关游戏，另外各 5 个 `won`；不能把这些 cancellation 算成执行崩溃。

单次加载比“两次同样的独立 session”约省 **526.54 秒，即 8.78 分钟/0.1463 GPU 小时**，相对于假设的分开运行总时长约省 5.06%。这是以本轮实测 startup 作为两次都相同的估计；第二次独立运行的加载速度未实际测量。

最新账户快照为 `experiments/003-quota-after.json`：

- 每周总额 108000 秒 = 30 小时；已用 19226.113756 秒，已预留 0。
- **剩余 24.6594 小时**；刷新时间北京时间 **10 月 17 日 08:00**。
- 相对运行前的 8442.630 秒已用，账户用量增加 10783.483756 秒 = 2.9954 小时。
- 该增加比 manifest 多 908.47 秒。账户快照覆盖全账户，可能包含平台计费边界、延迟结算或别的 session；没有证据能把差额全归因于本框架空转。我们能确认的是本轮自身计时 2.7431 小时。

## GPU 观测：采样均值与时间加权不能混用

来源是 `gpu-utilization.jsonl` 中每约 60 秒一次的 `nvidia-smi` 观测，A 79 个点、B 78 个点，全部采样命令返回 0。没有 startup 阶段的 GPU utilization 样本。

| 指标 | A baseline | B goal_evidence |
|---|---:|---:|
| GPU utilization 样本算术均值 | 91.22% | 92.17% |
| 按相邻真实时间间隔作梯形积分的均值 | 92.38% | 92.73% |
| 显存样本均值 | 95909.46 MiB | 95864.00 MiB |
| 显存样本峰值 / 总量 | 96189 / 97887 MiB | 95947 / 97887 MiB |
| 功率样本均值 | 385.79 W | 379.16 W |
| decode 日志中的运行请求样本均值 | 9.002 | 9.061 |
| decode 运行请求最大值 | 10 | 10 |

算术均值给每个采样点相同权重；梯形积分仅覆盖每组第一与最后采样时间之间，不能外推到没有采样的加载和尾部时间。因为只有一分钟一个点，**92.38%/92.73% 也是插值估计，不能称为连续监控得到的精确平均利用率**。

中途有若干 0% 观测，但不是“一整分钟闲置”的证据。例：A 的 UTC 14:06:18.968 显示 0%、307.57 W；同一秒附近 server 仍在 decode/prefill，4–5 条请求、约 494–611 tok/s。B 的 UTC 15:30:27.263 显示 0%、298.87 W，周围 1–2 秒同样有 8–9 条请求的活跃批次。可能是瞬时采样落在 kernel 间隙/切换阶段，不能用 `0%样本数 × 60秒` 计算浪费。

在各组首个到最后一个 prefill/decode batch 日志之间，最大日志间隔均为 **3 秒**。这不能证明 CPU 没有短时瓶颈，但没有支持长时间模型空闲的证据。高显存占用也意味着不能只看“平均9条、上限10条”就盲目提高请求上限。

## Tokens、缓存与吞吐

按 server `ReqTimeStats.entry_time` 落在各组父进程时间窗口分组，再按唯一 request ID 汇总。两组分别 1562、1455 条，request ID 无重复。

| 指标 | A baseline | B goal_evidence |
|---|---:|---:|
| server 输出 tokens | 2876390 | 2940738 |
| solver_note 累计 tokens | 2856116 | 2922797 |
| action-history + final 字段累计 tokens | 2810615 | 2813917 |
| solver_note 比 action-history 多 | 45501 | 108880 |
| server 输入 tokens | 114119775 | 104443262 |
| server cached input tokens | 107352256 | 97762176 |
| server uncached input tokens | 6767519 | 6681086 |
| 按 input token 加权的 cache 命中率 | 94.07% | 93.60% |
| server 输出 / `bm.run` 调用墙钟 | 614.06 tok/s | 632.18 tok/s |
| server 请求排队中位数 | 1.48 ms | 1.47 ms |
| server 请求排队 p95 | 4.23 ms | 4.92 ms |
| draft 接受长度，decode 日志样本均值 | 2.652 | 2.676 |

总计 server 输出 5817128 tokens。把一次加载及全部收尾纳入后，整个 session 的输出吞吐为 **589.08 tok/s**。这只是 serving 产出指标，不是有用推理或正确解法的产出率。

三个 token 口径不可互相替代：

1. TAAF action history 是动作发生时归账的 tokens；本轮 `final_generated_tokens` 全为 0，所以末尾没有触发动作的推理没有完全归账。例：A 的 sk48 action-history 156178，但 solver_note 171039。
2. solver_note 是 agent 结束时报告的累计生成量，覆盖了一些没有用于动作的推理，但仍比 server 少。
3. server 可以生成因请求超时/取消而没有被 client 消费的输出。两组 server 分别比 solver_note 多 20274、17941 tokens。结合 cutoff 时出现的 read timeout，未消费输出是合理解释之一，但本次没有逐请求串联所有 usage payload，不能把差额全断言为某一个原因。

同理，原 summary 中 `uncached_input_tokens=0` 是该字段未记录，不是没有 prefill。服务端明确观测到约 676.75 万/668.11 万 uncached input tokens。

建议后续汇总保留全部三种口径和各自来源，不要悄悄把 action-history 字段改名后当“GPU实际总token”。`Decode batch` 日志的 throughput 样本均值为 673.31/689.24 tok/s，它们以活跃 decode 批次为条件；不能拿来替换上面的端到端吞吐。

## Cache flush 与错误/空转核查

缓存清理已经有后端明确证据，**不是只看到 HTTP 200**：

- `serve.log:142`，UTC 13:28:17：`Cache flushed successfully!`，随后 baseline 启动。
- `serve.log:8206`，UTC 14:46:26：同一成功信息，随后 goal_evidence 启动。

两组共享权重及已编译 kernels，但各自开始前清理了请求缓存。这支持本轮的冷 prefix-cache 比较；不意味着重新清空编译缓存或操作系统文件缓存。

服务日志中的非 200 HTTP 仅两次，都是 startup 期间 `/health` 返回 503；没有 generation HTTP 非 200 记录、OOM、长错误重试链或中途 server crash。run.log 的 read timeout 为 A 7 次、B 6 次，集中在结束 cancellation 段，符合剩余预算缩短后的退出路径。

server 在整轮结束时收到 SIGTERM，随后有 detokenizer exit -15 和清理相关 SIGQUIT 信息。这发生在父launcher主动结束之后，且 manifest 明确 `gpu_server_stopped=true`；不能误报为中途服务崩溃。

两组分别执行 8 次 diagnostics render，总计 16.43/15.71 秒，约占每组墙钟 0.35%。渲染主线程时 solver 工作线程仍可继续，不能把这32秒直接算成GPU闲置；本轮没有理由为了这点开销丢弃研究日志。

## 不开 GPU 就能做的修复

按研究价值排序：

1. **修正汇总口径。** 将 action-history、solver_note、server tokens 和字段缺失分开保存；加入两次成功 cache flush 的证据。先在现有输出上重新计算，不需要重跑游戏。
2. **公开 research 模式关掉多余 warmup RESET。** 本次 A 的额外 RESET 落在 bp35，B 落在 sk48（各自 `run.log:4`）。这是并发启动抢 warmup slot 的非确定性；公开实验已等 server ready，不再需要它。下一轮研究模式统一 `ARC3_WARMUP_ACTION_GAMES=0`，比赛首动作时限所需逻辑仍由比赛模式决定。这会改变比较配置，应记录，不能追溯当作本轮已相同。
3. **补好下一轮采样。** 开始模型加载前就采样，并将 GPU 观测周期改到 5–10 秒；保存每组前后 `/metrics` 快照。这样可把 startup、收尾与推理阶段分开，避免一分钟采样混叠。只增加轻量日志，不更换模型或调度。
4. **先解释研究失败，再排下一次 GPU。** B 的吞吐比 A 稍高且 cache 命中略低，没有性能不足拖垮 B 的明显证据；优先读干预事件和失败轨迹，不把回退先归因于 serving。

已为下一版在 `src/arc3_research/run_arm.py` 的导入阶段设置 `ARC3_WARMUP_ACTION_GAMES=0`，并在arm metadata记录 `warmup_action_games=0`；该入口明确拒绝比赛rerun，只用于已由父launcher等待server ready的公开OFFLINE研究。003归档源码和输出保持不变。其余建议尚未实现；没有更换serving、模型或并发，也没有把此改动称为提分策略。

## 下一轮经济预算

使用本轮实测加载 526.54 秒作估计，并保留收尾余量：

| 下一步 | 预估 GPU 墙钟 | 建议上限 | 用途 |
|---|---:|---:|---|
| 单组全 25 游戏 baseline，7254 秒解题 | 约 2.17 h | 2.5 h | 补齐尚未覆盖的 9 个公开游戏，建立全公开基线 |
| 12 游戏 paired A/B，3482 秒 × 2 | 约 2.10 h | 2.5 h | 有新机制且 CPU 轨迹分析能提出可检验假设时筛选 |
| 同样16游戏 paired A/B | 本轮2.743 h，可暂作2.8 h估计 | 3.0 h | 需要更多覆盖或反转组顺序时使用 |

**不建议立刻再花2.8小时原样复跑同一个提示。** 先完成本轮失败解释，再决定全25 baseline还是一次新机制筛选。下一次先限2.5小时，账户仍保留至少约22.16小时，避免用很多无结论 seed 运行消耗整周。

这些是开发 session 预算估计，不把正式比赛 rerun 的配额计费规则混入计算，也不承诺 Kaggle排队、加载速度或评分稳定。与比赛高分研究相关的后续方向应由过关轨迹决定；本分析只说明当前硬件利用没有明显长时浪费。
