# 035 实施进展

2026-10-24。034 v9两题仍0host动作、同期均分−1.9939，已执行预定停损，不再调合同。035只比较辅助低推理模式与关闭推理，额外保留原009无辅助控制。[设计](../plan/035-auxiliary-reasoning-mode.md) · [v9结果](../../research/notes/034/034-v9-results-analysis.md)

## 实现与核验

冻结C→B→A：C只在辅助请求使用thinking=True＋reasoning_effort=low，B与v9关闭思考请求逐值一致，A不安装辅助分支。合同、上下文、PROMPT、对象几何、主循环、模型、触发、回滚及一次共享反馈保持。单次4096输出包含推理和代码，没有增加额度。

off／low各5个原生场景通过，共88次child调用、18次脚本completion；最终HTTP边界检查证明tokenize／generation用同一payload，low只改变两个模式字段，普通ToolAgent未变。测试使用合成世界和脚本completion，不是真模型／真ARC收益。[CPU报告](../../experiments/035-cpu-check/report.json)

33cells／1024169字节Notebook，SHA256 `ebe8a40219330c10913796d732811493aaa3ff1cfa32906a7207188fa2a6e6dc`；21份manifest输入、20份预冻结hash、16份Python payload核对及编译通过，combinedfork逐对象一致。独立预检确认尾部14个harness／服务／模型cell与v9逐字一致，源码、配置和最终CPU报告hash相符。[独立预检](../../experiments/035-preparation/independent-preflight.json) · [构建审计](../../experiments/035-preparation/build-audit.json) · [源码](../../experiments/035-source/)

实际挂载模板仍须在C首个模型生成前做CPU渲染／hash验证。夹具及当前上游模板不冒充Kaggle挂载证明；不支持low则整轮中止，不更新模板／模型／预算。

## 已保存排队

同一私有kernel ID **140147580** 一次保存为版本 **10**，平台QUEUED，远端33cells源码与类型完全匹配冻结版。Kaggle按035新标题把这个既有kernel的slug改为`zhuating/arc3-auxiliary-reasoning-diagnostic`；这不是第二个作业，未重复push。冻结配置保留最初目标ref，后续查询应使用launch中的observed_kernel_ref；不重写已提交源来伪造一致性。[启动记录](../../experiments/035-launch.json) · [远端核对](../../experiments/035-remote-source-check.json)

原预算仍每题450秒／60动作、每臂600秒、单辅助请求60秒、累计辅助120秒包含在450秒内。三臂最坏预留6870秒，仍在7200秒上限内；不足则中止，不缩短第三臂。启动前共享GPU即时余额约27.37小时，不等于计费证据。

完成后先核验实际模板与请求推理模式，再比较C/B规则质量及C/A净得分，保留B/A分支负担和全部涨跌。若仍无有用行动／对象识别，或没有相对009的净收益，就停止这个独立分支；不再放宽合同或提高预算。完整25题净收益后才准备正式submission；当前正式最佳仍31.16，尚无本轮求解结果或新正式提交。
