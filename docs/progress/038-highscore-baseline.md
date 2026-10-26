# 038：原样高分底座参考

2026-10-25。037正式26.71后，恢复The AGI Boys得分版v83的原样solver，固定同一Docker31401和5个输入版本，补上本队原样正式参考。上游35.35不是已在本队复现的分数；本队最佳仍009／31.16。

本地已构建并冻结25cells／676941字节，SHA256 `4711d9846e5d953cab075df1f78138e27eb39e277c8ce008b8ad349f87f4ad1f`。移除037的全部segmentation_runs安装单元；模型、服务、采样、调度、31920秒、120并发、10streams、warmup1及gateway与v83保持。复用已验证输入/save适配，两题300秒真实GPU保存检查配置已准备。

本地静态、配置和冻结副本检查通过；当前**未上传、未GPU运行、未正式提交**。本轮查询时GPU余额9.20h、今日提交额度0。下一步在平台额度允许时完成必要保存和准确版本提交，随后读取真实公开分数。只安排一次原样参考，不因未达到35.35就原样重复投。

[研究决策](../../research/notes/038/038-research-decision.md) · [配置](../../experiments/038-highscore-baseline.json) · [Notebook](../../notebooks/038-highscore-baseline/submission.ipynb) · [冻结核验](../../experiments/039-preparation/variant-build-review.json)

## jiyujia账号启动

2026-10-25 22:16北京时间，用户明确允许额度不足时使用jiyujia GPU配额。实时核对zhuating剩8.39h，jiyujia剩23.47h；jiyujia提交列表确认同一ccjjllt团队，今日正式额度仍为0。账号库存没有已确认运行中的保存会话，但3个旧ref返回HTTP错误及1个空ref不可查询，未声称交互会话已全面排除。

新建独立jiyujia配置和冻结副本；与原038相比仅Notebook首个配置/来源单元改变，其余24单元逐字相同。新源码SHA256 `51e11dc5d8d1a0a4852db9208b81dd2a1a453bfef4cf59f05092d64e3a3c06e8`，25cells／677608字节。共享builder只增加明确授权的账号检查，原038/039历史冻结副本保留。

CLI已成功push一次：**jiyujia/arc3-038-highscore-baseline version1，Notebook ID140791664**。22:17远端回读为RUNNING，25cells逐字匹配，GPU/私有/断网、镜像31401及5个输入版本共13项全部通过。当前运行的是GPU保存检查，尚未有038正式提交或新公开分。等待用户完成通知后读取本次结果，检查通过且团队额度恢复时使用准确版本提交。未设置自动监控、不重复push。

[启动记录](../../experiments/038-launch.json) · [jiyujia配置](../../experiments/038-highscore-baseline-jiyujia.json) · [远端核验](../../experiments/038-remote-source-check.json) · [实际运行](https://www.kaggle.com/code/jiyujia/arc3-038-highscore-baseline)

## 保存完成，等待团队提交额度

2026-10-25 23:49北京时间，用户通知完成后实时核对：平台COMPLETE、仍为version1；保存报告passed，真实RTX PRO6000。模型在627.12秒就绪，总保存检查951.26秒。sb26有62次非RESET动作、32991个动作挂接生成tokens、完成3关；cd82有53次动作、30693个同口径tokens、完成0关。两题按300秒预算正常cancelled，源hash与冻结manifest一致、benchmark SHA复算一致、模型清理完成。

完成后远端25cells再次逐字匹配，镜像及5个输入版本保持，共13项通过。原样solver仍未安装031/039。两题短测只证明可运行，不能判断是否复现上游35.35或优于037。

本次团队提交额度查询为今日已用1、剩0，因此**未创建038正式提交**。状态记为READY_AWAITING_TEAM_SUBMISSION_QUOTA；保留已通过的jiyujia版本1，额度可用时核对身份后直接提交，不重复构建或GPU保存，不设置自动轮询。当前正式最佳仍009／31.16。

[保存结果](../../experiments/038-save-result.json) · [完成后源核验](../../experiments/038-postsave-source-check.json) · [下载清单](../../experiments/038-save-output-manifest.json)

本轮新派独立代理完成26项复核，全部通过，无新增运行阻断项。[独立报告](../../experiments/038-save-independent-review.json)

## 正式提交已接受，等待评分

2026-10-26 10:11:54北京时间，用户通知额度恢复后，CLI确认团队今日剩1次，提交列表中没有038。远端仍为jiyujia v1／COMPLETE，25cells及镜像、输入版本等13项重新核验通过；本轮另派新代理只读复核，未发现阻断问题。

直接提交已保存版本，没有重构建或重跑GPU保存。CLI仅执行1次并正常退出；回读唯一新提交 **57650170，PENDING**，提交者jiyujia、团队ccjjllt、文件submission.parquet，描述绑定源码SHA256 `51e11dc5d8d1a0a4852db9208b81dd2a1a453bfef4cf59f05092d64e3a3c06e8`。今日剩余额度0，尚无038公开分数；当前正式最佳仍009／31.16，上游35.35仍未在本队验证。

等待用户通知完成后读取该提交的正式结果，不重复提交、不设置自动监控或持续轮询。

[正式提交记录](../../experiments/038-formal-submission.json) · [平台列表回执](../../experiments/038-after-formal-submissions.json) · [初始详情](../../experiments/038-submission-detail-initial.json) · [提交前源码核验](../../experiments/038-before-formal-source-check.json) · [新代理复核](../../experiments/038-formal-independent-review.json)

## 正式完成：27.73，未刷新最佳

2026-10-26 21:04北京时间，用户通知后官方CLI和GetSubmission均确认**57650170 COMPLETE／public27.73**。较009最佳31.16低3.43，较037高1.02，较上游历史35.35低7.62。原样v83本队参考已完成，不安排原样重提。

本轮准确比较009v2与038v1，代码仅配置/来源cell0与配置cell18不同；正式cell18求值结果完全一致，核心patch、模型/提示/采样/调度环境、启动器、gateway/soft_end均逐字相同。没有038带来实质新算法的证据。镜像及历史输入固定方式不同，但隐藏逐题诊断仍为空、下载403，不能单因归咎于镜像、随机性或平台，也不能由037与038的一次差值证明像素字段有害。

039降为低优先级小兼容备选。下一项优先核验D-prime准确得分版本，在009固定环境上隔离调度变化，目标是增加关卡覆盖。新代理完成独立只读复核。本轮未启动新GPU或提交。

[完整分析](../../research/notes/038/038-formal-results-analysis.md) · [最终记录](../../experiments/038-formal-submission.json) · [最终回执](../../experiments/038-formal-result-snapshot.json) · [源码/配置审计](../../experiments/038-analysis/038-vs009-runtime-audit.json) · [独立复核](../../experiments/038-formal-result-independent-review.json)
