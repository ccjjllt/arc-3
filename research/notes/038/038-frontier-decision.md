# 038 前沿机制与下一次正式提交的取舍

2026-10-25，北京时间。本轮为新派子代理的只读研究：重新读取一手论文和作者实现，并检查本地已有接口。没有修改solver、调用模型、启动GPU或提交。目标是提高本场Kaggle正式公开分，文献数字仅用于评估机制与成本。

**排序结论：一次原样v83正式参考优先；能力改动优先选已有日志证明、自动生效的兼容修正；有条件地试实际Python超时后的短诊断反馈。暂不直接搬整套世界模型框架或升级推理后端。** 上游35.35是历史显示最高分，不能当作本队已复现的期望值。

| 排序 | 下一项 | 依据 | 最小投入与停止条件 |
|---|---|---|---|
| 1 | 恢复原样v83 solver，固定其同一容器和输入，完成一次正式提交 | 037的26.71缺少本队原样v83对照；v83的正式求解核心与既有Franzen相同，但Docker与009不同。单次原样结果提供部署参考，也有直接恢复公开分的机会 | 必要GPU save后用准确版本提交一次；不追加社区前置。该结果仍不能分离随机波动与runs的因果效应。不要把未达到35.35当成必然故障后原样连投 |
| 2 | 选择本地审计发现的只读兼容修正，例如HistoryEntryView.step alias | 同期执行审计已发现036去重4593个工具结果中，该缺失出现10次、跨8游戏，后续改用h.frame.step或序号恢复。这是已有消费路径中的真实失败，比新增可选API更直接 | 用同一实际对象证明alias与现有frame.step一致，保留原字段；核对缺失/空frame语义。若会扩大不明确语义或改变状态，则停止。该数据来自另一新代理，最终以execution-audit原件为准 |
| 3 | 仅在真实Python timeout后，补充一段具体搜索诊断 | Retrodict的实际tools.py会在超时结果自动提示缩小搜索、换方法，并明确超时不代表无解；本地run_sandboxed_python目前只返回Tool timed out afterNs。同期执行审计记录20次30秒超时、分布12游戏 | 只改既有错误反馈，不加模型调用、不改变超时和动作预算、不增predict接口。先核对超时后的同规模重试及正确自然恢复样例；若反馈没有改变搜索/后续行动，或误导原本可恢复的轨迹，停止 |

20×30秒不是可直接回收的GPU墙钟：这些CPU工具在多游戏并发环境中运行，其他游戏可能继续占满GPU。`.step` alias和timeout反馈也不是已验证的涨分算法；下一正式提交仍要由实际公开分判断。兼容修正可以在原样v83等待评分时准备，避免把所有开发串行等待到比赛末期。

**Retrodict真正值得迁移的是具体执行反馈，完整协议的成本与采用风险很高。** 当前README报告公开25游戏99.86、660M tokens、$654，主模型为GPT-5.6 Sol max。系统有150k上下文重启、文件记忆、初始视觉模型、每动作expect、300动作或两次RESET后的强制建模升级。多数轨迹先本地运行再官方回放，作者说明部分max推理会超过在线API的15分钟无动作时限。这些条件不对应我们的单卡9小时隐藏评测。其“expect→mismatch停止”已与本地021/022重合，而本地采用为零，不能重新命名后视为突破。[作者README](https://github.com/ryanbbrown/Retrodict/blob/main/README.md)

可直接核实的小区别是[tools.py](https://github.com/ryanbbrown/Retrodict/blob/main/src/arc3/tools.py)：timeout错误自动带因果明确的搜索反馈；[prompts.py](https://github.com/ryanbbrown/Retrodict/blob/main/src/arc3/prompts.py)还要求在循环内限时、输出进度、先估搜索规模。本地[prompts.py](../../runtime-bundle/src/ARC3-Inference/inference/agent/prompts.py)已经有搜索、批量行动、无解时重审模型、压缩工具输出等指导，缺少的是这个特定错误时机的反馈。不能把已有指令再加一遍当新增能力。

本地[sandbox超时分支](../../runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py:866)直接丢弃stdout；Retrodict则读取临时stdout文件并保留截断内容。恢复部分stdout也可能有价值，但需要修改子进程输出协议/捕获方式，范围比短错误反馈更大。当前不建议和反馈补丁一同打包，更不能宣称加一句print(flush=True)就能跨越现有StringIO/JSON最终消息协议保住结果。

**Tycho、Schema、OPINE支持能力方向，但不支持把复杂接口强加给当前模型。**

- [Tycho作者实现](https://github.com/NIMI-research/Tycho/blob/main/README.md)保留直接求解，是否建模由actor决定。Opus4.8同模型结果中，按需调用builder为88.49，失配强制调用为83.07。公开25题100%的更新使用更强模型。实际代码还要求世界模型的State/transition/render/outcome及隔离运行环境；没有Qwen低预算等条件证据。
- [Schema](https://arxiv.org/html/2609.39140v1)让LLM自主组织hypothesize/certify/plan/act，依赖统一预测接口重放历史和逐步执行。它不是单一提示或一个检查器。论文的几何案例同时警示：真实游戏会生长物体，因此“像素数守恒”只能用于明确宣称的纯刚性变换，不能对环境状态强制应用。当前033的目标消费断点和034交付失败没有被一个外部高分证明解决。
- [OPINE-World v3](https://arxiv.org/html/2607.01531v3)强调遗漏属性、关系和交互的发现，支持有区分力的探索；但完整系统建模合计174小时，动作预算和模型也不同。本地024的泛化rule-versus-goal提示已有负结果。下一探索候选必须实际产生两个可区分预测与一个相关动作，不能把泛化提醒当作论文探索层。

**最新推理后端已有3.1.2，但没有足够证据把它作为下一次提分提交。**

[作者10月13日介绍](https://forums.developer.nvidia.com/t/penny-royal-3-0-qwen3-8-on-rtx-pro-6000-adaptive-mtp-524k-context-and-external-container-configuration-hicache-nixl/385785)从2.5.3发展到3.0；继续核对[现行仓库](https://github.com/jpezzulli/sglang-rtxpro6000)后，最新文档已到3.1.2，包含10月23日的验证记录。当前native MTP以并发数选择宽度，支持缓存和自动KV池；正式发布的预构建镜像存在。

[3.1结果](https://github.com/jpezzulli/sglang-rtxpro6000/blob/pennyroyal-main-sm120-final/RELEASE_NOTES_3.1.md)的native MTP C4/C6约555.11／472.79 tok/s，使用OrcaRouter ModelOpt NVFP4；尚无我们Intel AutoRound W4A16、C10、相同上下文负载的对照。不能把它与本仓库约600 tok/s的不同运行口径直接相减。新框架还有模型量化、启动、wheel打包和缓存语义适配成本。

[3.1.2发布说明](https://github.com/jpezzulli/sglang-rtxpro6000/blob/pennyroyal-main-sm120-final/RELEASE_NOTES_3.1.2.md)明确DFlash2为experimental/alpha，额外host缓存开销有实际观测，GPU checkpoint/cache-resume仍未完成验证。native MTP保持默认；新checkpoint修复主要针对DFlash2，并非已证明能修复我们2.5.3运行的问题。因此不建议为了版本号直接替换后端或换量化模型。若后续确实研究，必须先只比较固定请求集的合法工具交付、完成吞吐、显存/主存和长上下文恢复，未通过即停止，不先耗完整正式提交。

本轮未发现可直接替换Qwen3.8-Flash-Next、同时具有本场可运行资产与更高绑定成绩的新模型证据。闭源模型公开100%仅提示当前任务仍有能力空间，不是本地模型可复制的收益。

**一手源码定位。** 本轮GitHub读取返回的blob SHA：Retrodict README `34ad9fa341cb47fac976386efbaa2d4961dba694`，prompts.py `9a921d2079bb74a69ce66e24009c66dde5acb4e2`，tools.py `c2a4cd6f1472bdead3b90f41597260ec74bc2cb1`；Tycho README `62d33dc69d6539f994f816e171c4f0fbe40e3774`；Penny Royal RELEASE_NOTES_3.1.md `111bfaf140e5cc6f6309af28b8274328011eca46`、RELEASE_NOTES_3.1.2.md `bee1ed6d305fbd566ad457de1f1c932c5e06321d`。没有下载权重、容器或执行第三方代码。
