# 012：current_data 的真实采用审查

2026-10-13。**本轮没有形成“写入 → 跨 snippet 读回 → 使用原值”的采用链。** 13 局只有 ft09 调用过接口：2 次 `put`、1 次成功、1 次拒绝；所有游戏的 `get`、`context` 均为 0。cd82 与另外 11 局零调用，不因前置 CPU 假说而挑选它们做效果归因。

完整逐局计数见 [`telemetry.json`](../experiments/012-intervention-analysis/telemetry.json)。终态诊断明确 `snapshot_after_worker_join=true`、无 lingering worker；模块与运行 metadata 的 SHA256 均为 `0d6f825d65cb091203e590cc6777d402f5cf1a6fa5cdd3b92f3d0c5f29f05c4c`。计数中的缺失项按源码 Counter 语义记为 0。

| 指标 | 本轮 |
| --- | ---: |
| put 请求 / 成功 / 拒绝 | 2 / 1 / 1 |
| get / context 请求 | 0 / 0 |
| 返回 current / stale / missing | 0 / 0 / 0 |
| 随动作失效的已存条目 | 1，181 字节 |
| 确认跨 snippet 读回、随后用于规划或动作的游戏 | 0 / 13 |

## ft09 的两次写入

**L3，action 11：格式拒绝。** requests 首见第 23 行、`call_b74bdb41de044075b47d4b30` 中，模型生成 `clicks=[(RC[r]+3, CC[c]+3) ...]`，然后 `current_data.put('clicks', clicks)`。这是包含 tuple 的 list，不符合严格 JSON 值合同；结果明确为 `{'status': 'rejected', 'reason': 'unsupported_type'}`。同次计算还打印了一个约束冲突。后续模型继续检查手工转录与机制假说，没有显式修复此次 tuple 写入，也没有调用 get。L3 最终在 action 25 通过，早于本轮唯一成功写入，不能归功于缓存。

**L4，action 28：成功存入一个尚未确定的目标，下一段另行更正。** requests 首见第 37 行、`call_ac7add4d409c49fa9f6912b1` 中，程序搜索输出 `solutions 12`，随后取 `sols[0]` 构造 `tgt`，转换为字符串键 dict 后成功写入。ack 绑定 action 28 / L4，181 字节，value SHA256 为 `f6dd1acd3159d84e753555fd23709edbdf02abb321f3414a136953305d646c49`。

下一模型段（首见第 39 行，`call_ef6e8ff54d684dcfb788bfaf`）明确说：`My printed target used sols[0] which was a wrong combo.` 它利用 stdout 与既有规则重新判断，然后在新 snippet 中手写更正的 `tgt`，直接构造并执行 21 个动作；没有读取已存值。L4 在 action 49 通过。这里能确认模型使用了原工具输出进行推理，不能把这种既有 stdout 使用计为 current_data 采用，也不能把成功保存的任意候选解称为已验证事实。

成功写入与下一段开始之间没有游戏动作，缓存当时仍有有效读取窗口；后续首个 action 29 才触发合同规定的失效。终态 ledger 的唯一条目失效与此相符，但没有任何 stale get。**本轮证据不支持“动作后过期阻碍读回”这一解释，也无法从零 get 推断模型不读的心理原因。** 可直接确认的接口摩擦是第一次 tuple 被拒绝。

## 结果边界

ft09 baseline 各关动作数 `[4,7,14,21,64,15]`、6 关全通；候选 `[4,7,14,24,73,0]`、完成 4 关。前三关完成边界相同；唯一成功 put 位于第四关，且未读回。两次运行的成绩差异不能作为这个未实现读回链的效果证据，也不能据此独立认定缓存导致下降。

本轮不支持晋升 current_data，更不支持优先扩大容量或延长作用域；CPU 探针证明接口可交接数据，真实轨迹则只证明模型发现并尝试写入。后续若继续，首先要观察到实际 get 后原值被消费，同时区分测量结果与待验证假说，再讨论省重算或减少转录错误。

最小摘录、tool_call_id、首次出现的 request 行号、完整消息 hash、事件帧 hash 及两臂 6 份源文件 SHA256 均在 [`ft09-evidence.json`](../experiments/012-intervention-analysis/ft09-evidence.json)。本审查仅解析 JSON 与消息文本，没有执行日志代码、读引擎或启动 GPU。
