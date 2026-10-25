# 038 公开方案晚间更新

2026-10-25，北京时间晚间。只读刷新Kaggle官方CLI/SDK的公开Notebook按分前40、最近运行前60，以及近期讨论；定向取得8份源码。没有执行下载代码、调用模型、启动GPU、提交或修改solver。网页搜索未能读取部分Kaggle正文，事实以归档官方API返回及静态源码为准。[快照](../../snapshots/2026-10-25-evening/)

**最高分候选列表没有出现新突破。** 与上午相比，按分排序前24项顺序及列表lastRunTime均未变；前四仍为The AGI Boys、Franzen、lalalia-final、tantan D-prime。API本身不返回数值score，不能由排序推算分数；上午浏览器确认的35.35、34.30、33.94、33.55只是此前UI记录。本轮没有找到能准确绑定更高正式成绩的新算法。

| 本轮新审源码 | 返回版本 | 实际变化及边界 |
|---|---:|---|
| [youdocare/The AGI Boys Fork](https://www.kaggle.com/code/youdocare/the-agi-boys-fork-romantamrazov-35-35) | 2 | 文件SHA与上午AGI Boys v86完全相同，标题35.35是来源提示，不构成该fork独立复现 |
| [vickyfym/lalalia-dprime-m85tuned](https://www.kaggle.com/code/vickyfym/arc-agi-3-lalalia-dprime-m85tuned) | 1 | 既有SLM记忆缩短：动作30→8、reasoning900→300字符、规则600→450、完整保留关数3→1、询问2→1；同时叠加D-prime与55分钟启动/3600秒超时，缺少干净收益绑定 |
| [weitaoguo/SLM plus 55min startup fix](https://www.kaggle.com/code/weitaoguo/arc3-slm-plus-55min-startup-fix) | 2 | 既有SLM及启动等待修改，没有新的解题机制 |
| [guangyuanwangkaggle/Franzen solution](https://www.kaggle.com/code/guangyuanwangkaggle/arc-agi-3solution-basedondaniel-franzen) | 26 | 既有SLM，启动等待改120分钟、初始HTTP重试3600秒；不能未经9小时预算检查直接移植 |
| [ouyangruize/Milestone 2](https://www.kaggle.com/code/ouyangruize/arc-agi-3-milestone-2-solution) | 10 | 新增运行时兼容与保留函数补丁，同时混有D-prime、animation guard和temperature0.5；可拆出小修，不宜整体移植 |
| [Sovereign Agent](https://www.kaggle.com/code/bang1850/arc-prize-2026-sovereign-agent) | 35 | 大量压缩SDK、Lexicon、D-prime、守卫、keepalive和MEMFRAC0.92混合；无组件独立收益，审计及运行风险较高 |
| [Auditable CPU Batching](https://www.kaggle.com/code/hylin16/arc3-auditable-cpu-batching) | 1 | 作者明确为CPU diagnostic policy，模型路径为空；尚无本地Kaggle结果，不是可替换当前Qwen的高分实现 |
| [Priced Curiosity EC](https://www.kaggle.com/code/samuraiiii/priced-curiosity-ec) | 2 | 不调用LLM的图探索/动作经济策略，使用逐关估计动作基准；没有得分或有效解题结果绑定，不作为即时底座 |

8份下载源码都没有嵌入运行输出。版本与source hash见[detail-read-manifest.json](../../snapshots/2026-10-25-evening/detail-read-manifest.json)。旧作者正文及fork标题分数不能升级为最新版本得分。

**最值得拆出的改动是HistoryEntryView.step兼容属性。** ouyangruize v10的`apply_framework_upgrades()`对HistoryEntryView/TransitionView实现大范围`__getattr__`，将step/level/ascii/shape/segmentation/_grid委托给frame。我们的当前runtime有更小的落地点：

- `FrameView.step`由序列化payload中的step直接构造，代表该历史观察的原始步号。
- `_history_from_payload`为每条历史记录构造`entry.frame`；`_transitions_from_history`又将同一frame视作after_frame。
- 因而仅增加一个只读`HistoryEntryView.step`属性，返回`self.frame.step`，与求解器原本应写的`entry.frame.step`语义一致；不能用历史列表索引重建步号，因为历史可能裁剪。
- 不需要复制ouyang的其它属性代理、函数常量内联、soft timeout或temperature改动。也不需增加系统提示或每次观察输出。frame缺失时应保留错误，不伪造0/当前步数。
- 本轮仅做源码语义审查，未实现或运行该补丁。root的另一路日志审计已确认实际缺失step异常，收益仍须从减少失败调用及后续正式成绩验证。

对应本地源码：[python_tool_sandbox.py](../../runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py:160)，公开实现位于本次ouyang源码cell5。原始接口和新的property会改变`hasattr(entry, 'step')`结果，这是预期接口扩展；不要宣称对所有任意Python程序完全行为等价。

**第二顺位保留空动画返回字段修复。** 当最后动作没有多帧动画时，返回体仍提供合法的`action`、`frames=0`、`steps=[]`，能消除调用方按文档读取字段引起的KeyError。它是此前已知的小修，非今晚新发现；历史已有跨日志实例，通常下一调用很快恢复，因此收益预期应低于实质新增解题能力。它应独立验证，不与step alias同时塞入首个候选。[历史精确调用证据](../../../experiments/031-next-mechanism/animation-error-expanded.json) · [先前来源审查](../029/029-latest-candidates.md)

**平台问题是当前真实风险，但不足以解释037退分。** [751598评论3543749](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/751598#3543749)的回复署名María，明确说部分区域dataset cache不稳定导致慢读和启动超时，已部署修复但仍在调查后续受影响运行。10月25日仍有参赛者报告慢读、0分和部分分数。官方API消息没有独立作者身份字段，本报告保留其署名和原文，不以每条社区推断当作官方结论。

已有keepalive方案报告在本地competition-mode gateway避免了27分钟附近自动关闭，但作者后续正式运行仍为system error，未证明提分。单纯把startup拉到55或120分钟而保留31920秒solver，需同时审查全局9小时截止和初始gateway活动；不能按“等待更久一定更稳”直接添加。我们没有037正式运行日志，无法把26.71归因于平台或排除平台影响。[751598原件](../../snapshots/2026-10-25-evening/topic-751598.json)

**并发和调度证据没有新增支持。** [750885](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/750885)仍报告10→14 streams后吞吐及成绩大降，以及110k-token停关阈值退分；是参赛者自报，不能直接套用其方差或“至少10分”门槛。D-prime源码现在被许多fork复用，当前材料没有隔离出稳健净收益。

**GPU额度口径仍需保守。** 本赛[750586](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/750586)最新回复仍止于10月21日，只有普通用户说正式rerun不扣周额度，未取得本赛官方明确答复。检索到Ryan Holbrook在[AIMO3官方回复](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/discussion/635859)表示该比赛正式提交不计周额度，但那是另一场比赛的说明；不能用于断言本赛这次余额下降的原因。以root本次CLI读取的实际余额安排实验，不将未经证实的免费rerun作为预算前提。

本轮建议：保留准确v83原样对照，同时优先只做`HistoryEntryView.step`这个无需模型学习新工具的兼容候选。其余公开混合方案没有足够证据支持整本替换或叠加。
