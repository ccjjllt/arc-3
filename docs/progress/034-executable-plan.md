# 034 实施进展

## v3 代码交付重设计

2026-10-22，依据[下一轮交接](../handoff/034-next-round-research-plan.md)推进；本轮创建三个新子代理，未复用先前子代理。**v3已确认RUNNING，实际源码与冻结候选一致；目前模型冷启动中，尚无新的交付或得分结论。** 正式最佳仍为009 v2／31.16。

- 辅助分支改为独立紧凑事实包：完整当前帧、未截断暂停代码、静态依赖闭包、近期真实转移和最近反例；不重放主循环全部历史，不把旧模型判断作为事实。
- 辅助请求独立关闭thinking、指定现有python工具；用固定Pennyroyal服务的`/tokenize`对最终payload做16384输入token上限检查。计数失败或超限不发生成请求；保存实际payload、响应、finish_reason、usage和分阶段耗时。主循环设置保持原样。[交付CPU核验](../../experiments/034-v3-cpu/delivery-checks.json) · [固定服务API依据](../../experiments/034-v3-cpu/delivery-api-evidence.json)
- 程序合同明确ready／completed／abstain；短合同累计最多3个动作，每步重新读当前帧和更新的近期转移。局部完成和零动作不计为环境过关。短合同结束即解除，不把预测器留给后续普通动作。
- 预测必须绑定实际动作，声明真实当前对象与目标像素、预期结果和前提；支持相关no-op与unknown。实际mismatch才允许一次修订，unknown停止后缀并回主线。宿主只核对观测和绑定，不自动证明对象语义或目标正确。
- 额外处理累计120秒包含请求、验收、重算、检查和宿主动作，逐阶段及超出量落盘。同步阻塞回调仍可能形成尾部超时，不能声称绝不越界。
- 14个原生sandbox脚本情景通过，共105次sandbox调用、14次脚本completion、零联网／真实模型／ARC游戏动作。新增核对了重算失败后真实动作与progress仍保留，并且每分支只计一次host汇总。[最终CPU报告](../../experiments/034-v3-cpu-check/final/report.json)
- B→A真实公开前缀恢复通过：ft09前27动作、su15前86动作后的帧、历史、函数、代码hash全部一致。检查未调用模型；仅未使用绘图导入作本地兼容处理。[恢复报告](../../experiments/034-v3-preparation/fork-restoration.json)
- 北京时间17:05只读配额：zhuating共享周GPU剩余约4.17小时、reserved0，现有诊断Notebook为COMPLETE。足够一次7200秒上限诊断；不足承诺同日再跑完整25题的4.03小时纯求解及冷启动。旧9.29／7.54小时余额已不适用。[资源原件](../../experiments/034-v3-preparation/resource-snapshot.json)

实际冻结候选989878字节／32cells，Notebook SHA256 `fc0f8d940d96f8e58bb3a044d9d7df956b8c781d1c9c60ecf510a272d4f32840`。同一私有目标`zhuating/arc3-034-plan-diagnostic`当前版本3，B→A，两题每臂450秒／60动作，共享一次模型加载、总上限7200秒。[启动记录](../../experiments/034-v3-launch.json) · [远端逐cell核对](../../experiments/034-v3-remote-source-check.json) · [实际运行源码](../../experiments/034-v3-source/)

两次上传API曾返回空响应／JSONDecodeError，早期只读回查仍旧v2；后续远端确认新v3正在运行，不能把早期响应异常当成最终上传失败。源代码已逐cell核实为最初冻结版本，未再上传。期间准备的无损xz包装未运行，已独立归档；canonical文件和18份冻结hash已恢复为实际在跑版本。[溯源归一](../../experiments/034-v3-preparation/source-provenance-normalization.json)

在线日志已确认NVIDIA RTX PRO 6000 Blackwell Server Edition、Pennyroyal固定版本和原始模型参数。继承启动器在约721秒后交给研究运行器继续等服务健康，这属于已知等待路径，不代表已经开始450秒续跑。CPU接线通过不作为真实交付或得分证据；机制不成立则不扩池。

用户随后表示跑完后会主动通知；已停止本地日志跟踪，远端诊断继续运行。尚未下载最终结果，不作完成或收益判断。后续收到通知后，从`experiments/034-v3-launch.json`记录的版本3及实际源码归档继续下载、完整性核对和机制分析。

## v1 与 v2 历史结果

2026-10-22。**034 v2于北京时间14:25:31完成，两臂与GPU均已正常关闭。** 相同切点A/B：ft09新增0/0关，su15新增0/1关；但两个额外响应都只有推理、没有可执行代码，程序验收/宿主计划动作/预测检查均为0，不能把su15推进归因于预期机制。正式最佳仍009／31.16；停止该版原样扩跑，下一步收窄到有界代码交付。[完整结果](../../research/034-v2-results-analysis.md) · [机制判断](../../experiments/034-v2-analysis/mechanism-assessment.json)。

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
