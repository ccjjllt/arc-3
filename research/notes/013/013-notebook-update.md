# 013 — 公开 Notebook 与权重更新审计

检索日期：2026-10-17，Asia/Shanghai。刷新本赛 `ScoreDescending` 与 `DateRun` 各前 20 项，另按四名作者检索；取得 **12 本**当前公开 Notebook 的元数据和完整源码，逐 cell 比对其中 10 本与旧档，对 Fu、Heliosli、Sujan、Action7 Shadow 做机制和执行入口深审。本轮仅解析 JSON、AST 字面值、压缩文本和源码 diff，未执行下载的 Notebook 或其模块，未启动 GPU、游戏、模型请求或正式提交。

**没有找到已证实能把本项目 31.16 提升至金牌区间的公开替代方案。** Franzen 主基线及四个既有重要家族未变；新增有效研究机制是 Fu 的 pace 开关、Heliosli 的停滞后清空推理，以及 Sujan 的模拟器校验和宿主世界模型。存在代码、正确接入、模型实际采用、公开集收益、正式榜分数，仍是五个不同证据层级。

完整原始返回、当前源码、可读导出、cell diff、提取资产及哈希位于 [2026-10-17](../../notebooks/2026-10-17/)，机器可读索引为 [audit.json](../../notebooks/2026-10-17/audit.json)，可重复静态检查为 [build_static_audit.py](../../notebooks/2026-10-17/build_static_audit.py)。索引分别保存 API 中原始 source 字符串、落盘文件和 cell 内容的 SHA256；原始字符串与文件末尾换行的差别不混为源码变化。

## 1. 列表发现与分数绑定边界

下表是接口返回的顺序，**不是本次核验的分数排名**。两个列表均无数值 score、submission ID 或对应 native scriptVersionId。DateRun 还混有附着本赛但方法无关的 Notebook。原始顺序与时间分别保存在 [ScoreDescending.json](../../notebooks/2026-10-17/ScoreDescending.json) 和 [DateRun.json](../../notebooks/2026-10-17/DateRun.json)。

| 顺位 | ScoreDescending ref | DateRun ref |
|---:|---|---|
| 1 | dfranzen/arc-agi-3-milestone-2-solution | miyushiro/notebook3fa387f4f2 |
| 2 | jingshuifu/arc3-m2-solution | professorice/arc-agi-3-m2-qwen3-8-27b |
| 3 | heliosli/try-merging-it-you-might-get-lucky-and-win-gold | efthimiosfousekis/arc3-sota-unified-v1 |
| 4 | jingshuifu/arc3-m2-solution-v3 | mohamedmalikturay/arc-agi-3-milestone-2-solution-3e9adb |
| 5 | greenalgeria/arc-agi-3-milestone-final | pajakchaithongchai/gemma-4-developer-agent-competition |
| 6 | amatlas/dfranzen-fork-d-prime | hnd842005/qa-dar |
| 7 | sujanmajhisuzan/arc-agi-3-m2-top-submission | kriztianrubin/fork-of-thearbiteriii-5 |
| 8 | habanwer/arcaid3-lexicon-view-dfranzen-m2 | kai57sh/arc-agi3-vlm-test |
| 9 | zhangyues0000/arc-agi-3-m2-franzen-fork | web4app/bagging-tf-rmd |
| 10 | leoprovorov/fable-astra-play-arc-3-handbook-harness | kriztianrubin/atlas-ai |
| 11 | skarin/arc-agi-3-27-80-lb-100-trajectory-audit | tsitsinodzotsenidze/notebook43f8579dd8 |
| 12 | shiiin9/affectify-arc-31-54-in-a-single-sub | azouzibillel/jadda-hijaya |
| 13 | sigeward/arc-agi-3-milestone-2-solution | naileafalcon/arcmx |
| 14 | manwithacat/digital-mouse-qwen-genome-baseline | trungkiennguyn/myfeat-16102026 |
| 15 | yukailiu/arc-agi-3-champion-solution | mayankraaz/lb-46-2-arc-agi-3-neural-bfs-episodic-solver |
| 16 | spark328/arc-prize-2026-arc-agi-3-franzen-v1 | kriztianrubin/mosaix-vii |
| 17 | ouyangruize/arc-agi-3-milestone-2-solution | noormamhidayat/arc-prize-2026-sovereign-dsl-solver |
| 18 | prvsiyan/arc-agi-3-stock-taaf-action7-shadow | panxiaoxuan/arc-agi-3-milestone-2-solution |
| 19 | lwq255/arc3-dfranzen-m2-guarded | yuan1103/b5-2-hmm |
| 20 | dhruvb2028/arc-agi-3-milestone-2-solution | dungcongty/gemma-4-26b-a4b-it |

本轮固定的是 `get_notebook_info` 当次返回的 `current_version_number` 与源码哈希。搜索列表的运行时间与详情元数据的运行时间继续不一致，例如 Franzen 搜索返回 10/03、详情返回 10/14，但 cell 内容与旧档完全一致。因此不把详情时间当作新版本证据。12 本返回源码的 cell outputs 均为空；这不等于远端没有运行产物，只表示本轮源码响应没有带可验证运行结果。

本报告没有把作者团队当前榜分、标题里的 “gold / Champion / LB 46.2”、Code 顺位、历史上游分数或保存成功绑定给当前源码。尤其当前榜首团队的高分，不因其早期公开过 Duck 就能归给早期 Duck Notebook。本项目 009 的正式提交分数也不能反向证明各 fork 的效果。

## 2. Franzen 与既有主要家族：没有源码升级

| 本轮读取对象 | 当前 Kaggle 版本 | 相对旧档 | 挂载模型变化 |
|---|---:|---|---|
| [Franzen](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution) | 3 | 23 cells 全部一致 | 无 |
| [Jeroen Duck](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner) | 6 | 17 cells 全部一致 | 无 |
| [Scott FlashNext](https://www.kaggle.com/code/scottlegrand/taaf-flashnext-sheetu12b-0922) | 1 | 19 cells 全部一致 | 无 |
| [Lord Han Solo](https://www.kaggle.com/code/lordhansolo/built-on-tufa-labs-duck-harness-milestone-2) | 306 | 10 cells 全部一致 | 无 |
| [sirikilohit 18.1gc](https://www.kaggle.com/code/sirikilohit/arc-agi-3-duck-18-1gc-submit) | 5 | 50 cells 全部一致 | 无 |

四名作者各自的 DateRun 结果没有显示更晚的新公开 Notebook：Jeroen 最新是 7/01，Scott 9/22，Lord 10/01，sirikilohit 10/06。检索范围是这些用户名下附着本赛的公开内容，不能据此断言整个团队没有其他账号或尚未公开的研究。搜索结果保存为 `author-*.json`，详情与差异进入统一 audit。

四名作者的模型列表只有 Lord 返回两项：[旧 mixed NVFP4/FP8](https://www.kaggle.com/models/lordhansolo/qwen3-8-flash-next-mixed-nvfp4-fp8) 以及此前未存档的 [Swift 1.5 NVFP4](https://www.kaggle.com/models/lordhansolo/swift-1-5-qwen3-8-flash-next-nvfp4)。后者更新日期为 **9/28**，并非 10/13 后发布；variation v1、native version ID 1007146、约 186.46 GB。作者描述称保留 UkisAI 上游 revision `3ff0520224f264a2d0ac4ab56ece8f2f13aadb38` 原张量，H100 TP4/EP/Marlin 仅做过烟测，原生 Blackwell 与量化质量待验证，并标明 Swift 与 Qwen 两套许可。这里只记录模型页声明和元数据，未下载权重、验证张量或作奖金资格判断。Lord 当前 Notebook 仍挂载旧 mixed 模型，不是 Swift；没有分数绑定证明换 Swift 能提高本项目表现。[原始模型列表](../../notebooks/2026-10-17/models-lordhansolo.json)

## 3. Fu v2 / 新 v3：两个独立调度消融

[Fu v2](https://www.kaggle.com/code/jingshuifu/arc3-m2-solution-v2) 当前 Kaggle 版本仍为 2，23 cells 与 10/13 全部一致。它仅把 baseline 的 `TAIL_LOOKUP='remaining'` 改成 `'1'`，打开已有经验 80k tail 表；非正式 demo 保存配置另有变化，正式模型与求解机制未变。[源码](../../notebooks/2026-10-17/jingshuifu__arc3-m2-solution-v2/readable.py)

新增 [Fu v3](https://www.kaggle.com/code/jingshuifu/arc3-m2-solution-v3) 的 **Kaggle 版本是 1**。“v3”是独立 Notebook 的名称。与 Fu v2 仅 cell 4 不同：`PACE` 从 0 到 1，同时 `TAIL_LOOKUP` 从 1 恢复 remaining。故相对 baseline，它是 **pace 单开关**；相对 Fu v2 则是两项配置变化，不能把二者直接差异归因于其中一项。[精确 diff](../../notebooks/2026-10-17/jingshuifu__arc3-m2-solution-v3/source.diff)

Pace 的实现与 API 路径已经存在于 baseline，并会生效：

- 每完成一关，用该关生成 tokens 与公开关数参考成本之比更新 log EWMA，旧值/新值权重 0.6/0.4。
- 用 `completed/(completed+3)` 收缩后取指数，夹在 0.5–2。尚未完成关卡时 pace=1；第一关一直卡住的游戏不会因为该开关直接获得自身新证据。
- 参考表来自 1,417 个历史 reached-level episodes 的按关数 Kaplan–Meier 截尾均值，上限 120k tokens；不依赖推理时的游戏身份，也不是校准的隐藏集成功概率。
- 优先级除以 pace，同时当前关的 token 停滞衰减尺度乘以 pace。因此“更慢就总是更低优先级”并不成立：较慢 pace 也容忍更多当前关 token，长停滞区间可能出现反向作用。
- 实际重排仍在 context trim 后的 handover；没有改变 fresh-game band、首次入场顺序或强行打断温热 KV cache 的规则。

证据：[ProgressPace 与 priority_value](../../runtime-bundle/src/ARC3-Inference/inference/agent/priority_scheduler.py)，[reference](../../runtime-bundle/src/ARC3-Inference/inference/agent/priority_pace_reference.json)，`tool_agent.py` 的 `_update_summarized_knowledge_from_step_summary` 与 `_maybe_handover`。需要真实 token 账本、逐关边界和 handover 日志才能评估队列效果；紧凑 action-attached tokens 不足以精确复原。Fu v3 的 Code 第 4 位不是提分证据。

## 4. Heliosli v4：已经从 scoped memory 换成停滞重启

[当前 v4](https://www.kaggle.com/code/heliosli/try-merging-it-you-might-get-lucky-and-win-gold) 仍为 11 cells，变动集中于 0/1/3/4/5。10/13 v2 的 scoped data memory 已从当前执行路径撤掉，不能继续描述它为当前公开主方案。原 Franzen 大 patch 保持一致。[差异](../../notebooks/2026-10-17/heliosli__try-merging-it-you-might-get-lucky-and-win-gold/source.diff)

新 [stagnation_restart.py](../../notebooks/2026-10-17/heliosli__try-merging-it-you-might-get-lucky-and-win-gold/extracted-assets/stagnation_restart.py) 在每次 analyzer 前、工具调用结束后检查本关生成 tokens；达到 **96×1024=98,304** 且关卡未完成时，每关最多一次：

- 清空 `_history_messages` 与 `_kept_functions`，取消 yield-resume，重建包含当前棋盘的完整 opener。
- 保留真实游戏、当前状态、完成关数、观察历史、death ledger、token 统计、动作和运行预算；不执行 RESET。
- 给模型一次重审目标、控件与假设的提示。HTTP 请求失败且没有新生成 token 时，继续保留该 opener 通知，避免清空后失去解释。
- 调用 `_note_history_evicted()`，因而也会触发原调度 handover。即使后续分数改善，也需区分重审假设与让出 slot 的贡献。

安装器核对原 ToolAgent Git blob hash 并精确替换调用锚点，是真正接入的行为，不是未调用辅助函数。但正文明确没有 GPU 质量配对比较，而是根据回顾性失败分析直接提交。96k 阈值没有本轮可查的独立选择依据。对已接近正确模型的游戏，也可能丢掉有用函数并重新支付推理与 prefill 成本。

非正式 Save & Run 只写占位 parquet，正式分支才运行求解器，所以保存成功不证明服务器或机制有效。本项目若拆这个因素，应保留真实评估分支与失败证据，不能把 packaging 完成当作实测通过。

## 5. Sujan v29：有真实新增机制，也有不能直接泛化的假设

[Sujan 当前 v29](https://www.kaggle.com/code/sujanmajhisuzan/arc-agi-3-m2-top-submission) 相对旧 v28 改动 cells 0/2/3/4/15/16/19/22。原大 patch 扩充并新增第二份 UND patch；第二份不是注释里的宣传：cell 3 解压写盘，cell 4 顺序 `git apply` 两份 patch，相关环境开关也在导入前开启。提取文件见 [extracted-assets](../../notebooks/2026-10-17/sujanmajhisuzan__arc-agi-3-m2-top-submission/extracted-assets/)。本轮静态提取了新增文件中的 45 个 Python 文件，没有运行它们或声称全套测试通过。

### 可拆出的最小机制：按真实转移校验模拟器

第一份 patch 的 [world_model.py](../../notebooks/2026-10-17/sujanmajhisuzan__arc-agi-3-m2-top-submission/extracted-assets/patch-files/ARC3-Inference/inference/utils/world_model.py) 有 `check_sim`、`compare_grids`、`SimFrame` 与有界 BFS `search`。sandbox 实际注入 `check_sim/search/act_checked`，system prompt 在开关打开时说明它们。

`check_sim` 让模型写出的 `simulate(frame, action)` 回看最近至多 25 个有效同关真实转移，过滤 RESET/automatic/跨关，返回匹配率及坐标反例；无游戏动作成本。`act_checked` 在长动作批次的每一步先预测、再执行真实动作、再比较；首次偏差抛异常并停止余下批次，跨关/结束立即返回。这比单纯添加 BFS 更值得移植：底座本来允许写 BFS，欠缺的是低成本暴露错误机制并在错误计划继续执行前中止。[sandbox 接入，cell 2](../../notebooks/2026-10-17/sujanmajhisuzan__arc-agi-3-m2-top-submission/cells/002.txt)

可用并不等于可照抄：

- `act_checked` 传入模拟器的只有 action 名称，CLICK 的 x/y 没有一起传入；通用版本必须保留完整动作对象。
- 默认比较和 BFS hash 忽略外圈 4 像素，可能漏掉真实机制或目标；应使用明确且可审计的比较区域，不能把 HUD 假设硬编码为所有游戏的真理。
- 未定义 `simulate` 时直接走普通 `action`；没有证据覆盖时也不能称“验证通过”。当前源码没有强制模型采用工具。
- 回测匹配不能证明目标正确或预测能外推；需要在新真实动作上产生可检查的预测与反例。

中期最小实验可只提供“对真实历史转移校验 + 一步预测后的偏差停止”，保留原模型、serving、调度与观察方式。不必同时引入整个 UND、自动角色猜测、额外记忆和新的 BFS。需记录采用率、校验覆盖、错误假设被揭示后是否修正、停批节省的动作，以及是否因此获得新关卡；没有这些，CPU 函数正确只能支持工程合同。

### UND 宿主世界模型的实际入口与局限

第二 patch 把 `UndSession` 接入 ToolAgent，逐动作观察真实 transition，维护 claim graph、observed edges、对象追踪、timer、goal、death/no-op guard 和 telemetry；sandbox 通过 RPC 注入 `wm`。`wm.run` 每步调用 begin/end prediction，出现 MISMATCH/NULL 后停止后续动作；`wm.plan` 调用宿主 `CoreModel` 与 planner。`ARC3_UND_OBSERVE/TOOLS/DIGEST/HOOKS/UNDO/TIMER` 等实际开启，context-collapse 设为 0，不应把未开启的 collapse 也算作当前行为。

然而该实现仍有局限：[session.py](../../notebooks/2026-10-17/sujanmajhisuzan__arc-agi-3-m2-top-submission/extracted-assets/patch-files/ARC3-Inference/inference/und/session.py) 无 grounded actor claim 时优先猜颜色 1，否则猜最稀有非零色；[CoreModel](../../notebooks/2026-10-17/sujanmajhisuzan__arc-agi-3-m2-top-submission/extracted-assets/patch-files/ARC3-Inference/inference/und/core_model.py) 的泛化模拟主要依赖位移与颜色交互假设。`wm.plan` 接受的 `max_depth`、`strategy` 在其函数体中未下传给 planner；registry 能注册模型 hook，但本轮未发现 CoreModel 的预测入口调用该 registry，因此注册成功不能当成自定义机制已经参与规划。把这套通用猜测强加给所有关卡可能生成自洽但错误的模型。

v29 仍组合旧 Apex 深关优先级、Fresh band 替换、网络 timeout 下限等多因素。cell 16 的 yield/auto-frame-diff 环境设置仍晚于 benchmark 导入；不能按标题认定所有开关生效。cell 20 仍在正式 gateway 前无条件写 score=1 占位 parquet，并在退出缺文件时补写；不能移植这种结果兜底。没有当前源码绑定的正式分数或一因素比较，故本轮只保留上述可拆机制，不推荐整体 fork 替换。

## 6. 新高排 Action7 Shadow：当前版本实际是 canary

[prvsiyan Action7 Shadow v19](https://www.kaggle.com/code/prvsiyan/arc-agi-3-stock-taaf-action7-shadow) 有 111 cells，大量旧实验是 raw cells 或只赋值的压缩历史文本。当前最后一个可执行 cell 解压哈希绑定的 canary 源码，再运行受限原版 Franzen V1 服务与单动作检查；并不是把所有旧 Action7、动画、transport 和 adaptive extension 一起启动。

本轮仅静态解压阅读 [run_native_canary.py](../../notebooks/2026-10-17/prvsiyan__arc-agi-3-stock-taaf-action7-shadow/extracted-assets/run_native_canary.py)。它明确拒绝 competition rerun，单游戏、90 秒游戏预算、75 秒 analyzer、最多 2 个动作（含 warmup）、1500 秒受监督总时限；不生成正式 submission。正文将 34.30 标为上游 V1 分数，不是 canary 成绩。它提供的是复现与调用链验证思路，没有当前 agent 的新提分因素，因此不因 Code 第 18 位或标题里的 Action7 纳入算法候选。

## 7. 最新列表两项快速排伪

- [professorice：标题 Qwen3.8-27B](https://www.kaggle.com/code/professorice/arc-agi-3-m2-qwen3-8-27b)，实际 v1 代码、模型输入和正文均是 **Qwen3-VL-4B-Instruct**。相对 Franzen 改模型、关 thinking、移除 AutoRound/MTP/线性注意力 flags、tool parser、sampling/serving 设置和 smoke 范围。是小 VLM 换底座实验，不是已验证的 27B 或金牌配置。[diff](../../notebooks/2026-10-17/professorice__arc-agi-3-m2-qwen3-8-27b/source.diff)
- [mayankraaz：标题 LB46.2 Neural BFS](https://www.kaggle.com/code/mayankraaz/lb-46-2-arc-agi-3-neural-bfs-episodic-solver)，当前 v3 是挂载 Keith Tyser NVFP4/vLLM bundle 的启动外壳。执行源码含 vLLM profile、gateway、watchdog、28 并发/7920 秒等配置，但标题所指 Neural BFS/episodic 的新增实现或 46.2 对应运行证据未在返回源码中提供。Markdown 消融表无 submission/version/产物绑定，不能当成实测。Save 模式跳过 serving，末尾缺文件时生成占位 parquet；不能用保存成功证实正文分数。未进一步下载其 dataset bundle，故不声称包内不存在这些能力。[源码](../../notebooks/2026-10-17/mayankraaz__lb-46-2-arc-agi-3-neural-bfs-episodic-solver/readable.py)

## 8. 对本项目下一轮的影响

**本轮新增资料不足以推翻先做低成本、单因素调度对照的安排。** 首轮仍推荐 Fu v2 所代表的 **80k tail 单开关**：已在本项目同一底座中实现，10/13 已完成静态敏感性审查，不新增 prompt、感知或函数保留机制，25 游戏下能观察排队竞争。必须记录真实 handover、首动作覆盖、prefill 和关卡进展，不能把原固定轨迹上的优先级变化称作得分回放；也不承诺它能弥合金牌差距。

新增调度备选是 **pace 单开关**，需先把逐关 token 账本与动态 handover 路径审清，再与同一 baseline 比较，不能与 tail 同时开启后归因。Heliosli 96k 重启没有更强收益证据，且改变推理与调度两条路径，暂后排。

面向突破机制理解，中期保留 Sujan 的**按需真实转移反例校验**，按上述最小边界重写并先筛模型采用；它比整体引入 UND 更容易识别失败来源。它与本项目独立研究的短期变量交接可以分别立项，不能一次合并后用分数证明其中某个机制。当前 12 本源码与公开权重没有提供“直接合并即可金牌”的证据，也未解决奖金资格的模型许可确认问题。
