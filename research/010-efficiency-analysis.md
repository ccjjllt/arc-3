# 010 — 运行有效性、GPU 效率与资源分配

日期：2026-10-13（Asia/Shanghai）。分析已完成的 010；只读取归档源码及下载日志，没有启动 GPU、修改原始输出或进行新提交。可复算：`python3 scripts/analyze_010_efficiency.py`；结构化数据及来源哈希在 [010-efficiency.json](../experiments/010-efficiency.json)。

**本轮两组均正常完成既定 3482 秒解题窗口，未记录截止后的环境动作或过关，基础运行可以作为一次 A/B 筛选。** 候选组 GPU 利用率略高，实测归档与查询 CPU 成本较小，没有 OOM 或求解阶段持续 GPU 空转的证据。不过两组首次动作时刻和逐游戏 tokens 分配不同，且截止后的模型收尾并不相同；不能把成绩变化全部归因于动画接口。

## 1. 运行与来源核对

- 运行 manifest 的 15 项 source hash 全部匹配 `experiments/010-source/`；归档索引的全部文件哈希也匹配，运行配置与 build manifest 完全一致。Notebook 为 `36fae12d8d6e536f280d94632b1f0cc93af2852295e3919c9081e4c10dc17d35`，动画模块为 `ea4bb1a77433e2ccefbb9d46abe9e82e6eac8ae5c058828662e4732a940ca875`。
- 两臂完整 12 游戏 ID、顺序 hash、版本、1 pass、12 CPU 游戏会话、10 活跃推理流、环境参数及 3482 秒预算一致；进程 PID 分别为 1323、4742。
- 两臂均 `status=completed`、`exit_code=0`、无 forced CPU exit、无 lingering worker。A 为 2 won / 10 cancelled，B 为 1 won / 11 cancelled；其余取消发生在本轮 soft deadline 上下文，没有 crashed 或全部未启动状态。
- 两臂的 003/006/007 diagnostics 均 `enabled=false`；006 调用记录和 007 事件计数为零。运行环境 `ARC3_WARMUP_ACTION_GAMES=0`，24 条游戏轨迹的首动作全部是非 RESET，run.log 无 warmup RESET 记录。后续真实 RESET 属于游戏过程，不能误算为启动 warmup。
- 服务日志第 143、5823 行分别明确显示 `Cache flushed successfully!`，时间为北京时间 09:34:50、10:33:15。HTTP 成功回执之外还有服务侧确认；这仍不代表 CUDA 编译缓存或固定 A→B 顺序的影响全部消失。
- 两臂的 `benchmark_initial.pkl` 和 `tool_agent.py` 运行时哈希相同。输入定位耗时 0.00737 秒，本次实际使用嵌套 datasets/models/competitions 路径。

## 2. 实际时间和启动成本

仪表记录的会话为北京时间 **09:25:09—11:32:45**，共 **7655.90 秒 / 2.1266 小时**。结束时 `gpu_server_stopped=true`，GPU 采样正常停止。这是测得的 session 墙钟，不是平台计费时间；未用账户余额差估算本任务消耗。

| 阶段 | 秒 | session 占比 |
|---|---:|---:|
| 安装、权重加载、graph、ready 等启动 | 581.66 | 7.60% |
| 两组预定解题窗口 | 6964.00 | 90.96% |
| 其余准备、截止收尾、保存及关闭 | 110.24 | 1.44% |

| 指标 | A baseline | B retrievable_animation |
|---|---:|---:|
| 求解预算 | 3482.00s | 3482.00s |
| `bm.run` 墙钟 | 3500.45s | 3561.14s |
| parent arm 墙钟 | 3504.18s | 3564.19s |
| deadline 到 parent arm 结束 | 19.30s | 80.42s |

机器实际为 **NVIDIA RTX PRO 6000 Blackwell Server Edition**。服务日志记录主模型权重加载 324.33 秒、draft 0.86 秒；target verify CUDA graph 144.83 秒、draft decode/extend graph 7.05/0.96 秒。没有第二次模型加载。

## 3. GPU 利用率与吞吐

776 个 GPU 样本全部成功，常规每 10 秒一次，阶段切换另加样本。时间加权数值使用样本 `time`，在精确阶段边界截断相邻样本区间并做梯形积分，不外推未观察时间；这是离散插值估计，不是连续 kernel 测量。

| 指标 | A baseline | B retrievable_animation |
|---|---:|---:|
| 预算内 GPU 样本均值 | 90.62% | 93.11% |
| 预算内 GPU 时间加权估计 | **90.60%** | **93.09%** |
| GPU 显存采样峰值 | 96,051 MiB | 96,093 MiB |
| 归属本臂的 server 请求 | 1,018 | 1,100 |
| server 输出 tokens | 2,158,369 | 2,205,524 |
| analyzer 累计 tokens | 2,133,883 | 2,183,455 |
| history + final 动作记账 tokens | 2,037,821 | 1,986,610 |
| server 输出 / `bm.run` 墙钟 | **616.60 tok/s** | **619.33 tok/s** |
| 输入 token 加权 cache 命中率 | 92.34% | 93.45% |
| uncached 输入 tokens | 5,475,216 | 5,207,256 |
| decode 活跃请求样本均值 | 9.08 | 9.13 |
| server queue 中位数 | 1.41ms | 1.48ms |
| initial prefill 中位数 | 261.96ms | 269.84ms |
| draft 接受长度样本均值 | 2.639 | 2.661 |

B 的 server 输出多 **2.185%**，analyzer tokens 多 **2.323%**，但动作记账 tokens 少 51,211；端到端吞吐只高 **0.443%**。这些口径不可互换：A/B 分别有 96,062 / 196,845 个 analyzer tokens 没有落入动作账，server 还包含已计算但可能未被客户端消费的输出。下节另列截止附近请求，不把它们当作新增解题动作。

两组预算内均没有出现“至少 3 个连续采样低于 50%、跨度至少 19.5 秒且相邻间隔不超过 16 秒”的低利用区段；batch 日志最长间隔分别为 3/4 秒。没有证据说明查询归档造成持续 GPU 空转。整 session GPU 时间加权估计为 **84.77%**，启动阶段约 **1.93%**；包含启动及收尾后，两臂合计 server 输出 4,363,893 tokens，摊入 session 墙钟为 **570.00 tok/s**。

## 4. 截止与错误：无额外动作，但存在模型计算尾巴

| 指标 | A | B |
|---|---:|---:|
| soft deadline（北京） | 10:32:55.817 | 11:31:18.891 |
| deadline 后真实动作 / 完成关卡 | **0 / 0** | **0 / 0** |
| 最后一条 batch 日志晚于 deadline | 9.18s | 75.11s |
| server 记录 entry_time 晚于 deadline 的请求 | **1** | **1** |
| 上述请求的整条输出 tokens | **316** | **11,161** |
| client read timeout 记录 | 5 | 10 |

逐动作时间由 `game.started_at + history.wallclock_seconds` 对齐共同截止；24 局 `sum(actions_per_level)==len(history)`，并按完成关卡边界复核，没有晚于截止的动作或过关。

服务日志第 **5808** 行：请求 `0f405bc0704d42f4ae1ad8e9126581dd` 的 entry_time 为 1791858776.813，比 A 截止晚约 0.996 秒，整条输出 316 tokens。第 **11767** 行：请求 `77e495bed53f4021b81276dc0a9cf055` 的 entry_time 为 1791862279.818，比 B 截止晚约 0.927 秒，整条输出 11,161 tokens，完成日志在截止后约 75.11 秒。

**这些是服务器记录的请求进入时间，尚未映射到客户端发送时刻或具体游戏，不能据此认定 harness 在截止后新发请求、确定某个竞态根因，或把 B 的全部收尾都称作旧请求排空。** 已下载的部分 requests 尾段没有对应完整 response，未取得可靠的逐游戏绑定。本轮保留原始 server/analyzer/action 三套量，不能把 11,161 tokens 算作额外游戏得分，也不宣称两臂所有 GPU 计算都严格在 3482 秒内结束。

另有 A 6 条、B 10 条请求在 server 记录中从截止前跨到截止后完成。只有整条输出量，无法分出其中多少 tokens 在截止后生成。服务器日志时间只有秒精度，边界附近的完成时刻也有该精度限制。

HTTP 非 200 仅启动阶段 3 次 `/health` 503，之后正常 ready；没有 generation 非 200、OOM 或致命 Python traceback。启动出现的 `wrapt` 缺失、TileLang data-race 告警、CP fallback 在此前同底座运行也见过，本轮随后持续正常服务。结束阶段 03:32:39 UTC 明确 SIGTERM，之后 detokenizer `exit -15`/SIGQUIT 为关闭链路，不当作求解途中崩溃。现有日志只覆盖本地服务 HTTP；断网 metadata 及这些日志不是完整网络审计。

两臂各生成 6 次 diagnostics，累计 10.41/31.77 秒。B 有一次 22.46 秒的周期渲染（run.log:121），不能忽略这笔 CPU 处理，也不能仅凭现有日志归因于 archive；采样未显示对应的持续 GPU 停顿。

## 5. Archive 自身的资源账

候选报告记录 2290 次 capture，等于候选全部记录动作数（含真实 RESET）；全部 available，保存 8030 个原始 SDK 帧，无 capture error / invalid / too-large 报告。48 次查询包括 19 次 list、29 次 get；28 次 hit 全部是旧动作，1 次为明确的 outside-retained-history。

累计编码写入 93,519,896 字节，淘汰 1162 条记录；峰值保留 **39,974,777 字节（约 38.12 MiB）**，最终 39,613,422 字节，低于 64 MiB 全局上限。累计响应 JSON 为 **11,040,475 字节**；这是 IPC 数据量，不能当作 prompt 字符或 tokens。

capture CPU 为 **3.750 秒**，query CPU 为 **0.687 秒**。二者按线程 CPU 计时，不包含锁等待、完整管道写入、child 解码/segmentation 或模型后续输出成本；保留 JSON bytes 也不是 RSS。资源侧未发现足以把本轮解释成归档引起的整体算力崩塌的证据，但不能从这两个计数宣称开销为零或工具必然有效。

## 6. 固定游戏顺序，仍有不同的资源分配

首动作时间从 benchmark 开始算，可能包含等待、动作前模型推理与 CPU 处理；本报告没有还原首次 LLM 请求或实际取得 GPU slot 的时刻，不能将它当作排队时间或确定的入场顺序。以下不是新干预归因，只揭示本轮比较必须保留的事实。

| 游戏 | A 首动作秒 | B 首动作秒 | A analyzer tokens | B analyzer tokens | A/B 完成关卡 |
|---|---:|---:|---:|---:|---:|
| m0r0 | 967.06 | 27.27 | 159,380 | 212,513 | 1 / 5 |
| ft09 | 57.75 | 876.73 | 188,356 | 171,127 | 6 / 4 |
| ar25 | 995.17 | 893.20 | 100,539 | 132,174 | 8 / 8 |
| tn36 | 77.94 | 49.58 | 153,926 | 189,437 | 1 / 4 |
| lf52 | 25.38 | 19.36 | 210,942 | 133,221 | 3 / 1 |

A 首次动作最晚的是 m0r0/ar25，B 是 ft09/ar25。m0r0 的 B tokens 多约 33.34%，ft09 少约 9.15%；明显的关卡变化和 tokens 分配变化同时存在。不同随机路径、动作前思考、哪些游戏先结束、优先级反馈及固定 A→B 顺序无法在这一遍里拆开。总吞吐相近不等于每局计算相同；共同 token 截面也不等于等算力因果对照。

因此，本轮可以继续用于“接口是否被真实查询、查询后是否有有效证据使用”的筛选。若决定确认，应交换 A/B 顺序并保留完整全池结果。资源数据本身既不能证明 archive 导致净收益，也没有提供因明显基础设施失败而必须重跑的理由。
