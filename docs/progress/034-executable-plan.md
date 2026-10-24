# 034 实施进展

## v9 完成：停止合同调参

2026-10-24。v9已COMPLETE，44份返回产物全部回收，实际版本9与冻结的32cells候选逐项一致。A两题均分20.2479，B18.2540，差−1.9939；ft09 A新增1关／B0，su15均0。两题host动作／预测检查／真实反例修订／程序直接过关全部0，触发预定停损，停止合同调参，不扩大或正式提交v9。[完整结果](../../research/notes/034/034-v9-results-analysis.md)

四份源码都交付，实际返回值和反馈可靠；ft09首份错误提取背景却宣称completed，修订仍误读旧动作且预测集合不全；su15首份把顶部组件当棋子，预测集合与声明完全不交，修订后合法弃权。继续放宽绑定或像素要求不能证明正确规则。[程序审阅](../../experiments/034-v9-analysis/program-independent-review.json) · [原样复现](../../experiments/034-v9-analysis/generated-code-offline-review.json)

会话36.23分钟、模型准备20.80分钟；辅助34.285／40.840秒计入原450秒，成本未双算。A cache第3次才成功后开始，所有真实动作重基后在450秒内，su15 A保留2.071秒在途／收尾尾部。共享A日志补计一条su15尾响应，逐题表面4缺口校正为3，不能称4次超时。CPU／GPU正常收尾。[完整性](../../experiments/034-v9-analysis/integrity-independent-review.json) · [尾响应补计](../../experiments/034-v9-analysis/main-response-reconciliation.json) · [完成记录](../../experiments/034-v9-launch.json)

下一独立假设记为035：保持v9合同及PROMPT，仅比较辅助low推理／关闭思考，并同期保留009无辅助基线；不叫v10合同修复，不把关闭思考的效果当作已证明。[035设计](../plan/035-auxiliary-reasoning-mode.md) · [035实际进展](035-auxiliary-reasoning.md)

## v9 已保存排队

2026-10-24。v9已在同一私有诊断目标一次push为版本9，平台状态QUEUED，远端32个cell源码和类型与冻结候选一致；没有重复上传、额外作业或正式submission。SDK的`to_dict()`会省略默认值QUEUED=0，已改用`response.status.name`确认排队。[启动记录](../../experiments/034-v9-launch.json) · [远端核对](../../experiments/034-v9-remote-source-check.json)

34个原生场景／279次child／49次脚本completion／15项纯合同检查通过。四份v8实际计划回归证明三份弃权正常停止，su15错误ready仍因2个重复坐标和6个错色拒收。首轮checker因历史输入定位问题在child执行前失败，原报告保留，改用可追溯fixture后完整重跑通过。CPU不代表真实模型规则或得分收益。[最终CPU报告](../../experiments/034-v9-cpu-check-final/report.json) · [原样输出fixture](../../experiments/034-v9-preparation/v8-plan-fixtures.json)

冻结Notebook为32cells／1006499字节，SHA256 `b5788a726e38955ad2edc0b8b20ea231ecf6efaa22f6fff12f049ef2ab0273c5`；20份manifest／19份预冻结输入／15份Python payload一致。独立审核确认模型、thinking、原始事实、主循环、触发、回滚、预测检查、两切点和预算保持v8。辅助反馈含单份完整失败源码、实际returned_plan和多项诊断，不替模型改目标或像素。[独立预检](../../experiments/034-v9-preparation/independent-preflight.json) · [构建审计](../../experiments/034-v9-preparation/build-audit.json) · [源码归档](../../experiments/034-v9-source/)

仍450秒／60动作、每臂600秒、辅助120秒包含在450秒、单请求60秒、总7200秒。启动前GPU即时余额约27.97小时。完成后先看实际动作与规则修订，若仍双题0host动作就停止合同调参；没有扩大25题或正式提交的依据。[v9计划](../plan/034-v9-typed-status-interface.md)

## v8 回收结论与v9准备

2026-10-24。v8已COMPLETE，官方42项输出＋平台日志全部回收，远端版本8与冻结32cells一致。A/B两题都0新增关，均分18.2540→18.2540，差0。四份完整程序全extract通过，但三份真实abstain、一份错误ready全部在plan验收停止；host动作／预测检查／规则反例修订均0。交付门槛已越过，不代表行动机制成立，不扩大或正式提交v8。[完整结果](../../research/notes/034/034-v8-results-analysis.md)

ft09两份把ascii字符串误当二维数组，捕获异常后弃权，反馈却只报空replaces；su15把大写B背景当目标，首份既重复坐标又有6处错色，修订后仍弃权。离线原样复现不算在线推进，单独放宽字段不会获得有效动作。[独立程序审阅](../../experiments/034-v8-analysis/program-independent-review.json) · [原样复现](../../experiments/034-v8-analysis/generated-code-offline-review.json)

会话42.58分钟，模型启动27.20分钟；辅助31.997／39.506秒计入原450秒，没有重复。所有真实动作在预算内，结束尾耗时0.041–0.097秒保留；B缓存首试成功，A两次400后第3次200并获后端确认。主60请求／56响应，本轮无共享尾响应可补，缺4条不能称4次超时。GPU／CPU正常收尾，剩余即时余额约27.97小时。[完整性](../../experiments/034-v8-analysis/integrity-independent-review.json) · [完成记录](../../experiments/034-v8-launch.json)

依据本轮新子代理的独立审阅，只再做一次类型明确／状态敏感的接口修正：ascii:str示例，真实returned_plan＋多项计划诊断，合法弃权不当作ready填空错误；ready和预测证据保持严格。先原样输出回归与窄原生CPU核验，再原预算诊断。若仍双题零host动作，停止这一方向的合同调参。v9已完成核验并保存排队，未创建正式submission。[v9计划](../plan/034-v9-typed-status-interface.md) · [配置](../../experiments/034-plan-diagnostic-v9.json)

## v8 交付接口修复

2026-10-24。按用户授权继续研究提分，本轮新建三个子代理，未复用前轮代理。根据v7实际拒收，取消120非空行硬门槛，保留12000 UTF-8字节／AST节点资源限制；允许辅助函数使用有界不可变字面量默认值，入口仍严格。新增最多16项静态诊断及省略计数，反馈一次处理同时可发现的问题；被截断的副作用拒绝仍通过独立标志阻止重试。原零动作／观测不变、回滚、一次共享反馈和所有求解预算保持。[计划](../plan/034-v8-delivery-interface.md)

30个原生CPU场景及7个纯合同检查全部通过，249次child调用／43次脚本completion；12份错误反馈各含一份完整失败源码，最多2请求，未重复计费。它们是合成世界的接线证据，不是真实模型或ARC得分。[CPU报告](../../experiments/034-v8-cpu-check/report.json) · [复核](../../experiments/034-v8-cpu-check/independent-review.json)

真实v7保存源码原样重验，两份修订稿在v8可提取，两份初稿仍因语法或结构错误被拒收；未执行这些源码，不作为模型修复或规则正确的证据。v7已知ft09 abstain、su15预测集合错误仍待实际反馈解决。[纯提取复查](../../experiments/034-v8-preparation/contract-review.json)

已冻结v8 Notebook，32cells／990984字节，SHA256 `d56ab961983f72e75dc8e57f5ece2a1ce1087329ef7deb70616702176e904c6e`；20份manifest输入、19份预冻结输入及15份Python payload核对通过。[构建审计](../../experiments/034-v8-preparation/build-audit.json) · [配置](../../experiments/034-plan-diagnostic-v8.json) · [源码归档](../../experiments/034-v8-source/)

最终独立预检通过，在同一私有诊断目标一次push返回版本8，实际32个cell源码与类型匹配冻结版。v8现已COMPLETE，两题分数差0、host动作0，不扩大或正式提交；结果详上。原预算B→A：450秒／60动作，每臂600秒，辅助总120秒，启动4200秒／总7200秒；启动前可用GPU约28.69小时为历史快照。[独立预检](../../experiments/034-v8-preparation/independent-preflight.json) · [启动记录](../../experiments/034-v8-launch.json) · [远端核对](../../experiments/034-v8-remote-source-check.json)

## v7 短程序交付与零动作错误反馈

2026-10-24。**v7已COMPLETE，远端版本7的32个cell与冻结候选一致。两题均分23.8095→18.2540（−5.5556）；真实零动作反馈已工作，短程序交付仍未解决，不扩大或正式提交。** 按用户明确要求，仅处理短交付与零动作验收反馈：候选代码上限120非空行／12000 UTF-8字节；保持原定义／计算导入合同，不由宿主改代码。首次extract、plan或首预测失败，若0真实动作且level／step／grid完全未变，才可获得一次具体错误反馈。[计划](../plan/034-v7-short-program-feedback.md)

反馈含完整失败源码、真实异常／child traceback或schema错误与不变观测证据，并与原真实mismatch共用一次repair额度，每游戏仍最多2个辅助请求。修好后实际失配不再补发；第二次验收失败停止。基础设施、超时、副作用拒绝、合法unknown与预算不足均不自动重试。失败函数、history与repeat guard回滚；日志单独记录实际代码长度、失败阶段、反馈资格与实际消费。

首次事实和旧假设保留v6。反馈请求为保完整失败源码和错误，仅省略旧自然语言正文，保留来源index/hash并明确标记；不截断失败代码。原16384输入上限仍以服务tokenize判断，thinking=False、4096输出上限不变。对象目录、mainloop、自然触发、模型和游戏事实不变。

25个原生手工场景全部通过，194次真实子sandbox调用、35次脚本completion、1次显式注入基础设施故障；网络／真实模型／GPU／真实ARC动作均0。涵盖长度／常量／语法拒收反馈、plan和predict类型错修好后执行、两次请求上限、反馈后失配不再修、失配修订失败不再补发、预算耗尽、unknown／infra不重试、回滚和动作／耗时不双计。42项纯合同检查和4项Unicode反馈往返也通过。它们证明接线与边界，不证明真实模型会交付正确程序或提分。[权威CPU报告](../../experiments/034-v7-cpu-check-final/report.json) · [合同边界](../../experiments/034-v7-preparation/contract-bounds-checks.json) · [专项反馈](../../experiments/034-v7-preparation/unicode-feedback-check.json) · [实施记录](../../experiments/034-v7-preparation/implementation-note.json)

最终冻结Notebook983048字节／32cells，SHA256 `ab793c287c15a3feaaf76aa099fb1a5e44cc2915d00d76365d0e251da5cc42ca`；20份manifest输入、19份预冻结hash、15份Python payload及编译全部一致。独立重建v6两份初始事实与代码／旧假设一致，反馈完整失败源码恰一处；非模拟耗尽场景的branch elapsed之和与extra_seconds一致。[构建审计](../../experiments/034-v7-preparation/build-audit.json) · [独立预检](../../experiments/034-v7-preparation/independent-preflight.json) · [冻结配置](../../experiments/034-plan-diagnostic-v7.json)

原ft09／su15切点B→A，每题450秒／60动作，单请求60秒、辅助累计120秒全部计入450秒；每臂600秒、启动4200秒、总7200秒。启动前共享可用约29.26小时，上次私有版本6已COMPLETE且源码一致。不做正式submission，009 v2／31.16继续保留。


北京时间2026-10-24 14:36，同一私有目标`zhuating/arc3-034-plan-diagnostic`一次上传成功为版本7，随后平台RUNNING；32个cell源码逐项一致。用户通知跑完后已完整下载并完成两份独立审阅。[启动记录](../../experiments/034-v7-launch.json) · [远端源码核对](../../experiments/034-v7-remote-source-check.json) · [冻结源码](../../experiments/034-v7-source/)

本次ft09两臂均新增0关，续跑29／16动作；su15 A新增1关／B新增0关，23／42动作。两题首次代码165／183非空行超120，经完整错误反馈后缩到129／105行；ft09仍被新行数门槛拒收，su15则因字面量默认参数`r0=10`被全禁defaults合同拒收。四份代码均小于12000字节。每游戏恰好首次＋一次反馈，失败源码恰一份、真实错误／棋盘不变证据／旧NL省略标记均在线核对通过，没有第三次请求。

所有程序均止于extract，host动作／预测检查／真实反例修订／直接过关均0，覆盖审计“不适用”。离线仅取消ft09行限，虽可提取却返回abstain；su15把默认字面量移入函数后，计划通过但expected49像素与声明73像素完全不相交。这是本地Frame替身的机械反事实，不是原生执行或实际模型修复。说明120行格式门槛及全禁默认参数确有接口负担，放宽本身又不足以解决目标／规则和预测问题。[完整结果](../../research/notes/034/034-v7-results-analysis.md) · [机制判断](../../experiments/034-v7-analysis/mechanism-assessment.json) · [程序独立审阅](../../experiments/034-v7-analysis/program-independent-review.json) · [离线诊断](../../experiments/034-v7-analysis/generated-code-offline-review.json)

辅助处理分别33.444／38.933秒，与逐请求求和相同；会话34.23分钟、启动18.79分钟。源码20份manifest来源、恢复、四请求hash、实际payload/tokenize、cache及CPU／GPU收尾一致，全部真实动作在450秒内。逐题末response表面缺4条，B共享日志一条尾响应可按7字段唯一匹配并补计，实际仍缺3条；known usage不是完整成本，不称4次超时。[完整性独立审阅](../../experiments/034-v7-analysis/integrity-independent-review.json) · [尾响应补计](../../experiments/034-v7-analysis/main-response-reconciliation.json) · [最终平台快照](../../experiments/034-v7-final-platform-snapshot.json)

下一设计先降低人为接口负担：按字节／AST资源控制短代码、审查静态安全字面量默认值、汇总可同时发现的静态错误；保持零动作／副作用检查、一次共享反馈与原预算。不继续叠表示，也不把放宽验收当作得分成功。当前仅归档结果，未修改solver、未准备或启动下一候选；正式最佳仍009 v2／31.16。

## v6 当前对象几何与变化证据

2026-10-24。**v6已COMPLETE，远端版本6的32个cell与冻结候选逐项一致。两题均分18.2540→23.8095（+5.5556），但辅助host动作／预测检查／真实修订均为0，不能把su15普通主循环的新增1关作为对象目录收益，不扩大或正式提交。** 新配额读取为30 GPU小时，旧52分钟余额已过期。依据v5真实失败，下一版只检验“可直接使用的当前连通区域几何与近期变化表示＋配套使用说明”。角色仍是模型假设，不是宿主UI黑名单或正确对象答案。[计划](../plan/034-v6-object-evidence.md) · [设计独立审阅](../../experiments/034-v6-preparation/design-independent-review.json)

新纯函数在宿主事实包和原生`frame.object_evidence`中共用，提供逐帧ID、颜色、像素数、bbox和精确展开范围（矩形bbox／非矩形完整runs），不合并同色分离实例。近期最多两次真实变化只按当前坐标投影，跨关／形状边界不提供对象动作支持。多色、断开对象可以是多个分量组合；静止不等于UI，控件也可能可操作。超出完整几何界限明确unavailable，没有静默截断。

28项纯几何检查、7项原生child检查及原有14场景通过；原生动作后目录和ID重新计算，host／child逐值相等。v5预测覆盖校准复现4／36、4／36、4／16、4／16，第四次遥远计数条另为1／52；它只用于后续审计，不发送给求解器或新增验收门槛。[几何核验](../../experiments/034-v6-preparation/object-facts-cpu.json) · [原生刷新](../../experiments/034-v6-preparation/native-object-checks.json) · [回归核验](../../experiments/034-v6-cpu-check/final/report.json) · [覆盖校准](../../experiments/034-v6-preparation/coverage-audit-calibration.json)

两切点catalog含近期事实为7323／4312字符，最终请求仍以服务tokenize的16384-token上限为准。v5旧假设保留；thinking、模型、主循环、执行合同与真实mismatch修订不变，无新增模型轮次或异常重试。同ft09／su15切点B→A，每游戏450秒／60动作，额外处理120秒计入450，单请求60秒；每臂600秒、启动4200、总7200秒。准备通过不表示程序会采用目录或得分会提高。

冻结Notebook970283字节／32cells，SHA256 `1927e60863c4c39ee5e23d33bd284f3182b03e5208897b5fa20eecac92ac3a9a`；20份manifest源输入hash、19份预冻结hash和15份Python payload编译通过。[构建审计](../../experiments/034-v6-preparation/build-audit.json) · [冻结配置](../../experiments/034-plan-diagnostic-v6.json)


私有目标仍为`zhuating/arc3-034-plan-diagnostic`，本轮一次push明确返回版本6，随后平台RUNNING；实际32个cell逐项核对一致。启动前即时共享额度108000秒。用户通知跑完后已完整回收产物并完成独立审阅。正式最佳仍009 v2／31.16。[启动记录](../../experiments/034-v6-launch.json) · [远端逐cell核对](../../experiments/034-v6-remote-source-check.json) · [最终独立预检](../../experiments/034-v6-preparation/independent-preflight.json) · [实际源码归档](../../experiments/034-v6-source/)

本次ft09 A/B均新增0关（11／24动作）；su15 A0／B1关（均24动作）。ft09程序未使用目录，因顶层常量违反提交合同而extract拒收；su15使用目录并通过当前计划验收，但初预测tuple+float而失败。两份响应都未截断、未超输入token上限。覆盖审计为“不适用／没有checked_action”，不能称对象角色或完整预测通过。[完整结果](../../research/notes/034/034-v6-results-analysis.md) · [机制判断](../../experiments/034-v6-analysis/mechanism-assessment.json) · [程序独立审阅](../../experiments/034-v6-analysis/program-independent-review.json) · [覆盖审计](../../experiments/034-v6-analysis/component-coverage-independent-audit.json)

离线机械复现表明，单独允许ft09常量仍识别0棋盘格且错误局部完成；su15修类型后还出现下标、重复坐标及预测集合错误，角色判断也未获支持。下一候选先收窄到短程序与零动作错误反馈，并与现有一次真实mismatch修订共享后续额度；不继续叠表示模块，尚未实施或启动下一GPU。可运行不等于规则正确或提分。[离线诊断](../../experiments/034-v6-analysis/generated-code-offline-review.json)

20份manifest源／输入、15个Python payload、四请求hash、恢复输入及实际目录重算核对一致。会话44.24分钟、模型启动28.89分钟；两cache均首轮200+后端确认，两CPU／GPU正常关闭。四末请求缺response，known usage不是完整成本。当前共享剩余约29.26小时；余额充足不替代机制和得分证据。[独立完整性审阅](../../experiments/034-v6-analysis/integrity-independent-review.json) · [最终平台快照](../../experiments/034-v6-final-platform-snapshot.json)

## v5 保留切点前的未验证假设

2026-10-22。**v5已COMPLETE，实际31个cell与冻结版本一致，两臂完整。两题均分34.9206→20.1671（−14.7535），不扩大或正式提交。** ft09 A新增2关／B新增1关，动作33／60；su15两臂均0关，动作42／41。B的ft09在327.87秒用完相同60动作上限而结束，未缩短候选预算。正式最佳继续保留009 v2／31.16。[结果分析](../../research/notes/034/034-v5-results-analysis.md) · [机制判断](../../experiments/034-v5-analysis/mechanism-assessment.json)

本版只补回切点前已有assistant自然语言原文，明确标为未验证、可能过期，并记录来源hash与截断区间；没有手工正确规则、未来轨迹或新摘要轮。保留v4专用提交工具、执行合同、thinking关闭、真实mismatch才修订；每题450秒／60动作、单请求60秒、每游戏辅助累计120秒。总会话上限6300秒，完整双臂预算未被压缩。

三次辅助请求均交付完整程序，两个ft09程序通过当前计划和首预测验收，共4个host动作。前两次点击真实任务色块，4个采样像素O→R预测命中，实际每次36像素变化；这有动作相关性，但未验证完整对象或“nothing else”。随后程序误点右侧UI色条，反例修订后又误点顶部UI，均mismatch。新增的一关发生在普通主循环，直接host过关为0；已有动作可能间接影响后续，不能把它强行归为完全无贡献或独立解题。[程序独立审阅](../../experiments/034-v5-analysis/program-independent-review.json)

su15程序的目标描述已转向送球／合并／避追击，但对单像素threat取第二元素而IndexError，零动作失败。它同时把顶部图例与实际黄棋子合为一个bbox；纯CPU只修索引后仍有错误动作目标和预测集合不一致，单独异常重试不足以解决。[离线诊断](../../experiments/034-v5-analysis/su15-code-errors-offline.json)

下一问题收窄为对象范围与角色的校验，先用本轮真实转移设计离线判据；不加入游戏专用坐标屏蔽，也不把所有界面控件一律禁用。停止v5原样重跑；零动作错误反馈继续作为独立候选，不在本轮补测。v4→v5跨会话观察不能隔离旧文本补回的因果收益。

北京时间21:35上传为私有版本5。冻结Notebook957458字节，SHA256 `48f83080d3258cfddc81f942d7f48fbb52b818ac25634260dedb29db7cf98e01`；19份输入hash、14份Python payload及编译、14个原生sandbox场景均通过。ft09选切点前消息39／37共9047字符，su15选94／91共5657，在线tokenize与usage8471／10978／9166一致。[上下文核验](../../experiments/034-v5-preparation/hypothesis-context-checks.json) · [CPU核验](../../experiments/034-v5-cpu-check/report.json) · [独立预检](../../experiments/034-v5-preparation/independent-preflight.json) · [源码核对](../../experiments/034-v5-remote-source-check.json) · [冻结源码](../../experiments/034-v5-source/)

最终44项官方清单文件齐全，JSON／JSONL与请求hash核对通过；一次下载TLS断连已补下载恢复。会话59.19分钟，模型启动43.83分钟。A缓存曾HTTP400，约1秒后重试200并获后端确认，完整预算保留；两CPU／GPU正常关闭。三份末请求缺response，已返回usage不是完整成本。当前共享余额3145.402秒，不够一轮完整新诊断，不启动新GPU或正式提交。[完整性独立审阅](../../experiments/034-v5-analysis/integrity-independent-review.json) · [最终平台快照](../../experiments/034-v5-final-platform-snapshot.json) · [完成记录](../../experiments/034-v5-launch.json)

## v4 辅助专用程序提交接口

2026-10-22。**v4已COMPLETE，远端版本4的31个cell与冻结候选逐项一致，两臂产物完整。** 本地14个原生sandbox场景和独立预检在运行前通过；真实结果显示交付接口已进入执行，但未带来净收益。[CPU核验](../../experiments/034-v4-cpu-check/report.json) · [提交接口核验](../../experiments/034-v4-preparation/delivery-interface-checks.json) · [独立预检](../../experiments/034-v4-preparation/independent-preflight.json)

本版唯一研究干预为辅助专用`submit_program`接口及配套提交指令，替换v3中“普通Python观察执行工具”与“仅交付函数定义”之间的语义冲突。宿主仍按原合同验收、执行程序，不新增模型观察轮；事实包、主循环、模型、切点和全部预算保持v3。两个切点采用无损xz合并运输，解码对象与v3逐项一致，不构成新的求解机制。[冻结配置](../../experiments/034-plan-diagnostic-v4.json)

北京时间2026-10-22 20:07上传成功，同一私有目标保存为版本4，随后只读回查为RUNNING。冻结Notebook为952500字节，SHA256 `6f9e0a891f908bcfddb90144d7e4a6b0c3803b783b0b094556861c4d5b7eade5`；19份输入hash及源码归档已保存。上传前共享可用GPU约2.84小时，单会话上限7200秒；该余额是启动前快照。[启动记录](../../experiments/034-v4-launch.json) · [远端逐cell核对](../../experiments/034-v4-remote-source-check.json) · [实际源码归档](../../experiments/034-v4-source/) · [资源原件](../../experiments/034-v4-preparation/prelaunch-platform-snapshot.json)

用户通知完成后，已下载最终结果。ft09 A新增2关、B新增0关；su15 A新增0关、B新增1关。两题均分A为34.9206，B为23.8095，差−11.1111。这只是指定切点的同期诊断，不能推广为全池或正式分数。[结果分析](../../research/notes/034/034-v4-results-analysis.md) · [程序独立审阅](../../experiments/034-v4-analysis/program-independent-review.json) · [完整性独立审阅](../../experiments/034-v4-analysis/integrity-independent-review.json)

三次辅助请求均交付完整`plan_program/predict`程序。ft09初次与真实mismatch后的修订各执行1个实际动作，两个动作相关的36像素检查均mismatch；修订确实改变了规则和动作，但保留错误网格原点，第二次仍预测失败。宿主`made_progress=true`只反映真实状态变化，B没有新增关卡，不能称修订已有效推进。

su15程序在零动作`plan_program`验收中因goal格式化参数缺失而TypeError，未产生host动作或预测检查。后续普通主循环的`MOUSE(15,32)`清除L5，不能归因于候选程序执行。完整程序交付、运行有效性、规则正确性和得分必须分开评价。

结论：不原样扩大v4，不做正式提交；正式最佳仍009 v2／31.16。下一版单独检验保留已有未验证假设，不同时加入零动作错误反馈、空间提示或触发策略改动。

## v3 代码交付重设计

2026-10-22，依据[下一轮交接](../handoff/034-next-round-research-plan.md)推进；本轮创建三个新子代理，未复用先前子代理。**v3已COMPLETE，两臂完整，实际源码与冻结候选一致。** ft09和su15两个切点的A/B均新增0关；两个辅助响应约8秒返回普通观察脚本，没有交付`plan_program/predict`函数，候选实际动作和预测检查均为0。不能称执行或修订机制成功，不原样扩大v3。[结果分析](../../research/notes/034/034-v3-results-analysis.md) · [独立程序审阅](../../experiments/034-v3-analysis/program-independent-review.json)

- 辅助分支改为独立紧凑事实包：完整当前帧、未截断暂停代码、静态依赖闭包、近期真实转移和最近反例；不重放主循环全部历史，不把旧模型判断作为事实。
- 辅助请求独立关闭thinking、指定现有python工具；用固定Pennyroyal服务的`/tokenize`对最终payload做16384输入token上限检查。计数失败或超限不发生成请求；保存实际payload、响应、finish_reason、usage和分阶段耗时。主循环设置保持原样。[交付CPU核验](../../experiments/034-v3-cpu/delivery-checks.json) · [固定服务API依据](../../experiments/034-v3-cpu/delivery-api-evidence.json)
- 程序合同明确ready／completed／abstain；短合同累计最多3个动作，每步重新读当前帧和更新的近期转移。局部完成和零动作不计为环境过关。短合同结束即解除，不把预测器留给后续普通动作。
- 预测必须绑定实际动作，声明真实当前对象与目标像素、预期结果和前提；支持相关no-op与unknown。实际mismatch才允许一次修订，unknown停止后缀并回主线。宿主只核对观测和绑定，不自动证明对象语义或目标正确。
- 额外处理累计120秒包含请求、验收、重算、检查和宿主动作，逐阶段及超出量落盘。同步阻塞回调仍可能形成尾部超时，不能声称绝不越界。
- 14个原生sandbox脚本情景通过，共105次sandbox调用、14次脚本completion、零联网／真实模型／ARC游戏动作。新增核对了重算失败后真实动作与progress仍保留，并且每分支只计一次host汇总。[最终CPU报告](../../experiments/034-v3-cpu-check/final/report.json)
- B→A真实公开前缀恢复通过：ft09前27动作、su15前86动作后的帧、历史、函数、代码hash全部一致。检查未调用模型；仅未使用绘图导入作本地兼容处理。[恢复报告](../../experiments/034-v3-preparation/fork-restoration.json)
- 北京时间17:05只读配额：zhuating共享周GPU剩余约4.17小时、reserved0，现有诊断Notebook为COMPLETE。足够一次7200秒上限诊断；不足承诺同日再跑完整25题的4.03小时纯求解及冷启动。旧9.29／7.54小时余额已不适用。[资源原件](../../experiments/034-v3-preparation/resource-snapshot.json)

实际冻结候选989878字节／32cells，Notebook SHA256 `fc0f8d940d96f8e58bb3a044d9d7df956b8c781d1c9c60ecf510a272d4f32840`。私有目标`zhuating/arc3-034-plan-diagnostic`实际运行版本3，B→A，两题每臂450秒／60动作，共享一次模型加载、总上限7200秒。[启动记录](../../experiments/034-v3-launch.json) · [远端逐cell核对](../../experiments/034-v3-remote-source-check.json) · [实际运行源码](../../experiments/034-v3-source/)

两次上传API曾返回空响应／JSONDecodeError，早期只读回查仍旧v2；后续远端确认新v3运行，不能把早期响应异常当成最终上传失败。源代码已逐cell核实为最初冻结版本，未再上传。期间准备的无损xz包装未在v3运行，已独立归档；canonical文件和18份冻结hash已恢复为实际运行版本。[溯源归一](../../experiments/034-v3-preparation/source-provenance-normalization.json)

在线日志确认NVIDIA RTX PRO 6000 Blackwell Server Edition、Pennyroyal固定版本和原始模型参数。继承启动器在约721秒后交给研究运行器继续等服务健康；实际模型启动3828.87秒，会话4780.17秒，CPU进程组和GPU服务均已确认关闭。启动耗时单列，续跑结束存在在途请求和清理尾部，不将实际时长裁成精确450秒。

用户通知跑完后，已下载最终两臂记录并核对完整性。实际辅助输入4435／6564 tokens、输出139／131，reasoning tokens均为0，finish reason均为tool_calls；服务tokenize与usage一致。两份脚本在extract阶段拒收，未执行或产生观察输出，因此只能确认长推理耗尽的失败形态已改变，不能评价程序重算、预测相关性或修订能力。后续普通主循环的ft09／su15分别执行24／40动作，仍停L3／L5，均不算候选程序消费。

## v1 与 v2 历史结果

2026-10-22。**034 v2于北京时间14:25:31完成，两臂与GPU均已正常关闭。** 相同切点A/B：ft09新增0/0关，su15新增0/1关；但两个额外响应都只有推理、没有可执行代码，程序验收/宿主计划动作/预测检查均为0，不能把su15推进归因于预期机制。正式最佳仍009／31.16；停止该版原样扩跑，下一步收窄到有界代码交付。[完整结果](../../research/notes/034/034-v2-results-analysis.md) · [机制判断](../../experiments/034-v2-analysis/mechanism-assessment.json)。

- 已新增局部程序合同、原生动作入口、自然合同建立、宿主目标/计划重算、逐动作冻结预测、失配停止与一次后续修复。
- 原sandbox脚本模型初轮7个情景通过：批次建立、连续单动作暂停、反例后修复、unknown停后缀、验证零动作、拒收回滚、换关边界；51次原sandbox调用、9次脚本completion、0联网。只证明接线，不证明真实模型采用或游戏收益。
- 追加两项边界通过：嵌套检查保留原重复动作保护；首步预测失效时零动作并回滚。追加6次原sandbox调用、1次脚本completion、0联网，原报告未覆盖。
- su15 L5切点已准备：86个原动作、97条历史消息、9个保留函数；两次公开reset/step逐步hash一致，当前帧与原请求PNG逐像素相符。求解包不含L5后续答案。
- 内部审阅已修复：最新观测与实际待修程序源码未入请求、原sandbox嵌套调用清空重复动作保护、预测验收前提交函数、额外处理预算缺统一deadline、聚合动作结果字段不一致。
- 真实A/B恢复dry-run通过：ft09前27动作、su15前86动作；两臂帧、消息、函数与源码hash相同，零模型/联网调用。本地缺少绘图库，仅未使用的绘图导入被替代，报告说明实际边界。
- 启动前账户快照：zhuating可用约9.29 GPU小时；其他优先身份均不足冷启动。该余额是启动前历史值，当前作业已启动。
- 已冻结Notebook：`notebooks/034-plan-diagnostic/experiment.ipynb`，953091字节，SHA256 `06350686614c7486e307c3e4a21f4bb87ad9291c3d07ad482a72f054308ca741`。13个Python helper cell编译通过，8份源/输入hash重新核对一致；普通配置历史校验行为保持一致。
- 第一次启动前统一将动作上限调整为60、每局450秒不变，以免30动作上限低于su15历史L5完整恢复所需动作；配置与两臂完全一致，后验解法不进入求解包。
- 自动审批两次在创建进程前拒绝`kaggle kernels push`：要求对具体私有目标`zhuating/arc3-034-plan-diagnostic`、轨迹/模型历史上传及GPU消耗获得明确确认。补充上传清单和凭据模式检查后仍拒绝；没有绕过审批，没有实际上传或启动GPU。
- 随后用户明确回复“批准”，同一冻结953091字节候选成功push为v1。北京时间12:15确认平台RUNNING，回读远端31个cell源码全部一致；日志核实实际GPU；随后完成模型启动及A臂，B前失败。上述拒绝仅为历史记录，不再是当前阻断。

接下来：修复并CPU核验有界服务端排空/缓存重试；保留v1原件，候选效果仍待同前缀在线比较。原件入口：[CPU核验](../../experiments/034-cpu-check/report.json)、[追加边界](../../experiments/034-cpu-check/followup-v2/report.json)、[A/B恢复](../../experiments/034-cpu-check/fork-restoration.json)、[su15输入边界](../../experiments/034-fork-inputs/input-boundaries.json)、[资源快照](../../experiments/034-resource-snapshot.json)、[配置](../../experiments/034-plan-diagnostic.json)、[上传清单](../../experiments/034-upload-audit.json)、[启动记录](../../experiments/034-launch.json)、[远端源码核对](../../experiments/034-remote-source-check.json)。

运行观察：原始启动器约721秒时在服务仍加载的情况下交出控制权；034研究运行器继续按4200秒总启动上限等待，观察时两臂求解尚未开始。用户随后明确关注子代理模型一致性，旧活动子代理已中断，后续结果分析新建并显式使用`gpt-6.1-sol`；比赛候选的Qwen模型和冻结源码未变。

阶段更新：模型预读62文件/185.40GB耗时1888.95秒；session2275秒时服务健康，`executable_plan_A`已开始，两题并发。长启动开销单列，450秒实际续跑预算保持完整。

最终阶段：北京时间13:00服务端确认仍有2个running请求，清缓存拒绝HTTP400。A两份请求hash与汇总一致，8份冻结源/输入hash一致；B缺失保持null，不作为零收益。已下载原始产物并生成[配对分析](../../experiments/034-analysis/summary.md)和[完整性证据](../../experiments/034-analysis/integrity-and-failure.json)。本地排空修复单列，不覆盖冻结v1。

本地收尾：已修复可选有界缓存等待与重试、HTTPError状态/body记录、每次独立滚动日志确认；CPU臂预算从缓存成功后开始，硬总预算先预留完整剩余臂和收尾。75项CPU检查通过，含7个缓存情景；默认0秒保持单次请求。未改写v1 Notebook/config及8份冻结文件，未上传或启动新作业。[报告](../../experiments/034-cpu-check/cache-drain.json)。

13:27后续：用户要求检查fail。重新读取平台ERROR与服务日志，补充独立Sol审阅发现的自适应CPU预算未预留cache时间问题。修复后94项CPU核验通过（7个缓存情景及3个会话预算场景），配置显式启用`cache_flush_wait_seconds=120`，按此前批准的同一私有两题诊断范围push成功为v2。新Notebook957565字节，SHA256 `29fab97229600b3d8ba51deb2caaa9bcef9a4825981cd500973bd3dc0668f2b9`，新建本地目录保留v1。构建器本地Python3.9生成的ft09 gzip OS头不同，解压后的逐字节内容一致；su15压缩包亦一致，8份冻结源/输入不变。v2远端31cells源码一致；尚无新求解结果。[构建核对](../../experiments/034-v2-build-audit.json) · [远端核对](../../experiments/034-v2-remote-source-check.json)。

最终结果：v2平台COMPLETE，3498.25秒；模型启动2571.23秒。两臂cache都首次200+后端确认，未实际触发忙碌重试。四份请求hash及18份源/输入hash与远端原件一致，A/B恢复hash全部相同。两份bootstrap各4096 completion、content空且tool_calls为空，提取前拒收；finish_reason在completion对象存在但未入事件，当前只作上限截断强推断。B的su15由普通循环17动作清L5、另11动作推进L6；无宿主计划执行。两额外分支累计处理87.19秒，游戏并发，不能当作额外会话墙钟。已保存两份独立Sol审阅，未启动新GPU作业。
