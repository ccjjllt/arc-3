# 031 精确像素：执行进展

2026-10-21，北京时间。目标与决策规则见[交接方案](../handoff/031-score-and-submission-handoff.md)。

## 当前状态

**031 v2自然短跑已启动，尚无新正式submission。** 最佳正式成绩仍为009的31.16。031 v1已完成且不晋升，不能以其结果证明v2效果。

## 已完成

- 刷新比赛、前500榜单、提交及额度。11:58、031启动前快照为本队393/4566、允许正式提交1次、CLI GPU23.74h；均不是此刻实时状态。
- v1同状态诊断 `zhuating/arc3-031-recorded-state-exact-pixels` v1已COMPLETE。两臂各三个250秒切点，均0新增；ft09两边各2动作，B新代码仍用boundary填框，把背景g误成W，0次runs读取。见[结果](../../research/notes/031/031-forks-results.md)和[采用审阅](../../experiments/031-forks-analysis/adoption-review.json)。
- v1远端28个cell与冻结源码完全一致；下载后仍为v1/COMPLETE。模型就绪1693.78秒，会话2278.67秒、约0.633h，缓存刷新和完整覆盖通过，GPU服务正常退出。原helper已归档，不重跑v1。
- 限时公开候选刷新未找到准确源码版本与更高正式成绩的可靠绑定，不据队伍榜分直接换底座。
- v2只在系统节点清单补齐已有runs合同，增加150字符；13项系统提示/host/sandbox/卸载核验通过，0模型或GPU调用。正式候选16项静态检查通过，helper与研究一致。

## 已启动的唯一自然短跑

- 实际Notebook：`zhuating/arc3-031-natural-aligned`，**Notebook v1、helper v2**。启动记录：`experiments/031-natural-launch.json`。
- 固定10题、10 streams，两臂各900秒，baseline先、segmentation_runs后；warmup=1，不安装request_deadline。总上限5400秒，模型服务共享一次，进程独立且臂间清缓存。
- helper SHA256：`b4c5cc5b398d8b7365c1f2e2b022b5f3bc7a575afcc7e3e56c46b5a92450deee`。
- Notebook SHA256：`01fa4dc75e14a23f8a90150c6a2d6966bf856fd2fb7860d04232e94fec82d9cf`。
- 启动前最新CLI余额23.11h（v1结束后），是账号共享通用GPU余额，不是独立RTX保证。

## 接下来

读新请求里首次segmentation到集合的代码，核对实际runs消费、纠错、动作/关卡推进及输出成本。有直接增量才进入冻结全25题A/B；仍不消费或没有纠错推进则停止本版。相关关卡未到达时记为窗口未回答问题，不自动扩大。

全池、正式候选GPU save和真实competition submit均未执行。用户已要求实际提交，候选通过交接中的效果判断后直接完成save及准确版本提交；不以push、静态检查或开发分数代替正式submission ID和COMPLETE成绩。

- 13:18观察到模型已就绪、baseline已开始（会话约1454秒时进入第一臂，日志已到elapsed60s）。两臂仍保留各900秒；候选尚未开始，无分数结论。

- 用户要求由其在运行完成后通知：暂停状态轮询，保留GPU作业继续执行，不创建自动化或新作业。恢复时先查询现有自然对照并读取结果，不重复push。
