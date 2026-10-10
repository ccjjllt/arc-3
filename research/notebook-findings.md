# ARC-AGI-3 公开 Notebook 与模型研究

研究日期：2026-10-10（Asia/Shanghai）。这是本项目第一轮资料研究，尚未运行我们的 GPU baseline，也没有自己的线上分数。本笔记区分公开源码、原作者报告、下载产物重算与研究假设。

## 1. 结论与版本边界

比赛没有结束、没有更名。Kaggle MCP `get_competition` 返回标题 **ARC Prize 2026 - ARC-AGI-3**，截止时间 2026-11-02 23:59 UTC，约 4,090 队。不要把 “Milestone 2” 当成整个比赛已结束。

**复现主基线选 Daniel Franzen v3，不从高票数或“Superstack/SOTA”标题选基线。** 它完整公开 harness patch、固定运行时和模型资产，有真正的公开 demo 运行产物，也详细报告不奏效的方向。当前公开高排 notebook 大部分是 Duck → Franzen 的派生，而不是互相独立的强方法。直接合并这些 fork 通常是在重复同一基线，还容易混入不同预算与不同缓存策略。

最重要的研究判断：先提高**机制和目标推断的成功率、把已学到的机制落实为可复用程序**，再提高预算分配与吞吐。原版已经具备长上下文、函数保留、动画、差分、UNDO 与有经验依据的调度器；单纯再加摘要、规则列表或更多提示不构成清晰突破。

原始竞赛页：[Code](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/code)、[Leaderboard](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/leaderboard)。

## 2. 来源、分数和可复现性

本轮使用 MCP 按本次 competition 的 `ScoreDescending` 获取前 50 个 notebook。该 API 返回顺序、title、votes 等，**不返回每本 notebook 的数值分数**。因此下面分数必须带来源；votes 不等于成绩，notebook 上显示的 best score 也不等于该代码的平均性能。

| 来源及已读版本 | 本次比赛相关证据 | 应如何使用 |
|---|---|---|
| [dfranzen / Milestone 2 Solution](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution)，v3 | 作者 [write-up](https://www.kaggle.com/writeups/dfranzen/arc-agi-3-milestone-2) 报公开 LB 27.89；v3下载产物是25 demo games ×4 passes、mean46.49 | 主基线；46.49不是比赛 LB |
| [shiiin9 / 31.54 in a Single Sub](https://www.kaggle.com/code/shiiin9/affectify-arc-31-54-in-a-single-sub)，v2 | 作者表格：原版27.89、notebook best31.47、其原样复现27.62；D'一次31.54 | 可作 scheduler 对照；不宣称已证明提升 |
| [skarin / 100-Trajectory Audit](https://www.kaggle.com/code/skarin/arc-agi-3-27-80-lb-100-trajectory-audit)，v3 | 作者给 immutable v1 submission 56762591=27.80、56786055=21.01；v3分析原版100轨迹 | 复现方差与轨迹分析，n=2不足估计方差 |
| [Lord Han Solo / Milestone 2](https://www.kaggle.com/code/lordhansolo/built-on-tufa-labs-duck-harness-milestone-2) | 获奖版明确是 v293 / scriptVersionId=353922905、source bundle v297；当前notebook v306换了更新runtime，作者明确未超过旧最高分 | 次要架构参照，避免把最新版本当获奖版本 |
| [sirikilohit / v18.1gc](https://www.kaggle.com/code/sirikilohit/arc-agi-3-duck-18-1gc-submit)，Kaggle v5 | 源码含完整演进注释及 UCB 时间池；本轮没有核验其独立数值 LB | 与Franzen的缓存自然交接策略对比 |
| [scottlegrand / sheetu12b](https://www.kaggle.com/code/scottlegrand/taaf-flashnext-sheetu12b-0922)，v1 | 196 votes、NVFP4/vLLM serving 修改；没有在返回元数据中取得分数 | 参考推理性能，票数不是算法证据 |
| [sujanmajhisuzan / m2-top-submission](https://www.kaggle.com/code/sujanmajhisuzan/arc-agi-3-m2-top-submission)，v21 | 基于完全相同的Franzen大patch；新增提示和调度外壳，无独立受控效果证据 | 阅读差异，暂不作主基线 |
| [Fable & Astra handbook](https://www.kaggle.com/code/leoprovorov/fable-astra-play-arc-3-handbook-harness)，v7 | 分析/手册，metadata没有模型资产、无GPU；引用闭源模型成绩 | 假设来源，不是可离线复现的高分solver |
| [Tufa Labs June winner](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner)，v6 | notebook明确其易读版不等同于幸运得到1.21的原始提交 | 祖先架构及历史里程碑；1.21不是当前模型水平 |

本轮排行榜快照前五：62.96、56.52、44.32、42.66、40.97。公开基线27–31分与榜首仍有显著差距，不能从“已复现基线”推导出金牌。快照保存在 `notebooks/leaderboard-2026-10-10.json`；这是当时的公开榜，不是最终名次或奖牌线。

已保存13本notebook的 `.ipynb`、便于阅读的 `.py` 和 metadata；`.py` 是逐cell阅读导出，包含 notebook magic / patch，**不是可直接运行的普通Python脚本**。文件清单与模型卡摘要在 `notebooks/discovery.json`。

## 3. Franzen baseline 的实际实现

来源：上面的 v3 notebook、[作者源码仓库](https://github.com/da-fr/arc-agi-3-solution)、[配置指南](https://github.com/da-fr/arc-agi-3-solution/blob/main/ARC3-Inference/CONFIGURATION.md)。源码基于 Tufa commit `7652836056c59e044f093e3c13ed7438c814169e`。

### 3.1 计算平台不是普通小模型运行环境

- 单张 RTX PRO 6000 Blackwell 96GB，离线。
- Qwen3.8-Flash-Next，Intel W4A16 AutoRound；BF16 PLE 表卸载到CPU RAM；外部MTP draft checkpoint。
- Pennyroyal/SGLang v2.5.3，base commit `d00d88e`，含Mamba prefix-cache保留、投机状态预算及小batch GEMM等patch。
- 10条活跃game stream；harness context128Ki，输出保留12Ki；server context136Ki；大块截断drain58Ki。
- FP8 KV cache，Mamba capacity60，chunked prefill8192，speculative steps3；temperature0.7/top-p0.95/top-k20。
- 本次下载的main checkpoint约181.24GB、draft约4.16GB（存储大小不等于GPU占用）。不必先把全部权重下载到Mac，Kaggle notebook可直接挂载公开模型。

`dfranzen__arc-agi-3-milestone-2-solution.py` 的约10170–10265行是**实际开启的配置**；并非文件中出现的每一个开关都开启。baseline含许多失败或未启用实验代码，批量打开会改变复现目标。

### 3.2 观察与动作

基础循环是VLM写Python来解释棋盘、搜索、调用action并观察反馈。不是“每个动作都让语言模型盲猜”。

实际启用：
- 10倍图像放大、current-grid图像、行动前后差分、死亡前后差分；
- intermediate animation frames/timeline作为Python变量按需读取；只有出现中间瞬态像素时明确提醒；
- 4连通同色分量的 `frame_diff`，可输出移动/旋转/出现/消失；这是启发式匹配，不是真正稳定物体ID；
- 将ACTION7真正接通并展示成UNDO；
- 函数和部分imports跨整局保留；**普通变量不保留**，每次Python调用仍是fresh namespace；
- 逐action反馈，死亡与自动reset分开；同一工具调用的结果不被reset覆盖；
- level转移时先复用机制、再确认新元素与目标变化。

最值得继承的设计是“更可信的观测接口”，而非更长的自然语言约束。

### 3.3 调度公式与缓存的联系

源码 `priority_value`（阅读导出约372行）：

```
P = (A + B) * C
A = level * (25 / (25 + actions))^2 * 55 / (N*(N+1)/2)
C = .25 * 2^(-(actions/115)^2) + .75 * 2^(-(tokens/62000)^2)
B = 8, 7, 5, 0       # 当前关完成后剩余 >=3 / 2 / 1 / 0 关
```

N夹在6–10；最后20%总时间线性衰减B。作者用725个历史level attempts（557完成、168未完成）拟合耗费与完成机会的下降形状，但B是手工启发，不是学得的价值函数。未完成attempt存在截尾，不能简单当失败标签训练。

**游戏通常在上下文被截断时才交出slot。** 其余工具间隙继续保留slot，避免把warm KV/Mamba cache赶走。这意味着 scheduler 的正确研究单位是“期望得分提升 / 含重建prefix的实际GPU成本”，不只是token数或action数。

### 3.4 负结果要继承

作者明确报告：结构化World/Goal/Action模型写回、周期摘要、自动动画图拼接、更强步骤验证提示、记忆fatal/no-op规则和更复杂priority没有清晰收益。实际配置 `ARC3_MEMORY_SECTIONS='off'`。大上下文保留历史已经足够有用；不可靠摘要会反复强化旧错误。

UNDO、action解释、level-transfer提示、函数持久化曾联合带来明显提高，但没有单独ablation，所以不能归因为UNDO一个因素。更多开关不自动意味着更强。

## 4. 已下载原始结果后的定量诊断

本轮用CLI下载了原作者真正的 `benchmark.json` 和三个p0 request logs，没有启动GPU推理。

- 原始 `benchmark.json` SHA256：
  `ea1862912c8438f944fbb22349d70a5f31ba71277df791a88138c103f38a7895`
- 与skarin embedded evidence里列出的文件hash一致。
- 25个public demo ×4 passes =100轨迹，**100个harness session共享10个server slot和一个8h10m56s job**，不是4次独立顺序实验。
- 实际mean46.4930、417个完成level、33个完整game；原stdout报告17,504,777 generated tokens、594.25 tokens/s。
- 固定这些轨迹已完成关卡数，将每条轨迹动作效率全部提高到其完成上限，均分为49.1227。因此这批轨迹仅有 **2.6297分** 可纯靠已通关关卡的动作效率追回，剩余主要空间来自通过更多关卡。该结论只描述此公开运行，不能当作私榜比例。

计算：
```
completion_ceiling = 100 * k*(k+1) / (N*(N+1))
```
其中k为已通关数。实际原始分数、ceiling及逐game汇总在 `notebooks/dfranzen-v3-audit-recomputed.json`。

| 游戏 | 四次完成关卡数 | 平均分 | 已观察问题 |
|---|---|---:|---|
| sk48 | 0,0,0,0 | 0.00 | 稳定第一关失败，约25.8万token总耗费 |
| bp35 | 1,1,1,1 | 1.18 | 稳定第二关瓶颈 |
| lf52 | 1,1,1,1 | 1.82 | 稳定第二关瓶颈，机制解释未收敛 |
| wa30 | 1,1,2,1 | 3.22 | 早期瓶颈 |
| m0r0 | 2,5,6,0 | 46.42 | 0–100大波动 |
| tn36 | 7,2,1,7 | 53.52 | 3.57–100大波动，成功时有效利用动画 |
| cd82 | 6,6,6,6 | 81.20 | 已稳定通关，行动效率有空间 |
| lp85 | 8,8,8,8 | 100.00 | 此运行已饱和，不优先优化 |

**tokens字段陷阱**：`game_run.final_generated_tokens`不是整局总tokens，样本中为0；应汇总history中的generated_tokens再加final字段，得到stdout的17,504,777。`solver_note`中还能包含最终没有附着到action的推理token（例如sk48：history61101，note68104）。若研究真正compute成本，需要逐request usage/时间；不能直接读final字段。

## 5. 手工读原始轨迹，定位因果假设

证据保存在 `notebooks/dfranzen-v3-output/`。为阅读去掉重复历史后，另存 `*_compact.json`；它保留原始工具与assistant消息，不执行里面的代码。

### 5.1 sk48：转移正确不意味着目标正确

p0的analysis step16/17附近，agent写BFS寻找自己定义的 `goalA`，找到16动作计划。中间一次因普通变量S没有持久化产生NameError，随后修好。最终真实执行16步，agent的每步预测都与观测相符，但**关卡没有完成**。下一轮它才开始质疑goalA，随后RIGHT实际发生块链式推动，推翻了原来对blocked push的部分假设。

所以：
1. 函数保留已帮助它产生并复用BFS/search/executor，单纯再教“用BFS”价值很低。
2. 在“环境状态预测匹配”之外，需要独立的**目标假设与成功证据**。
3. “自建模拟器中的计划成功”不应变成“真实游戏已理解”的替代指标。
4. 机制模型要记录在哪些观测/对象组合上有支持；新交互出现时局部修订，不能将一个可用函数永久视为真规则。

这是本轮从实际源码和轨迹得出的关键研究线索，不是只引用论文概念。

### 5.2 lf52：有动画接口不等于正确使用

p0在level2后段多次猜测token和peg/pipe关系。step39/40的动作反馈提示中间动画有16个瞬态像素，但agent工具主要检查settled frame和 `no_op`，便把点击解释成无效；它继续在多个假设间口头摇摆。后续还有19帧animation，但没有形成清晰、可区分的机械解释。

可研究：当“settled不变、animation有变化”与模型no-op解释冲突时，只触发一条明确证据事件，并提供小范围动画差异/候选交互；不要默认每一轮都塞入完整timeline。baseline已经有提示，因此新实验应测**是否提高了实际取用和解释动画的比例**，不能只确认新prompt已存在。

### 5.3 tn36：成功轨迹的有效行为

p0完成7关，日志多次遍历 `last_animation_frames`，提取 `plugpos`，比较真实运动轨迹；level7还把“hazard仍致死”当待区分假设，选择既能分辨机制又能保留进展的行动序列。这是可以学习的**行为模式**，不是可硬编码的游戏答案。

建议主线学习这样的证据使用方式与短程序组织，而不是把这三个游戏ID写进solver分支。

## 6. 其他实现的可迁移差异

### 6.1 D'：有趣但未证实的调度对照

shiiin9 v2在运行前替换priority并取消“未启动游戏天然优先”：

```
P = A*M*C + B*phi
A = (1+.5*(level-1))*norm(N)*(300/(300+a))^2.5
M = clip((30000/mean_tokens_per_cleared_level)^.4, .25, 4)
C = .1*max(.1,1-a/115) + .9*max(.1,1-t/T)
T = 225000 * clip(mean_tokens_per_cleared_level/30000,.5,2)^.5
B = 16/14/10/0
```

最后40%时间fade尾项。与原版相比，动作惩罚缓和，探索耐心更长，future reward不再一起乘C；新游戏也参加正常优先级竞争。这可能帮助“需先长时间发现机制”的game，也可能饿死尚未启动的难游戏。作者不公开系数推导，31.54仅一次提交，因此应保留为可解释对照，不照抄“高分即正确”。

### 6.2 Lord Han Solo：程序资产与策略审视

已下载固定source bundle v297（约655KB zip，Kaggle dataset metadata license=Apache2.0），只提取需要读的生产代码，未创建测试文件。

- `inference/agent/python_workspace.py:166`：保存源代码模块时以冻结的观测检查其自写测试，跨回合/level/context复用。模块函数接收显式观测参数，避免捕获陈旧棋盘。
- `tool_agent.py`：每次动作带plan、逐动作变更；game_overs可查询；动画保留16帧、最近16个history entry，blink/tween/path描述。
- `framework/solver.py:239`：strategy audit周期来自初始预算的25%，并非自报的“我卡住了”；prompt要求区别事实/假设，以真正环境观测验证，明确“自己的代码测试通过不是机制完整性的证据”。
- serving使用mixed NVFP4/FP8、patched vLLM，wave式运行、不preempt，重视tool gap内存状态与prefix缓存。

作者明确无法确认这些harness修改单独提高分数。最值得迁移的是代码/证据可复用和被事实触发的假设修订；不为本项目引入测试工程。

### 6.3 sirikilohit：共享时间池的成本教训

v18.1gc采用M72：优先级取“累计weighted levels/tokens”和最近32k tokens进展率的均值，再加UCB探索项。最初300秒slice，当前改成2400秒，注释称110游戏恢复时反复prefill约占10% GPU。这与Franzen只在context eviction交接的取舍直接相关。

其最终层又关闭/覆盖部分早期模块（例如M24 ledger），不能从长notebook里看到某段实现就认定仍启用。v18.1gc新增FP8 KV、16 games、57344→45056截断；header中“v18.1”是作者实验命名，和Kaggle current_version_number不同。

### 6.4 “Superstack”具体代码不等于标题

对sujanmajhisuzan v21与Franzen v3逐cell比对发现：
- 核心大patch没有新算法；新增的是最近3关记忆（从最后assistant文本尾200字符提取）、死亡警告、每12次 `_build_user_prompt` 的audit提示。
- 变量叫 `_consecutive_actions_on_level`，实现却是每次prompt构造加1，因此并非实际action计数。
- death通过旧反馈字符串匹配计数，可能把重述也计入；它没有基于transition ID的去重。
- 固定提示“Same physics/controls persist”比原版“先继承假设、再检查新机制”更强，不适合未经确认的跨level迁移。
- 非真实submission时跳过模型初始化与benchmark，仅生成占位 `submission.parquet`。快速commit成功不等于推理路径有效。
- patch应用失败可以继续用base harness，容易让结果对应的真实算法不清楚。

这些是静态阅读所得，不是运行失败判定。不建议把它作为主基线或一次合并全部变化。

## 7. Models 页的研究价值与误导源

`list_models(search="arc-agi-3")` 返回27项，搜索是全文相关性而非“本比赛高分模型认证”，混入Mistral、ARC-AGI-2和NeuroGolf。这些不计作ARC-AGI-3有效证据。实际高分notebook引用的模型比关键词列表更有决策价值。

| 模型 | 已核验材料 | 研究取舍 |
|---|---|---|
| [Franzen Intel W4A16](https://www.kaggle.com/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1) | v1，重分片不改weights，BF16 PLE，181.24GB；明确Qwen Community License1.0 | baseline精确挂载；不能写成Apache模型 |
| [Franzen MTP drafter](https://www.kaggle.com/models/dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1) | v1，4.16GB，只有draft head，不是独立LLM；同Qwen许可 | 需要与主模型/serving成套复现 |
| [Lord mixed NVFP4/FP8](https://www.kaggle.com/models/lordhansolo/qwen3-8-flash-next-mixed-nvfp4-fp8/PyTorch/hf-mixed-mtp-nvfp4/1) | upstream revision07915ee79ec217c117e8a57bf2557a4a1418c10f；约180.17GB | 后续serving对照，不先换模型再改harness |
| [Naestro27B LoRA](https://www.kaggle.com/models/cputer/naestro-agi3-27b) | v4、rank16 synthetic mechanic-class planning fallback；未提供可核对比赛分数 | 合成训练方向参考，不是现成冠军模型 |
| [perception-512](https://www.kaggle.com/models/mariogemoll/arc-prize-2026-arc-agi-3-vlm) | Qwen3.6-27B合并视觉LoRA；只说local balanced perception slice最优 | 感知微调需证明迁移到整局得分 |
| [ARC Laya](https://www.kaggle.com/models/ser8147/arc-laya) | card自报421M、88.24%分类/100%deadlock、Brier0.0818；无本次比赛分数 | 不能拿分类准确率当RHAE，不优先 |
| [Qwen2-VL2B schema QLoRA](https://www.kaggle.com/models/mikedan7/qwen2-vl-2b-arc3-schema-qlora-bf16) | 作者诚实报告loss5.2265→2.7931，四game/20-action holdout为0关0分 | 明确反例：SFT loss改善不代表交互求解改善 |
| [Wayfinder](https://www.kaggle.com/models/edudev-commons-org/arc-agi-wayfinder-agent) | 模型卡描述CNN+world-model+graph+tree search，未给核实成绩 | 架构愿景，不能作为实证强baseline |

代码仓库 [Apache-2.0 LICENSE](https://raw.githubusercontent.com/da-fr/arc-agi-3-solution/main/LICENSE) 已实际读取。模型的Qwen Community License与比赛奖金条件之间的具体适用性应依据主办方明确答复；本轮不作法律资格结论，也不因此停下研究。

## 8. 建议的研究优先级

1. **先把原版复現为自己的固定版本**：保留同样权重/serving/预算，手动运行一次完整public25，保存逐game/level结果、request usage与少量失败轨迹。把真实结果写入对应progress；代码准备完不等于分数复现。
2. **主实验：证据驱动的机制/目标修订**。在目标预测失败、动画与settled-state冲突、level引入新对象等事件下，输出短的“假设—区分观测—预测—实际结果”。函数保留记录适用状态条件；不重新开启每回合World/Goal/Action摘要。优先看稳定瓶颈是否突破、失败是否减少和tokens是否花在新证据上。
3. **辅实验：缓存成本感知的预算调度**。比较原公式/D'/轻量hazard-value估计，所有版本使用同一harness和time；显式计入冷启动prefix成本，避免把低效切换误当探索。没有必要先写复杂调度学习器。
4. **第二阶段：有限范围机制程序归纳**。从观测归纳局部transition/program，搜索只在证据支持的状态范围里规划；目标假设单独维护。不依赖真实engine clone，不读隐藏源。
5. **条件成熟后才做合成训练/LoRA**。现有公开模型不能证明直接SFT就是强方向；应针对轨迹中可计数的缺陷，如取用动画、提取关系、区别goal和dynamics，设计训练任务并以整局指标复核。当前离截止较近，先利用现成大模型与harness产出的轨迹。
6. **吞吐保持为乘数**。基线已做大量SM120优化；先量化GPU是否在prefill、decode还是tool gap耗时。只有发现实际瓶颈再改engine，不先重造serve stack。

实验结果至少区分：public demo、正式public LB、作者报告、自己的运行；同批次多个pass共用调度预算时不要声称独立重复。人工抽查指定失败轨迹即可，本轮没有新测试文件或自动测试工程。

## 9. CLI实物与下一位接手者入口

已验证成功：
```bash
kaggle kernels pull dfranzen/arc-agi-3-milestone-2-solution -p research/notebooks/cli-baseline -m

kaggle kernels output dfranzen/arc-agi-3-milestone-2-solution \
  -p research/notebooks/dfranzen-v3-output \
  --file-pattern '(^benchmark.json$|^(sk48|lf52|tn36).*p0_requests.jsonl$)'
```

CLI2.2.4帮助宣称可追加 /version，但本次 `.../3` 得到403；不带版本成功，逐cell与MCP current_version_number=3内容完全一致。固定下载文件hash，而不声称版本化pull已经验证成功。CLI ipynb SHA256：
`88a379f17c3a4ba8c98715fc23155346ccd6eb289bdafebadfc61a3178f9d9bd`。

`cli-baseline/kernel-metadata.json` 是真实CLI格式：`id`为owner/slug、`id_no`为原notebook ID，字段为 `dataset_sources`、`model_sources`、`competition_sources`。创建我们自己的private notebook时必须改id/title、去掉原id_no并设 `is_private=true`，保留输入与指定GPU；不能把MCP的snake-case metadata原样当CLI push metadata。

本轮没有push、没有提交、没有消费我们的Kaggle GPU额度。源文件与公开输出仅用于阅读分析。

