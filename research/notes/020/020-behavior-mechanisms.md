# 020 — 让已有预测控制动作，并为错误目标留一次短探测机会

日期：2026-10-19，Asia/Shanghai。本轮实现两个独立CPU模块，复读Sujan v29/DF-WM v12归档源码、016真实请求，并重新访问作者WRITEUP、官方计分方法和OPINE v3。没有执行下载Notebook、历史模型代码、游戏实现或GPU；没有修改run_arm、实验config、019或grounded_state。主线仍是精确状态直接进入程序；这里为第二、第三条行为研究准备可运行的最小机制。

**已完成的是停批执行器与每关探测预算账本，尚未把它们接入模型。** CPU示例确认控制行为，不代表模型会自然采用，也没有产生新分数。最有价值的本地证据是m0r0已经产生预测与比较，却在首次失配后继续执行；同一基线后来也会停批、修模和探测目标，因此不需要重建完整世界模型系统。

## 1. 现有实现中可以直接拆出的部分

10/18归档的[Sujan v29](../../notebooks/2026-10-18/sujanmajhisuzan__arc-agi-3-m2-top-submission/source.ipynb) source SHA256为`c1f976bc419b5cd2be336f8aa2666d0e842c4a1b1251db9e7e23d6a741d012f1`；[DF-WM v12](../../notebooks/2026-10-18/vladimiryakunin__df-wm/source.ipynb)为`8e4e1c07dfc43890b314ef5169a187f684844db805cc0ec80af224414033784c`。这次复用已存版本，没有声称10/19重新取得Kaggle最新版本；两者归档无outputs，未取得版本绑定的自然调用链或独立收益。

- [`check_sim`](../../notebooks/2026-10-18/sujanmajhisuzan__arc-agi-3-m2-top-submission/extracted-assets/patch-files/ARC3-Inference/inference/utils/world_model.py:203)回看最近真实同关转移，跳过RESET、automatic和跨关记录；它是历史一致性检查，不是目标正确性的证明。
- [`act_checked`](../../notebooks/2026-10-18/sujanmajhisuzan__arc-agi-3-m2-top-submission/cells/002.txt:2177)先预测、执行一个动作，再检查terminal/level flags，最后比较画面；首次比较失败中断。DF-WM的对应[cell2](../../notebooks/2026-10-18/vladimiryakunin__df-wm/cells/002.txt:2177)为同族实现。
- 不移植的部分：缺simulate时静默调用普通action；给模拟器只传action名，漏MOUSE row/col；默认忽略4px边缘；异常可被普通`except Exception`吞掉；额外BFS、默认去重及其他UND/调度修改。上述混合方案不是本轮单因素。

我们的改动空间是**已有可比较预测与后续计划时的控制断点**。原版no-op guard只知道某片区域有没有变；一个有明显变化但方向错误的动作仍需预测比较。反过来，所有像素变化也不等于错误：动画、UI、提取歧义、换关、隐藏历史阶段均可能造成差异。

## 2. 真实m0r0断点与卡关窗口

原始[016 baseline m0r0请求](../../../runs/016-pace-allocation-jiyujia/baseline/m0r0-492f87ba_p0_requests.jsonl)，静态摘录、原文件hash与重算见[020-behavior-evidence.json](../../020-behavior-evidence.json)。仅用JSON/`ast.literal_eval`读取输出元组，没有运行模型代码。行号是归档请求快照；相同历史在后续快照出现，不重复计调用。

| 快照行 | 可观测事实 | 可作用的行为 |
|---|---|---|
| 37 | 18动作循环记录`pred==act`，只在terminal时break；第2个RIGHT预测右块(44,44)，实际(44,34)，总8次失配，仍执行剩余16动作 | 第一处相关失配即可结束这一个批次。16是未执行后缀的机会**上界**，不是净节约或提分反事实 |
| 39 | 模型据反例转向右侧水平镜像控制，用一个RIGHT看真实对象反向移动 | 已有自然修模与短探测，helper应保留这条后续推理路径 |
| 79、81、85、89 | 第2关第12动作失配后停下；读history发现重置，随后把危险格从阻挡改为DEAD，19步新序列符合模型 | 中断的价值是暴露矛盾供修订，不是自动判定某种规则或自动RESET |
| 47、51 | 已观察两块合并，但仍未完成；自然推理明确讨论“合并不是充分条件” | 可在下一次原有模型回合开一次替代目标窗口，无需另起critic |
| 53、55、57、67–73 | SPACE、后续移动及过关结果用来区分合并、移动后检查、到特定区域等解释；最终仍保留不确定性 | 探测输出应保留被观察到的差别，不能宣称一次成功就唯一确认规则 |
| 93、95、99 | 后一关合并/移动未赢使旧解释失效，模型转向正面对撞并计划执行 | 支持按**新关真实矛盾**更新目标，而非把旧关坐标/条件当真值 |

反例同样重要：[r11l:111](../../../runs/016-pace-allocation-jiyujia/baseline/r11l-495a7899_p0_requests.jsonl:111)在真实换关后先比旧M点，误记`verify_fail`；105/107还出现把相邻颜色当多个物体中心的提取假报警。故终态/level边界必须先于比较；失配后需要检查表征、动作规则和目标，不能默认是模拟器错。

## 3. 第二方向：可运行的单步预测停批

新增[`checked_execution.py`](../../../src/arc3_research/checked_execution.py)。入口为`execute_checked(actions, initial=..., execute_one=..., pred=..., extract=...)`，由调用者提供已有预测器与可见观察提取器：

1. `ComparableState(scope, values)`声明比较的坐标/单位/提取器版本与字段。只比较这一投影，不自动裁边、不猜物体、不补空洞；支持对象位置、局部字符或模型已定义的其他可见状态。
2. 预测在动作前计算，完整action值含点击row/col独立复制给pred和原one-action API。预测及观察身份hash在执行前确定，避免可变对象在动作后改变“预测”。
3. 一步动作后，先看terminal、明确boundary、level/episode变化。出现边界即返回`boundary`，不会用新关画面检验旧关模型。
4. 同scope、同字段且观察事件前进时才比较。首次失配返回`mismatch`，剩余动作不再调用；缺预测、空/歧义提取、字段改变返回`unverifiable`并停批，绝不默降普通执行。执行异常不重试，因为动作可能已经发生。
5. 返回执行尝试数、取得结果数、未尝试后缀、动作/观察身份、预测与实际摘要hash和最多8处差异；大字段差异只给有限预览。它没有自动LLM调用、UNDO、RESET、奖励推断或隐藏状态读取。

`Observation.data`必须来自公开frame；`observation_id`是观察事件而非图像hash，NO-OP也有新事件。`episode_id`可以使用稳定的宿主会话身份；真实RESET也可由boundary标明，不要求读取引擎内部状态。模型若无法得到某个属性应让extract拒绝，不应造一个值满足合同。默认最多32动作只是CPU入口的容量限制，未宣称是最佳计划长度。

**已实现的保证只限这个函数持有的批次**。回调须遵守已有API/纯提取约定；模型在返回后另写action是一个新决定，当前模块不是不可绕过的sandbox屏障。也没有独立限制任意模型pred/extract运行时间，后续应继续使用原Python工具timeout。该模块尚未注入sandbox，不能把“文件存在”当采用发生。

适配位置已经确认：原[`python_tool_sandbox.action`](../../runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py:489)继续负责动作、状态刷新与既有guard；新helper可在同一Python调用内将`action([full_action])`封装为`execute_one`。宿主[`_handle_action`](../../runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py:5776)的实际结果及刷新后current_frame提供可见生命周期信息。保留原guard优先级，不新增另一条环境执行通道。本轮没有实施这个适配，避免与精确状态通道同时改变因素。

## 4. 第三方向：一次、1–3个动作的替代目标探测

新增[`bounded_probe.py`](../../../src/arc3_research/bounded_probe.py)，只实现预算及证据记录，**尚未实现自动触发或选动作策略**：

- 每个稳定game/level只能打开一次窗口，1–3个普通单动作调用。宿主会话持有账本，不能每次Python子进程重建；RESET、改目标名、异常都不退款。
- 开窗需一个可见轨迹引用，触发类别是“预测目标达到而真实未完成”“重复计划没有进展”或模型明确报告停滞。类别不代表宿主已经证明停滞，当前API不会靠关键词自行打开。
- 模型提出两个仍合理的竞争解释；每个probe需声明各解释下可见且不同的结果。首版最多两个解释，已按本轮用户要求收紧。账本只能检查声明存在且字符串有区别，无法证明实验具有信息价值。一个probe的位移准备也占一次动作，不能把远距离导航藏成免费准备。
- 先扣一个槽再执行，回看实际观察并记录发现后才可申请下一个。终态/换关立即关窗；未知执行结果关窗而不是重试。无需执行完全部预算，可以一次信息明确后回到正常计划。

初始可用触发位置是**原有工具结果之后、下一条原有user prompt之前**：`_run_python_tool`返回实际动作结果；[`_build_user_prompt`](../../runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py:4806)接收当次进展。它可加入一次局部提示，但不产生额外模型请求，也不清空上下文。另一个已有路径[`no tool_calls`](../../runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py:6910)本来就会续聊；不能把这条恢复能力当新发现。

短探测不应再次依赖003的`GOAL_EVIDENCE`强制格式。当前[`goal_evidence.py`](../../../src/arc3_research/goal_evidence.py)已有报告/反馈核对机制，却不能替模型证明目标条件；将“多报一个marker”当突破会重现采用缺口。下一候选的最小动作是，在自然的“计划实现却未过关”或重复计划证据窗口，保留当前状态，提出不同机制/目标解释，挑一个现有合法动作区分，并使用返回结果改变下一步。像m0r0那样已经完成这件事的窗口，应算基线既有能力，不能算候选新增收益。

## 5. 三份一手来源本次复核的含义

10/19读取的[Franzen WRITEUP §5–6](https://raw.githubusercontent.com/da-fr/arc-agi-3-solution/refs/heads/main/WRITEUP.md)确认基线已有no-op、stale-state和terminal三种保护，也说明更强逐步验证提示、重复状态/死亡记账等未取得清楚收益。因此本轮针对“有效动作但预测已错”的具体断点，不据公开榜分推断新helper有效。

[官方方法](https://docs.arcprize.org/methodology)仍为完成关卡的平方动作效率、每关1.15上限、后关权重较大和完成覆盖cap。研究动机是用少量有关反例发现新机制、推进后关；仅提高局部预测准确率或少走几步，不能等价于总分突破。

[OPINE-World v3 §3.2、Table7](https://arxiv.org/html/2607.01531v3)确为Opus4.8 high、25公共游戏；去Bayesian探索层后78.40→58.16、160→126关。它比较的是探索与建模联动的组合系统，不是短提示、1–3probe或本项目Qwen同GPU预算消融。论文的checked planning支持预测失配中断再采集反例；同时强调目标与对象表征也需修订。其合成工作全池174小时，单环境累计可到20亿tokens，不能直接移植收益量。

## 6. 实际交付与接下来做什么

运行`python3 -B scripts/demos/demo_020_behavior_mechanisms.py`，产物为[CPU示例](../../../experiments/020-behavior-cpu/demo.json)：11个合成小场景展示首次失配停后缀、终局/换关/RESET优先、HUD不在投影内不误停、不可比较/缺预测不执行、未知动作异常不重试、点击参数保留；两次预算拒绝展示用尽和同关RESET后不开第二窗口。它是人工构造控制示例，不是m0r0回放，更不是反事实救回16步的实验。

当前可立即继续的行为工作顺序：先完成精确状态主线的独立接入；第二方向只给模型已经有的pred/extract一条停批执行路径，观察是否从真正失配改到修模/新探测；第三方向单独接入一个低开销探测窗口，关注真实试出的新交互与后续目标变化。三者不一起上线，019继续独立。完成证据是动作和关卡轨迹改变，而非新增helper数量或CPU用例数量。
