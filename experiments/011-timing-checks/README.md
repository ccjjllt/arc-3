# 011 inference timing 手工核验

冻结模块：`src/arc3_research/inference_timing.py`，SHA256 `5ff98e60341015277b84cf88dbe4d54abe842e03834b6fd4f6080c3721db00f8`。

`manual-report.json`记录31项通过结果、受控session事件与计时样本；`replay-command.json`保存完整可复核CPU命令。未增加tests/CI，没有模型、GPU、真实HTTP或引擎实现读取。

使用真实Franzen `_PriorityGate` 与 `ToolAgent._chat_completion`，只将transport换成受控JSON/SSE响应，并用custom Session建立观察范围。核验单slot A→B→A handover、原参数与返回/异常identity、原重试次数、流仅由原方法消费一次、clock诊断故障不改变原执行、128/4096默认参数之外的小容量边界。010动画模块SHA256未变。

1000次CPU合成请求循环：未安装约8.99ms，安装约23.59ms，增量约14.60µs/逻辑调用；安装侧含一个只用于identity核验的spy append。不是GPU解码、真实网络或完整实验成本估计。

时间口径：

- `chat_*`包住逻辑调用，含原重试、stream消费与解析；可能包含summary调用。
- `http_attempt_*`是现有`requests.post`的进入/返回/异常。stream返回可能只有headers，不等于生成完成；首次入口不证明服务器已经接收或开始decode。
- `gate_enqueue_begin → gate_admitted_return`包含enqueue、pump、等待、唤醒及重获Condition，不是纯sleep，也不是另一线程grant credit的精确时刻。
- `gate_release_credit`观察原有`_free += 1`之后的位置，没有自己释放slot。`observed_slot_held`包含持slot时的模型、Python与其他本地工作。
- 各类duration有嵌套关系，不能相加当总耗时。最终snapshot应在worker drain后读取；运行中snapshot标`provisional`。
- 固定容量保留最新event；首时间与全程计数独立保留。未得到usage的生成量保持未知；诊断失败以`observer_record_errors`计数。

独立审查已核对冻结hash及本报告，无剩余启动阻断；最终Notebook和GPU运行由root负责。
