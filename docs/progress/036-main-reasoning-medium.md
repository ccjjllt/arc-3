# 036 实施进展

2026-10-24。035三臂均分均18.2540、程序动作0，独立辅助程序分支已按预定条件结束。036仅检验默认主循环medium相对原009的完整25题净收益，036已完成，公开均分39.4358→40.6409，但不足以晋级正式候选，无新正式提交，正式最佳仍31.16。[设计](../plan/036-main-reasoning-medium.md) · [035结果](../../research/notes/035/035-results-analysis.md)

本地实现、冻结及独立预检已通过，版本11已正常COMPLETE。每臂7254秒，完整25题从起点、10streams、warmup1、原12288输出；main_medium先，baseline后，共用原模型服务。外层21600秒，不足完整预算就中止。

主循环请求边界CPU检查已通过，传输和tokenizer为明确标注的替身；真实挂载模板则已在本次运行的双方首个生成前各自通过CPU验证。[主请求CPU报告](../../experiments/036-preparation/main-mode-cpu.json)

56项路由检查和41项独立冻结审计通过；原009 setup_env实证输出12288、thinking=True、采样0.7／0.95／20及summary0。候选HTTP请求只增加一个缺省effort字段，保留显式ladder；baseline不安装候选。CPU替身不冒充真实模型或速度收益。[路由报告](../../experiments/036-preparation/fullpool-route-review.json) · [独立预检](../../experiments/036-preparation/independent-preflight.json)

冻结Notebook 28cells／770189字节，SHA256 `90d130cc5ed14d8515cb71890ef1e8b8a54a0cdc312d93d61c8452564ebdb47d`。15份manifest输入、14份预冻结输入及archive一致，12份原生Python payload逐字核对并编译，尾14cells与035逐字一致，原harness／数值服务未变。[源码归档](../../experiments/036-source/) · [Notebook](../../notebooks/036-main-reasoning-medium/experiment.ipynb)

2026-10-24 12:20 UTC，一次保存为既有私有kernel **140147580** 的版本 **11**，保持035已观测ref及标题以避免再次重命名；这是036，不是035第二轮。平台**RUNNING**，远端28cells源码和类型全部匹配。启动前即时GPU余额26.510小时；21600秒是最大会话额度，不等于实际消耗。[启动记录](../../experiments/036-launch.json) · [精确远端核对](../../experiments/036-remote-source-check.json) · [Kaggle运行](https://www.kaggle.com/code/zhuating/arc3-auxiliary-reasoning-diagnostic)

两臂真实挂载模板证明仍记为pending_runtime，须在双方首个生成前各自执行，不能由035成功或本地替身预填通过。运行完成后回收全部返回文件，核对两个模式、25题覆盖、完整预算、cache及退出，再比较均分、关卡、全部涨跌和去掉最大涨题敏感性；保留缺响应及成本不确定性。用户通知完成后继续回收，不创建监控或重复push。尚无036成绩／正式提交，官方最佳仍31.16。

2026-10-24 23:55北京时间实时检查：平台仍RUNNING，version11及冻结源码相符。main_medium已于22:50完成25题，exit0、无遗留线程；当前baseline最近父进程心跳elapsed3900秒／session12909秒，按60秒持续更新。启动约1607秒，第一臂总wall7397秒，均处于预定边界内；当前时长本身正常，预计约25日00:55前后收尾，硬上限约02:20。运行中产物接口尚不可用，父进程心跳不等于逐题动作证明，完整模型／GPU日志及配对得分仍待完成回收。本次仅只读查询，没有取消、重启或新增GPU任务。[状态判断与证据边界](../../experiments/036-runtime-health-assessment.json)

## 2026-10-25 完成与判定

平台version11已COMPLETE，远端28cells仍与冻结源码一致。完整25题独立重算：baseline39.4357749066→medium40.6408954810，均分+1.2051205743；关卡97→100、全通4→5，10涨9跌6平。最大涨r11l+85.7143、最大跌tr87−68.2666；去最大涨题后其余24题均分差−2.3161。按预登记规则不直接晋级正式候选、不提交036，保留全部涨跌与历史正式负结果。[完整结果](../../research/notes/036/036-results-analysis.md) · [独立得分复核](../../experiments/036-analysis/score-independent-review.md)

两臂实际模板hash相同、8项检查全通过；12288／原采样／summary0在线断言保持。所有50条轨迹已记录动作均在各自7254秒窗口内。启动1607秒、总会话16406秒、两次cache首HTTP200与后台确认、CPU进程组及GPU均退出；baseline收尾有一条遗留线程并强制退出本臂CPU，保留尾响应／成本完整性限制。先前RUNNING时长属于正常完整池执行。

大型原始轨迹归档、实际请求模式／缺失响应及最大涨跌题离线反例审阅均已完成；不启动新GPU或正式提交。正式最佳仍009 v2／31.16。[完整性审阅](../../experiments/036-analysis/integrity-independent-review.json) · [下载记录](../../experiments/036-download.json)

最大跌题原样纯函数反例已复现并归档，但模型当时已自行修好，不能推出检查提示必然提分。新的独立决策建议先做预固定选取的跨题离线审计，确认广泛性与实际开销后再决定单因素候选；不从单例直接改全池prompt，也暂不为medium补跑GPU。[独立决策](../../experiments/036-analysis/next-decision-independent-review.json)

全量归档完成：442份返回输出＋平台日志，共443份／3,581,489,694字节；16份预览与全量逐字相同，下载后version11／COMPLETE和冻结源码再次确认。原009并发warmup在medium落cd82、baseline落dc22，故23/25首请求除effort相同、其余两题有预热RESET历史／step差异；所有25题仍保留，作为一次顺序实验的额外因果限制。

最终独立完整性审计47项通过，173份JSON／JSONL解析成功。medium2349请求／2339已知返回，基线2343／2333，各缺10响应；推理占比86.75%／86.59%，不支持medium明显减少推理。37条子计数大于总计数的usage异常保留，不以缺失响应冒充超时或完整成本。本轮结果已归档、不晋级；后续先跨题离线审计，并在任何新对照前明确控制／报告warmup分配。[机器可读判定](../../experiments/036-analysis/research-decision.json)
