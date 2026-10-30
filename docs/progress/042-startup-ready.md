# 042：先确认模型就绪，再进入比赛

2026-10-29。用户通知提交额度恢复。实时核查团队今日剩1次；041仍为0.00、3411B，没有重评结果。平台讨论仍有零分报告，没有取得平台已修复的确认。本轮继续针对041疑似正式启动早停准备最小修复，尚不能确认041根因。

## 新证据和改动

[753489](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/753489)作者自报stockFranzen仅延长modelwait到90min得26.16；这是参赛者报告，源码未公开，本账号读取其submission返回权限不足，不能独立证明净收益，也不能把其local47.39和LB26.16差当20分生产损失。[753447](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/753447)另有生命周期wrapper27.05的源码公告，本轮不整套搬入。

独立源码审查表明：本代码的scorecard在bm.run→GameAPI._start_game→_CompetitionScorecard.open_run时打开，位于原launcher之后。先等health200可避免我们在模型未就绪时开启自己的card。SDK默认idle15min不证明远端配置相同；Kaggle另有Notebook级无动作限制及平台故障仍可能影响运行。

042基于041准确23cells，只改两个代码单元：cell4等待常量12→90min和对应注释；cell12尾部等待块改为必须health200、进程仍活且尚未超deadline才放行。退出或超时打印模型日志并抛错，写startup-readiness.json。其它21cells、模型启动命令、模型/提示/采样、游戏求解、gateway、占位输出协议、v83镜像31401和五输入版本保持。未加入D-prime、step、像素字段或额外游戏动作。

NOTEBOOK_START_TIME起90min上限使用剩余时间换算单调时钟，HTTPtimeout与sleep受剩余预算约束。慢启动占用同一9h平台预算，不能把90min后剩余7.5h说成还能玩9h。原demo仍为10题×25min。

## 验证与资源

新增片段的11项CPU检查通过，覆盖12min后才就绪、连接错后恢复、503持续到90min、进程退出、健康返回后进程退出、已超预算、晚到200以及等待边界。测试使用可控时钟/HTTP/进程，没有真实网络、模型、GPU或动作。Notebook反向差异核验通过，仅cells4/12变化，原启动命令及正式gateway未变。

候选23cells／654435字节，SHA256 `7e7920ff6f74b4206d617ed46443bf4f2d30978a1261d6fbfd66625adfc98ee9`。片段SHA `1f9027be1dc7ef3b60df23a8d8bd4657c26a2c595e61372751a62aac92f57f90`。

按账号CLI查询并复查：jiyujia剩2.12h、zhuating0.51h，刷新10月31日UTC00:00。新Kaggle连接的quota用户身份未确认，不将其余额归到这两个账号。jiyujia保存任务库存没有已确认RUNNING／QUEUED，交互session未被完整列出。原demo最坏约90+25=115min，小于2.12h，但共享额度和退出耗时有余量风险；今天正式1次尚未使用。

先做一次042真实GPU保存验证，检查readiness ready→benchmark开始→真实动作与输出的顺序。保存成功后才可选择准确版本正式提交，不拿CPU通过当提分或正式运行成功。按用户习惯等待完成通知，不设置自动化。

[构建Notebook](../../notebooks/042-startup-ready/submission.ipynb) · [冻结源码](../../experiments/042-submission-source/) · [CPU检查](../../experiments/042-preparation/readiness-cpu-check.json) · [独立设计审查](../../experiments/042-preparation/startup-design-review.json) · [来源快照](../../research/snapshots/2026-10-29-startup/)

## 已启动v1保存验证

09:15北京时间，CLI push一次成功，**jiyujia/arc3-042-startup-ready v1／Notebook ID141425517，RUNNING**。新Kaggle连接读取该私有Notebook被权限拒绝，改用已授权jiyujia CLI完成回读：23cells全与本地相同，仅相对041的cells4/12变化；镜像31401、五输入版本、RTX、私有断网等14项全部通过。新派独立代理对最终产物22项检查通过。

启动前账号GPU再次读取仍2.12h，保存库存无已确认运行任务。未消耗今天的正式提交次数，仍以先前读数1次为准；尚无042公开分数。等待用户完成通知后下载startup-readiness.json、benchmark、serve.log、Notebook日志和submission.parquet，检查ready确在benchmark与动作之前，保存通过后再用准确v1提交一次；先重新排重和查额度。没有创建自动任务或连续轮询。

[运行页面](https://www.kaggle.com/code/jiyujia/arc3-042-startup-ready) · [启动记录](../../experiments/042-launch.json) · [远端源码核验](../../experiments/042-remote-source-check.json)

## 保存完成并正式提交

2026-10-29 18:08北京时间回读。042 v1保存 **COMPLETE**，重新获取远端代码/配置15项全部通过；23cells、SHA、镜像31401和五输入版本与冻结原件相同。下载六份输出并记录哈希，保存结果21项通过；本轮新派独立代理复核通过，没有提交阻塞项。

模型在Notebook起 **559.662秒（约9分20秒）** health200且进程存活。日志相对时序为READY 565.077秒→Starting benchmark 566.957秒→warmup RESET 567.410秒，硬就绪门按预期放行。日志中的原文“before analyzer reachable”是保留的warmup文案，出现在READY之后，不能据此推断模型仍未就绪。本次未达到旧12min阈值，故没有真实GPU验证超12min慢启动恢复；CPU覆盖了这个分支，也不能据此确认041零分根因。

原demo10题×25min完整结束：**2 won／8 gave_up，共47关、1365次非RESET动作、836153个记录生成token，离线均分49.561256**。benchmark耗时1521.426秒；两个日志均无致命Traceback/OOM/ERROR，GPU型号与补丁应用正常。预算边界存在已处理的analyzer read timeout，Notebook正常收尾。离线分不是榜单分；此次没有更改求解器，单次demo分差不能作为提分证据。

保存的submission.parquet为2648B，PAR1头尾，SHA与原版offline placeholder相同，符合原保留协议。正式提交使用Notebook版本执行（-k／-v1），没有将demo占位文件当预测直接上传。

提交前确认团队ccjjllt剩1次且没有042历史提交。**18:07:25北京时间**通过jiyujia正式提交准确v1一次：**submission 57767406，scriptVersionId363333844，PENDING**，今天剩0次。CLI成功并已从提交列表和详情确认接收；尚无公开分数。保留009的31.16最佳，等用户完成通知再查正式结果，没有自动监控或重复提交。

[保存结果](../../experiments/042-save-result.json) · [独立复核](../../experiments/042-save-independent-review.json) · [保存输出清单](../../experiments/042-save-output-manifest.json) · [提交前源码核验](../../experiments/042-before-formal-source-check.json) · [正式提交记录](../../experiments/042-formal-submission.json) · [准确版本](https://www.kaggle.com/code/jiyujia/arc3-042-startup-ready?scriptVersionId=363333844)

## 正式结果：26.09，未刷新最佳

2026-10-30 08:44北京时间，Kaggle连接和已授权jiyujia CLI独立读取均确认 **submission57767406，COMPLETE，public26.09，3807B**。CLI列表同时绑定准确scriptVersionId363333844、原提交描述与源码SHA；团队仍为ccjjllt。相对009最佳31.16低 **5.07**，不替换最佳版本。

本次获得非零正式分数，但不能证明是90min硬就绪门造成了改善，不能宣布041零分根因已解决。042只改启动等待，没有新增求解算法；保存时559.66秒就绪，早于原12min上限。不同日期各一次正式结果不是配对对照。

正式episodes接口返回空对象，没有可见逐题记录、health日志或实际worker运行起止。COMPLETE、3807B与非零总分均不能证明所有隐藏游戏充分运行。API的date仍为提交创建时间，不计算成实际评测时长；离线49.56和正式26.09来自不同题池与预算，二者差值不能解释为运行损失。

决定：**结束042原样重提，保留009的31.16。** 就绪检查可留作工程稳健性措施，但不再把延长timeout当提分方案。已有038静态审计覆盖了009与公开基线的核心求解等价关系，无需重做相同diff；下一轮候选应从现有036等轨迹的跨题工具/程序失败中寻找可验证的耗时或动作损失，再选择单变量求解改动。该方向尚未形成新的可提交版本，不直接重启已停损的D-prime或medium分支。

今日额度读数为 **剩1次、已用0次**。本轮只读结果并归档，没有新正式提交、GPU运行或自动监控。新派代理独立审核同意上述结论。

[正式回执](../../experiments/042-formal-result-snapshot.json) · [诊断可用性](../../experiments/042-formal-diagnostics-availability.json) · [独立结果审核](../../experiments/042-formal-result-independent-review.json) · [既有009/v83差异审计](../../experiments/038-analysis/038-vs009-runtime-audit.json)
