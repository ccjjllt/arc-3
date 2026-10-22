# 实施交接：020 结果与下一步可执行工作

> 2026-10-19 实施更新：预测失配停批已接入 [checked_action.py](../../src/arc3_research/checked_action.py)。CPU 路径见 [021进展](../progress/021-checked-execution.md)。12 游戏 GPU 短筛尚未启动。不要提交 020。

更新：2026-10-19，Asia/Shanghai。交接基于仓库 `4be361d`，以及本次取回的 020 v1 输出。**你接手后不要直接提交当前 020 正式 Notebook：研究版已完整跑完，均分 41.21 → 26.51，下降 14.70。** 本轮按你的要求交接实施；没有启动下一批实验或新的正式提交。

## 先读这份结果

12 个熟悉的官方开发游戏，baseline → grounded_state，各 1800 秒。两臂完整、预算一致、缓存清理确认、服务正常关闭。完成关数 44→36，全通 3→1，动作 1476→1825。GPU 求解窗口采样均值 92.22%／90.81%，会话内部 70.40 分钟。计算资源已被有效使用，但本版没有取得解题收益。

最大退分是 `cd82`（100→4.90，6→2关）和 `ft09`（100→47.62，6→4关）；`ar25` 与 `re86` 各多一关。只做了一轮固定顺序对照，不能把每个变化归因到新 API，更不能外推私榜。

`ar25` 的 94 个已返回、去重 Python 调用没有使用新增 region 接口；它的局部涨分不能归因于新通道。`ft09` 也未使用；`cd82` 仅在末尾调用一次打印区域，尚未形成后续求解消费。另一方面，`r11l`确实把`positions()`用于选点击，并间接复用了区域读取函数；这条真实数据流没有带来本局涨分。全池采用索引及重点轨迹出处见下方结果报告。**CPU 能运行不等于模型实际采用，完成关卡也不等于状态全部编码正确。** 下一版应改变实际的数据消费或执行行为，不继续单纯增加提醒。

- [完整结果与逐游戏分数](../../research/notes/020/020-results-analysis.md)
- [ar25 轨迹审查](../../research/notes/020/020-ar25-adoption.md)
- [cd82／ft09 轨迹审查](../../research/notes/020/020-cd82-ft09-review.md)
- [全12局采用索引](../../experiments/020-analysis/adoption-index.json)：720个唯一代码调用，3局出现新API语法；不是720条逐一语义审读。另见[r11l真实消费](../../experiments/020-analysis/r11l-adoption-note.md)。
- 本次分析原件：完整评分及运行记录`runs/020-overview/`、候选日志`runs/020-candidate-logs/`、重点事件`runs/020-focused-events/`。`runs/020-grounded-state/`是额外批量下载的部分档案，不能当成完整输出集。
- 复算：`python3 -B scripts/analysis/analyze_020_results.py`。只读 JSON，不执行历史模型代码。

正式成绩仍为 **009 v2 / submission 57101330 / public 31.16**。本轮没有新 leaderboard 成绩。

## 现在到底完成了什么

| 部分 | 可以直接复用 | 还缺什么 |
|---|---|---|
| 精确状态通道 | `grounded_state.py`、008 `observation_representation.py`、真实 sandbox 示例、完整020运行 | 更稳定的数据消费及净收益；已有局部真实采用，当前版本整体回退 |
| 预测失配停批 | `checked_execution.py`：预测冻结、单动作、边界优先、失配停止后缀 | 接入真实 Python action／FrameView；在线采用与收益 |
| 有限替代解释 | `bounded_probe.py`：每关一次、两个解释、1–3动作预算账本 | 停滞触发、提示、跨调用账本、真实动作扣费及后续修模 |
| 社区验证 | 固定源码／许可证、家族划分、40/40 CPU接口检查、独立SDK adapter | TAAF／ToolAgent桥接、统一预算、独立指标及文件可见性隔离 |
| 正式提交构建 | `build_020_submission.py`，jiyujia身份、原009 gateway/save流程 | 当前版本不值得提交；选中下一候选后需真实GPU save smoke |
| 019 FP8 | 实际wheel审计与哈希修复、18cell CPU/GPU本地重建 | 修复版CPU上传及实权重结果；GPU速度／质量仍未测 |

本轮没有修改候选求解逻辑，只读取结果、整理分析和交接。原009与已运行020冻结源都保留。

## 建议第一件事：把失配停批接进现有动作入口

优先做一个独立候选，例如 `021-checked-execution`。从稳定基线分支接入；不要把已退分的020长说明、FP8、探索一起加上。`checked_execution.py` 是可复用核心，不必重写一套系统。

具体实施顺序：

1. 阅读 `src/arc3_research/checked_execution.py` 和 `research/notes/020/020-behavior-mechanisms.md`。它当前不是 Agent 补丁，不能仅把文件打包就当作接入完成。
2. 参照 `grounded_state.py` 的 bootstrap 安装方式，为现有 Python `action(actions)` 增加可选的预测执行路径；普通 action 保持原行为。接口可以是 `action(plan, pred=..., extract=...)`，或一个很薄的同环境 helper，避免要求模型再转抄一套状态对象。
3. 适配模型现有 `pred`／`extract`，在框架内部包装 `ComparableState`。预测输入和实际提取使用同一坐标系、字段与语义；不要默认比较整幅画面，也不要自动忽略边界像素。
4. `execute_one` 每次只送一个动作给**原有** `action`。保留点击位置与所有已有 payload；不要在新 helper 内重新解释点击坐标或吞掉原 no-op／terminal 异常。原入口签名是 `action(actions)`，不是 `action(**payload)`，应复用原 normalization。
5. 动作返回并刷新 `current_frame` 后，先读取 `level_completed`、`game_over`、`done/run_complete`、`stop_reason` 等公开反馈，再比较预测。`FrameView` 本身没有完整终态字段，不能从像素相等推断终局。
6. 真实失配后停止当前计划剩余后缀，把首个反例、已执行数和未执行数交给下一模型轮。未知提取、预测异常单独报告；不能悄悄降为 unchecked 执行。不要增加模型评审调用或额外回滚。

接入点在冻结运行库 `research/runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py` 的 `_SANDBOX_BOOTSTRAP`、`action` 和 `_refresh_state`；生产补丁放在新 research 模块，保留原运行库原件。终局标记和公开事件身份必须来自真实返回；不要为了满足 `Observation.episode_id` 凭空编造游戏内部状态。

**最低完成证据：**真实 Python 工具中确实调用这个路径；一条真实失配使后缀停止并进入后续修模。CPU 只需确认普通动作、首次失配、换关/结束、点击这几个关键路径。随后做同预算对照，看分数和代价；不再要求全部辅助指标一起上涨。若模型仍完全不采用，应先改连接方式，不花整池 GPU 重复同一问题。

## 状态通道怎么继续，避免重演020

保留现有区域读取代码，其准确像素／原点／mask 能用于新候选。当前缺口是**让实际求解程序消费它**。先处理已观察到的摩擦，不立即扩写通用对象世界模型。

- 以真实轨迹为样例，让模板直接完成“当前帧选择区域 → 读出值 → 原生值进入现有求解函数”。不要只把结果打印给模型，再要求它写回数组。
- 可试将常用原生字符矩阵放到已有 `current_frame` 的直接属性，减少新增方法记忆和二次复制；这只是待验证实现选择，不保证比 `region()` 更有效。
- 现有接口只接受当前帧；`r11l`读取合法历史帧时被拒绝，且曾把bbox作为四个位置参数传入。后续可减少参数摩擦、支持明确标注来源的历史观察；保留来源与新旧状态区分，不把所有历史比较都当作陈旧误读。
- 对象选区仍需要证据。bbox 包括背景、断开部分漏取、颜色 mask 与碰撞足迹不同，不能由精确读取自动解决。ar25 已展示这些错误仍可能发生。
- 与执行校验分开做第一轮，或明确只在已经验证的底座上叠加。不要把“代码可用”“调用一次”“多过一关”都解释成通道成功。

## 社区统一 Agent 接入

已冻结源 commit：`02152bc4806869ace6ef167468970ca84bac0c5a`。252包，去3个官方参考和4个教程后245包，保守并为47组；筛40组各一代表。冻结清单 `experiments/020-community/split-frozen.json` SHA256：`ad16158ca664daaf107e228837ec6861566ad047aabec36ea15fc280c56d6230`。

**12开发／12预留／16冻结**，同族全部绑定同侧。40/40正常接口可用不代表已确认可解性或难度。不要再抽签换一份清单，不用holdout来调提示。

下一步建立独立社区 runner，先用开发集 `tt03-63be02fb` 和 `pt01-63be02fb` 接通：

1. 复用 `taaf.game_api.GameAPI` → `_HarnessGameSession.current_frame/write_runtime_state` → `ToolAgent`；`src/arc3_research/community.py` 当前只完成独立SDK适配，**没有现成完整TAAF桥接脚本**。
2. 环境目录可沿用 `ARC3_RESEARCH_ENV_DIR`，引擎端需要社区根目录以导入共享helper。读取 `solver-allowlists.json` 选游戏；prompt保留 `hint=None`，不给描述、规则、解法或隐藏状态。
3. 固定真实环境seed。现有TAAF `make()` 默认seed0，而社区CPU smoke用200019；配对运行必须显式统一，不能把 reset 当作重建随机种子。
4. 社区 `baseline_actions` 没有可靠人类依据，应在创建 GameRun 前清除／单独处理，避免既有评分或长度断言。报告全通率、完成关数／总关数、动作、tokens、耗时，不用官方AE名义呈现社区结果。
5. 先用人工写的合法工具代码验证完整帧、合法动作、点击坐标、关卡信号与动作后刷新，然后用现有模型跑开发集。模型和预算与候选对照一致。
6. Python工具有模块白名单、临时目录和资源限制，但当前没有独立文件系统挂载隔离。冻结验证时应让工具进程看不到环境源码和研究metadata，由独立引擎通过公共观察协议提供数据。若尚未做到，明确只具备协议约束，不声称强隔离已经完成。

当前CPU复用环境的NumPy是2.3.5，低于社区声明≥2.4.3；正式部署需固定可用依赖并复跑同一份接口检查。临时社区源码在 `/tmp/arc3-community-02152bc48068`，可能被系统清理；固定下载地址、blob tree与许可证都在 `experiments/020-community/`，可以恢复同一版本。

## 有限探索的剩余实现

`GoalProbeBudget` 目前只是账本，不会自动判断卡关、调用模型或执行动作。把账本放在单局 Agent／host 生命周期中，不放在每次销毁的 Python sandbox 中；同关RESET不退款。

首版只选择一个清晰触发，例如模型声明无解并且已有反例，或固定次数的同关重复计划无进展。保留真实观察和有效函数，下一轮提示提出两个竞争解释及能区分它们的1–3个动作。动作正常计费，准备移动也算；每关一次，输出预算有限。记录触发→假设→探测→真实反馈→规则或目标改变，避免把“想了另一种解释”当能力改善。不要先做复杂自动语义停滞分类器。

## 019 的接续边界

远端CPU v1仍为ERROR，失败发生在wheel源码身份检查，未采样权重、未启动GPU。`4be361d`已修复：实际wheel整体与四文件hash绑定，PLE两个核心文件与原审计相同，另两处是预取／BF16支持差异。当前CPU/GPU构建都是18cells；**本地没有CPU v2上传记录**。

若继续，先运行已有 `scripts/checks/check_019_preparation.py`，再只上传CPU修复版。GPU微基准仍独立80分钟上限；没有真实速度／质量收益就结束该支线。它不应阻塞行为候选。分析器三处已知问题已修代码，专门分支验证尚未做；如遇不完整结果，应读原JSON确认，别把缺失当通过。

## GPU、正式提交与命令

所有GPU都使用 **jiyujia**。专用凭据仅在当前进程注入，不打印、不复制到仓库；每次上传前核对CLI/API返回用户名。通用quota曾显示已用大于总量，但RTX任务仍被平台接收，不能从该数字推算精确剩余额度。

已准备的正式模板为 `experiments/020-grounded-submission.json` 与 `scripts/build/build_020_submission.py`，身份 `jiyujia/arc3-020-grounded-submission`。Notebook SHA256：`c16c9f339a37e89492ee82c817396e203f005cc32c9fe4885e9072838c2bdb11`。原009 builder/config未改，真实gateway动态枚举、31920秒solver预算和原save smoke保持；没有研究12游戏过滤。

模板当前只供下一候选改造，不直接提交负向020。选中候选后按顺序：

```bash
# 本地构建模板，不使用GPU，不提交
python3 -B scripts/build/build_020_submission.py --output-dir experiments/020-submission-source

# 为真正选中的新候选生成独立目录及身份后，再用jiyujia执行
kaggle kernels push -p <候选目录> -t 32400 --accelerator NvidiaRtxPro6000
kaggle kernels status jiyujia/<候选slug>
kaggle kernels output jiyujia/<候选slug> -p <独立输出目录>

# 仅使用真实完成save smoke的kernel版本；不能沿用研究kernel的v1
kaggle competitions submit arc-prize-2026-arc-agi-3 \
  -k jiyujia/<候选slug> -v <实际版本> -f submission.parquet -m <候选说明>
```

正式rerun由Kaggle提供环境标记和隐藏游戏；不要自行模拟该标记，不手写隐藏评测结果。Save placeholder不是成绩。新版本只要机制合理、运行稳定、本地风险可接受，就可以尽早用一次正式隐藏评测；无需等所有辅助指标都上涨。

原冲刺安排是3–4次有用途的正式验证；现在应把第一次留给新实施候选，而非为了满足日程提交退分版本。截止前留出完整9小时运行及故障处理余量。最终两个候选按届时证据选择，不机械锁死009，也不因目标是金牌就承诺收益。

## 最短实施清单

1. 读020的具体轨迹，保留复用模块，停止原版扩跑和提交。
2. 将预测失配停批接进真实动作入口，取得一条实际停止后缀并修模的在线证据，再做同预算短筛。
3. 并行接通社区开发集的统一Agent；16冻结游戏留给少数最终候选。
4. 候选有合理收益及可接受风险后，完成正式save smoke并提交；记录真实kernel版本和submission ID。
5. 有限探索单独形成下一候选；019仅作为限时支线。

历史研究方向说明保留在 [020冲刺交接](020-research-sprint.md)；涉及当前结果和下一执行动作时，以本文件为准。
