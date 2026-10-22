# 011 — 旧动画检索倒序确认进展

日期：2026-10-13。对应[计划](../plan/011-animation-confirmation.md)。

状态：**011 v1已COMPLETE：baseline 33.9794→候选32.1157（−1.8637），关卡42→41/91，全通2→2。** 010的总体正向结果未在倒序确认中复现，冻结候选暂不晋升、不进入全25扩跑或正式提交。原010动画源码未改动，011只交换组顺序并对两臂加入相同的被动计时。

已完成固定12游戏/3482秒配置、runner可选计时入口、两臂相同flag、baseline统计reference及冻结hash检查。新Notebook继续普通原生cells，历史009/010Notebook及归档保持原样。

运行顺序：retrievable_animation → baseline。预估2.2h、硬限9000秒；实际7576.01秒（2.10445h），北京时间13:28:06→15:34:22，GPU服务已停止。启动前余额约5.40h，完成后共享账户余额约3.29h；这是账户快照，不把全部变化归为本次作业。

## 完成复核与决策

| 指标 | baseline | 候选 |
|---|---:|---:|
| AE均分 | 33.979397 | 32.115706 |
| 完成关卡 | 42/91 | 41/91 |
| 全通游戏 | 2 | 2 |
| 动作 | 2501 | 2517 |
| analyzer生成tokens | 2,138,116 | 2,185,737 |

逐游戏3升7降2平，24个game-run从原始逐关动作数复算与输出完全一致。两组预算各3482秒、exit0、游戏池/顺序/环境及冻结源码正确、独立CPU进程、cache flush成功；旧003/006/007干预disabled且0事件，截止后动作与完成关卡均0。[数值复算](../../experiments/011-analysis/comparison.md)、[独立审核](../../experiments/011-results-review.json)

010差值+3.8864，011差值−1.8637；两轮简单平均仍+1.0113，但同12局重复、每顺序仅1次，不能据此声称稳定或显著收益。tn36再次1→4关，却没有一次旧动画查询；m0r0本轮候选得到更多持slot时间/tokens仍5→3关，初始排队不能独立解释总分波动。

计时记录两臂各12会话完整，无丢弃、observer错误或退出后未释放slot；按全局截止时间核验，两臂均没有截止后新chat、HTTP尝试或gate准入。尾部ReadTimeout来自截止前请求，不是额外动作预算。[计时与资源分析](../../research/notes/011/011-timing-analysis.md)

**决策：不原样晋升动画候选，不用剩余GPU盲目重复本版本。** 下一项优先做“当前观察绑定的结构化计算值跨snippet交接”的CPU验证，已有两种游戏的直接证据与反例，尚未实现或接入运行。正式记录仍为009的31.16；本轮没有正式submission或新GPU作业。[综合结果与后续](../../research/notes/011/011-results-analysis.md)、[下一候选研究](../../research/notes/011/011-evidence-reuse-next.md)

## 已完成的交付与验证

- [Notebook](../../notebooks/011-animation-confirmation/experiment.ipynb)：28个原生可读cells，21个代码cells、12个helper。使用实际IPython写出源码，逐byte/hash与manifest匹配；继承patch解析通过，无新增exec/compile/eval外壳。
- Notebook SHA256：`4d7bd650af420bcaf47d71fe8dc2e63e9198cf783badfa4e93e9b1dd3f580211`。冻结源码与构建依赖见[011-source](../../experiments/011-source/source-hashes.json)，历史009/010 Notebook未改变。
- 计时模块SHA256：`5ff98e60341015277b84cf88dbe4d54abe842e03834b6fd4f6080c3721db00f8`。31项CPU手工核验通过，覆盖真实gate交接、真实chat方法的受控JSON/SSE响应、原参数/返回/异常identity、重试、有界记录及计时失败时保留原执行结果。详见[CPU范围和记录](../../experiments/011-timing-checks/README.md)。这些不是模型采用、生产并发性能或提分证据。
- 独立审查确认源码、Notebook实际payload、manifest和IPython报告一致，无剩余工程启动阻断。[Notebook核验](../../experiments/011-notebook-checks.json)
- 下一候选完成两种游戏的直接证据链及反例复核，24条摘录/14份来源hash核验一致；建议先在CPU上验证“当前观察绑定的结构化计算值跨snippet交接”，尚未实现或加入011。[研究报告](../../research/notes/011/011-evidence-reuse-next.md)

## 启动与实际日志（历史记录）

用户明确答复“授权上传并启动011”后，成功执行：

```bash
kaggle kernels push -p notebooks/011-animation-confirmation -t 9000 --accelerator NvidiaRtxPro6000
```

Kaggle返回`Kernel version 1 successfully pushed`，平台状态RUNNING。[私有011 Notebook](https://www.kaggle.com/code/ccjjllt/arc3-011-animation-confirmation)；回拉的28个cell类型/正文与冻结版本完全一致，metadata确认私有、GPU、断网和RTX PRO 6000。远端`docker_image_pinning_type`返回null，不能据此声称实际镜像pin已核验。[远端源码记录](../../experiments/011-remote-source-check.json)

13:29后的实时日志确认12个helper写出、原patch应用成功、离线依赖安装成功、实际GPU为RTX PRO 6000 Blackwell Server Edition、serving进程已启动。当时模型加载中，尚未确认health或候选组真实动作；当时停止的只是本地日志读取器。[启动观察](../../experiments/011-startup-observation.json)。完成输出现已确认model-ready为567.66秒，两组均实际运行结束。

加载后自动执行retrievable_animation→baseline，各3482秒，预计会话约2.2h，硬限2.5h。本轮不是正式比赛submission，未占每日正式槽位。启动前即时quota查询一次遇到SSL EOF；重读成功，启动后共享余额约5.39h（CLI两位小数，持续消耗中）。上传后的独立复核再次确认22份冻结文件、所有payload及009/010历史Notebook哈希未变。

## 已解决的上传审批阻断

10/13 13:10–13:11，北京时间，前两次相同启动命令均在进程创建前被自动审批拒绝。首次理由为已有继续研究授权未明确覆盖上传这份Notebook到Kaggle及共享GPU消耗；第二次在核对上一轮具体方案及用户承接回复后仍被拒绝。当时没有改用其它工具绕过，未发送011源码、未消耗011 GPU时数。用户后续明确批准后才执行成功上传。

平台版本、回拉源码、实际GPU、模型health、两组完成及结果有效性均已分别验证。[完成记录](../../experiments/011-completion.json)

启动状态见[011-launch.json](../../experiments/011-launch.json)。正式榜仍为009的31.16；010公开筛选26.05→29.94不是新的正式成绩。
