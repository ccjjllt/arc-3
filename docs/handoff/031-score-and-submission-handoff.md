# 031 提分验证与真实提交交接方案

后续研究优先级及公开候选的试验入选规则以[032–033交接](032-033-memory-and-controller-handoff.md)为准；本文保留031执行流程与当时决策记录。新交接明确：缺少准确高分绑定不妨碍低成本机制实验，但不能据此声称已验证高分。

基点：`229e090`；核验日期：2026-10-21，北京时间。目标是尽快取得有能力增益依据的新 submission，争取奖牌。**保留009的31.16；停止原样重提030；优先验证009＋031精确像素。** 本文区分已完成、待验证、正式结果，不把Notebook构建或开发池成绩写成提分提交。

**当前执行点：031 v1同状态诊断已失败；补齐系统字段合同的v2已启动唯一一次自然短跑。** 实际Notebook为`zhuating/arc3-031-natural-aligned`，Notebook v1、helper v2；见[启动记录](../../experiments/031-natural-launch.json)。接手先读取此作业，不重复push。031全池、GPU save和正式提交尚未执行。

## 当前状态与目标

| 项目 | 已核实事实 | 下一步含义 |
|---|---|---|
| 最佳正式版本 | 009 v2，submission **57101330**，COMPLETE，**31.16** | 保留原Notebook和提交记录 |
| 最新正式版本 | 030 v1，submission **57447779**，COMPLETE，**24.40** | 比009低6.76，不原样重提、不继续容量搜索 |
| 030开发池 | 42.6134→47.1699；103→102关；12题涨、10题跌 | 单轮收益存在，但不稳定，未迁移到正式榜 |
| 031精确像素v1 | 同状态GPU对照已COMPLETE，三切点两臂均0新增；ft09仍错误填色、未读取runs | 不晋升；只补齐系统字段合同后给v2一次自然短跑 |
| 031正式候选 | 已建立独立构建器、配置及Notebook；16项静态检查通过 | 仍需模型验证、候选自身GPU save、正式提交 |

10月21日API返回4566队，本队`teamId=17139255`、队名ccjjllt、公开排名393，约前8.61%。读取了榜单前500队，分页不是原子快照：铜牌附近第456名30.85，银牌附近第228名32.22，金牌附近第19名37.98。当前公开分数在铜牌附近仅多0.31，距银牌附近1.06；**短期以扩大铜牌余量、争取银牌为实际目标，距本次公开金牌附近分数约6.82分，不能换算成私榜所需提升。**这些只是按公开队数和位置估算，最终奖牌看私榜、有效队伍及资格。第5名49.85，奖金和奖牌是不同目标。

比赛截止为**北京时间2026-11-03 07:59**；每日最多1次正式提交，最终可选2份。10月21日11:58、031启动前的zhuating快照为提交额度`numAllowedNow=1`，CLI显示GPU余额约23.74h；余额不是本作业实际计费，也不是独立RTX型号的额度保证。启动、正式提交前均重新查询。[本次在线原件](../../research/snapshots/2026-10-21-handoff/) · [官方比赛](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3) · [奖牌规则入口](https://www.kaggle.com/progression/competitions)

## 研究判断

030的持久化确实被采用，但会同时延续正确计算和错误计划。公开收益主要来自r11l、cd82，而本轮基线在这两题恰好偏弱；历史公开基线波动约7.82分，超过本轮净增4.56。正式轨迹未取得，不能断言退分全由RESET未清缓存、普通异常后的半成品、OOM或时间不足造成。030小修可留档，不占下一轮主要GPU预算。

028已经证明“模型生成、执行并使用修复代码”仍可能把图案背景格误填成白格。031针对这个已定位的输入错误，在现有`current_frame.segmentation`节点增加`runs=[[row,col_start,col_end_inclusive],...]`，直接给出真实像素足迹。它保留009的Python生命周期，避免引入持久状态。代价也明确：示例帧默认输出约增加46.5%，模型可能继续只打印旧字段；**接口存在不等于采用，采用也不等于涨分。**

014/027调度、019 FP8 PLE、020新状态接口、021检查接口、026提示修复、028当前修复版均已有失败或不足证据。本轮不叠加这些机制，不重开提示参数搜索。空动画字段和RESET失效编号属于独立小修，不偷偷混入031对照。

## 最短验证顺序与停止规则

### 1. 先复用真实失败状态，约0.5–0.8 GPU小时

使用已导出的028包：ft09的27动作切点、tu93的276动作切点、r11l正常控制；同帧、同消息、同保留函数。包内历史图片已对称删除，只能称两臂恢复输入一致，不能称完整原会话逐字恢复。每臂三个切点并发，各250秒、最多30个新增动作，按包内固定约束执行。baseline先、031后，共享一次模型加载，臂间清缓存。

新增`segmentation_forks.py`只复用恢复逻辑，完全不调用028程序修复。031安装会修改进程级分割函数、sandbox和工具说明，**必须使用独立CPU进程隔离A/B**；不能在一个进程里给B装全局patch后声称A未受影响。复放必须逐像素匹配，记录输入hash、函数hash、后续真实请求、完整动作id与data。

判断只看四点：执行代码是否读取runs；是否用它构造正确像素集合；是否改善后续动作、恢复速度或新增关卡；输出及时间成本是否抵消收益。切点沿用了旧历史，可能使模型固守旧提取器，因此该实验只回答同状态纠错能力。原有前缀得分不能计为031收益。

### 2. 必要时接10题自然短跑，约0.7–1.0 GPU小时

若切点出现真实纠错，或旧历史导致无法判断自然采用，用固定10题各900秒观察自然运行。相关关卡未到达时标记“窗口未回答问题”，不能当作成功或失败。若两种窗口均有机会读取精确像素，却仍不消费或继续填错，就停止本版；不要以字段安装成功为由扩到全池。

### 3. 有增量证据后，冻结候选做全25题A/B，约4.3–4.8 GPU小时

每臂7254秒、10 streams、同一模型和服务，baseline先、候选后。新配置将`request_deadline=false`、`warmup_action_games=1`真正传入runner，与009正式的请求入口及warmup行为对齐；不沿用旧031配置的deadline补丁和零warmup。仍需承认公开OFFLINE题池、按题数缩短的预算、日志和外部收尾与正式长运行不同；研究还有全局`soft_end`截止，正式为`None`，研究跳过重复的全模型预读但保持数值服务不变。

主指标为官方公式下的25题平均分，关数、全通数、动作和token用于解释。读取最大胜题和最大败题，和历史基线分布对照，检查完整覆盖、缓存清理、排空、截止与输出截断。无效运行不能算效果失败，也不能删去失败题后重算。

| 观察结果 | 决策 |
|---|---|
| 平均分无增益或回退 | 停止本版，不提交原版031 |
| 正增益，有实际纠错带来的推进，运行完整且无明显集中风险 | 立即进入候选自身save与正式提交 |
| 收益主要来自少数本轮异常偏弱的基线，或顺序影响无法排除 | 同一实现最多一次反序确认；结合两轮逐题证据决定，不边跑边调 |
| 漏题、预算不足、残留请求或崩溃 | 明确标失效，修具体故障后最多补一次有效运行 |

不设任意“至少+10分”门槛，不要求所有辅助指标同时上涨；也不把一次正均值称为稳定提分。通过后的正式隐藏评测是下一份必要证据，不继续无限追加验证。

## 可执行文件与命令

| 用途 | 路径 |
|---|---|
| 独立机制 | `src/arc3_research/segmentation_runs.py` |
| 同状态续跑 | `src/arc3_research/segmentation_forks.py`、`experiments/031-segmentation-forks.json` |
| 对齐自然短跑 | `experiments/031-natural-aligned.json` |
| 对齐全池 | `experiments/031-full-aligned.json` |
| 正式构建 | `scripts/build_031_submission.py`、`experiments/031-runs-submission.json` |
| 正式候选原件 | `experiments/031-submission-source/`，含manifest和static-checks |
| 本轮执行状态 | `docs/progress/031-exact-pixels.md` |

诊断v1已实际完成，实际地址为`zhuating/arc3-031-recorded-state-exact-pixels`，平台按title生成slug，和原metadata请求的slug不同。见`experiments/031-forks-launch.json`及[诊断结果](../../research/031-forks-results.md)。**不重复push或重跑v1。** 其Notebook冻结保留；当前helper将升级为v2，不能直接用当前helper重构v1。以下命令使用平台实际地址读取原件：

```bash
KAGGLE_API_TOKEN="$HOME/.kaggle/access_token_zhuating" \
  kaggle kernels status zhuating/arc3-031-recorded-state-exact-pixels
KAGGLE_API_TOKEN="$HOME/.kaggle/access_token_zhuating" \
  kaggle kernels output zhuating/arc3-031-recorded-state-exact-pixels -p runs/031-segmentation-forks
```

每次上传记录实际owner/slug/version、输入hash、源码hash、返回时间和GPU型号。下载前后核对latest版本，没有固定版本下载成功证据时不声称锁定下载。正式与研究helper必须同hash，候选独立打包不得装入fork、030或其他求解补丁。

v1已经显示工具说明含runs、系统节点清单却遗漏该字段。v2仅补齐这处合同，先执行`031-natural-aligned`一次自然短跑；通过才执行`031-full-aligned`。它们均需使用v2新hash重新构建，不得拿v1诊断为v2背书。

当前自然作业读取与分析入口：

```bash
KAGGLE_API_TOKEN="$HOME/.kaggle/access_token_zhuating" \
  kaggle kernels status zhuating/arc3-031-natural-aligned
# COMPLETE后取benchmark、experiment-manifest、arm-metadata、请求与transcript；
# 大输出使用--file-pattern，仅筛需要的文件。下载前后核对仍是Notebook v1。
KAGGLE_API_TOKEN="$HOME/.kaggle/access_token_zhuating" \
  kaggle kernels output zhuating/arc3-031-natural-aligned -p runs/031-natural-aligned
python3.12 -B scripts/analyze_031_natural.py
```

v2 helper hash为`b4c5cc5b398d8b7365c1f2e2b022b5f3bc7a575afcc7e3e56c46b5a92450deee`；自然Notebook为`01fa4dc75e14a23f8a90150c6a2d6966bf856fd2fb7860d04232e94fec82d9cf`。全池预构建目录为`notebooks/031-full-aligned`，通过效果判断后才允许push，时限18000秒。全池分析必须使用该目录的配置和实际25题结果，不能沿用900秒的短跑预算检查。

通过效果判断后，才运行正式候选自己的save smoke：

```bash
python3.12 -B scripts/build_031_submission.py \
  --config experiments/031-runs-submission.json --output-dir experiments/031-submission-source
KAGGLE_API_TOKEN="$HOME/.kaggle/access_token_zhuating" \
  kaggle kernels push -p experiments/031-submission-source -t 32400 --accelerator NvidiaRtxPro6000
```

验证候选自身sb26、cd82两题有真实非RESET动作、生成token和合法结束；核对031安装记录、源码版本及`save-smoke-report.json`。save产生的官方占位parquet不计分，不能把push或COMPLETE save称作正式submission。smoke开始后不再push该slug；需要修改则使用新版本重新核验。

再次查询提交额度，对刚通过smoke的**实际版本号**执行：

```bash
ARC3_SMOKE_VERSION='' # 填入实际通过smoke的版本号
ARC3_NOTEBOOK_SHA=''  # 填入核验过的冻结Notebook SHA256
: "${ARC3_SMOKE_VERSION:?请先填写实际smoke版本}"
: "${ARC3_NOTEBOOK_SHA:?请先填写已核验的Notebook SHA256}"
KAGGLE_API_TOKEN="$HOME/.kaggle/access_token_zhuating" \
  kaggle competitions submit arc-prize-2026-arc-agi-3 \
  -k zhuating/arc3-031-runs-submission -v "$ARC3_SMOKE_VERSION" \
  -f submission.parquet -m "031 exact pixels; own save passed; v${ARC3_SMOKE_VERSION}; sha ${ARC3_NOTEBOOK_SHA}"
KAGGLE_API_TOKEN="$HOME/.kaggle/access_token_zhuating" \
  kaggle competitions submissions arc-prize-2026-arc-agi-3 --format json
```

用户本轮已明确要求实际提交；验证通过后直接执行，无需重复索要泛泛确认。提交响应不明确时先查列表和description/hash，不盲目重复请求。保存新submission ID、创建时间、状态和Notebook版本，等待COMPLETE后报告真实public score及相对31.16的变化；ERROR则区分平台与代码原因。

## 时间和失败后的选择

从GPU可执行且无同项目冲突时T0起，目标T0+2小时得到机制结论，T0+8小时完成首轮全池及提交判断，T0+24小时取得新submission ID，T0+48小时取得正式结果；排队、额度与平台故障单列。全池反序确认只在上述条件触发时进行。含一次确认的计划研究与save预算约11–13 GPU小时，保留其余余额应对正式候选修复；这不是计费承诺。

若031失败，不为满足“提交过”而重交009或030。限定一次不超过1小时的公开候选刷新，只考虑能绑定明确源码版本与更高实际正式成绩、依赖可用且可复现的候选；作者队伍高分和Notebook标题都不能替代绑定证据。无合格候选时如实交接“当前没有通过验证的新提分submission”，保住009并说明下一项具体证据缺口。10月29–30日保留最终选择、恢复和复跑窗口。

最终交付固定为：**当前正式最佳；031机制与全池结果；同一实现的GPU save证据；新submission ID／状态／得分；剩余预算与下一条决策。** 奖牌是目标，不能由公开25题结果作保证。
