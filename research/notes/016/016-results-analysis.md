# 016 pace 全池对照：小幅正差但未过晋升门

日期：2026-10-18，Asia/Shanghai。**jiyujia/arc3-016-pace-allocation 修复重跑已 COMPLETE；均分 +0.3293、总关 +6，但剔除最大正向游戏后其余 24 局 −1.5205。按预设门，不晋升、不启动同版倒序确认、不据此提交。正式 009/31.16 不变。**

本文以已回收的 `runs/016-pace-allocation-jiyujia/` 为准，区别于首个 ccjjllt 失败会话；README、016 旧进展和 10/17 综合决策中的 RUNNING 是旧快照。以下均为公开开发池描述性结果，不是隐藏榜成绩或显著性结论。

## 1. 两次运行不可混淆

- 首次 ccjjllt 会话：baseline 25 局均有结果、exit 0，状态 8 won / 8 gave_up / 9 cancelled；旧完成池检查只接受 won/cancelled，错误拒绝 gave_up，未运行 pace 后臂。baseline 均分 50.4234、108 关；整轮 manifest 为 failed，GPU 已停。该单臂不参与新 A/B。
- 修复提交 `1d717a6` 将 gave_up 纳入有效终态，仍拒绝 crashed/not_started。jiyujia 新 Notebook SHA256 `42b0ce4934185a3608183d04f07b998955daec49243eb0a038decdd2912a98ab`；session_runner SHA256 `e2bf61508b17d57a8eb4dc5e557908854fe6091d511d6440674120ef2e1da3bb`。
- 新会话 baseline 北京时间 10/18 01:40:39.636→03:42:14.255；pace 03:42:15.823→05:43:35.195。summary 于 05:43:41 生成。内部会话 15139.409 秒，即 **4.205391 小时**；这是加载、运行、清理的会话口径，不等于平台额度账单。

来源：[旧失败 manifest](../../../runs/016-pace-allocation/experiment-manifest.json)、[新 manifest](../../../runs/016-pace-allocation-jiyujia/experiment-manifest.json)、[冻结构建](../../../notebooks/016-pace-allocation-jiyujia/build-manifest.json)。

## 2. 独立复算与五项门槛

同 25 个 exact game ID、同顺序、各 7254 秒、10 活跃流、1 pass、warmup0；先 baseline 后 pace。TAIL 均为 remaining；唯一环境差异是 `ARC3_PRIORITY_PACE: 0→1`。50 局根据逐关动作数、参考动作数、115% 单关效率上限、递增关卡权重和完成覆盖上限重新计算，与原 `final_score` 全部一致（最大浮点误差约 7.1e−15）。

| 指标 | baseline | pace_1x | 候选−基线 |
|---|---:|---:|---:|
| 同池平均分 | 47.134038 | 47.463381 | +0.329342 |
| 加权完成覆盖上限 | 50.131602 | 50.345166 | +0.213564 |
| 已完成关卡 | 105/183 | 111/183 | +6 |
| 全通游戏 | 8 | 7 | −1 |
| 动作数 | 5291 | 5744 | +453 |
| Analyzer 自报生成 tokens | 4458146 | 4513940 | +55794（+1.25%） |
| Action-attached recorded tokens | 4392208 | 4392270 | +62 |

Analyzer/recorded 是不同记账口径；不能把 +62 解释成模型总用量完全相等。两臂尾部尚未附着动作的 token 残差分别为 65938 和 121670。

| 预设门槛 | 结果 |
|---|---|
| 平均分为正 | 通过：+0.329342 |
| 加权完成覆盖为正 | 通过：+0.213564 |
| 总关不下降 | 通过：+6 |
| 至少两游戏新增关 | 通过：7 游戏增关；另 8 游戏减关 |
| 非单游戏支撑 | **未过**：去除 r11l 后，其余 24 游戏均差 −1.520521 |

最大正向 r11l 的局内 +44.726070 贡献全池均分 +1.789043，大于总增益 +0.329342。剔除检验沿用 [014 的敏感性口径](../014/014-results-analysis.md)，是落实“非单游戏支撑”的描述性检查，不是新运行、显著性检验或挑选后的评测分。

[016 预设门](../../../docs/plan/016-pace-allocation.md)规定任一失败即不倒序、不晋升。7 个游戏增关说明改变了分配与轨迹，但不足以证明稳定净收益。

复现：`python3 scripts/analysis/analyze_016_results.py`。输出：[完整比较](../../../experiments/016-analysis/comparison.json)、[原运行 summary](../../../runs/016-pace-allocation-jiyujia/summary/summary.md)。脚本只读取 JSON、解析 AST/字面量，未调用模型、引擎、GPU，也未执行日志内 Python。

## 3. 工程有效性及截止边界

全部检查通过：运行配置与冻结构建相等；完整 source hash map 相等，冻结 Notebook 全文件 SHA 及其内嵌 18 份 harness/source payload 逐项一致；首次分析时当前主源码也匹配，后续研究修改主源码不影响该冻结证据；两臂 runtime source map 一致；两个独立 CPU PID；两次缓存清理均有 backend 成功确认；25 局完整、exit 0、worker 全排空、GPU 进程组已停止。

| 时序/调度 | baseline | pace_1x |
|---|---:|---:|
| 记录会话数 | 25 | 25 |
| 客户端 chat/HTTP 请求开始数 | 2308 | 2285 |
| handover 次数 | 89 | 91 |
| 调度 selection 次数 | 114 | 116 |
| 调度事件数 | 491 | 499 |
| 观察器丢事件 / 记录异常 | 0 / 0 | 0 / 0 |
| 最大并发 slot / HTTP | 10 / 10 | 10 / 10 |
| 截止后新 chat/HTTP 开始 | 0 | 0 |
| 截止后动作记录 / 新过关 | 0 / 0 | 0 / 0 |
| 截止后排队唤醒，被 after_handover 闸门阻止 | 7 | 8 |

所有选择均符合当时实际 priority/FIFO；enqueue/selection 身份匹配、token 配对、时间单调性均无异常。deadline 有界队列丢弃了旧的 check_passed 事件（6732/6665），不能把它当完整历史；完整无晚新请求结论来自无丢失的 inference-timing 账本。7/8 次截止后唤醒不等于新模型请求；对应 after_handover 阻止事件保留完整。两臂各 7 个 HTTP/chat exception 属于记录到的截止收尾，不能据此称随机崩溃。

仍有边界：客户端开始时间不能证明服务端接收/生成停止在截止之前；ActionRecord 是动作记录完成时戳，不是独立动作开始探针。这里只确认当前已记录边界。详见 [timing.json](../../../experiments/016-analysis/timing.json)。

## 4. 分配变动与轨迹分歧

以下为实际持有 slot 秒数和已成功返回模型请求的 tokens，不含初始排队等待。二者与得分共同受轨迹影响，不能把分配差机械解释成得分原因。

| 游戏 | 分数差 | 关卡 A→B | slot 秒 A→B | Analyzer tokens A→B | 首个不同动作（1 起） |
|---|---:|---:|---:|---:|---:|
| r11l | +44.7261 | 4→6 | 4027.40→3943.40 | 253717→270150 | 1 |
| sc25 | +28.5815 | 0→4 | 1486.76→3252.71 | 91248→187502 | 1 |
| su15 | +30.7713 | 1→5 | 1698.23→3614.14 | 110832→234250 | 1 |
| m0r0 | −52.3810 | 6→4 | 3199.16→2785.20 | 192646→170238 | 2 |
| tr87 | −52.3810 | 6→4 | 1733.84→1971.18 | 100566→110362 | 2 |

五局都在各自第一次 handover 之前已经出现不同动作；其余游戏中，合计 23 局两臂都有 handover，均在各自首个 handover 前分岔；ft09/sb26 的 baseline 没有 handover，在首次持有 slot 内已全通，两臂动作也已不同。第一次 handover 时已过关数分别为：r11l 1→1、sc25 0→0、su15 1→3、m0r0 1→2、tr87 4→4。

不能由此断言所有差异均与 pace 无关：r11l 首次 HTTP 等待由 905.70 秒变为 0.068 秒，两个会话最初 10 个取得 slot 的游戏集合本身不同；模型采样、线程启动顺序及排队暴露也会改变早期轨迹。可确认的是“尾段给多少 token”不能单独解释终局变化。尤其 tr87 在更多 slot/tokens 下仍少过两关，原始日志可定位到字形裁剪错位及假设检验失真，详见 [017 本地机制证据](../017/017-local-evidence.md)。

首个 ccjjllt baseline 50.4234 与新 baseline 47.1340 相差 3.2893，远大于本轮 +0.3293；它们不是独立重复实验的方差估计，但提醒不能把单轮小正差解释成稳定收益。

来源：[第一次 handover 与前缀](../../../experiments/016-analysis/first-handover.json)、[baseline 请求](../../../runs/016-pace-allocation-jiyujia/baseline/)、[pace 请求](../../../runs/016-pace-allocation-jiyujia/pace_1x/)。原始请求只选取了上表 5 游戏×2 臂，不能把 10 份请求中的机制频率外推至全 25 游戏。

## 5. 当前研究决定

1. 016 pace 不晋升，不花下一轮预算做同版倒序；仍保留为描述性分配实验。
2. 015 不能因小池 +11.46 晋升。新审计找到 re86 一次确切原生值复用，但仍无两游戏采用链，也不能解释 ft09/ar25 的涨分。
3. 下一候选优先考虑“把观察转换为程序时的保真检查”，先验证已有 ASCII、小裁剪、mask 与节点像素数是否一致；不把 bounding box 当填充形状，不把提取器错误当规则被反证。该方向有 ft09 与 tr87 跨游戏直接错误链，但必须先过 CPU/自然采用门，仍无提分承诺。
4. 自然 mismatch→修程序已有正反病例，适合做有界检查的备选。当前数据不支持再添全局报告/反思提示，或直接引入新的记忆 API。

公开 25 已被多轮开发使用；所有候选继续分开验证，不能把多个未经验证机制叠加成正式版本。对金牌/奖金的最终判断必须依据正式隐藏评测和有效资格，不把本报告的同池分数当未来 LB 预测。
