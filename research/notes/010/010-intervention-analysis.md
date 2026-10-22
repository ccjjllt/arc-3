# 010：历史动画采用与机制诊断

日期：2026-10-13。范围：已完成的12个公开开发游戏 A/B；本文件审查信息交付和使用机制，不把离线均分当正式 leaderboard 分数。

**历史动画已真实交付并被使用，不能把这一轮解释为“零采用”。但目前没有足够证据把整体 +3.89 分归因于旧帧查询，也不足以据此直接晋升正式 solver。** 最明确的局部收益发生在 tn36：模型找回被后续动作覆盖的旧动画，提取开关与运动的对应关系。后续关卡确实复用了操作模型；然而 baseline 也通过原有 latest 动画学到了基础规则，而候选后续突破所需的新操作来自后续实验、原 latest 接口及当前 demo，旧帧工具的独立贡献仍未分离。

## 1. 捕获、查询、交付是不同证据

来源：[archive telemetry](../../../runs/010-retrievable-animation/retrievable_animation/retrievable-animation.json)、两臂 `benchmark.json`；机器核算见 [telemetry.json](../../../experiments/010-intervention-analysis/telemetry.json)。

- 12局共 **2,290 次真实动作捕获，全部编码为 available；8,030 张 raw SDK 帧**。这说明保存路径成功，不等于每张帧都被模型读取。
- 共 **48 次 archive 查询：19 次 list、29 次 get**；get 有 **28 hit、1 miss**。28次命中全部是 nonlatest，即早于当时最近一次实际执行动作，包含 RESET 在内。
- 28次命中涉及 **13个不同动作引用**，另15次是重复取同一引用。重复包括逐步细化裁剪、改检测器和比较不同历史动作，不能仅凭重复次数判为无效循环。
- **4/12局调用了历史查询，其余8局零调用**。最大正向变化 m0r0（+70.92）和最大负向变化 ft09（−55.29）都在零调用组；整体分差不能由历史读取次数解释。
- `recent_queries`恰好保留全部48条，与总计一致，没有因128条环形上限而缺失查询样本。
- 累计编码93,519,896 bytes；结束驻留39,613,422 bytes，峰值 **38.12 MiB**，低于全局64 MiB上限。淘汰1,162条frame blob，结束保留1,128条。记录数上限与每会话字节上限都可能触发淘汰。
- 记录的 capture CPU为3.750秒、archive query CPU为0.687秒。这是局部 `thread_time` 计数，**不包含完整 IPC、sandbox转换/segmentation、模型阅读与额外推理的端到端成本**。11,040,475 response JSON bytes是host到sandbox的数据量，不是prompt大小或token量。

| 游戏 | 捕获 | list | get / hit | 命中不同动作数 | 完成关卡 A→B | Δ离线分数 |
|---|---:|---:|---:|---:|---:|---:|
| tn36 | 193 | 1 | 3 / 3 | 1 | 1→4 | +31.86 |
| sp80 | 78 | 12 | 20 / 20 | 8 | 1→1 | 0.00 |
| lf52 | 204 | 5 | 4 / 3 | 3 | 3→1 | −9.09 |
| bp35 | 83 | 1 | 2 / 2 | 1 | 1→2 | +4.44 |

这张表是运行后的采用分组，不是随机化分组或独立重复实验。

## 2. 已核对真实 outbound request 与 tool stdout

对上述4局逐行解析原始 requests，保留call_id去重及context trim边界；未执行模型生成代码。四局第一次真实request的system message都包含完整新API说明，system文本SHA256一致。所有取到的analysis transcript系统段也包含说明。

共定位 **28个包含 `animation_refs` / `animation_at` 的Python调用**，每一个都能对应原始requests中实际出现的assistant代码和tool返回。一个Python调用可执行多个list/get，所以28个Python调用不等于48次archive请求。核对结果与原始行号见 [request-delivery-verification.json](../../../experiments/010-intervention-analysis/request-delivery-verification.json)，说明文本见 [request-system-delivery.json](../../../experiments/010-intervention-analysis/request-system-delivery.json)。这28个调用的stdout未被本次compactor截断；这不保证模型历史从未在之后被裁剪。

调用代码通过 `frames[i].ascii`、`before_frame.ascii`、`FrameView.segmentation` 读取具体帧，并将差分、颜色数、坐标或小块ASCII打印到随后模型请求。因而证据强于“代码里出现了API名字”。命中计数本身则只证明host返回了指定数据。

## 3. tn36：局部恢复成立，后关迁移也成立，独立因果尚未成立

候选在执行14个动作后（analysis 6）明确发现：动作5点击蓝球有256个暂态像素，但最近一次动作没有动画，原 `last_animation_frames` 已不能找回动作5。模型主动列引用并准确查询 `attempt=0, action_num=5`，三次读取同一7帧动画，依次做颜色差分、运动坐标、局部形状检查。

返回显示黄plug沿行13→17→21下移，蓝色T高亮在不同开关间横扫；最后棋盘基本复原。模型进一步用新动作比较全亮开关，明确提出“每个暗开关使plug下降一格”，随后将五个开关设暗并在动作26完成L1。证据：候选 events行22、24、35–38；请求行21、23、25、27对应四个历史API调用。这里有**旧信息恢复→具体规则→新实验→可见通关**的局部链。

后关并非重新盲猜，以下迁移有真实代码与动作证据：

1. **L2**：模型多次显式引用L1的“从左到右逐列执行开关操作”。不过它仍用了120个L2动作并经历一次死亡/RESET。决定性突破是后续新实验验证 **`h0+v2 = UP`**，使用原 `last_animation_frames` 检查结果，再把组合放进四列；动作146完成L2。候选requests行169、171、173及events行210。
2. **L3**：直接复用 **`v0 = RIGHT`、`h0+v2 = UP`** 编出路线。首次把墙洞的像素行16–19误算为格行4，原latest动画表明第二次向右被墙阻挡；模型纠正为格行3，改为`UP, RIGHT×4, UP`，动作162完成L3。请求行181、183、185；events行230。
3. **L4**：复用已有LEFT/DOWN和“每列一条操作”的模型，从当前左侧demo识别 **`h0+v1 = SHRINK`**，构造`SHRINK, LEFT, DOWN×4`；动作182完成L4。请求行195、197、199、201、203；events行258。这里还出现过裁剪包含keyboard、列数从4变3却沿用旧坐标的错误，模型随后重新定位修正。

**baseline对照限制了归因。** A在L1已经通过原latest动画读出了`BB=DOWN、wB=RIGHT`及逐列执行，并在动作9完成L1，比B更早。因此不能说B独有基础开关知识，也不能说A因无法读取动画而停滞。A在L2末期仍围绕“可用操作没有UP、目标是否其实不是socket”反复推断；虽然考虑过整列编码，但没有在预算内把跨行组合验证成成功的上移程序，最后停在L2。基线requests行21–25、135、137、139可复核。

B确实形成并迁移了更完整的操作表，但 **UP、SHRINK的决定性新增证据来自后续新动作/原latest/当前demo，L2–L4没有再次调用历史API**。可合理保留的结论是：旧帧工具修复了B早期一个已发生的信息缺口；其后形成可迁移知识的路径可见。不能由这一条轨迹断言“额外三关由历史API造成”。两臂模型轨迹、共享调度和运行顺序也未构成同随机数的反事实对照。

## 4. 其余三局：读到了，但没有新增完成关卡的直接链

**sp80：20次旧帧命中，仍卡L2。** 首次get发生在L1已由动作15完成之后。读取该成功动作的20帧后，模型观察到两个cup依次转暗红，建立“全部cup命中”的候选目标；随后对比7次SPACE历史，修正过把shot编号、真实action_num和平台旧位置混在一起的表格。该恢复提供了实际约束，不是空调用。但它将L2固定ROI检测器用于L1旧帧时先得到“零命中”，之后才发现L1cup位于屏幕下方而非L2上方并纠正。后续仍没有完成L2。最后一次查询动作68（attempt 1）也仅确认cup状态，无新关卡进展。events行31、59、63–65、128；完整调用材料见 `sp80-api-calls.json`。

**lf52：能观察事件顺序，未转成有效目标规则。** 动作16已过L1；到动作32后才读取动作24、25（27帧、21帧），看到了所有绿色块消失、紫色key出现、点击后棋盘重建。模型据此继续讨论“奖励/重试/解锁”的含义，但L2没有完成。之后读取动作136，又把全部块消失的顺序打印出来，仍未打破目标解释循环。最后请求动作15得到`outside_retained_history`，没有发生latest回退。**动作15本身也不是L1的完成动作；实际完成动作是16**，显示transition零起点与action_num身份绑定仍易混淆。events行25–26、55、203、220。

**bp35：+1关发生在历史读取之前。** 候选动作66已完成L2；历史API首次在动作83后才调用，读取的是`attempt=1, action_num=73`的死亡动画，此时已经RESET进入attempt 2。该跨attempt精确读取成功，模型确实打印死亡前后局部像素，讨论碰撞/浮升/障碍物；但之后没有新动作或关卡完成。因此这局+1关不能直接归为查询后收益。events行109、122–124、144、146。

## 5. 实际暴露的接口与推理边界

- **记录层级易误用**：sp80、lf52各一次把`record['ref']['action_num']`误写为`record['action_num']`，产生KeyError；随后都修正。不是archive给错引用，但API说明仍未完全消除使用摩擦。
- **状态守卫未被稳定遵循**：lf52打印`outside_retained_history`后仍无条件读`before_frame`，再产生KeyError。工具明确拒绝，没有静默错误数据；调用方仍需按status分支。
- **检索正确不等于表示正确**：sp80跨关复用ROI、tn36墙洞格行换算和左侧demo裁剪，都在数据可得时发生。添加更多帧不会自动解决坐标绑定、目标识别或操作组合归纳。
- **没有发生交付失败或零采用**：本轮不能用于否定“旧动画丢失可构成信息瓶颈”的假说；tn36已有直接恢复实例。也不能反向把“信息恢复成功”当“提高泛化分数已经证明”。

后续若继续此方向，应先用现有CPU材料压低引用层级/status/ROI误用，再以有限复验确认tn36式收益能否重复、其他采用局是否真正增加完成关卡。当前单轮12局的26.05→29.94、34→37关仍是描述性结果；保留009正式baseline，不把010直接等同新正式成绩。

## 可复核材料

- 原始：`runs/010-retrievable-animation/{baseline,retrievable_animation}/`。
- 统计及来源hash：`experiments/010-intervention-analysis/telemetry.json`、`source-manifest.json`。
- 4局查询turn、按call_id对齐的代码/ stdout/前后推理：同目录`*-query-turns.json`、`*-api-calls.json`、`request-delivery-verification.json`。
- tn36两臂请求及后关迁移：同目录`compacts/{baseline,retrievable_animation}__tn36-ef4dde99_p0_requests.compact.json`、`tn36-crosslevel-evidence.json`。
- 本次只读分析，没有追加模型/GPU运行、正式提交或修改solver。archive telemetry未持久化全部8,030张原始像素，未查询帧的内容正确性不能仅由计数再次逐张验证。
