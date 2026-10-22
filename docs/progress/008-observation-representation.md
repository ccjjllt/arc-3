# 008 — 当前帧区域表示：CPU 进展

日期：2026-10-12（Asia/Shanghai）。对应 [008 计划](../plan/008-observation-representation.md)。状态：**接口研究、独立只读原型及保存帧 CPU 核对完成；未接入 agent，未安排 GPU，无提分结论。**

## 完成的工作

- 已审阅真实 `FrameView` 与通用 segmentation：现有 API 缺少绑定当前帧的区域 mask、明确 bbox/前景和裁剪诊断；已有旋转 hash 不替代本轮完整多组件区域表示。
- 新增 [observation_representation.py](../../src/arc3_research/observation_representation.py)：getter 每次读取当前帧，带 step/level/shape/ASCII hash；bbox 零起点且含端点；显式前景字符；完整 raw rows/mask；四连通组件并集；exact 默认保姿态，旋转/镜像键仅显式请求。
- 可按当前 segmentation node 求 bbox，显式 inset；node 请求必须带当前 reference。空 mask、未知符号、越界、旧 reference 和跨边前景均有明确返回；不默认去边框、拆符号或合并类别。
- 新增 [手动 CPU 复算脚本](../../scripts/analysis/analyze_008_representation.py) 及 [派生结果](../../experiments/008-representation/analysis.json)，保留输入路径/行号/hash、mask 与输出大小。原始 005/007 产物未改。
- 未修改 run_arm、研究基线、007、模型或 serving；没有 SDK 动作、GPU、游戏引擎源码读取、模型日志代码执行或新增测试文件。

## 实际 CPU 结果

| 检查 | 结果 |
|---|---|
| 保存区域坐标/字符/像素核对 | 69 份提取均匹配保存帧；含同帧及重复区域，不是 69 个独立样本 |
| 007 tr87 错误→正确图例裁剪 | pink 匹配 1/4→4/4；yellow 显式 D4 分类 9→7 |
| 当前节点 bbox+显式 inset | 六个 P 图例内框得到正确起点 5/14/23 |
| 旧/新保存快照 getter | action_num 24→25 时重新读取且 mask 变化；旧 reference/node 请求拒绝 |
| 姿态和镜像 | exact 保持区别；旋转类不混镜像；显式 D4 才合并 |
| 005 tr87 字母/二进制失配 | 24 个区域均非空，22 个 exact 形态；未知前景 `1` 不静默归零 |
| 005 re86 杆坐标 | rows30–47 的 S 位于 col36；bbox 中心 col27 不是杆位置 |
| 来源完整性 | 分析前后输入 hash 一致 |

## 必须保留的限制

截断诊断只命中 12 个实际错误裁剪中的 10 个；两个整体落在范围外的断开部分不会跨边，不能由“未发现跨边”推出完整。黄色长面板含多个符号，组件也不等于符号；本轮复算仍使用当时可见画面标注的子区域，未实现通用分槽。

完整单区域 JSON 为 926–1803 字符，在线输出合同尚需打磨。当前 getter 检查是保存快照替换；原型未注入真实 sandbox，不能称已证明在线帧新鲜性。正确 mask 不等于模型采用或增加通关。

## 下一步

保留独立原型，先明确面板/子区域选择和紧凑输出方式，再决定是否形成一因素 GPU 候选；不叠加 007 或新调度。默认 baseline 保持不变。详细来源、接口合同、反例与可复算命令见 [008 研究分析](../../research/notes/008/008-representation-analysis.md)。
