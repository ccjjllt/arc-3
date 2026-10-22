# 029 最新公开候选与 GPU 吞吐研究

核验：2026-10-20，北京时间。只读刷新本赛 `scoreDescending` 与 `dateRun` 各40项，下载六本公开Notebook当前源码和元数据，读取四则讨论；没有运行下载的代码、GPU或新提交。原件见[检索快照](../../snapshots/2026-10-20-candidates/)与[源码审计](../../notebooks/2026-10-20/audit.json)。

**没有找到同时绑定“当前公开源码版本＋实际更高正式成绩”的可靠替代。** 因而不建议在028运行前更换底座。可新增的退路是两个具体程序执行机制；吞吐方面出现了反对盲目增加并发的最新负结果。

## 公开版本与成绩绑定

| Notebook | 当前版本 | 相对10月18日材料的新增内容 | 成绩边界 |
|---|---:|---|---|
| [Heliosli](https://www.kaggle.com/code/heliosli/try-merging-it-you-might-get-lucky-and-win-gold) | 6 | 从v4变为关内持久Python，保留空动画兼容修复 | 源码明确未宣称隐藏分收益；本队名匹配到的公开提交56835496／32.60来自10月4日，不能归给新v6 |
| [Dennis D-prime public base](https://www.kaggle.com/code/dennis6886/arc3-d-prime-public-base) | 2 | D-prime公式与输入／Python运行时适配 | 作者队名匹配的57396830／32.59可见，但公开安全API不含Notebook版本绑定；正文31.54为旧作者叙述 |
| [Yongjiehi T06](https://www.kaggle.com/code/yongjiehishi/arc3-duck-lab-t06) | 6 | 原Franzen底座与路径适配，维持10 streams | 没有嵌入输出或当前版本正式成绩绑定 |
| [Yukailiu Champion](https://www.kaggle.com/code/yukailiu/arc-agi-3-champion-solution) | 36 | 从v34撤掉Lexicon／D-prime组合，回到23-cell原底稿及适配 | harness patch与10月18日归档相同；Champion标题不代表新能力 |
| [Habanwer Lexicon D-prime](https://www.kaggle.com/code/habanwer/arcaid3-lexicon-dprime-dfranzen-m2) | 1 | Lexicon加D-prime及空动画兼容 | 正文明确尚未计分；团队31.90不能归给该组合 |
| [Neural BFS Episodic Solver](https://www.kaggle.com/code/mayankraaz/arc-agi-3-neural-bfs-episodic-solver) | 5 | 实际为Franzen＋D-prime＋空动画兼容，并非标题暗示的新神经BFS | 无嵌入输出或独立新增搜索收益 |

上述六本返回源码全部没有嵌入运行输出。尝试进一步读取三份公开提交详情均403；[公开安全提交列表](../../snapshots/2026-10-20-candidates/team-heliosli-public-submissions.json)只能给出ID、日期和分数，不能建立源码版本因果关系。搜索列表与详情的 `lastRunTime` 仍不一致，采用版本号与实际源码hash判断更新，不能把搜索日期当源码发布日期。

## 三项可用价值

### 空动画返回保持文档字段

Heliosli v5／v6、Habanwer新组合和Neural BFS v5都包含同一小修复：`animation.py` 在最新动作只有单帧时，原来只返回 `error`；新实现同时返回 `action`、`frames=0` 和 `steps=[]`，避免模型按文档读取 `steps`／`frames` 时产生KeyError。这是可单独抽出的兼容修复，与新调度或新提示无依赖。[当前源码cell5](../../notebooks/2026-10-20/heliosli__try-merging-it-you-might-get-lucky-and-win-gold/source.ipynb)。

如果028没有净收益，可先从现有请求找这种具体异常和随后的重复重算；确有作用窗口时只移植这处返回结构，沿用既有GPU验证入口。它减少的是可预防的工具错误，当前没有正式提分证据，不能单独预期银牌增幅。

### 关内持久 Python 可以保存搜索进度

Heliosli v6以每游戏每关一个独立解释器替代每工具调用新进程。模型变量、导入、搜索队列和计划可跨调用存在；换关、换游戏或工具超时清空。运行时每次刷新当前帧和历史，普通缓存不会自动跟随画面更新。原安全函数池仍用于跨关，不能把它等同于015的受限字面量缓存。[静态提取模块](../../notebooks/2026-10-20/heliosli__try-merging-it-you-might-get-lucky-and-win-gold/persistent_python.py)、[接入补丁](../../notebooks/2026-10-20/heliosli__try-merging-it-you-might-get-lucky-and-win-gold/patch_persistent_python.py)。

这直接对应本项目“搜索表／模拟器变量消失，下一次重新构建”的故障。若作为028退路，应挑已有日志中确因普通变量丢失而中断的自然病例，比较是否保存并使用已有搜索结果；只移植持久解释器，不连带D-prime、重启或新观察API。源码已取得但未执行，内存、旧帧缓存及超时后的状态丢失都需在真实病例中计成本。不能把10月4日的32.60归给这个新机制。

### 提高 GPU 利用率优先填满十路队列

10月20日新[讨论750885](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/750885)报告：同Franzen M2／RTX PRO6000，把streams、MAXREQ与CUDAGRAPH_MAXBS从10改为14后，吞吐从约600–620 tok/s降到后段约280 tok/s，均分47.30→29.90。作者另报告110k-token停关阈值使均分下降约9.1分。这是参赛者自报，未取得其逐题原件独立复算；不能把作者自行推算的标准误或“至少10分才可信”当本项目门槛。

对本轮的可执行含义是：优先保持现有十路有请求、并行CPU恢复与工具执行、共享一次加载，观察真实吞吐、排队和KV抢占。不要为了GPU利用率百分比把并发直接提到14，也不要用停滞token阈值抢占仍可能解出的游戏。该经验与本项目027调度负结果方向一致。

另有[750981](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/750981)自报同一版本32.76→24.03，当前没有主持人确认平台变更；只能支持保留版本、硬件及吞吐记录。关于正式rerun扣费，[750586](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/750586)有用户回答仅save扣额度，但当前响应没有作者身份／官方标记，不能升级为官方计费确认。

当前执行建议：先完成028真实修复及采用证据；没有收益时，从“空动画异常修复”或“关内搜索进度保留”二选一开展最小能力比较。此次检索不支持直接换上某本所谓高分Notebook并宣布预计提分。
