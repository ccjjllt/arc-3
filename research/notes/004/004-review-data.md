# 004 — 原始轨迹、压缩工具与归因复核

日期：2026-10-11（Asia/Shanghai）。范围：003 的 sk48、lf52、su15、tn36，两组共 8 份原始 `*_requests.jsonl`，以及 004 归因文档。只做 CPU 阅读与手动核对，未读游戏引擎解法，未新增测试文件，未启动 GPU。

## 审查结论

旧 compact 的历史去重存在真实漏数：**30 次上下文长度下降，漏掉 25 个可在 raw 中直接定位的工具调用**，还漏掉纯 assistant 推理和部分 user cue。更严重的是，旧工具把没有新消息的 response 整条跳过，丢失其 usage 与 finish_reason。

已经修复 [compact_requests.py](../../../scripts/tools/compact_requests.py)，新结果写入 [runs/004-reviewed-compact](../../../runs/004-reviewed-compact/)，保留 `runs/003-compact/` 和全部原始轨迹。对 8 份 raw 按 tool_call ID 独立重计后，新 compact 完整覆盖 **682 个可见调用**；旧 compact 是 657 个。新结果保留原始 **1,405 条事件（705 request、700 response）**；旧 compact 只有 675 条非空增量记录。事件数增加主要因为现在保留 response 元数据，不能解释成新增模型调用。

修正后，“sk48 没有可见的 `last_animation_*` 代码引用，其他游戏存在多次引用”的大方向仍成立。**但“候选摘要不会改变过关结果”不是可由这些观察轨迹推出的结论**。当前可支持“不足以将该候选优先投入 GPU”，不能支持“该候选已被证明无效”，也不能从 003 单次差异排除提示的因果效应。

## 1. 实际问题与最小修复

### 按历史长度切片会丢掉裁剪后的新消息

旧逻辑是 `new = messages[seen:]`，再令 `seen = len(messages)`。在 raw 中，历史会从 100 条裁到 40 条左右，同时在尾部加入刚产生的 assistant/tool/user 消息。长度下降时，这个切片为空；下一条 response 仍然是相同快照，因此这些新消息不会再次被旧工具提取。

新逻辑使用相邻快照的消息内容序列对齐，保留 insert/replace；记录 delete/replace 的前后区间和 `context_length_decreased`。assistant/tool 的稳定 tool_call ID 防止重放内容被重新计为一个调用。user 对齐使用纯文本，图像从旧上下文移除时不把同一句 cue 重计。

每条可见增量消息新增一基 `source_line`、零基 `source_message_index`、原始消息 SHA256 和稳定消息标识。`analysis_step/action` 是**首次看见它的快照标签**，不一定是模型生成该回复时的标签；同一 `(analysis_step, action, request_index_within_turn)` 也可能重复，不能拿这个三元组代替原始行号。

### 不能把相同 messages 的 response 丢掉

这些日志的 response 往往仍保存请求输入 messages；生成回复通常在下一次 request 快照中才变得可见。旧脚本因没有新增 messages 就跳过，导致绝大多数 response usage/finish_reason 无法核查。

新工具保留每条输入事件，即便 `messages=[]`（没有新增可见消息），并单独累计 response usage。该计数只代表已记录的响应 usage，不保证包含取消请求的部分生成；例如 sk48 A 的 response completion 总和为 167,128，仍不等于 analyzer note 的 171,039。不能把 response usage 新合计再次误称成完整算力账单。

### 多模态 user 消息不能先序列化成一行再提取“动画行”

旧 `_user_excerpt` 把 text/image 列表整体 JSON 序列化，再用 `splitlines()`。序列化后的换行是转义字符，一旦匹配 animation，就保留整条消息，连同 base64 图像。8 份旧 compact 的 289 条动画 user 消息均携带这类图像数据。

新工具只提取 text part，按真实文本行保留相关提示，并记录非文本 part 被省略的数量。新增 `transient_cue_lines` 专门匹配 `animated over N frames`，区别于一般 animation 名字提及；前缀仍是有意节选，不能根据节选内容缺失推断原 prompt 没有其他信息。

### 代码引用、代码执行与采用须分开

旧 `reads_animation_api` 同时匹配 `frame_diff`。`frame_diff` 是结算帧比较，不能计为动画帧入口使用。

新结果分别保存：

- `code_content_reference_statistics`：按可见的唯一工具调用计，代码文本包含某 API 名字。包含注释/字符串/有语法错误的代码，所以只能叫“内容引用”。
- `direct_api_reference_statistics`：AST 中对应 Name 的 Load；`frame_diff` 单独列出。一次调用里出现同名对象多次，`name_loads` 可以大于 `tool_calls`。
- `code_parse_error`、工具返回的 error/returncode/其他 payload 元数据：用于人工结合 stdout 核查。AST Load 仍不保证代码走到该分支、函数被调用或返回成功，更不等于模型据此正确更新假设。

保留字段 `reads_animation_api` 以便旧读法迁移，但其含义已明确限定为直接语法引用，不宣称执行成功。没有执行任何轨迹里的 Python 代码。

## 2. 修正后的计数

raw 调用数按 `tool_calls[].id` 去重，不按消息内容或请求历史总次数计。user cue 以序列对齐后的新文本消息计；这 8 份数据又用 raw 中不同 cue 文本集合独立核对，数量完全一致，没有重复或遗漏。该文本唯一性是本批数据的核查结果，不是未来所有轨迹的通用去重键。

| 臂 / 游戏 | raw request / response | 长度下降次数 | 工具调用旧 → 新 | transient cue 旧 → 新 |
|---|---:|---:|---:|---:|
| baseline / sk48 | 67 / 66 | 2 | 59 → 59 | 18 → 18 |
| baseline / lf52 | 109 / 109 | 4 | 104 → 108 | 38 → 40 |
| baseline / su15 | 116 / 115 | 5 | 110 → 115 | 62 → 65 |
| baseline / tn36 | 101 / 101 | 5 | 95 → 100 | 42 → 44 |
| goal_evidence / sk48 | 30 / 29 | 2 | 24 → 24 | 13 → 13 |
| goal_evidence / lf52 | 137 / 137 | 6 | 130 → 136 | 48 → 50 |
| goal_evidence / su15 | 88 / 87 | 4 | 83 → 86 | 51 → 53 |
| goal_evidence / tn36 | 57 / 56 | 2 | 52 → 54 | 17 → 19 |

sk48 的两次裁剪均没有漏工具调用，但丢失了 assistant 推理；不能因为 API 引用数字未变就认为其旧 compact 全部完备。

以下为**代码内容引用的唯一工具调用数**，不是成功读帧次数。`timeline + frames` 不能直接相加：同一调用可以同时引用两者。

| 游戏 | baseline timeline / frames / 任一 | goal_evidence timeline / frames / 任一 | AST 直接引用任一 A / B |
|---|---:|---:|---:|
| sk48 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 |
| lf52 | 5 / 0 / 5 | 4 / 2 / 4 | 5 / 4 |
| su15 | 4 / 3 / 6 | 19 / 2 / 21 | 6 / 21 |
| tn36 | 4 / 45 / 49 | 9 / 30 / 34 | 48 / 34 |

tn36 A 原内容引用统计为 4/43/47，B 为 9/28/32，分别恢复 2 个 frames 调用。A 的 49 个内容引用里有一个语法错误，整个工具返回明确报错，故不能称为 49 次真实读帧。su15 B 的 timeline 是 19 个调用、21 个名称出现；将出现次数与调用数混用也会多计。

全部逐文件核对、遗漏调用清单、原始定位和来源哈希见 [review-audit.json](../../../runs/004-reviewed-compact/review-audit.json)。

## 3. 可以直接回到 raw 核查的例子

### A. 裁剪吞掉了已执行并返回逐帧结果的调用

原始：[baseline tn36 JSONL 第 101 行](../../../runs/003-goal-evidence-ab/baseline/tn36-ef4dde99_p0_requests.jsonl#L101)，快照 `analysis_step=32, action=106`。前一个快照 78 条消息，这条只有 28 条。

- `messages[25]` 的调用 ID 是 `call_60229b213f9e4b64b21ea00d`，代码含 `runP(); fr=last_animation_frames`，然后逐帧打印 socket 坐标。
- `messages[26]` 是对应 stdout，显示 RUN 为 NO-OP，但帧 0 插座位于 rows 20–23、cols 37–40，帧 2 位于 cols 41–44，帧 3 位于 rows 16–19，帧 4 位于 rows 12–15。
- 这段可验证“确有执行到帧访问并返回了不同帧”，不只是提及 API。旧 compact 完全没有此调用，新 compact 已恢复。它不自动证明模型正确理解了坐标，更不证明新增摘要无效。

同类遗漏：[goal_evidence tn36 第 69 行](../../../runs/003-goal-evidence-ab/goal_evidence/tn36-ef4dde99_p0_requests.jsonl#L69)，`analysis_step=16, action=50`，前快照 85 条，裁后 27 条。`messages[24]` 是 `call_c4dc24ce1dba44ada0cd8ac8`，`messages[25]` stdout 显示帧 0 的黄块 rows 24–27，帧 3–4 rows 28–31，帧 5 回到 24–27。这也给后续“翻滚假设”归因增加了一段应阅读的具体证据。

### B. 字符串匹配会把语法错误计为“读帧”

原始：[baseline tn36 第 123 行](../../../runs/003-goal-evidence-ab/baseline/tn36-ef4dde99_p0_requests.jsonl#L123)，`analysis_step=38, action=135`。

- `messages[55]`，调用 `call_e715579a915a4411b02dfe50`，代码包含 `last_animation_frames`，但第 3 行的 `big=max(([c for c in Y],key=len),key=len) if False else None` 语法不合法。
- `messages[56]` 返回 `Python syntax error: invalid syntax ... (<python_tool>, line 3)`。
- 这是“代码内容引用”而非“成功读帧”。即便 `if False` 使作者想跳过该表达式，Python 仍需先解析整段代码。

### C. context trim 后新消息仍然属于当前轨迹

原始：[baseline lf52 第 79 行](../../../runs/003-goal-evidence-ab/baseline/lf52-271a04aa_p0_requests.jsonl#L79)，`analysis_step=25, action=73, request_index_within_turn=2`，历史从 106 条减到 43 条。

新出现的 `messages[41]` 是 `call_a0febb547f1844c284301e60`，读取当前 segmentation，stdout 在 `[42]`。旧长度切片漏掉这两个；第 80 行 response 同样是 43 条消息并带 completion_tokens=3,194。新工具同时保留新增消息与 response usage。第 81 行同一 analysis_step/action 的 request_index 又回到 1，因此原始行号比这几个标签更可靠。

### D. user cue 不是新增调用或新增效果

修复后 lf52 A 的 cue 从 38 变成 40，su15 A 从 62 变成 65；这只是把早已提供给模型、被旧工具漏掉的文本找回来。不能解释成模型采用率提升；阶段 3 仍须逐例检查推理与之后动作。

## 4. 需要降调的因果和反事实措辞

本节记录审查时的原措辞，主归因文档由主任务统一修订。

| 审查位置 / 原表述 | 证据问题 | 可支持的改写 |
|---|---|---|
| 综合归因“候选假设为何不成立”；“一格都不会因为多一段 old>new 而改过关集合” | 候选从未实现或随机对照，不能观察其反事实结果。更早、更紧凑的观察呈现可能改变计算路径。 | 当前实例尚未提供足够强的优先实验依据；未证明无效。 |
| progress 表“004 候选会改过关？否”及各游戏“不会改变任一 episode” | 从已发生轨迹无法排除节约一次追问、改变注意力或预算分配的下游影响。 | 本例已有相近证据被暴露/查询；额外收益未验证。 |
| 综合归因“su15 大分差不是干预效应” | nudge 未触发并不等于附加指导文本没有因果影响。单次非独立 A/B 同时不能确认或排除影响。 | 分差无法归因；核心 nudge 未被检验，仍存在指导文本、随机路径与共享调度混杂。 |
| “user 已给 bbox/帧数，因此局部时序事实只是重复” | bbox/帧数不等同于每帧 old→new/物体位移；接收通道与出现时点也不同。 | 只重复 bbox/帧数的新因子较弱；更细时序摘要是否有增量需要独立评估。 |
| “阶段 2=0，所以阶段 3=0” | 若阶段 3 限定为“由显式 API 读取动画帧更新”可以作为观察口径；但 user cue 本身已经含动画信息，不能泛化成模型未利用动画。 | 没有可见的 API 名称引用；仍有从 user cue 采用信息的例子。 |

可保留的研究决定：先完成 25 游戏 baseline 能力图，暂不花 GPU 实现一个还没有明确可测收益路径的观察摘要。它是基于配额和证据强度的优先级选择，**不是该候选效果已被否定**。

## 5. 手动验证范围与限制

人工运行新工具处理 8 份 raw，逐文件按 raw tool_call ID 独立校对，覆盖集合全部一致；raw 不同 cue 文本集合与新输出均匹配。保留每条 response usage，检查新增帧引用、语法错误及裁剪边界的原始 stdout。原 raw 和旧 compact 的 SHA256 保存在审计产物中，未修改原始文件。

这些 request/response 条目的 `messages` 是输入快照。最后一次生成内容若未进入下一条快照，不能仅靠该文件保证完整看见；调用计数明确是“raw 快照可见的唯一调用”。stdout 可以证明某次工具曾返回帧数据，不能证明模型随后正确理解。compact 仍省略图片和部分大输出，所有机制结论都应能回到 raw、真实动作事件与完成状态核查。

命令：`python3 scripts/tools/compact_requests.py <8 个 raw requests.jsonl 路径> --output-dir runs/004-reviewed-compact`。为防误覆盖，工具默认拒绝已有输出；本次追加统计字段后只显式重写新的 reviewed 输出目录，未碰旧 compact。
