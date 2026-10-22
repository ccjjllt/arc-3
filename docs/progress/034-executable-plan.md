# 034 实施进展

## v5 保留切点前的未验证假设

2026-10-22。**v5已确认RUNNING，远端版本5的31个cell与冻结候选一致。** 下一版优先检验紧凑上下文是否删掉了必要的既有玩法／目标判断：仅有界复制切点前已存在的assistant自然语言原文，将其明确标为`unverified`假设，并记录来源hash与截断区间。选择不依赖手工判断哪条规则正确，不加入切点后的响应、未来动作、手工正确规则或新模型摘要轮。

本版保留v4的专用提交接口、代码合同、真实mismatch才修订、每题450秒／60动作、单请求60秒及分支累计120秒等预算；总会话上限调整为6300秒，不能缩短后臂求解窗口来凑时长。正式最佳继续保留009 v2／31.16；准备通过不代表在线交付或提分，当前不进入完整25题或正式提交。

零动作验收／运行错误的一次具体反馈修订，作为[独立候选建议](../../experiments/034-v4-analysis/program-independent-review.json)保留，不与本轮上下文改动混测。选择本轮方向的依据是旧玩法／目标判断确实未进入v4紧凑包；这仍是假设，需要真实结果检验。[下一方向审阅](../../experiments/034-v4-analysis/next-direction-review.json)

北京时间2026-10-22 21:35上传成功，私有目标仍为`zhuating/arc3-034-plan-diagnostic`。冻结Notebook957458字节，SHA256 `48f83080d3258cfddc81f942d7f48fbb52b818ac25634260dedb29db7cf98e01`；19份源输入hash、14份Python payload及编译通过，14个原生sandbox场景通过。ft09选切点前消息39／37，共9047字符；su15选94／91，共5657字符。字段`old_conversation_included=false`表示不回放完整会话，新增`prior_assistant_text_included`另记有界旧文字。[上下文核验](../../experiments/034-v5-preparation/hypothesis-context-checks.json) · [CPU核验](../../experiments/034-v5-cpu-check/report.json) · [独立预检](../../experiments/034-v5-preparation/independent-preflight.json)

上传前即时配额仍6708.032秒，已确认上次COMPLETE。6300秒会话上限保留4200启动、1800秒原双臂／缓存／收尾预留和300秒余量，不足完整预算则中止。本轮只有一次上传，API明确返回版本5，源码逐cell回读一致；尚无真实模型交付或得分结论。按用户此前安排等待跑完通知，不持续跟踪长冷启动；远端作业继续。[启动记录](../../experiments/034-v5-launch.json) · [源码核对](../../experiments/034-v5-remote-source-check.json) · [冻结源码](../../experiments/034-v5-source/)

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
