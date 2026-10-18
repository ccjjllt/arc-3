# 019 — 独立 FP8 PLE 速度与数值验证

日期：2026-10-18。用户已同意实现，GPU仅使用jiyujia。018停止扩跑，正式009保持原样。本方案是系统与有限质量验证，不运行游戏、不创建正式提交，也不执行模型生成代码。

## 单因素与证据

对照为固定Intel BF16 PLE v1 → Albucino FP8 PLE v1 → 同一Intel BF16 PLE。主体非PLE权重、独立INT4/group32 drafter、tokenizer/template、KV/Mamba、context139264、10请求容量及Pennyroyal-v253保持一致。唯一模型数值差异为PLE的存储/反量化；所有阶段统一显式server seed190018和请求seed，不能据此保证并发逐字确定性。

CPU挂载检查先于任何GPU服务：三个模型附件的config/index/header、222587个非PLE键、固定分层样本字节、128个PLE shard每个8行，以及全局BF16 scale。所有读取都有字节和时间上限。检查ZIP内四个关键运行库源码hash（模型、kernel、environ、loader），安装后再核相同hash；它们不代表全部运行库逐文件身份。合同细节见[权重说明](../../research/019-fp8-ple-contract.md)与[机器合同](../../experiments/019-weight-contract.json)。错误即停，不能看到实际误差后放宽阈值。

实际FP8 scale为0.00019931793212890625，必须正且有限、dtype/shape及原始字节匹配。CPU按FP8值×scale后BF16舍入与基线抽样比较，NRMSE≤0.06、逐元素误差≤7%×|基线|+scale/512、无非有限值。该阈值是工程smoke门，不是无损、推理质量或隐藏分数证明。当前HF metadata/header证据与Kaggle镜像实读分开。

## 冻结请求与测量

[019-suite.json](../../experiments/019-suite.json)固定SHA256标识`f42e6b9c309432735fd5ff5e08d1344758d09fae7c689c311bba5e3d518391c1`。按018 baseline的ft09/tr87/ar25/sb26顺序取各首个和中间请求，再取前两局3/4位置，共10个公开请求；保存完整messages/tools和来源hash/行号，不截断系统提示或游戏观察。只重放请求，响应不会进入游戏或Python执行器。

每阶段固定34次请求：

| 组 | 并发 | 请求数 | 输出控制 |
|---|---:|---:|---|
| latency_cold / latency_hot | 1 | 各2 | 各128tokens，短诊断 |
| load10_cold / load10_hot | 10 | 各10 | 各256tokens，主吞吐 |
| quality10 | 10 | 10 | 合成精确答案工具题，自然EOS，上限512tokens |

冷组必须有新的后端flush成功记录，逐请求使用不同cache_salt防止同批共享前缀；热组逐字节重复冷组请求。缓存实际usage、固定输出长度、完整请求数、服务控制参数都不满足时，不给速度比较。流式chunk不是token；TTFT是首语义payload延迟，可能受到parser缓冲；decode按连续usage估算，不能称GPU kernel速度。spec acceptance直接保留返回计数/服务指标，缺字段保留unknown，不填零。所有SSE和指标原件落盘。

服务启动日志、GPU每10秒利用率/显存/功率、进程RSS/VmLck/VmPin及系统内存独立记录。进程RSS可能重复计算共享页；VmLck不证明完整CUDA pin量。权重审计已触及页缓存，连续三次启动亦共享OS/JIT缓存，因此加载时间仅为该运行顺序的观察，不能宣称严格冷I/O加速。不清整机page cache。

## 预算与停止条件

先运行CPU-only Notebook核实实际附件，不预占GPU。成功后才考虑GPU Notebook：单卡RTX PRO6000，硬限4800秒（80分钟），不是目标消耗。CPU audit父进程上限240秒；每模型启动上限900秒，每固定suite上限360秒；后续阶段剩余预算不足时停止，不缩短请求后仍当完整对照。预期约40–60分钟但以实测为准。

同一阶段10路主负载集中运行，不填充无关任务追利用率；每次更换权重必须先排空并确认本会话server进程组消失。服务异常、启动超时、请求不完整、固定长度或缓存控制未建立，立即停本次，不自动重试。最外层cleanup和hard watchdog只处理本会话登记的进程组，保留失败报告。

## 进入下一阶段的门

必须全部满足，才能另行设计同预算游戏A/B：

1. 实际挂载权重合同和四个关键runtime源码检查通过；三阶段同suite及控制参数、完整输出和清理证据齐全。
2. 两个BF16质量smoke均至少8/10正确；FP8精确正确数不低于两个BF16中较低者，且无新增工具格式/非有限JSON/截断错误。逐字差异单列，不能直接判数值退化。
3. 并发10冷、热组的FP8吞吐均超过两个BF16的较高者，且相对两次BF16均值至少+10%。两次BF16吞吐漂移若超过10%，结果只作不稳定提示，不宣传可靠提升。
4. 没有OOM或不解释的内存/资源恶化。仅加载变快、只单流变快或仅高利用率，不足以进入长游戏A/B。

这些是小规模投入选择门，不是置信区间或金牌概率。通过也不能替代完整游戏质量验证；未通过保留负结果，009不变，不把019叠加018。

## 实现入口

- [权重CPU审计](../../src/arc3_research/ple_weights.py)
- [固定请求客户端与离线比较](../../src/arc3_research/ple_microbench.py)
- [服务生命周期与预算](../../src/arc3_research/ple_session.py)
- [Notebook构建](../../scripts/build_019_microbench.py)、[手动CPU检查](../../scripts/check_019_preparation.py)
- 当前执行状态见[019进展](../progress/019-fp8-ple.md)。
