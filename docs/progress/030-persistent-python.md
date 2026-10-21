# 030 关内持久Python执行进展

最新阶段（2026-10-21 11:16北京时间核验）：**submission57447779已COMPLETE，public24.40，比009的31.16下降6.76分**。保留009为当前最佳，030不扩大，不重新push／submit。核验时间不是平台完成时间。[正式记录](../../experiments/030-formal-submission.json)、[回退诊断](../../experiments/030-final/regression-diagnostic.json)。以下保留分阶段历史。

2026-10-20 21:05，北京时间。用户已授权实际GPU研究、尽快确认提分并正式提交，并单独授权每15分钟自动续接，直到本轮submission评测完成。

`zhuating/arc3-030-capability-comparison` **v2已真正进入求解**，真实单张RTX PRO6000、97887MiB。候选persistent_python先跑，原baseline随后跑；各25题、7254秒、10 streams，共用一次模型加载。日志已观察候选运行120秒；尚无030均分或新正式submission。求解预算合计约4小时，最终时间以真实日志为准。

Notebook SHA256 `265ed9a9b84f118190a4262b96f85c6204be031de613f64a6fd4ca755ab8a994`，冻结源 `experiments/030-capability-source-v2/`，状态入口 [launch](../../experiments/030-capability-launch.json)，完整本地日志 `runs/030-capability-comparison/live-notebook-v2.log`。v1因1200秒启动分配不足退出，没有运行求解；v2修复wrapper签名、放宽启动等待至1800秒，未缩短任一臂预算。v2全量模型预读458.31秒，首臂开始时会话约835秒。

028已完成真实模型修复诊断，三对均无新增关卡，关闭本版；不重复GPU，不混入030。[028结果](../../research/028-program-repair-results.md)。030不新增模型API，直接让模型的普通变量／搜索队列在同一关存活，换关／超时／结束清理。

本聊天自动续接 **arc3** 已ACTIVE，每15分钟检查；无变化保持安静，收到实际结果继续分析，出现有意义增益即推进候选自己的必要Kaggle保存流程及真正competition submit，记录ID并跟进COMPLETE。原最佳009 v2／57101330／public31.16保留。自动审批最初拒绝持久任务；用户随后明确授权，创建已成功。

结果分析入口：`python3.12 -B scripts/analyze_030_results.py --root runs/030-capability-comparison --output-dir experiments/030-analysis`。用真实官方均分、逐题/关卡、token成本和变量复用轨迹判断，不套新的多条件晋升门或新增测试套件。若030明确负面，再用已准备的独立031精确分割runs短研究；031尚未启动GPU。

zhuating CLI在20:54读到剩余28.28h，属于历史快照，不据此推导本作业计费。实际生成利用率证据见 [GPU说明](../../research/030-gpu-utilization-notes.md)。下一次031已停用与SGLang分片预读重复的整目录model precache，保留分片预读、wheel预缓存及全部推理数值参数；当前030源码不因此改变，下一次效果未实测。

## 23:05阶段结果

v2候选臂在23:03:58完成：25题、102/183关、8全通；控制台均分47.17，4643动作、4,408,842生成token。运行状态为8 won／12 cancelled／5 gave_up，无crashed／not_started，无残留工作线程，arm退出码0，wall约7278.85秒。均分及逐题分数目前仅有控制台两位小数，完整benchmark尚未下载，不能据此代替后续精确重算。

baseline已在同一服务自动接续，每臂7254秒不变，没有再次加载模型。截至该阶段没有同轮基线均分或配对增益，不能用027历史基线作本轮对照。冻结[候选控制台片段](../../experiments/030-analysis/candidate-console.txt)及[部分结果JSON](../../experiments/030-analysis/candidate-partial.json)，保存真实完成事件与片段hash。尚未产生新正式submission。

## 10月21日01:10阶段结果

研究v2两臂均已完成。实际benchmark精算baseline42.613362→candidate47.169880，**+4.556518**；全通5→8，总关103→102，记录token+1.76%。去最大正向r11l后其余24题仍+1.4939。会话内部4.2785h、模型进程组已关闭；GPU求解均值92.33%／91.74%，中位99%／98%。[完整研究分析](../../research/030-results-analysis.md)；不要求所有辅助指标同时上升，不追加全池确认。

**正式候选保存v1已经推送**：`zhuating/arc3-030-persistent-submission`，源hash `cf08d5876048343b86102917e171d77b2c27b8e65de431afc7fb22d76befb95a`，使用与研究v2相同的helper。下一步优先读 [030-submission-launch](../../experiments/030-submission-launch.json)，监控这个已有保存作业；不要重复push或再跑030／031。保存成功后提交该准确版本，之后跟进实际submission ID。

当前还没有新正式submission；保存运行和placeholder不能算正式提交。自动化已经更新到保存／正式提交阶段，保留应用当前配置的30分钟检查节奏（早期文档15分钟是创建时意图），无变化保持安静。实际CLI余额24.08h是01:05快照。

## 01:31真实提交

候选保存v1已COMPLETE：health200、`save-smoke-report.status=passed`，sb26有114非RESET动作／30285记录token、cd82有21动作／33461token；两题状态cancelled均合法。保存整体内部1229.45秒，模型health ready915.28秒，拥有的模型进程组已清理。完整[保存报告](../../experiments/030-submission-smoke/save-smoke-report.json)及[输出hash](../../experiments/030-submission-smoke/output-manifest.json)保留；未把保存分数或placeholder当隐藏榜分数。

下载前后latest均为v1，远端所有cell源码与冻结Notebook一致。查询当日额度为1后，已用 `-k zhuating/arc3-030-persistent-submission -v1 -f submission.parquet` 真正competition submit；CLI退出0、返回当天剩余0。随后API新增 **57447779**，日期 `2026-10-20T17:31:02.180UTC`，描述与030源码hash完全一致，状态PENDING、public为空。[正式记录](../../experiments/030-formal-submission.json)。

自动续接已改为只跟踪57447779至COMPLETE，再报告实际分数并停用；不重复消耗每日机会，不启动031。原009 v2／57101330／31.16保留。保存后CLI余额23.74h仅为快照，不据此推导正式评测计费。

## 正式结果与判断修正

2026-10-21 11:16北京时间查询确认COMPLETE／public24.40。正式回退−6.76分（约−21.69%），private未公开；API未返回完成时间。官方GetSubmission同样返回COMPLETE／24.40，未返回错误描述；episodes为空、正式parquet下载403，拿不到隐藏逐题轨迹或实际运行时长。因此不能宣称已证明“完整跑完全部隐藏题”，也不能断言此次回退由OOM、模型加载或某段错误缓存直接造成。[正式接口原件与限制](../../experiments/030-final/read-manifest.json)。

公开证据显示此前对+4.56的稳定性判断过于乐观：005／027／030基线49.8997／50.4293／42.6134，观察跨度7.8160；这些历史运行不等于严格重复，但030候选47.1699也未超过历史高基线。最大两项r11l与cd82合计对均分贡献+5.8643，超过净增益；其余23题平均−1.4214仅作敏感性说明，不是删题后的官方分数。12正10负3平，新增22关同时丢23关。持久状态真实采用的证据足够，却不能替代广泛净收益和隐藏迁移证据。

原009继续保留。当前自动化更新接口返回arc3已不存在；没有重建自动化，也没有新增GPU、提交或测试套件。
