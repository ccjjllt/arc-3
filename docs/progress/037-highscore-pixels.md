# 037：最高公开分 Notebook 的精确像素候选

2026-10-25，北京时间。用户要求基于当前最高公开分Notebook尽可能提高正式公开榜成绩，已开始构建可提交候选；不开展社区盲测或论文路线。

- 新底座：[The AGI Boys v83](https://www.kaggle.com/code/romantamrazov/the-agi-boys-i-am-better?scriptVersionId=359573474)，网页直接显示Public Score **35.35**，scriptVersionId **359573474**。当前最新版v86不是得分版本。
- 准确v83已从该版本页面下载并冻结于 `experiments/037-highscore-source/`，完整Notebook SHA256 `8221f1e64ad7d4c8b3ecbbcbd83f68c9469707246484b0bbcaa5254da809905e`。23个cell源码与v86一致；保存输出和依赖元数据单独保留。该事实不代表本队已复现35.35，也不能把分差归因于新算法。
- 本队正式最佳仍009 v2／57101330／31.16，保留其Notebook和提交记录。
- 唯一求解改动：原031 v2 `segmentation_runs`，把真实组件像素行段提供给已有分割接口；不叠加持久Python、成功记忆、辅助程序、D-prime或medium。
- 正式模式保留v83模型、draft、服务、采样、10 streams、120并发、31920秒、warmup1和实时gateway游戏列表。
- 保存模式仅做真实模型启动及sb26/cd82两题300秒检查。清空原作者的演示排除列表以保证两题存在；保存启动上限2400秒，总上限3600秒。正式预算不变。检查通过才生成官方未计分占位产物。
- 来源元数据的GPU标记冲突已识别：运行输出及页面均为RTX PRO6000，候选明确启用该GPU和断网。

资源快照：10:45账户CLI剩余约21.95 GPU小时、预留0、允许一次正式提交，28个自有Notebook的最新保存会话均已结束。余额及提交机会在启动前再次核对；这不是独立RTX配额保证。

执行顺序：完成本地构建与针对性CPU检查 → 冻结准确源码和依赖 → CLI保存真实GPU版本 → 核对远端源码及保存输出 → 使用该准确版本正式提交 → 读取真实公开成绩。此候选是探索性改进，已有031短池结果混合，不能预先称已提分。

当前未启动GPU、未创建新正式提交。后续实际状态及ID在本文件追加。

北京时间11:04左右，37候选通过CLI成功保存为私有Notebook `zhuating/arc3-037-highscore-pixels` **version1**。冻结源码29cells、688397字节，SHA256 `a4457c0605349539198dc3a516549bf6ed4c976a132e4a8255d34d9be62a6b57`。正式提交尚未创建；正在核对远端源码和真实GPU保存结果。仅保留此次save，不重复push查询状态。

启动前CLI余额21.90小时，当日提交机会1次。新CPU接入验证32项通过、真实隔离sandbox调用6次；保存和正式得分仍待验证。[启动记录](../../experiments/037-launch.json) · [CPU检查](../../experiments/037-preparation/pixel-cpu-check.json)

用户随后明确“跑完了我告诉你”：已停止状态轮询和本地CLI日志跟随，云端GPU作业未取消；未启动自动提交或定时任务。等待用户完成通知后，读取现有version1结果、核对准确源码与保存报告，再进行正式提交，不重复push。

## 保存完成与真实提交

用户通知完成后，已通过CLI回收保存报告、benchmark、安装记录、输入路径、模型/平台日志与占位产物。平台COMPLETE，仍为version1；完成后远端29cells与冻结源码逐字相同，13项源/环境核对通过。新派出的独立代理复核22项通过，未复用旧代理。

真实RTX PRO6000，模型在803.73秒就绪，保存共1124.45秒；sb26产生68次非RESET动作、33016 tokens、完成4关；cd82产生34次动作、31246 tokens、完成0关。两题按300秒预算正常cancelled，保存报告passed、helper active、源hash一致，模型清理完成。这些是运行检查，不是正式提分证据。

北京时间2026-10-25 **11:32:26**，通过CLI实际提交准确version1，编号 **57615378**，提交者zhuating、团队ccjjllt。列表已确认PENDING，尚无公开分数。只执行了一次submit，没有重新push。原最佳009／31.16保留。

[正式记录](../../experiments/037-formal-submission.json) · [接收原件](../../experiments/037-after-formal-submit.json) · [新独立复核](../../experiments/037-save-independent-review.json)

2026-10-25 13:21北京时间，用户再次通知后实时查询：正式提交57615378在CLI列表仍PENDING、publicScore为空；GetSubmission也未返回分数或错误。Notebook状态COMPLETE属于已完成保存检查，不能当作正式评分完成。距离11:32提交约1小时49分钟，未重新push或提交，等待正式结果。
