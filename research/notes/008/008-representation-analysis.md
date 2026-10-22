# 008 — 当前帧区域表示：CPU 原型与证据边界

日期：2026-10-12（Asia/Shanghai）。对应 [008 计划](../../../docs/plan/008-observation-representation.md)。本轮只读取 005/007 已保存帧、通用底座和轨迹文本；没有模型请求、GPU、SDK 动作、游戏引擎源码或模型日志代码执行。原型未接入 agent、run_arm 或正式提交。

## 结论

现有接口确有一个可以独立实现的缺口：模型只能自行从 ASCII 切片并编码，或使用单个四连通组件的形状摘要。新增的 [observation_representation.py](../../../src/arc3_research/observation_representation.py) 提供当前帧读取、明确坐标和前景集合、完整区域 mask、组件并集、可选且分开的姿态变换键，以及空区域/未知符号/局部跨界诊断。

CPU 核对证明原型按指定区域忠实读取；它不能确定模型会选择正确区域、采用接口、修正推理或增加关卡。**目前继续保留为独立原型，不据此安排 GPU 或合入默认策略。** 黄色长面板的多符号拆分仍未解决；约千字符的单区域输出也需要在后续接口设计中考虑。

## 现有能力与真正增量

| 底座能力 | 已有功能 | 008 的独立增量与限制 |
|---|---|---|
| `FrameView` | `.ascii/.step/.level/.shape/.segmentation`；动作后替换当前帧对象 | 通过 getter 每次解析当前对象，返回 step/level/shape/ASCII hash；保存旧对象的错误 getter 仍无法由模块自动发现 |
| segmentation | 四邻接同色组件、外边界、children、像素数 | 允许读取包含多个组件的明确矩形，保留完整 raw rows 和 mask；组件或面板均不自动等于一个字符 |
| shape keys | 带颜色的旋转规范化 hash、保姿态 pose_hash、去颜色保姿态 shape_hash | 对所选前景并集保留完整矩形 exact key；旋转与镜像变换仅显式请求，没有默认类别合并 |
| 局部 ASCII | 模型可以手工切片、判断 `B` 等字符 | 坐标顺序、含端点、前景字符合同固定；未知符号不能静默变成全零 |
| 区域完整性 | 没有独立的局部裁剪诊断 | 区分前景触边和前景跨边继续；不以未检测到跨边作为完整性保证 |

源码依据：[FrameView](../../runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py:160)、[动作后刷新](../../runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py:384)、[组件与签名](../../runtime-bundle/src/ARC3-Inference/inference/utils/segmentation.py:82)。未修改这些底座文件。

## 原型接口

下面是未来接入方式的示意；当前 sandbox 尚未导入该类：

```python
reader = RegionReader(lambda: current_frame)
ref = reader.reference()
region = reader.read(
    (top, left, bottom, right),
    foreground="B",
    expect_frame=ref,
)
panel = reader.from_node(
    node_id,
    foreground="B",
    expect_frame=ref,
    inset=1,
)
```

- 坐标为 **零起点、`(top,left,bottom,right)`、两端包含**。越界、反向、非整数或默认超过 1024 格的区域返回 unavailable，不静默裁切。1024 是输出范围限制，不是认知最优值。
- 前景必须明确指定合法单字符。`foreground="BY"` 表示 B/Y 的二值并集；颜色本身保留在 raw rows 和 color_counts。mask key 不编码颜色身份，比较者必须知道自己正在比较哪个前景并集。
- 默认只给 `exact_key`，保留矩形大小、姿态、空白边及前景在矩形中的位置。不隐式去平移或 trim，也不把 key 当作对象身份。
- `include_transforms=True` 才返回 rotation_canonical、mirrored_exact（左右镜像）、mirrored_rotation_canonical、dihedral_canonical。后者仅是一组显式像素变换后的比较键，不证明游戏允许忽略镜像或方向。
- 空 mask 有明确诊断且 key 为 null；未知前景（如误用字面字符 `1`）及区域未知字符不给 mask/key。裁剪有跨边诊断时仍可返回该裁剪的像素 key，不表示完整字符。
- `from_node` 必须提交完整当帧 reference，因为 segmentation ID 仅在当前帧有意义。它由当前节点外边界求 bbox，`inset` 由调用者显式选择；输出原 bbox、节点颜色和是否有同色矩形周界，绝不默认去边框或拆符号。
- 模块不保存跨调用帧缓存。getter 应在调用时读取 runtime 的 live global，不能闭包捕获旧 `FrameView`。reference 在单个游戏会话内使用，不是跨会话唯一标识。

## 已执行的 CPU 核对

可复算命令：

```bash
python3 scripts/analysis/analyze_008_representation.py
```

结果：[analysis.json](../../../experiments/008-representation/analysis.json)。其中保存输入路径、物理行号、完整文件 SHA256、每份 frame reference、区域原文、mask、变换键与输出长度。69 份区域输出均重新按 bbox 从保存 ASCII 切片核对，再独立逐字符核对 mask 和像素数；保存的 numeric board 与 ASCII 也逐格一致。69 包含同帧不同区域和重复的对照提取，不能当作 69 个独立样本。分析前后输入 hash 均保持一致。

| 病例 | CPU 观察 | 支持范围 |
|---|---|---|
| 007 tr87 L2 的错误/正确裁剪 | 底部 4 个 pink 与图例匹配从 1/4 变 4/4；12 个 yellow 在显式 D4 下从 9 类恢复 7 类 | 重现保存帧上的坐标后果；不证明自动定位或 D4 是通用游戏规则 |
| 当前 segmentation 节点读取 | 六个 P 图例面板由当前 boundary 求 bbox，显式 inset=1 后得到正确内框起点 5/14/23 | 降低手抄节点坐标风险；不是全局字符分割器 |
| 旧/新保存快照 | getter 所指快照从 action_num 24 换到 25，区域 mask 变化；旧 reference 及旧 node 请求返回 unavailable | 证明无内部帧缓存；尚未验证真实 sandbox 的在线接入 |
| 姿态/镜像 | 从实际 A0 区域构造 90°旋转、左右镜像：exact 不同，旋转类一致，镜像的旋转类不同，显式 D4 才一致 | 派生像素变换的编码合同，不是新环境观测 |
| 005 tr87 L6 编码失配 | 24 个历史区域全部为非空 B mask，有 22 个 exact 形态；误用 `foreground="1"` 返回 unknown_foreground_symbol | 不会把字母编码当二进制后静默坍塌；未重放或替代当时模型推理 |
| 005 re86 L7 几何 | rows30–47 的 S 前景均在 col36；bbox 中心是 col27 | 完整 mask 可核查“中心等于竖杆”的错误假设，未得出真实绕障策略 |
| 空 mask/未知字符/越界/反向/超大区域 | 输出相应显式诊断；无静默裁剪或虚假全零类别 | API 输入及返回行为 |

007 初始帧来自 [B events L34](../../../runs/007-program-state/program_state/artifacts/tr87-cd924810_p0_events.jsonl:34) 与 [A events L71](../../../runs/007-program-state/baseline/artifacts/tr87-cd924810_p0_events.jsonl:71)，ASCII SHA256 同为 `7a67d1c1609cff8d5ee692b1c63c8fcdc7192a22f5129405793828804834c64a`。新保存快照来自 B events L39，hash 为 `9ec88c94034e0d9f31fdc339c5c4d740f0d7883b7dd88688b189e8a63621d51c`。离线适配器将 event.action_num 映射为原型 step；这是保存快照检查，不冒称已验证生产 `FrameView` 注入。

005 的编码帧是 [tr87 events L331/action291](../../../runs/005-full-baseline/baseline/artifacts/tr87-cd924810_p0_events.jsonl:331)，对应 [raw135](../../../runs/005-full-baseline/baseline/tr87-cd924810_p0_requests.jsonl:135) 中恢复后的 g5c/sig 文字；几何帧是 [re86 events L707/action603](../../../runs/005-full-baseline/baseline/artifacts/re86-8af5384d_p0_events.jsonl:707)。显示 prompt 的 step 比实际 action_num 大一，不混用两种编号。历史坐标仅作为分析样本标注出现在脚本中，通用模块没有游戏 ID、固定 5×5、图例位置或答案表。

## 实际负例与未解决的问题

**截断检测并不完整。** 007 上移一行的 12 个区域（4 pink、8 yellow）中，10 个存在前景四邻接跨越下边界，被标出；C0 和 F0 的裁剪也分别从 9→7、10→8 像素，却没有任何被裁前景与外部前景相连，未触发跨边诊断。它们是完全遗漏断开部分的实际反例。正确内框同样大量触边，不能把 touches_edge 当作错误。

**节点不是字符。** 六个 P 面板可以由边界确定矩形内框，但一个 Y 长面板可包含 2–3 个符号，每个符号又有 3–5 个断开黑组件。当前成功复算的 12 个 yellow 区域仍使用研究者从当时可见画面/日志标注的槽位置，原型没有声称可以自动得到它们。简单用 children、四连通组件或非空列分组都会留下错误机会。

**输出成本未确定。** 本批单份区域完整 JSON 为 926–1803 字符，69 份合计 69,678 字符，很多样例显式包含变换键。这不是在线累计上下文成本，也不是 tokens 或 prefill 测量；按需读取是否过重、是否需要只返回被请求字段仍需设计，不能机械把全部区域塞进每个 prompt。

**模型采用链未检验。** 008 没有真实模型调用，不能证明模型会选对前景/面板、请求该工具、留意截断、放弃错误规则或更快过关。由节点读 bbox 对最初的手抄坐标问题有直接帮助，但无法纠正模型拿错节点、假定符号边界或错误使用 dihedral key。

## 后续决定

先保留此模块、复算脚本及派生证据。后续若设计 GPU 候选，须明确是在 sandbox 中新增一个只读区域入口，以及模型如何在当前 observation 上定位需要的区域；不要同时加入 007、调度或额外泛化提醒。优先解决有依据的面板到子区域接口与输出长度问题，保留现有 segmentation 为主视图。

下一阶段至少要分别记录：候选是否被调用、是否绑定当前帧、返回 mask 是否被后续代码使用、具体错误是否被纠正、跨游戏覆盖与资源是否变化。当前代码完成和 CPU 表示保真已完成；模型采用与得分效果均未测。
