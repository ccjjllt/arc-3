# 028 真正程序修复的实际结果

2026-10-20。执行版本为 `zhuating/arc3-028-program-repair` v1，使用修复helper v1；后来新增的连续两次异常触发策略v2没有参与本次GPU实验。

**本版不扩全池，不作为提分候选。** ft09完成了“模型改写代码、实际执行、保留函数、主模型继续使用”的链路，但最关键的像素提取错误仍在；tu93修复调用60秒超时，未返回代码。三个同状态A/B都没有新增关卡。应将GPU投入独立的持久Python候选与基线对照，而不是为导出故障重跑本实验。

## 实际运行与工程故障

模型只加载一次，六个会话并发续跑：ft09、tu93、r11l各A/B两臂。每会话250秒、最多30个续跑动作；ft09和tu93 B各允许一次额外修复调用，修复耗时包含在250秒内；r11l B仅装在线hook，未强制修复。

所有六个会话均实际退出并留下请求、工具执行和完成日志。随后结果导出把TAAF的 `ActionRecord` 当作dict调用 `.get()`，因此arm和Notebook最终为ERROR，没有生成benchmark。manifest中由缺少benchmark推导出的 `all_games_failed_to_run=true` 不符合逐会话原始日志，不能据此声称模型没有运行。

会话内部总时间1155.63秒，其中模型就绪819.86秒，fork arm330.06秒；服务已关闭。这些是会话内部时间，不是平台配额扣费证明。[会话原件](../../../runs/028-program-repair/experiment-manifest.json)、[实际运行日志](../../../runs/028-program-repair/repair_forks/run.log)。

## 对照结果

| 游戏 | 切点完成关 | A结束 | B结束 | A续跑动作 | B续跑动作 | A分析器总token | B分析器总token |
|---|---:|---:|---:|---:|---:|---:|---:|
| ft09 | 2/6 | 2/6 | 2/6 | 1 | 1 | 12968 | 16297 |
| tu93 | 8/9 | 8/9 | 8/9 | 0 | 9 | 19973 | 15589 |
| r11l正常对照 | 2/6 | 2/6 | 2/6 | 0 | 2 | 14688 | 17023 |

没有一对产生新增关卡。tu93 B多执行9个动作，但没有修复代码返回，不能将其称为采用修复后的恢复。r11l两臂行为差异提示这类单次并发续跑存在生成与排队波动，不能把动作多少单独解释为机制收益。

分析器总token来自各会话完成日志。ft09 B其中1116个生成token属于额外修复调用；tu93超时请求的生成token没有响应usage，实际成本未知。tu93 A的完成日志比已保存response usage合计多1454个token，分析保留此差额，不把它默认为零或当作额外可分配预算。token均不是计费记录。

## ft09代码真正执行和使用了 但没有改对关键提取

额外请求生成1116个token、输入58470个token，耗时50.19秒。模型返回 `analyze(frame)` 与 `satisfaction(grid, legends, mode)`，实际Python输出了四个图案的匹配统计，两函数被真实沙箱保留；修复期间环境动作0个。后续主模型明确检查这些统计并编写、执行 `analyze2`、`analyze3`、`polar` 等派生代码，因此结果确实被消费。

主模型的第一个后续推理已经指出 `satisfaction` 的center模式把另一种颜色设为 `None`，使相关统计错误。更关键的是，返回的提取器把连通块外接框整块填色；在图案 `(5,2)` 中，原始图案中间行是 `WOg`，它仍提成了 **`WOW`**。逐格对照原切点帧发现唯一错格在原帧row46、col32：实际颜色 `g`，修复输出 `W`。这正是本轮试图纠正的核心表征错误，并没有被修复分支消除。

该像素审计仅在本地用已返回代码和原始切点帧做计算，没有新增模型调用，也没有向运行中的模型提供正确图案。[逐格审计](../../../experiments/028-analysis/ft09-repair-pixel-audit.json)、[真实修复代码与输出](../../../runs/028-program-repair/repair_forks/artifacts/ft09-0d8bbf25_B_tool_runtime_state_program-repair.jsonl)、[B后续执行](../../../runs/028-program-repair/repair_forks/transcripts/ft09-0d8bbf25_B.txt)。

A和B唯一真实续跑动作完全相同：`ACTION6`，data为 `{"x":22,"y":30}`，即MOUSE(row30,col22)，两次都是实际执行的no-op。这里可以精确确认完整ID与坐标相同，没有仅比较动作ID的漏报。[A执行](../../../runs/028-program-repair/repair_forks/transcripts/ft09-0d8bbf25_A.txt)。

## tu93修复请求超时 后续动作不是修复结果

tu93 B额外请求在60秒read timeout后返回 `ReadTimeout`，耗时60.32秒；没有代码、执行输出或usage。保留函数列表仍是切点恢复的旧函数。进入主模型的是修复要求文字，没有可供采用的新程序。

B随后执行九个真实方向动作：DOWN、DOWN、RIGHT、DOWN、LEFT、DOWN、LEFT、DOWN、DOWN；A没有续跑动作。两臂仍为8/9关。本例只证明有限时间内该修复请求没有成功返回，不能声称已检验并否定了“正确修复后的模拟器能否帮助通关”。[修复超时事件](../../../runs/028-program-repair/repair_forks/artifacts/tu93-0768757b_B_tool_runtime_state_program-repair.jsonl)、[B后续记录](../../../runs/028-program-repair/repair_forks/transcripts/tu93-0768757b_B.txt)。

## 恢复方法与边界

viewer/events未能从平台输出接口取得，故本轮动作由各臂transcript中实际 `[action]` 回声恢复，转为完整引擎ID及data，再与完成日志的总动作数对齐。六局都能以“前缀动作数＋恢复的续跑动作数”精确对上完成日志，因此没有把未执行的模型代码当成动作。未取得的完整帧序列、独立viewer与逐动作墙钟不补造。

[恢复脚本](../../../scripts/analysis/analyze_028_results.py)写出[完整结果JSON](../../../experiments/028-analysis/summary.json)及[简表](../../../experiments/028-analysis/summary.md)，保留每臂请求文件hash、修复usage、真实代码和输出、完整动作参数及token差额。重算只需运行脚本，无需重跑GPU。

本次结果关闭的是这版额外修复实现的扩跑机会。在线v1又存在“首次普通异常很快自然恢复，却提前消耗唯一修复机会”的问题，见[触发审计](028-error-trigger-audit.md)。v2只将默认触发改为连续两次真实异常，尚无GPU收益证据；不能因触发条件变窄就重新把失败修复器晋升到全25题。
