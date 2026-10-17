# 013 比赛数据与竞争位置更新

核验日期：2026-10-17，北京时间。项目正式提交仍为009 v2 / 57101330 / public 31.16；当前API排名324。终局金牌与奖金需要不同的成绩门槛，继续叠加未经验证的小补丁不足以支撑两项目标。

## 最新位置与时间窗口

| 当前公开榜快照 | 排名 | 分数 | 距31.16 |
|---|---:|---:|---:|
| Tufa Labs | 1 | 68.91 | +37.75 |
| 终局前五奖金的当前参照 | 5 | 48.92 | +17.76 |
| 按当前队数估计的金牌边界 | 18 | 38.20 | +7.04 |
| 本队ccjjllt | 324 | 31.16 | — |

比赛元数据返回4388队。按[Kaggle奖牌规则](https://www.kaggle.com/progression/competitions)的1000+队公式，金牌名额估计为10+floor(4388/500)=18；最终有效队数、私榜与资格审查才决定获奖。这里的38.20和48.92是当前竞争参照，不是固定终局分数线。

连续取得4页、400个不重复team_id，ccjjllt在第324项，与competition.user_rank一致。第三页首次请求Transport closed，随后重试成功；没有将出错响应当空榜单。每页并非原子同一时刻快照。见[比赛元数据](snapshots/2026-10-17/competition.json)、[400队榜单](snapshots/2026-10-17/leaderboard-first-400.json)。

[Timeline](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview/timeline)和metadata共同确认最终截止2026-11-02 23:59 UTC，即**北京时间11月3日07:59**。每天最多1次正式提交，最终可选2份。当前大约还有16天多，应留出实际排队、启动验证、正式评测与最终选择的时间，不能把全部日历天数等同可用实验日。

入赛截止存在接口不一致：Timeline正文写10月26日23:59 UTC，metadata.new_entrant_deadline为10月26日11:59 UTC，差12小时。本账户已经入赛；若另行考虑并队，应当先核对平台实际截止，不能把该字段直接替代并队截止。没有发出任何组队消息。

最终前五奖金仍为$40k/$15k/$10k/$5k/$5k。$700k额外大奖的Kaggle条款要求100%，不能作为当前31.16路线的现实收益预期。两次里程碑期限已过。奖金、模型与依赖条件见下文。

## 比赛数据没有出现可确认的新版本

本次重新读取全部148个文件条目，合计48,969,679字节，与10月10日下载zip的路径集合及逐文件大小完全一致；25个游戏metadata、arc_agi0.9.8和arcengine0.9.3仍在。远端列表没有内容hash，因此这个检查不证明远端每个文件字节一致，也没有重新下载/读取游戏机制源码。[当前文件清单](snapshots/2026-10-17/data-files.json)、[已有数据研究](data-findings.md)。

公开集仍为25游戏/183关，隐藏评测仍是110游戏、55/55 public/private。公开25已被用于多轮设计，不能再当完全未见holdout；008的69份区域也不能当69个独立游戏。

本地SDK计分保留逐关115%效率上限及按完成权重裁剪；网页data-description仍使用旧简述。下一轮继续以实际运行scorecard与逐关动作复算为准，不改用网页旧公式。最有价值的变化应能增加加权关卡覆盖：005保持完成集合时只有0.4764分的纯动作效率空间，不能外推为隐藏集上限。

25游戏调度压力也弱于正式110游戏（都为10活跃流）。调度候选至少用完整25池，观察真实排队、handover、关卡覆盖和成本；CPU固定历史重排只能证明排序敏感性，不能提供反事实得分。

## 高榜分数和公开源码仍不能自动绑定

额外读取前五团队及Franzen的public-safe submission接口，取得真实提交ID和分数，但接口不提供对应Notebook源码版本。例如Tufa68.91对应57119159、Yi-Chia67.49对应57084915、Franzen36.86对应57190736。榜单submission_date与public-safe date_submitted部分不同，不能据日期猜源码。[原始返回](snapshots/2026-10-17/top-team-submissions.json)。

因此下一候选只依据可审读源码、可复现机制和本项目实测晋升，不把团队最新高分归给同名公开Notebook。详细代码比较见[013 Notebook审计](013-notebook-update.md)。

## 奖金相关的新答复

10月16日00:39 UTC，Kaggle工作人员María Cruz以ADMIN身份在[许可讨论745079](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/745079)回复：无法就模型许可与比赛规则提供指导或解释。这改变了此前“尚无工作人员回复”的状态，但**没有确认Qwen3.8-Flash-Next的奖金资格，也没有宣布禁止它**。[完整回帖快照](snapshots/2026-10-17/topic-745079.json)。

Kaggle Winner License既有开放系统/模型/权重要求，也有输入数据及预训练模型许可不兼容时无需重新授予许可证的条款；这里不替主办方作法律解释。ARC Prize总体页面对自有代码/方法的开放条件与Kaggle具体条文措辞也不完全相同。当前实务是保留每项模型、量化、drafter、runtime和自有改动的准确来源/许可，准备可复现公开材料；不能从公开挂载模型或他人里程碑表现推定终局奖金资格。[Kaggle规则](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules)、[ARC Prize要求](https://arcprize.org/competitions/2026)。

## 资源与训练路线

本轮启动研究时读取共享GPU配额：总30h、已用2277.712秒、预留0，余额约**29.3673h**，下次刷新北京时间10月24日08:00。与上一条29.91h快照的差额属于共享账户消耗，本轮没有启动GPU。[配额原件](snapshots/2026-10-17/quota.json)。

[训练讨论748593](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/748593)出现参赛者直接经验：Flash-Next微调使用2×96GB、QLoRA/FSDP2/CPU offload；有人报告未获得收益，另一位只报告27B在public上SFT/行为克隆约2分提升。这些是参赛者报告，没有模型/源码/提交绑定和受控复现，不足以让当前30h单卡预算转向大规模训练。[快照](snapshots/2026-10-17/topic-748593.json)。

本阶段应把主要算力留给少量单因素在线验证、反向顺序确认及有证据的正式候选。训练/换模型需要另有可复现权重和本机离线吞吐证据，不能因为论文满分或论坛高分就跳过部署成本。
