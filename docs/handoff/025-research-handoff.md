# 025/026 研究与实施交接：聚焦真实故障修复与低成本调度筛查

更新：2026-10-19，Asia/Shanghai。起点提交：`8fce06b`（北京时间 2026-10-19 21:03）。本交接文件确立下一阶段的研究主线与工程边界；后续执行以本文件及实际运行记录为准，不再沿用 020–024 中已结项或暂停的扩跑计划。

## 一、核心决策与当前基线

1. **保留 009 模型与推理底座**：继续使用 `dfranzen Milestone 2 v3 / Duck-TAAF / Qwen3.8-Flash-Next`（MTP3、长上下文、前缀缓存、函数保留与 UNDO 底座不变），正式成绩基线仍为 **009 v2 / submission `57101330` / Public LB 31.16**（见 [009 进展](../progress/009-baseline-submission.md)）。
2. **结束 019–024 原路径扩跑**：
   - **停止 024 GPU 扩跑**：[024 结果](../../research/024-level-stall-results.md) 与 [024 可解性及随机性审计](../../research/024-level-stall.md) 已证实 `ih01-v1` 7 关数学上无解、`tt03-63be02fb` 全局 `random.choice` 未固定种子。024 结项不代表否定“主动探索”路线，而是终止在损坏或未受控题目上的无效测试。
   - **停止新增需要模型主动记忆/调用的工具入口**：020（−14.70 分）、021（−7.57 分，0 次传参）、022（0 次 `expect=` 调用）一致表明，向提示词追加新 API 关键字或长说明无法转化为有效决策。
   - **停止 019 FP8 PLE 扩跑**：[019 进展](../progress/019-fp8-ple.md) 已确认 RTX PRO 6000 上 10 并发热吞吐为 BF16 的 0.966 倍且质量 smoke 未过门（5/10、5/10、3/10 vs 门槛 8/10）。
3. **下一轮双线推进**：
   - **优先 GPU 主线（建议编号 `026`）**：在已核实的本地真实故障前缀（`ft09`、`tr87`、`m0r0`）上，通过确定性环境动作回放恢复现场，由宿主驱动验证“一次有限的证据复核能否比原模型继续推理更容易恢复通关”。
   - **并行 CPU 筛查（建议编号 `025`）**：仅提取 D-prime 的“首次入场排序”（让未开始游戏与续跑游戏按 009 现有价值函数竞争算力），直接基于本地已保存的 014/016 完整 `scheduler-observer.json` 队列日志在 1–2 小时 CPU 内精确重算改选率。
4. **验证与正式提交节奏**：官方 25 题重新作为主要开发与回归池，社区题仅作精选补充；有效候选尽快进入官方 25 题 10 并发对照与正式隐藏评测（Submission）。

---

## 二、现状复盘与必须纠正的工程缺陷

### 1. 016–024 关键结论汇总

| 实验 | 已核实结果 | 对下一阶段的约束 |
|---|---|---|
| [016 时间分配](../../research/016-results-analysis.md) | 官方 25 题均分 47.1340 → 47.4634（+0.3293），105→111 关 | 存在调度研究空间，但尚未形成稳定提分结论 |
| [019 FP8 PLE](../progress/019-fp8-ple.md) | 10 并发热吞吐为 BF16 均值的 0.966 倍；质量 smoke 未达标 | 无速度与质量收益，支线结项 |
| [020 精确状态通道](../../research/020-results-analysis.md) | 12 题同预算 41.2112 → 26.5081（−14.7031），44→36 关 | 720 个唯一调用仅 3 局出现新语法；不再要求模型主动调新读取 API |
| [021 预测失配停批](../../research/021-results-analysis.md) | 12 题同预算 36.9270 → 29.3560（−7.5710），41→38 关 | 1438 条请求 0 次传入 `pred/extract/scope`，不重复该提示前缀 |
| [022 预测检查](../../research/022-results-analysis.md) / [023 卡关探针](../../research/023-stall-probe-results.md) | 3 题 600s 短池分数波动，但 0 次 `expect=` 调用、0 次窗口触发 | 短池涨分全部来自并发/采样方差，严禁归因于未触发的新机制 |
| [024 64 步卡关探针](../../research/024-level-stall-results.md) | 窗口打开 3 次，但完成关数无增量（`ih01` 0/7，`tt03` 2/3） | 结束该版本；后续修复分支必须由宿主直接组织证据并严格扣减动作预算 |

### 2. 必须纠正的四项工程与方法缺陷

1. **动作预算必须在每次实际执行动作前拦截（且截断时不能抛未捕获异常破坏沙箱状态）**：
   - **现状问题**：当前 [stall_probe.py](../../src/arc3_research/stall_probe.py) 在 `_tool_wrapper` 整段 Python 工具返回后才调用 `tracker.observe(...)` 扣减 `self.following[key] -= count`。模型在单个回合内仍可调用 `step3()` 等循环一次性连走 12 步，导致“3 步探测窗口”形同虚设。
   - **修正要求**：在 `026` 或任何限时修复/探测分支中，若限制最多执行 $K$ 个环境动作（如 $K=0$ 零动作重算或 $K=3$ 短探测），必须在 `action_handler` 每次向环境送出单步动作前检查并扣减剩余配额。一旦配额耗尽、过关（`level_completed`）或死亡（`game_over`），应像底座处理 terminal 动作一样**优雅停止当前批次剩余动作并返回带 `stop_reason="probe_budget_reached"` 的正常结果字典**（严禁直接抛出未捕获异常导致整段 Python 工具报错，否则该 snippet 内的 `print` 诊断输出和已定义的 `def` 持久化函数会被丢弃）。
2. **修正社区与开发选关的“可复现”标准（区分环境确定性与 LLM 采样方差）**：
   - **现状问题**：[024 记录末节](../../research/024-level-stall.md) 将选关门写成“同一 seed + 同一录像动作两次全同，且多次基线都停在同一关”。要求 LLM 多次独立运行都停在同一关过严，既浪费 GPU 算力，也会把正常的模型生成方差误判为环境不合格。
   - **修正要求**：环境准入只需验证 **确定性回放**（同一环境版本、显式独立 RNG seed 与固定动作录像下，状态与过关结果 100% 一致）与 **机制可解**（排除 `ih01` 类数学无解环境）。不再要求多次 LLM 基线运行停在同一关。
3. **009 底座跨回合只保留 `def` 函数与消息历史，不保留普通全局变量**：
   - **现状问题**：009 底座未启用 `015-native-adoption`，每次 `python` 工具调用都是全新子进程，仅通过 `retained_functions.py` 跨回合保留顶层 `def` 函数，并通过 `_history_messages` 保留工具标准输出文本；普通全局变量（如 `targets = ...`）在下一回合会消失并触发 `NameError`。
   - **修正要求**：`026` 修复分支的产出必须通过 **(a) 写入 `_history_messages` 的紧凑核对结果输出（stdout）** 和/或 **(b) 更新顶层 `def` 提取/求解函数（进入 `_kept_functions`）** 交回原 `ToolAgent` 循环，不能假设普通局部变量会自动跨回合存活。
4. **D-prime 与 009 初始 `PrioritySnapshot` 的 `cost_multiplier` 语义不兼容（严禁照抄 `0.0`）**：
   - **现状问题**：[D-prime 源码](../../research/notebooks/2026-10-18/amatlas__dfranzen-fork-d-prime/extracted-assets/cell017-_FP_SOURCE.literal.txt) 在 `acquire()` 中构造未开始游戏快照时写了 `PrioritySnapshot(1, 0, 0.0, 0.0, n)`，因为其自定义 `FormPace` 用 `0.0` 表示“尚未通关任何关卡”。但 009 原版 [priority_scheduler.py](../../research/runtime-bundle/src/ARC3-Inference/inference/agent/priority_scheduler.py) 中 `pace = min(2.0, max(0.5, state.cost_multiplier))` 且最终分数除以 `pace`；若传入 `0.0`，会被截断为 `0.5`，导致**所有未开始游戏的初始优先级被人为放大 2 倍（`÷ 0.5`）**！
   - **修正要求**：在 `025` 中复用 009 原版 `priority_value` 计算未开始游戏（`level=1, actions=0, tokens=0.0`）优先级时，**中性 `cost_multiplier` 必须传 `1.0`**，且 `total_levels` 从该局 `game_run.number_of_levels`（或离线 `arm-metadata.json`）读取。

---

## 三、比赛约束、目标分解与外部借鉴边界

### 1. 赛程与硬件约束

- **截止时间**：2026-11-02 23:59 UTC（**北京时间 2026-11-03 07:59**），剩余约 14 天半。
- **运行规格**：单张 RTX PRO 6000（96 GB 显存）、180 GB 主机内存，正式重跑上限 **9 小时**，断网运行（见 [比赛页面快照](../../research/snapshots/2026-10-18/competition-pages.json)）。
- **评测集与提交配额**：25 道公开开发游戏；110 道隐藏评测游戏（Public / Private LB 各 55 道）。每天最多 **1 次**正式提交，最终可选择 **2 份**。
- **金牌与奖金分开规划**：10/18 历史榜单快照（见 [017 赛情更新](../../research/017-competition-update.md)）中，第 18 名金牌参考线为 **38.20**（距 009 v2 差 7.04 分），第 5 名常规奖金线为 **48.92**（差 17.76 分；前五奖金分别为 $40k / $15k / $10k / $5k / $5k）。这要求改动必须能实质性提高后序关卡通过率或显著减少错误表征导致的无效动作。

### 2. 公开 Notebook 与前沿论文的取舍

- **公开 Notebook（[017 Notebook 审计](../../research/017-notebook-update.md)）**：
  - 19 本公开 Notebook 中没有核实到同时具备“完整源码 + 明确版本 + 绑定更高 LB 实测分数”的可直接替代方案。
  - **仅提取 D-prime 的首次入场排序思想**：见 [D-prime 提取源码](../../research/notebooks/2026-10-18/amatlas__dfranzen-fork-d-prime/extracted-assets/cell017-_FP_SOURCE.literal.txt)，宿主要求未开始游戏与已开局游戏按同一价值函数竞争，不依赖模型调用新接口。
  - **暂不盲目升级 Pennyroyal 3.0.2**：其多并发 `W4` 对应 3 个 speculative steps，与我们当前 `MTP3` 宽度相同，升级不会自动在 10 并发下多获一步草稿，需先核对配置兼容性。
- **前沿论文（[017 前沿更新](../../research/017-frontier-update.md)）**：
  - **OPINE-World / PRO-LONG / Tycho** 的核心启发是：**“找到与事实冲突的解释 → 从原始历史/帧恢复真实证据修正它 → 让修正直接驱动下一步动作”**，同时严格控制修复开销（Tycho 证明单纯提高转移预测准确率但付出过高修复成本反而降低游戏得分）。
  - Franzen 底座已内置长上下文、动画历史、UNDO 和函数保留，不能再靠泛泛追加“请验证/请总结”提示词取胜。

---

## 四、下一轮具体执行计划（026 与 025）

### 主线一（优先使用 GPU）：`026-failure-repair` 真实失败前缀修复诊断

**核心问题**：在相同的真实失败状态和剩余预算下，由宿主发起一次有限的证据复核，是否比原模型继续顺着原上下文推理更容易恢复通关？

#### 1. 诊断样本池（直接复用本地已保存的原始请求 JSONL 与动作记录）
全部取自 [017 本地机制证据](../../research/017-local-evidence.md) 及本地已落盘的 `runs/` 文件（无需重新跑几十局采集）：
- **正例 1（`ft09` 外接框填色与字面量转抄错）**：[ft09 请求日志](../../runs/015-native-adoption/baseline/ft09-0d8bbf25_p0_requests.jsonl)（第 19–41 行将 `gWg / WOg / WWW` 误写为 `WOW`，导致第 3 关耗费 91 动作 vs 正确提取路径 14 动作）。
- **正例 2（`tr87` 字形裁剪错位与假反证）**：[tr87 请求日志](../../runs/016-pace-allocation-jiyujia/pace_1x/tr87-cd924810_p0_requests.jsonl)（第 65–105 行将 tile top 当作 ink top，漏掉底部墨迹行，把 15 黑点裁成 11 黑点，导致轮盘搜索 `HITS []` 误判规则被否定）。
- **正例 3（`m0r0` 预测失配后未及时停批修模）**：[m0r0 请求日志](../../runs/016-pace-allocation-jiyujia/baseline/m0r0-492f87ba_p0_requests.jsonl)（第 37 行 18 步循环中第 2 步已出现 `(44,44)` vs `(44,34)` 失配，仍继续执行 16 步）。
- **负例 / 正常对照（检查是否误伤）**：从同批日志（如 [r11l 请求日志](../../runs/016-pace-allocation-jiyujia/baseline/r11l-495a7899_p0_requests.jsonl) 第 111 行真实跨关，或 `m0r0` 第 79–89 行自然修模段）选取 1–2 个正常前缀，验证干预不会打断正常通关或制造假报警。

#### 2. 状态恢复与分叉机制（关键工程前提）
原始 `*_requests.jsonl` 仅保存了 OpenAI 聊天消息序列，**不包含当时的游戏引擎内存快照或沙箱临时目录中的 `_tool_runtime_state.json`**。因此 `026` 的分叉器必须在 CPU 上按以下三步精确重建切入点 $T$ 的现场：
1. **确定性重放环境动作**：读取对应 `benchmark.json`（或前缀内已执行的动作序列），在离线 `Arcade` 环境中从头执行到切入点 $T$ 之前的最后一个真实动作，核对当前关卡号、`step` 与画面 `ascii` 和请求日志中记录的观察完全一致。
2. **重建 `ToolAgent` 与沙箱运行态**：用重放得到的帧历史写出 `_tool_runtime_state.json`（含 `current_frame`、`previous_frame`、`history`、`transitions`、`last_action_call_result`），并将 JSONL 中截止到切入点 $T$ 的 `_history_messages` 与已成功提交的顶层函数 `_kept_functions` 注入 `ToolAgent`。
3. **A / B 同状态分叉运行**：从该一致状态出发，共享相同的剩余时间与动作预算。**A 臂**按原策略直接继续 `ToolAgent` 推理；**B 臂**先由宿主执行一次短修复分支，再继续原有 `ToolAgent` 循环（两臂之间执行 `/flush_cache` 或使用各自独立重放的 `Arcade` 实例）。

#### 3. 修复分支设计与止损线
1. **只给观测证据，严禁泄漏人工答案**：B 臂输入仅包含宿主自动整理的真实前后帧（或局部精确 ASCII 裁剪）、触发异常/失配的相关动作记录、以及产生该状态的历史代码与标准输出。绝不写入人工总结的游戏规则或正确坐标。
2. **可执行与可核查的修复输出**：
   - 优先执行 **0 环境动作** 的纯 Python 证据重算（如重新核对分割节点像素数与局部 ASCII crop、重算提取器坐标边界、重跑刚才报错/无解的搜索函数）。
   - 仅当纯重算确认需区分两个竞争规则/目标时，才允许申请至多 **3 个真实环境动作** 的短探测。
   - 修复结论必须通过标准输出（进入 `_history_messages`）或修正后的顶层 `def` 函数（进入 `_kept_functions`）交回主循环。
3. **严格计账与优雅截断**：
   - 额外模型调用、prefill、Python 执行耗时及探测动作**全部计入同一剩余预算**。
   - 探测动作在 `action_handler` **每次送出单步动作前**逐一扣减配额；配额耗尽、遇到 `level_completed` 或 `game_over` 时，停止送出剩余动作并返回带 `stop_reason` 的正常字典，不抛未捕获异常。
4. **止损线与后续晋升条件**：
   - 首轮额外 GPU 预算上限约 **1 小时**。
   - 若在已知失败前缀上无法产生增量恢复、仅多出一段文字分析，或在正常对照上频繁误伤，立即停止该实现。
   - 若前缀恢复有效，下一步再专门设计低误报的在线触发器，接入官方 25 题验证。

---

### 主线二（并行 CPU 筛查）：`025-initial-admission-order` 首次入场排序分析

**核心问题**：仅将未开始游戏的首次入场优先级改为与已开局游戏使用同一套 009 价值函数竞争（单因素差异），在实际排队中能改变多少次调度选择？

#### 1. 现有本地数据核实（无需等待新 GPU 运行即可 100% 精确重算）
虽然 [first-handover.json](../../experiments/016-analysis/first-handover.json) 只汇总了各局首次换手前的动作与时间，但仓库**已经完整保存了零丢事件的 `scheduler-observer-v1` 原始候选队列日志**：
- 016 全 25 题两臂队列：[016 baseline scheduler-observer.json](../../runs/016-pace-allocation-jiyujia/baseline/scheduler-observer.json)（491 事件，114 次 selection，`events_dropped=0`）与 [016 pace_1x scheduler-observer.json](../../runs/016-pace-allocation-jiyujia/pace_1x/scheduler-observer.json)（499 事件，116 次 selection）。
- 014 全 25 题两臂队列：[014 baseline scheduler-observer.json](../../runs/014-tail-allocation/baseline/scheduler-observer.json)（499 事件，116 次 selection）与 [014 tail_80k scheduler-observer.json](../../runs/014-tail-allocation/tail_80k/scheduler-observer.json)（487 事件，113 次 selection）。

在这些文件中，每次 `selection` 事件的 `candidates` 数组都完整记录了当时等待堆中的所有候选（含 `token`、原 `priority`、已开局游戏的 `snapshot` 以及所属 `session.game_id`）。对于尚未开始的游戏（原 `snapshot: null`，原 `priority = 2000000 - 100 * idx`），只需从同目录的 [arm-metadata.json](../../runs/016-pace-allocation-jiyujia/baseline/arm-metadata.json) 读取该 `game_id` 的 `number_of_levels`，构造 `PrioritySnapshot(level=1, actions=0, tokens=0.0, cost_multiplier=1.0, total_levels=number_of_levels)`，再代入 [priority_scheduler.py](../../research/runtime-bundle/src/ARC3-Inference/inference/agent/priority_scheduler.py) 的 `priority_value(...)`（保持 `tail_lookup="remaining", normalize_score=True` 及当时的 `tail_fraction`），即可在纯 CPU 上精确重算每一次历史 `selection`！

#### 2. CPU 筛查与挂载兼容性要求（预算上限 1–2 小时）
1. **立即重算 014/016 的 4 份历史完整队列**：统计在首次 handover 发生后（等待堆同时存在“未入场新游戏”与“刚过关/裁剪的续跑游戏”的选择点），将未入场游戏改为真实初始价值后：
   - 有多少个选择点的赢家发生改变（改选率）？
   - 被提拔的续跑游戏当时处于第几关、已消耗多少动作与 tokens（检验是否真如预期那样优先续跑了“刚进入新关不久的高价值局”，还是因为续跑局已消耗大量 tokens 导致价值仍低于新局）？
2. **若进入 GPU 实测的 Hook 兼容性约束**：
   - [scheduler_observer.py](../../src/arc3_research/scheduler_observer.py) 对 `_PriorityGate._enqueue_and_wait` 与 `_pump` 有严格的源码 SHA256 校验（`_EXPECTED`），而 [inference_timing.py](../../src/arc3_research/inference_timing.py) 与 [preflight.py](../../src/arc3_research/preflight.py) 会校验 `_PriorityGate.acquire` 与 `_HarnessGameSession.play` 的原始引用与卸载恢复顺序。
   - 因此，若 `025` 进入在线 GPU 实测，补丁必须只包装 `_PriorityGate.acquire`（不改动 `_enqueue_and_wait` 与 `_pump` 源码），按固定顺序安装/逆序卸载，且在 `experiment_config.py`、`run_arm.py` 与 `preflight.py` 中显式注册新 arm 名称。
3. **晋升 GPU 的门槛**：
   - 只有离线队列重算证实存在有意义的改选窗口，才进入 GPU 实测。
   - **若进入 GPU，必须使用官方 25 题、10 并发**。重点核查：新题是否被饿死（零动作游戏数）、续跑题是否多过后续高权重关卡、额外上下文裁剪后的 prefill 开销是否抵消收益。

---

## 五、泛化验证规范与正式提交规划

### 1. 验证池分工与工程纪律
- **小诊断池 vs 官方 25 题主池**：
  - `026` 类小诊断只回答“机制能否在真实故障上生效”；
  - **官方 25 题（全池 10 并发）**回答“整体得分与预算代价是否值得晋升”，两类结论严格分开记录。
- **社区题库作为精选补充验证**：
  - 沿用已冻结的 `02152bc48068` 划分（[split-frozen.json](../../experiments/020-community/split-frozen.json)：12 开发 / 12 预留 / 16 冻结），不为每轮实验全量认证社区题库。
  - 仅从 12 开发题中挑选少量机制不同、已确认可解且具备确定性 RNG 的代表题（如 `pt01` 等；排除已证实无解的 `ih01`，对 `tt03` 须先在引擎入口固定独立 RNG 才可作对比）。
  - **并发环境 RNG 隔离**：多并发运行环境时，每个游戏实例必须使用独立 `random.Random(seed)` 或进程隔离，不能依赖共享进程中的单次全局 `random.seed()`。
- **评估指标口径**：
  - 主指标统一使用官方评分公式计算的聚合 **RHAE**（兼顾通关率与高关权重下的动作效率）。
  - 完成关数、总动作数、耗时、零动作游戏数用于解释收益来源与风险；社区题缺可靠人类基线时的 `score=0.00` 严禁与官方 AE 混算。
  - 对有希望晋升的候选，做交换运行顺序（AB / BA）的有限复测并披露收益是否集中于单题，不再将“去掉最大正向游戏仍上涨”或“所有辅助指标同时上升”设为机械一票否决门槛。

### 2. 正式提交（Submission）准备与执行规范
> **注意**：仓库现有的 [build_020_submission.py](../../scripts/build_020_submission.py) 与 `experiments/020-grounded-submission.json` 内部硬编码了 `research_interventions: ["grounded_state"]` 与 `install_grounded_state()` 校验，**不能直接运行它来构建新候选（否则会打包已否决的 020 代码或触发校验报错）**。

当 `026` 或 `025` 通过官方 25 题验证后，应以 [build_submission.py](../../scripts/build_submission.py)（009 v2 原版构建器）为底座、参照 `build_020_submission.py` 的插入方式，为新候选编写对应的 `experiments/<候选编号>-submission.json` 与构建脚本（注入新候选模块并保持 `jiyujia` 账号、官方动态 gateway 枚举与 31920 秒 solver 预算）：

```bash
# 1. 使用针对新候选定制的构建脚本生成正式提交 Notebook（本地 CPU，不耗 GPU）
python3 -B scripts/build_<候选编号>_submission.py \
  --config experiments/<候选编号>-submission.json \
  --output-dir experiments/<候选编号>-submission-source

# 2. 使用 jiyujia 账号推送至 RTX PRO 6000 完成真实 save smoke（sb26 + cd82 300s 实测）
kaggle kernels push -p experiments/<候选编号>-submission-source -t 32400 --accelerator NvidiaRtxPro6000
kaggle kernels status jiyujia/<候选slug>
kaggle kernels output jiyujia/<候选slug> -p runs/<候选编号>-submission-smoke

# 3. 核对 save-smoke-report.json 状态为 passed 且生成 submission.parquet 后，执行正式提交
kaggle competitions submit arc-prize-2026-arc-agi-3 \
  -k jiyujia/<候选slug> -v <实际完成save_smoke的版本号> -f submission.parquet -m "<候选编号> 机制说明与基线哈希"
```

---

## 六、接手后的立即执行清单（Checklist）

1. **[CPU / ≤1h] 完成 `025` 历史完整队列离线重算**：编写只读分析脚本，直接解析 `runs/016-pace-allocation-jiyujia/*/scheduler-observer.json` 与 `runs/014-tail-allocation/*/scheduler-observer.json`（联合同目录 `arm-metadata.json` 的 `number_of_levels`），用 `cost_multiplier=1.0` 的 009 原版公式重算未开始游戏优先级，输出真实改选率与受影响对局报告 `research/025-admission-order-analysis.md`。
2. **[CPU] 构建 `026` 失败前缀确定性回放与宿主修复器**：
   - 针对 `ft09`（015 baseline）、`tr87`（016 pace_1x）、`m0r0`（016 baseline）与 `r11l`（正常跨关对照），实现从动作历史重放 `Arcade` 环境、重建 `_tool_runtime_state.json` 并恢复 `_history_messages` / `_kept_functions` 的分叉器；
   - 实现宿主短修复分支，在 `action_handler` 中实现**逐动作执行前扣减配额 + 优雅截断返回 `stop_reason`（不抛未捕获异常）**，确保修复结果通过 stdout 或 `def` 函数交回主循环，完成本地 CPU 单元核验。
3. **[GPU / ≤1h] 运行 `026` 失败修复 A/B 诊断**：在 RTX PRO 6000 上完成同剩余预算下的前缀恢复对照，核查是否真正改变后续动作并恢复通关。
4. **[GPU / 全池回归与提交]**：若 `026`（配在线触发器）或 `025` 取得真实收益，先更新 `experiment_config.py` / `run_arm.py` / `preflight.py` 通过 CPU preflight，再进入官方 25 题 10 并发同预算对照；验证通过后定制提交构建器完成 `save smoke` 并提交隐藏评测。
