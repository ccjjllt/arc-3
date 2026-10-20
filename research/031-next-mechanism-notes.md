# 031 下一项独立机制研究建议

2026-10-20。适用前提：030关内持久Python没有净收益。**优先尝试在现有 `current_frame.segmentation` 节点中直接交付精确像素足迹，阻止求解器继续把轮廓外接矩形当作物体本身。** 后续准备已完成可逆模块和一次原帧研究计算；没有新建门控或测试套件，没有启动GPU或模型请求。

## 为何选择这一项

028已经给出了比泛泛“模型会抄错”更具体的负证据：模型确实生成、执行并使用了修订程序，却仍把ft09图案的一格背景填成白色。错误发生在**从节点轮廓重建实际像素集合**这一步。030即使让变量长期存活，也只会保留同一个错误集合；继续保留或反思并不能补回缺失的数据合同。

| 原始证据 | 已确认的断点 | 对下一机制的含义 |
|---|---|---|
| [028逐格审计](../experiments/028-analysis/ft09-repair-pixel-audit.json) | 修复程序把图案 `(5,2)` 的中间行提成 `WOW`，原帧为 `WOg`；唯一错格为row46、col32 | 不能再依赖模型从boundary包围盒填色；精确足迹应来自实际像素 |
| [028真实结果](028-program-repair-results.md)及对应B transcript | `analyze()`／`satisfaction()`被执行、保留并被后续模型使用，但核心提取仍错，A/B都未新增关卡 | 瓶颈已不是“有没有调用新工具”或“修复文本有没有送达” |
| [020 ar25轨迹](020-ar25-adoption.md) | L5先把15×15范围填成225格，后来从ASCII重新提取成99格才得到可用placements；L6仍有裁剪漏块 | 原始像素的精确集合能进入已有搜索，但重建、裁剪和转抄反复出错 |
| [020 cd82复核](020-cd82-ft09-review.md) | 真实涂色范围为四列，动作效果模型手写成三列，搜索据此判无解 | 精确数据同时应服务物体形状与动作前后变化，不能只看目标图 |

这不是已证明能提分的机制，尚未直接验证“给出精确足迹后模型会用它”。但它针对的是已经复现到真实修复输出中的错误，不需要继续泛搜公开Notebook。

## 最小改动

现有[segmentation.py](runtime-bundle/src/ARC3-Inference/inference/utils/segmentation.py)的 `segment_layer()` 在flood fill时已经保存每个component的真实 `cells` 集合，返回节点时却仅输出 `pixels`、`boundary`、hash和children。文档明确 `boundary` 是外轮廓角点，**不描述内部孔洞**，也不是“可直接填满的矩形”。FrameView只把该结果作为原有 `.segmentation` 属性公开。

建议唯一求解变化是在同一个节点dict中增加 **`runs`**，内容为完整、排序的绝对坐标行段 `[[row, col_start, col_end_inclusive], ...]`，直接由已有component cells生成。它是实际色块足迹，不推断哪个颜色是玩家、背景或目标。所有原字段保持原语义；不添加新工具、region API、世界模型或自动修复请求。

同一接口说明只需明确：精确像素用runs，boundary是外轮廓、不要直接填包围盒。模型本来就在读和打印 `.segmentation`，因此该数据进入现有主入口，减少020新region入口完全未被使用的负担。搜索代码可以从runs直接构造集合，避免看ASCII后再手写坐标表。

这一新增字段可能拉长整节点输出；使用行段而非逐像素列表，是为减少同一物体的冗余。应保留完整数据，不按题目、已知图案或手工槽位裁剪。已有工具输出截断照常计成本，不能把“字段已提供”当“被消费”的结果。

## 已准备的可逆实现

[segmentation_runs.py](../src/arc3_research/segmentation_runs.py)提供 `install_segmentation_runs()` → `snapshot()`／`uninstall()`，无需配置参数。安装先包装宿主原 `segment_layer`，在原节点dict中附加runs；同时更新 `python_tool_sandbox._SANDBOX_BOOTSTRAP` 内已经嵌入的分割副本，确保真实隔离工具也能读到字段。原runtime文件不改写。工具说明只增加35词字段合同，不修改系统求解策略，不叠加030、029或任何调度机制。

当前实现用一次额外线性flood fill复得原4连通component membership，并按原始阅读顺序附回节点。原内部cells没有可直接访问的运行时出口；独立wrapper避免改写原函数源码及重复整套分割／包含分析。后续若优化可复用原cells，但这不是本轮研究必需工作。

root接入时将本模块与空包初始化文件加入Notebook payload，在构造agent前安装即可：

```python
from arc3_research.segmentation_runs import install_segmentation_runs
segmentation_runs_patch = install_segmentation_runs()
```

卸载调用 `segmentation_runs_patch.uninstall()`。不要与persistent_python同时安装；031的独立比较应使用009原Python生命周期。

## 原帧计算与实际开销

[ft09-footprint-calculation.json](../experiments/031-segmentation-runs/ft09-footprint-calculation.json)使用已保存028包中的原始ft09 cum27画面。真实调用宿主分割与 `ToolAgent._run_python_tool` 隔离sandbox，没有模型请求或游戏动作。52个节点、433个runs完整覆盖4096像素，每点仅属于一个节点，所有原节点字段逐项不变。

错误处白色node45的外接框是rows46–49、cols28–33；精确runs为 `[[46,28,29],[47,28,29],[48,28,33],[49,28,33]]`。因此原错误点 `(46,32)` 不属于白色集合；sandbox实际打印 `white includes (46,32): False`，全帧白色精确集合为72像素。该结果只证明返回的是原图足迹，不证明模型会修改旧提取器或完成关卡。

| 该64×64帧的返回体 | 原版 | 附加runs | 增加 |
|---|---:|---:|---:|
| 紧凑JSON | 12264 bytes | 17377 bytes | 5113 bytes，41.69% |
| 默认JSON／Python repr | 13891 chars | 20355 chars | 6464 chars，46.53% |

单次宿主调用观察为原39.17ms、候选40.32ms，只有一次读数，不能当性能基准。新增字段说明为243字符、35词。整节点打印明显变长，真实输出成本需计入后续比较。

日志中自然出现的原生读取路径也已保留：015 baseline ft09第3行 `call_8bf25b5a733245fab539e595`，直接读取 `seg=current_frame.segmentation; nodes=seg['nodes']`。该原代码在当前切点sandbox执行成功，stdout为4053字符；它随后只打印原有选定字段，所以**不会自动打印或消费runs**。另一次显式runs集合读取是本研究计算，不包装为模型自然采用。模型是否按简短字段说明使用runs，仍由下一次自然运行回答。

## 和旧路线的区别

- 018是一段全局提醒；此次交付的是宿主实际像素集合。
- 020要求模型另调region接口，主失败链基本没有采用；此次扩展原本就在使用的segmentation节点。
- Lexicon用尺度、对象分组和语法推断；此次不改变原4连通、同色component，也不猜规则。
- 028让模型再次修提取器；此次省掉从外轮廓猜内部占据的环节。

不能把这些区别当作效果证明。若模型继续从boundary生成错误集合，继续扩大runs输出也无意义；应直接从本次自然轨迹判定是否真正消费。

## 最短 GPU 研究安排

原帧输入比较已完成。接着可进行一次 **10题、10 streams、A/B各900秒、共享一次模型加载** 的自然运行：ft09、ar25、cd82、tr87为主要失败类型，其余从当前公开题中固定六题用于维持队列并观察正常轨迹。预算约 **0.7–0.9 GPU小时**，取决于模型加载时间；正式评测底座和服务参数保持009。

本轮只回答已有代码是否消费runs、是否避免再次填错足迹、是否在相同预算内完成更多关或更快推进。不要先做多轮CPU门控或要求模型提供自报。若短运行达到的关卡尚未出现相关形状错误，就明确该窗口未回答问题，不把无异常当成功。出现直接增量后再决定全池与正式提交。

## 空动画兼容修复作为低成本修正

同时完成的只读审计找到了确实存在的另一个兼容缺陷：`last_animation_timeline`在单帧时只含error，模型按文档读取 `action`／`steps`会报KeyError。027 sc25第9行和第13行分别命中；扩读005／014／016／020基线又发现11个去重调用，集中于sc25与sp80。合计13次，分布于5份日志、2款游戏。[本次局部审计](../experiments/031-next-mechanism/animation-error-audit.json)、[扩展审计](../experiments/031-next-mechanism/animation-error-expanded.json)。

Heliosli公开v5／v6已有补 `action/frames=0/steps=[]` 的小修复。但这些错误大多很快自然恢复，当前证据只支持减少局部失败调用，不支持把它当作主要奖牌突破或专门投入一轮5小时全池。若要做，应作为另一个独立小修候选，不能偷偷叠入031精确足迹比较。

当前结论：030若失败，优先研究**精确足迹进入原有segmentation消费链**；不再追持久化容量、调度参数或多加一段泛化提示。空动画字段修复保留为低成本兼容修正。
