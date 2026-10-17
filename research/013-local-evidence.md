# 013：从真实运行约束下一候选

日期：2026-10-17，Asia/Shanghai。范围是本地 005–012 已保存的 benchmark、011/012 计时事件、选取下载的原始请求日志及公开 harness。没有启动 GPU、请求模型、执行日志内 Python、读取游戏机制源码或修改生产 `src/`。公开 Notebook 的最新版本与论文证据由本轮另外两份研究核对，本文不给第三方源码绑定未核实成绩。

**结论：可以继续研究两个彼此独立的方向：现有调度开关，以及无需 put/get 的同观察原生计算值交接；没有任何一个已获本地提分证据。** 80k tail 与 pace 都有实际竞争时刻，但现有计时记录缺精确 PrioritySnapshot，不能重放反事实成绩。原生值方向新增了直接的跨 snippet NameError 证据，强于仅凭“可能少抄写”的假说；它仍只覆盖少量可确认错误，不能承诺弥补 012 的 17.3 分下降。

## 1. 本次新增证据与可复现口径

- [分析脚本](../experiments/013-local-evidence/analyze.py) 逐文件解析已有 JSON/JSONL，按每文件 `tool_call_id` 去重累计请求快照；只 `ast.parse` 模型代码，不执行。结果：[请求审计](../experiments/013-local-evidence/request-audit.json)、[基线波动](../experiments/013-local-evidence/baseline-variation.json)、[等待区间](../experiments/013-local-evidence/queue-opportunities.json)、[运行日志](../experiments/013-local-evidence/run.log)。每个输入保留路径/SHA256。
- [调度分析脚本](../experiments/013-local-evidence/scheduler.py) 只导入现有纯 `priority_scheduler.py`，读取固定轨迹并比较现有公式。结果：[敏感性 JSON](../experiments/013-local-evidence/scheduler-sensitivity.json)、[摘要](../experiments/013-local-evidence/scheduler.log)。它不是 scheduler simulator，也不创建新动作、成功关卡或分数。
- 直接案例的前后代码、工具结果、首次请求行号及消息 hash 保存在 [native-value-cases.json](../experiments/013-local-evidence/native-value-cases.json)。行号是一基的首次可见请求快照，**不是执行时间**。

手动复核命令：

```bash
python3 -B experiments/013-local-evidence/analyze.py
python3 -B experiments/013-local-evidence/scheduler.py
python3 -B experiments/013-local-evidence/pace-contract-probe.py
```

60 份请求文件覆盖 15 个不同游戏，其中 baseline 32 份、干预臂 28 份。它们是历次问题驱动选取下载的日志，**不是 25 游戏全量样本，更不是随机样本**。同一游戏不同运行均保留，不能把全部工具调用当独立统计样本。AST 解析失败 10 次，未猜测修复。

| 观测 | baseline 32 份 | 其他臂 28 份 | 合计 |
|---|---:|---:|---:|
| 去重 Python 调用/结果 | 2,849 | 2,596 | 5,445 |
| 结果明确 NameError | 54 | 52 | 106 |
| 错误变量此前有顶层赋值源码 | 34 | 36 | 70 |
| 上项且 request action 字段相同 | 25 | 34 | 59 |
| 结果报告函数保留拒绝 | 394 | 355 | 749 |
| 上项含 unavailable dependencies | 361 | 321 | 682 |
| AST 完全相同的函数重复定义 | 139 | 96 | 235 |

106/5,445=1.95% 只是此选取语料中的调用占比。59 次同 action 赋值线索只占 1.08%，不能转成“可省 1.08% 总算力”；有些赋值没执行、有些值含函数/对象、有些旧值不正确、重算本身也不昂贵。749/682 按**含提示的结果数**计数：同一函数可能反复被拒绝，不是 749 个独立 bug。235 次重复定义也可能是主动重新展示、上下文恢复或适应新关，不能全计浪费。

六次 baseline 的共同交集只有 8 游戏；其均分依次为 31.7777/38.7958/41.4192/34.2163/46.1522/48.7111。原实验池分别有 25/12/12/12/12/13 游戏，共享调度和暴露不同；这是 **16.93 分描述性范围，不能叫同条件随机方差**。它进一步限制从单次总分判断新机制收益。

## 2. 候选 A：80k tail 单开关

机制与边界由底座 [priority_scheduler.py:80](runtime-bundle/src/ARC3-Inference/inference/agent/priority_scheduler.py:80) 直接给出：`P=(当前关价值 A + 尾部价值 B × fade) × chance / pace`。baseline 的 B 是剩余关数映射 8/7/5/0；`TAIL_LOOKUP=1` 换成条件于完成当前关的未来总价值表，再乘 0.8。80k 是所有未来关共享的 token 假设，后段有合并/外推，不能称为当前游戏的校准成功概率。表源/局限见同文件 8–26 行及 [010 Notebook 审计](010-notebook-update.md:24)。

**新增的真实竞争机会证据**：011/012 计时观察器记录了 acquire/handover 的开始和返回，但没有记录传入 priority/snapshot；见 [observer:322](../src/arc3_research/inference_timing.py:322)。本次在每次截止前释放 slot 时，从观察到的等待区间筛选“没有 fresh 等待者，至少两个已运行游戏竞争”的时刻，忽略 1ms 内唤醒歧义，再冻结各游戏入队时状态。

| 保存运行 | handover 次数 | 等待 >60s | 公式可能改变选择的时刻 | baseline 代理与实际首返回一致 | tail 改变代理赢家 | pace 改变代理赢家 |
|---|---:|---:|---:|---:|---:|---:|
| 011 baseline | 42 | 5 | 18 | 17 | 1 | 1 |
| 011 animation | 39 | 9 | 33 | 33 | 0 | 3 |
| 012 baseline | 44 | 15 | 41 | 35 | 1 | 1 |
| 012 current_data | 45 | 19 | 44 | 40 | 6 | 7 |
| 合计 | 170 | 48 | 136 | 125 | 8 | 12 |

代理状态用 benchmark 的实际动作时间、关卡完成边界及 action-attached tokens 重建；**缺少无动作推理/正在执行的 token 与精确完成账本**。125/136 一致只能说明代理有相关性；11 个不一致保留在 JSON，不能通过事后更改状态“修正”。8 次换序不是 8 次会获得的 admission，更不是 8 次提分；切换政策会改变后续行动和队列，固定轨迹分析无法识别这些反事实。

支持此候选的理由是：已有纯函数/单开关，不依赖模型读新说明或学新 API，而且存在真实重排机会。反证/限制是：011 baseline 只有 1 个代理选择变化；先前 005 全 25 游戏的固定时点次序翻转也只有 7.4%。效果可能小，且方向不知。tail 降低浅层未来价值，可能牺牲晚熟但高价值游戏。

fresh 游戏处于独立的高优先级 band；已有空 slot 的线程先到先得，公式不改变首次入场顺序。handover 仅发生在 context trim 后，[tool_agent.py:6372](runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py:6372)。因此不能把 tail 包装为修复初始覆盖延迟、确定性公平或自动给近终局游戏追加算力。

**最小验证**：保持当前 baseline、模型、prompt、10 slot、预算、游戏顺序和工具不变，只设 `TAIL_LOOKUP=1`。先用人工状态检查退化/边界与参数生效，再在不改变队列行为的 observer 中记录：实际 enqueue 的 level/actions/tokens/pace/priority，队列 repricing 和被选 token、真实首次准入、prefill/有效生成量。公开 25 游戏比 12 游戏更能体现正式 110 游戏的资源竞争；先同预算一轮筛选，若正向再倒序确认，不能依单轮公开结果晋升。

**停止条件**：真实 snapshot 下几乎不改变分配；选择变化主要损害多游戏进展、均分与关卡不能共同支持净收益；或方向在确认轮反转。不得为了本次得分按游戏 ID 手调表，也不能把总分随 seed 波动追溯成 tail 的稳定效果。

## 3. 候选 B：pace 单开关，需要先核验真实完成账本

这是与 tail 不同的单因素。`ARC3_PRIORITY_PACE=1` 时，每完成一关将该关实际已记 session 生成 tokens 与按关号的参考成本比较，更新对数成本比 EWMA（旧 0.6、新 0.4）；以 `completed/(completed+3)` 向 1 收缩，最终倍率夹在 0.5–2。首关未完成时 multiplier 恒为 1。见 [ProgressPace:51](runtime-bundle/src/ARC3-Inference/inference/agent/priority_scheduler.py:51)、[完成账本入口:3847](runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py:3847)。

参考 [priority_pace_reference.json](runtime-bundle/src/ARC3-Inference/inference/agent/priority_pace_reference.json) 来自 1,417 个历史 reached-level episodes，Kaplan–Meier restricted mean、截断 120k tokens；不是隐藏集规则，不按 game identity 推理，但历史配置不同。pace 消费生成 token 成本，不是墙钟 latency/模型正确性/未来关难度。此前完成快也不保证下一关机制相似。

**不能把它简化为“快的多给、慢的少给”。** 倍率既除整个 priority，也改变 token 衰减尺度 `token_scale*pace`。原公式 CPU 合成值（L4、25 actions、N8、未 fade）：

| 当前关生成 tokens | pace 0.5 | pace 1 | pace 2 |
|---|---:|---:|---:|
| 0 | 1890 | 945 | 472 |
| 31,000 | 1175 | 831 | 457 |
| 62,000 | 550 | 587 | 415 |
| 124,000 | 461 | 275 | 293 |

例如曾快的游戏在 62k 处反而低于默认，曾慢的在 124k 处反而高于默认；action 分量还保留非零地板。不是实现错误，但必须按完整公式解释。上节 12 个代理赢家变化也不能按“变化多”宣称比 tail 更有价值。

**关键未知**：005–012 均未启用 pace；此次看到的是源码连线和 action-token 代理，**没有 live pace 运行账本**。`_update_summarized_knowledge_from_step_summary` 用 `level_transition` 并以已记最高 completed level 去重；生成 token 和关卡边界的更新时机、重复 summary、死亡/RESET、同 snippet 中过关及失败后账本必须用真实 ToolAgent 的人工 stub 调用验证。仅测试 ProgressPace 纯数学不够。现有 `PACE=0` 下正常运行不能替代这一验证。

一个需要排除的伪 bug 是“同 snippet 连过两关，汇总成本却只记一次”。[人工 CPU 探针](../experiments/013-local-evidence/pace-contract-probe.py) 从 harness 源码提取原 summary 方法及成本更新块，给两次人为 `level_completed` 确实只产生一个终关记录；但**这种输入不符合正常动作合同**：实际 [solver:1124](runtime-bundle/src/ARC3-Inference/inference/framework/solver.py:1124) 在第一次过关停止 batch；[宿主:5784](runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py:5784) 与 [sandbox:490](runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py:490) 均拒绝同 snippet 过关后的后续动作。因此不能把这个人工输入结果称为线上已触发的 pace 缺陷。逐次单关输入按参考成本记两次得到 multiplier=1，4 个窄检查通过，见 [结果](../experiments/013-local-evidence/pace-contract-probe.json)；这仍不替代完整 ToolAgent/usage 账本验证。终关后游戏退出，不再参与后续调度，终局是否完整入 pace 统计本身不影响该局的下一次选择。

**最小验证**：CPU 人工模型 usage/动作反馈检查：每关只记一次实际成本，不能重复观察、不能把失败但已消耗的推理全部抹掉；同 level 重试与新 session 的冷启动明确，配置路径可用、参考缺关 fallback 可见。通过后仍保留 `TAIL_LOOKUP=remaining`，仅打开 pace 做匹配 25 游戏筛选；不能同时开 tail 或改 context/并发。

**停止条件**：完成账本与实际成功 usage 无法对账；倍率多数夹边界而缺乏解释；早期成功把后续未知新机制过早饿死；或确认轮净收益消失。本文不声称 pace 的预期收益低于/高于 tail；目前 **tail 的机制更容易审计，pace 的新增 live 路径验证欠缺**。这决定工程准备顺序，不能代替 GPU 效果排序。

## 4. 候选 C：成功的无动作 snippet 自动交接普通值

这与 012 的 `current_data.put/get` 有实质区别：模型继续按普通 Python 变量用数据，宿主负责同一观察下恢复可接受的值，**不要求先学新 API**。只把数据生命周期作为一个因素；不一起恢复任意 Python 进程、扩大跨关记忆或自动保留闭包。

**新直接证据**（下面前一调用均成功、没有 `[action]` 回显，后一次同 request action 字段，明确 NameError；原始摘录在案例 JSON）：

| 原日志 | 成功计算 → 自然使用失败 | 值类型和边界 |
|---|---|---|
| [005 bp35 L53→55](../runs/005-full-baseline/baseline/bp35-0a0ad940_p0_requests.jsonl) | `cams` 已由历史公开帧计算且打印，下一段读 `cams[i]` 失败 | 整数 list，数据交接可覆盖；不证明相机估计正确 |
| [005 re86 L113→115](../runs/005-full-baseline/baseline/re86-8af5384d_p0_requests.jsonl) | 搜索返回 16 个 `sols` 候选，下一段迭代即失败 | list/tuple 候选；保存只消除丢值，不把候选变正确解 |
| [012 baseline ft09 L21→23](../runs/012-current-data/baseline/ft09-0d8bbf25_p0_requests.jsonl) | `cl = solve(current_frame)` 计算 14 个点击，下一段 `for a,b in cl` 失败 | list of tuples；纯函数 `solve` 已保留，直接重调用也可修复 |
| [012 current_data ft09 L129→131](../runs/012-current-data/current_data/ft09-0d8bbf25_p0_requests.jsonl) | 已计算 `LV`，下一段 `LV.items()` 失败 | 含 set/tuple-key 的结构，严格 JSON 不覆盖；新 API 存在也没被用于交接 |

**明确反例**：[005 cd82 L57→59](../runs/005-full-baseline/baseline/cd82-fb555c5d_p0_requests.jsonl) 的 `STAMPS` 确实先赋值后 NameError，但值包含 lambda。受限普通值交接应拒绝它；不得用 pickle/恢复可执行对象来扩 scope，只为把错误计数“解决完”。模型可把这类逻辑改为已有纯函数返回结果，或把函数名直接显式调用。

反方向证据同样重要：012 baseline ft09 在发生 `cl`/`T` 两次丢值后仍全通 6 关；新机制至多改善这一段成本，没有证明它能突破其他机制瓶颈。012 成功 put 的是未验证且后来被否定的 `sols[0]`，模型不读回；自动恢复普通变量也可能更方便地继续使用错误假说。cd82 先前“正确 stdout 被错述”和 ft09“像素坐标手算错逻辑列”发生在语义转换层，原生保存不自动纠正这些错误。[012 采用审查](012-intervention-analysis.md:19)、[011 误抄证据](011-evidence-reuse-next.md:11)。

底座每次新建 `runtime_globals`，[sandbox:355](runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py:355)；它只从源码恢复函数/import，[sandbox:652](runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py:652)。函数依赖的普通值不在可用名字中就会被拒绝，[retained_functions:125](runtime-bundle/src/ARC3-Inference/inference/utils/retained_functions.py:125)。因此此问题不是“baseline 完全没记忆”，也不是再增加 repair hint 就自然消失：当前拒绝结果已经告诉模型依赖名称，106 次 NameError 仍有出现。

**最小 CPU 合同，而非立即实现大持久层**：

1. 第一版只提交成功且整个 snippet 没有真实动作的普通计算值；写入身份为 session/RESET attempt/action/level/frame hash。失败或超时不提交部分赋值。任何真实动作令宿主旧快照失效；新 snippet 只恢复同身份值。这样保守地排除“动作前旧局部值在 snippet 结束时被错标成新帧值”。
2. 用有界的类型标签编码有限 scalar/list/tuple/dict/set/frozenset，明确 tuple key、顺序、别名/副本和字节/深度限制；只接受这些确切内置类型，不执行对象协议，不用 pickle，不保存 frame/module/callable。若第一版只支持 JSON，应承认 cl/LV 等主要病例覆盖不足，不把旧统计当覆盖率。
3. 不自动使依赖数据的函数升级成跨关可保留函数：按原版可用名字集合先恢复函数，再注入当前值，保持函数 retention 原合同。避免把 C 与另一个“闭包保留”因素混测。
4. 保留 reserved names，不覆盖新 current_frame/history/action，变量名重绑/删除语义可检查；无额外模型调用，不把所有值自动渲染进上下文。模型说明仅准确说明普通值的短期寿命。
5. 只运行人工小值/公开保存帧的独立提取器验证类型往返、身份失效和动作不重放，不能直接执行上述日志计划来展示成功。通过后再安排少量模型真实采用门槛，观察现有自然变量引用是否真正免于丢值，并统计恢复字节/拒绝类型/CPU 和额外 token。

**采用门槛/停止条件**：必须出现“已有计算→自动交接→下一 snippet 原变量被消费”且行为与正确重算一致；若恢复候选主要不可序列化、通常跨动作才用、成本小于开销，或陈旧数据错误上升，则停止。只有减少几次 NameError、没有跨游戏关卡/效率改善也不晋升。当前数据支持做 CPU 合同及小采用验证，尚不足以让此工程取代已可测的调度单因素。

## 5. 独立工程修复与本轮取舍

012 的两次真实迟到客户端请求均在 handover 等待后发出，见 [计时审计:17](012-timing-analysis.md:17)；005–010 也有服务器尾请求。应在 handover 返回后、HTTP 之前复查真实 deadline，但它是资源边界修复，**不是争取 17 分收益的研究候选**。先用 CPU 验证截止前请求不变，再作为两臂共同底座变更冻结；不要只修候选臂并把节省时间归给推理机制。

本地证据支持以下准备顺序：先完成调度 snapshot/pace live ledger 的 CPU 可审计性，再决定 tail 或 pace 的单开关 25 游戏筛选；并行以明确合同验证自动普通值交接的最窄版本。暂不扩大 012 的显式缓存、也不把第三方全包的重置/调度/记忆一起移植。收益指标必须同时保留均分、关卡、全通、逐游戏资源和真实采用；公开研究分数不能换算成正式金牌/奖金概率。
