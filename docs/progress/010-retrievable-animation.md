# 010 — 按动作检索完整动画进展

日期：2026-10-13，Asia/Shanghai。对应[计划](../plan/010-retrievable-animation.md)。

状态：**010 v1已COMPLETE：baseline 26.0501→候选29.9365（+3.8864），完成关卡34→37/91，全通2→1。** 4局真实使用旧动画，28次非latest命中；目前只有tn36存在清楚的信息恢复与后续知识迁移线索，独立提分效果未确认。保留为待确认研究候选，不晋升正式版本。正式成绩仍为009的31.16；这里是公开12游戏研究分数。

## 完成结果与决策（10/13结果复核）

平台CLI确认为COMPLETE，manifest completed，两臂exit0，无crashed/forced exit/残留worker；GPU服务已关闭。会话北京时间09:25:09—11:32:45，实测2.1266h。完整记录见[010-completion.json](../../experiments/010-completion.json)，MCP本次传输失败，改用CLI取回完整产物。

| 指标 | baseline | retrievable_animation |
|---|---:|---:|
| 12游戏平均AE | 26.050139 | 29.936494 |
| 完成关卡 | 34/91 | 37/91 |
| 全通游戏 | 2/12 | 1/12 |
| 动作，含RESET | 2296 | 2290 |
| analyzer生成tokens | 2,133,883 | 2,183,455 |
| 预算内GPU时间加权利用率 | 90.60% | 93.09% |

24条轨迹的评分公式逐项复算一致；同12游戏/顺序/各3482秒，来源hash和配置一致，独立CPU进程、两次服务端cache flush成功，003/006/007都关闭。截止后真实动作和通关均0。候选多约61秒benchmark尾段没有变成额外分数；服务记录显示两臂各1条entry_time晚于截止的请求（316/11,161输出tokens），尚未绑定客户端发送时刻或具体游戏。因此不能把全部尾段称为旧请求排空，也不能把server/analyzer/action三种token数混用。[数值报告](../../research/010-results-analysis.md)、[资源报告](../../research/010-efficiency-analysis.md)

### 工具确实使用了，但分差不能直接归因

候选2290次实际动作全部成功归档、8030帧，4/12局调用新API。19次list、29次get，28次get全部命中非latest动作，1次明确返回outside_retained_history。归档+查询累计线程CPU约4.44秒、峰值存储帧JSON约39.97MB，无capture error；这些不是进程RSS或完整IPC/模型开销。

- **tn36：1→4关。** 在latest已被后续动作覆盖后，读取旧action5的7帧，修正“开关逐列执行”的解释；后续确实复用操作表。然而A首关也通过原latest取得基础规则，且B的UP/SHRINK关键证据来自后续新动作/原latest/当前demo。旧API解决了一个真实信息缺口，不能把全部+3关算成其独立收益。
- **sp80：20次命中，仍1关。** 回查成功动作与失败射击帮助修正部分约束，但没有过L2；还出现跨关使用旧ROI的错误。
- **lf52：3次命中，3→1关。** 读到了事件顺序，仍未形成有效目标规则；另有一次旧引用超出保留范围。
- **bp35：1→2关。** 第2关在动作66已完成，历史查询直到动作83之后才发生，不能把新增1关记为查询后的收益。

28个含新API的Python调用按call_id核实进入真实request/工具反馈；3次KeyError来自字段层级/status守卫误用，说明接口仍有使用摩擦。没有把捕获成功或调用次数当作理解成功。[采用与迁移证据](../../research/010-intervention-analysis.md)

最大涨分m0r0没有查询新工具，1→5关，贡献全池+5.9102；最大下降ft09也没有查询，6→4关，贡献−4.6074。两臂首次动作时刻和实际token分配差异较大，首次动作不等于已测出的GPU入场/纯排队时间；实际gate尚未完整还原。ft09候选第3关还因约束抄写/解释失误多用58个动作。共同动作账token截面下m0r0仍有部分优势，但这不是等算力因果对照。[零查询轨迹](../../research/010-zero-query-traces.md)

### 下一步取舍

本轮具备真实工程交付和非零模型采用，完整同池结果为正；但没有多个查询病例新增关卡的直接证据，少了一个全通，故**不晋升、不直接正式提交，也不宣称已达到稳定提分条件**。已有009的正式31.16保持为生产参考。

若继续投入GPU，优先一次固定010源码的候选先跑→baseline后跑确认，仍保留完整12局；只补实际首请求/slot与逐游戏成本等观测，避免把首次动作时间当排队时间。不在同一轮叠加接口简化、deadline修复或调度经验表。重点检验tn36式知识迁移能否重复、零查询大涨是否重现、ft09等控制是否持续退化。若净覆盖优势不复现，则停止这一版的扩跑；确认后才考虑全25及正式候选。

接口字段/status误用、跨关ROI过期、已计算约束被手工改写、截止附近无效生成分别保留为独立后续问题。当前共享账户剩余5.40h（CLI舍入值），10/17 08:00北京刷新；不是本项目独占额度。本次仅下载与分析，没有新GPU作业或正式提交。

## 实现、核验与GPU启动（10/13 09:26更新）

新增[retrievable_animation.py](../../src/arc3_research/retrievable_animation.py)，在每个真实动作返回后独立复制SDK完整帧；通过现有callback/sandbox IPC提供 `animation_refs()`、`animation_at(ref)`。原last_animation含RESET的特殊语义保持。每session128条metadata/4MiB帧JSON，全局64MiB/128sessions；有明确淘汰/超大/错scope状态和帧hash，不自动把完整历史加入prompt。reference arm完全不import或安装新模块；003/006/007均关闭。

最终模块SHA256为 `ea4bb1a77433e2ccefbb9d46abe9e82e6eac8ae5c058828662e4732a940ca875`。真实SDK→逐动作capture→callback→隔离sandbox通过，包含同batch中较早动画、实际RESET后旧帧、独立真实session隔离、精确像素/hash、retained函数跨snippet查询、原latest开/关合同。容量/错误输入的边界另用合成帧验证。[97项最终记录](../../experiments/010-integration-checks/cpu-20261013T012311Z/summary.json)、[19类边界记录](../../experiments/010-integration-checks/boundary-checks.json)、[复算和范围](../../experiments/010-integration-checks/README.md)。这些不是97个独立游戏或模型实验；没有真实跨关、fatal autoreset及生产并发压力结果。

生产候选采用有界JSON内存存储，区别于下方早期NPZ研究原型。此CPU实际6动作捕获12个SDK帧，带before约150,531B；旧7帧IPC约102,542B。完整sandbox调用约0.131–0.132秒，只打印选区/校验字段约1,044字符。这是手写CPU探针，不是模型自动采用；JSON字节上限不等于进程RSS。

Notebook采用27个可读普通单元，11份helper各自使用原生 `%%writefile`。实际IPython写出字节/hash全匹配，20个code cells转换后编译通过，原大patch cell保持一致、末LF及git apply解析通过。没有新增exec/compile/eval单元外壳。[Notebook核验](../../experiments/010-notebook-checks.json)

已推送私有 [ARC3 010 Retrievable Animation v1](https://www.kaggle.com/code/ccjjllt/arc3-010-retrievable-animation)。Notebook 692,483B，SHA256 `36fae12d8d6e536f280d94632b1f0cc93af2852295e3919c9081e4c10dc17d35`；源码冻结在[010-source](../../experiments/010-source/)。Kaggle返回version1，MCP状态RUNNING；回拉27个cell类型/正文与本地全部一致，私有/GPU/断网/RTX PRO 6000 metadata正确。[启动记录](../../experiments/010-launch.json)、[远端源码比对](../../experiments/010-remote-source-check.json)

实际启动命令：

```bash
kaggle kernels push -p notebooks/010-retrievable-animation -t 9000 --accelerator NvidiaRtxPro6000
```

两组顺序baseline→retrievable_animation，各12游戏/3482秒/10路活跃、共享一次模型加载，启动上限1200秒，总硬限9000秒，预期约2.2h。不是正式比赛submission，没有占用每日正式槽位。09:29后实时日志确认11份helper写出、原始patch应用成功，实际GPU为RTX PRO 6000、离线Pennyroyal安装和serving进程启动完成。目前模型加载中，尚未确认health或首组真实游戏动作；本地日志读取器已关闭，远端Notebook继续运行。见[启动观察](../../experiments/010-startup-observation.json)。模型采用、结果与逐游戏覆盖需待输出完成后核验。

## 本轮完成

1. 从比赛API确认009正式COMPLETE和31.16；连续读取榜单前5页/500队，定位本队247名。比赛当前4221队、金牌附近第18名36.98、第五名42.66。读取最新比赛页面、近期讨论和共享GPU余额7.5249h；原件在[10/13快照](../../research/snapshots/2026-10-13/)。
2. 刷新两种排序各50个Notebook条目，审计三类实现及版本/源码对应：未找到有独立成绩证据的直接升级。额外用005–007保存状态检查80k tail排序敏感性，不把重排推算成分数。[Notebook审计](../../research/010-notebook-update.md)
3. 重新阅读VISTA、Tracing、PRO-LONG、Tycho、Twin论文原文和作者实现/报告，核对预算、动作上限、重复次数、公开/隐藏协议。明确高预算近满分不能迁移为9h比赛预期。[前沿报告](../../research/010-frontier-update.md)
4. 下载既有005 cd82公开日志补齐对照，确认其首关608秒，前300秒也0关；009短验证不构成退化证据。区分正确观察被误记和旧动画不可访问两个机制。[本地诊断](../../research/010-local-diagnostics.md)
5. 使用公开SDK完成旧动作帧归档/取回的最小CPU研究；没有执行日志中的模型代码、没有读取引擎实现或隐藏状态。[研究脚本](../../scripts/analyze_010_animation_archive.py)、[详细可行性](../../research/010-animation-feasibility.md)

## 实际CPU结果

独立seed=0公开tn36，只执行5个已固定MOUSE坐标和1次RESET。action2返回7帧/256暂态像素，action5与RESET各1帧。动作3/4/5后均能把旧action2的7帧完整取回；RESET后重新从磁盘载入索引，全部13帧与本次原始返回逐像素/哈希一致。错误attempt/session键拒绝；5个旧轨迹可见端点与005一致，但这不等于恢复005未保存的中间帧。

- 13帧uint8原数组53,248B；压缩payload3,129B、索引5,918B，合计9,047B。
- 单次16×16区域输出688字符；单个完整帧4,670字符；7个区域合并4,824字符。输出开销仍须在线计量，不能因为存储小就默认全部注入prompt。
- 100次本地热读：区域查询中位0.297ms，整帧1.190ms；包含解压/hash/ASCII构建，不含json.dumps、IPC、模型、冷读。
- Python读取索引对象约27,293B；整项研究tracemalloc峰值包含SDK/校验副本，不能当生产archive增量RSS。

来源：[latest.json](../../experiments/010-animation-archive/latest.json)指向带hash的独立运行report。脚本是研究原型，不是在线补丁；本轮没有真实跨关、生产并发隔离、容量淘汰或长期存储压力验证，也没有模型采用证据。

## 决策与下一执行门槛

CPU结果支持“原始信息可以准确取回且短序列存储可控”的工程前提。已有基线完整稳定history不变，唯一新增能力将是按旧动作选择中间帧。上述接入、作用域/反馈/日志核验与Notebook构建已完成；010 v1已完成运行及结果分析，正式比赛未submit。最新取舍见本页顶部。

首筛固定006同一12游戏与顺序、各3482秒、10活跃流、一次模型加载，预计约2.2h。记录查询→采用→行为及全池覆盖/资源；无采用不原样复跑，有采用但净覆盖不支持也不晋升。正面结果才值得倒序确认和全25检验。80k tail调度单独保留，cd82证据归属是另一候选，不叠加。

原009生产Notebook与归档的SHA256均重新核对为 `203da467cb0534fdf50b5683a55a524e647023e0d490524c59f2fda9a73b5dd5`。历史005–009源码/运行产物未覆盖；本轮新增候选模块、研究runner接入口与原生helper cell构建模式，并更新研究记录；没有新增test/CI。

完整优先级、奖牌/奖金边界和赛程取舍见[010研究决策](../../research/010-research-decision.md)。工程交付、真实查询与单轮公开正分差已核验；稳定性、检索的独立收益与正式排名提升仍未确认。
