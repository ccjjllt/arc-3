# 017 — 深度研究进展

日期：2026-10-18，Asia/Shanghai。状态：**比赛/数据、公开Notebook、前沿与本地原始轨迹研究已完成；选择018观察状态保真作为下一推理候选，FP8 PLE作为独立工程备选。** 对应[计划](../plan/017-research-next.md)、[综合决策](../../research/notes/017/017-research-decision.md)。

## 本轮新增证据

- 连续读取500队榜单，当前本队jiyujia第339/4444、31.16；009提交仍COMPLETE。当前金牌边界参照38.20、前五48.92。全部148文件路径/大小及规则正文与10/17一致；Paper Track与模型许可讨论也重新核对。
- 两账号配额接口当前均报总6h、已用超额、预留0，刷新10/24 08:00北京；与旧30h记录冲突。原件保存，未猜测原因，GPU规划余额按0。
- 读取19本公开Notebook准确版本/源码；主要强基线家族无变化。Lexicon历史引用计数不足以证明当前版本自然消费或收益；Sujan校验的点击/比较边界明确；FP8 PLE的上游15分片相同、host表减半与既有loader路径核验完成，尚无GPU速度/质量结果。
- 新增10/15 stop-and-report论文，更新OPINE-World v3探索消融，核对作者控制代码与预算。已有ToolAgent续聊能力重叠、公开强模型/大预算不能直接推导本项目效果。
- 回收016队员完整结果并复算50局：+0.3293、105→111关，去r11l后−1.5205，未过晋升门；冻结源码、预算、缓存和排空有效。原ccjjllt失败轮分开记录。
- 静态审计015/016的18份请求、1281个去重Python调用。纯字面量复核ft09转抄一格错误、tr87裁剪15→11像素、ar25颜色88/物理足迹99/目标207的区别。re86确认一次真变量复用，仍无第二游戏。
- 四份完整25游戏baseline共100局重新复算，描述稳定低覆盖与不稳定全通病例；事后最好包络不作为可部署策略、重启收益或隐藏分数预测。

## 决策与已开展的准备

018仅用既有system-prefix提示模型在图形转程序时核对当前局部原始单元和坐标；不新增API、不自动修改提取结果、不强制每个动作都验证。使用ft09/tr87/ar25/sb26四游戏短筛方案，各臂1000s，先看自然采用与开销，再决定全25及反序。代码/实际CPU核验状态单列于[018进展](018-observation-grounding.md)，不与研究依据混报。

014/016当前版不做同版倒序，015不进全池，009正式不变。资源实际可用时仍遵从jiyujia账号规则；本轮未创建新GPU作业、正式提交、对外消息或自动化。

## 可复核入口

- [比赛数据与资源](../../research/notes/017/017-competition-update.md)及[原始快照](../../research/snapshots/2026-10-18/)
- [Notebook与FP8 PLE研究](../../research/notes/017/017-notebook-update.md)及[源码审计索引](../../research/notebooks/2026-10-18/audit.json)
- [前沿研究](../../research/notes/017/017-frontier-update.md)及[来源账本](../../research/frontier/2026-10-18/source-ledger.json)
- [016结果](../../research/notes/016/016-results-analysis.md)、[017原始调用证据](../../research/notes/017/017-local-evidence.md)
- [50局复算和时序](../../experiments/016-analysis/)、[四次baseline统计](../../experiments/017-research/cross-run-coverage.json)

所有结果继续区分CPU正确、模型自然采用、行为改变、公开同预算净覆盖和正式隐藏成绩。下一步最重要的未知是短提示是否会改善模型自己构造程序状态的行为；当前没有提分或获奖概率结论。
