# 010 — 公开 Notebook 更新审计（2026-10-13）

本项目 009 v2 的正式 Public LB 为 31.16（submission 57101330）。本轮刷新本赛 ScoreDescending 和 DateRun 各前 50 项，聚焦三组新增或实质更新的源码。**没有发现一个已证实能直接把 31.16 提升到奖牌区间的公开替代品。** 最便于做一因素对照的是原底座已有的 80k tail 表开关；更值得长期拆解的是显式、分作用域的数据记忆。两者都没有在本轮获得提分证据。

列表、源码、元数据、逐版本尝试和 CPU 检查统一归档于 [2026-10-13](../../notebooks/2026-10-13/)，汇总见 [audit.json](../../notebooks/2026-10-13/audit.json)。本轮没有运行 GPU、游戏动作、模型请求或正式提交，也没有执行下载 Notebook。

## 先处理分数与版本的可信度

- 排序 API 只返回顺序、标题、作者、运行时间和票数，没有数值成绩；DateRun 列表还包含附着本赛的无关分类 Notebook，不能按标题/排序直接选算法。
- 对 Fu、Heliosli、Sujan 的 CLI 下载与 MCP 当次 source 逐 cell 比较一致；记录的 `current_version_number` 分别为 1、2、28。Fu 另一本 `arc3-m2-solution-v2` 的当前 Kaggle 版本为 2。显式 `versionLabel` 请求均返回 Not found，因此本轮固定的是当次返回的版本号与下载内容 SHA256，不声称成功拉到了任意历史版本。列表 `lastRunTime` 和 GetNotebookInfo 的 `last_run_time` 不一致，均保留原值而不用于绑定成绩。
- 三组当前页面的数值分数和版本对应提交 ID 未能通过本轮接口核实；不能把排序高、标题“gold”“1st Rank”或作者团队当前成绩当成这些源码的效果。尤其 [746010 讨论](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/746010) 中 Son Pham 于 10/11 怀疑派生 metadata 将其约 39 分显示到 Franzen 页面，CPMP 于 10/12 表示若属实就是严重 bug。这是参与者报告及假设，尚非平台确认的归因；已足以要求独立的 submission/version 证据。
- Franzen 团队新的 35.86 分也不能自动归给公开 v3。我们的 31.16 是自己的真实单次提交；与公开 v3 的既有作者报告、公开 25 游戏实验是三个不同证据层级。

## 1. Jingshui Fu：新高排并不等于新算法

来源：[ARC3 M2 Solution](https://www.kaggle.com/code/jingshuifu/arc3-m2-solution)，本轮排序第 2，Kaggle v1；以及 [独立 v2 Notebook](https://www.kaggle.com/code/jingshuifu/arc3-m2-solution-v2)，Kaggle v2。

`arc3-m2-solution` v1 与 Franzen v3 的 23 个 cell 只有 cell 16 不同，而且仅改非正式分支：4 pass 改 1 pass，公开 demo 设 600 秒。**正式 solver、模型、serving、patch、调度全部相同。** 因此它没有提供新的正式求解机制，也不能用它在 Code 列表的位置证明 baseline 已有稳定更高成绩。它的简介和 write-up 链接仍指向 Franzen，不是另一份独立获奖方法说明。

独立 v2 除上述 save 修改外，仅在 cell 4 把 `ARC3_PRIORITY_TAIL_LOOKUP='remaining'` 改成 `'1'`。这开启了已经存在于 Franzen patch 的经验未来关卡价值表，并未新增程序归纳、观察工具或训练模型。参见 [v2 阅读导出](../../notebooks/2026-10-13/jingshuifu-m2-v2/readable.py) cell 4/16，和 [底座 priority_scheduler.py](../../runtime-bundle/src/ARC3-Inference/inference/agent/priority_scheduler.py)。

### 80k tail 表实际改变什么

底座优先级可以概括为 `P = (A + B × fade) × C / pace`：A 是当前关的等级权重与动作效率，C 是动作数/token 耗费的启发式衰减。我们现有 baseline 的 B 是剩余关数对应的 8/7/5/0；开关改为 `TAIL_LOOKUP_80K[N][level-1] × 0.8`。A、C、pace 默认关闭、最后 20% 的 fade、context trim 后才交接 slot 的规则均不变。

表中 80k 是**完成当前关之后，全部未来关共同使用的 token 预算**，并非额外给当前关 80k token。源码注明：336 次历史 passes、1,417 个已到达 level；1–4 关分开建 Kaplan–Meier 时长分布，后段将观测到的 5–8 关合并，9–10 关为外推；表在输出时再乘默认 0.8 效率。它是有公开历史统计来源的先验，既不是隐藏集拟合，也不是当前状态的校准成功概率，更没有随实际剩余算力重新求解整个未来过程。

以 N=8 为例，B 从 `[8,8,8,8,8,7,5,0]` 变成约 `[3.14,4.15,4.63,5.59,6.28,6.16,4.36,0]`，主要减少浅层的大额“未来机会”奖励。当前关若已停滞，仍同时受原 C 衰减；不是仅在通关后才改变预算，而是在当前任务重排时改变其“若此关能过，后面还值得投入多少”的估计。

N 来自现有 `game.number_of_levels` 公开会话回调，使用与 baseline 一样的 metadata 边界；没有访问隐藏环境源码、未来布局或答案。无效/缺失数值 fallback 为 10，数值夹在 6–10。这个 fallback 是对 N 的估计，不会自动切回旧 B。首次尚未启动的游戏依然使用独立的高优先级 band，开关不直接改变它们的首次入场顺序。

### 固定轨迹上的 CPU 敏感性，而非得分回放

[分析脚本](../../notebooks/2026-10-13/tail-priority-cpu.py) 只读 005/006/007 baseline 的小型 `benchmark.json`，以预算的 10/25/50/75/90% 为固定观测时点，保留真实历史，把最新已观察 action 所代表的未完成游戏状态分别代入两个公式。使用原 score normalization、pace=1 和末尾 fade。它不重建未知的等待队列，也不生成新的动作或 token。

| 原运行 | 固定状态成对次序翻转 | 最高优先级改变 | 真实 baseline 首动作全覆盖时间 |
|---|---:|---:|---:|
| 005，25 游戏 | 56/754（7.4%） | 1/5 个时点 | 2000.3 秒 |
| 006，12 游戏 | 19/287（6.6%） | 0/5 个时点 | 853.1 秒 |
| 007，12 游戏 | 19/209（9.1%） | 1/5 个时点 | 932.5 秒 |

`ActionRecord.wallclock_seconds` 是从 game start 起的累计时间，分析没有错误相加。关卡边界由单调的实际逐关动作计数重建；action-attached tokens 未包含进行中的无动作推理，也不能精确还原同一工具调用跨关时的 scheduler 账本。**真实 gate-entry/trim 时点及 admitted/waiting 集合没有包含在这些紧凑文件中，候选的覆盖时间差无法识别，结果中明确为 null。** 次序变化不是 slot 分配变化，更不是通关/分数提升。

相较新增历史动画检索，这个开关工程成本更低：已有纯函数、单一配置、无新增 prompt 或感知误报。但现有静态变化规模和未绑定的公开成绩不足以证明它的期望收益更高。12 游戏只有 10 个活跃 slot，竞争压力明显弱于 110 游戏正式场景；若后续做该候选，25 游戏的一因素匹配对照比 12 游戏更有调度诊断意义，应记录真实 trim/handover/排队/首次覆盖与 prefill 成本。它适合作为廉价的独立调度对照，不能代替观察/机制学习主线。

## 2. Heliosli v2：从函数保留扩展到显式数据生命周期

来源：[Scoped Python data memory](https://www.kaggle.com/code/heliosli/try-merging-it-you-might-get-lucky-and-win-gold)。原已读版本为 v1、23 cells；当前 v2、11 cells，标题仍是“Try merging…”但正文已明确：六项 CPU sandbox 检查通过，GPU 配对比较未完成，**没有声称得分提升**。本轮没有取得独立 GPU 结果或与当前源码绑定的正式 submission。

原始 Franzen 大 patch 完全相同；新增 `scratch` 数据字典和宿主/sandbox 传递协议。已把 Notebook 中的源码字面值提取为 [scoped_memory.py](../../notebooks/2026-10-13/heliosli-update/extracted-assets/scoped_memory.py) 与 [patch_scoped_memory.py](../../notebooks/2026-10-13/heliosli-update/extracted-assets/patch_scoped_memory.py)，仅阅读、未安装到本项目。

- `scratch['game']` 保存跨关假设/证据；`level` 在关卡变化时清空；`step` 在动作使 step 或 level 改变时立即清空。模型必须主动存储，不自动保留普通变量、frame 或可执行对象。
- 只接受有限 JSON 值，拒绝非有限浮点；总量限制 128 KiB、24,000 个节点、嵌套深度 20。普通成功与可处理异常返回都提交快照；格式错误恢复上一有效数据。硬超时没有新快照时，宿主继续持有旧的已提交字典，下一调用依据真实 level/step 清理短期 scope。
- 动作后清空顶层 scope 字典时使用原地 `clear()`，能使指向该字典的别名看见清理。但它不会神奇地使模型此前取出的嵌套数组或普通局部变量失效；把动态棋盘放错到 game/level scope 仍然会制造陈旧观测。
- 工具反馈只列保存 key，而不是把全部记忆强塞入 prompt；模型可以主动读取数据。128 KiB 是允许存储的字节数，不能直接等同在线 token 成本或可用上下文。

这与 007 有本质区别：007只修复失败调用缺函数快照时的源码丢失；这里保留的是模型显式写入的数据。它可能减少重建解析布局、搜索结果和机制参数的浪费，也可能固化错误模拟器。因此可迁移的是**明确生命周期与提交语义**，不是简单增加持久变量。与 008 的当前帧 reference 组合是后续设计方向，不能未经单因素核验就叠加上线。

源码仍使用相同权重/serving 和正式 532 分钟预算；另一个 `run_arm.py` 只是准备的公开比较工具，存在 final token 字段/文本后备统计，不能直接当完整 usage ledger。当前正式 helper 还要求公共 `environment_files` 附件存在，这是我们的 submission-only resolver 已避免的额外依赖。已有正面检查只支持代码合同，尚未支持模型采用和分数。

## 3. Sujan v28：实质增加很多，证据反而更难解释

来源：[arc-agi-3-m2-top-submission](https://www.kaggle.com/code/sujanmajhisuzan/arc-agi-3-m2-top-submission)。旧档是 Kaggle v21；当前 API 是 **v28**，正文自命名 **v27**。它的原始大 patch、模型配置与 launcher cell 和 Franzen v3 相同；主要差异仍集中于 customization cell 16 和运行 cell 20。

新增的深层优先级把尾项改成剩余关数为 0/1/2/其他时分别给 22/18/16/14，再与停滞衰减耦合；启用多项死亡/no-op guard、timeout 改写和 requests 连接池。它把深层已取得进展的游戏放在更显著位置，可以拆出“继续投入已接近完成的游戏是否值得”这一研究问题。但最后一关有高权重不等于存在额外的全通奖励，完成游戏也不会自动抹掉之前的动作效率损失，不能按源码“banks 100%”注释理解计分。

本轮查到几个影响结论的具体问题，见 [源码导出](../../notebooks/2026-10-13/sujan-update/readable.py) 与 [提取的网络扩展](../../notebooks/2026-10-13/sujan-update/_hr_source.py)：

1. cell 14 的反序列化已导入 ToolAgent；cell 16 才改 context=65536、yield tokens=0、auto frame diff。这三项是 import-time 常量，修改环境不会改变已导入值。[CPU 原始赋值语义检查](../../notebooks/2026-10-13/sujan-update/import-order-check.json) 得到 131072/2048/False 保持不变；这是静态调用顺序加精简 CPU 证据，不是远端 GPU 日志。因此不能直接把标题里的 64k 或零 yield 当成实际运行配置。
2. 原请求始终传 `stream=...`，扩展里的 `if args or kwargs` 因这个参数走直连 `session.post` 分支，绕过自定义 `robust_post` 重试循环；底座原重试仍存在，但新增重试的效果不能按说明照单全收。
3. 对原来取“配置 timeout、剩余游戏时间、soft deadline”最小值的函数强加 180 秒下限，可能延长临近 deadline 的请求等待。这里只证明逻辑改变，不据此断言远端已超时。
4. “interior click target”和“Zobrist cycle breaker”仅定义，没有发现安装/调用点；不能把存在代码段当作 agent 已使用这些能力。
5. cell 20 在进入正式 gateway 前**无条件写一行 score=1 的占位 parquet**，并在退出时缺文件再补写。不能移植这个兜底：我们的正式分支必须由 gateway 生成真实文件，失败应保留失败证据，不能用占位产物遮蔽。

没有可信的一因素结果能归因上述组合。建议只借鉴深层进展与计算成本的研究问题，**不把整个 v28 作为正式升级候选**。

## 资源、许可和本轮决定

三组都没有换成更大的新模型：均挂载 Franzen 的两份 dataset、同一 Intel W4A16 主模型 v1 与 MTP drafter v1、Pennyroyal v2.5.3、RTX PRO 6000、断网和原 Docker 镜像。主/draft 资产存储规模及资源限制没有消失。Franzen 上游源码此前已核实 Apache-2.0；Qwen 权重仍适用其单独模型许可。当前三组增量代码的 Kaggle License 页本轮未能成功读取，不能仅从上游许可自动推定所有新增文件的授权，也不把标题当奖金资格证据。

本轮保留 009 v2 为可复现的正式 baseline。对剩余约 7.52h 个人 GPU 预算，先完成能改变候选取舍的 CPU 证据；不因 Code 页排序再跑一轮相同基线。80k tail 是低工程风险的备选一因素；若研究目标是突破无法形成机制/目标的关卡，008 当前帧区域工具和历史观察取用仍更直接。显式数据记忆属于另一个独立因素，先核对重建成本和陈旧数据失败病例，不与 007、008、scheduler 一次合并。

未来 Notebook 继续使用可读原生 cells、固定源码与实际产物 hash；保存运行成功、代码合同通过、模型真实采用、公开关卡收益、正式榜成绩必须分别记录。
