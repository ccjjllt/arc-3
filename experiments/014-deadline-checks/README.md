# 014 请求截止修复的手工 CPU 核验

最终模块：`src/arc3_research/request_deadline.py`，SHA256 `204c7bcb86478ee4b60aa9fffbe5b251abf5b27e4bf1534f1e773b9461372112`。

`report.json` 保存 36 项通过检查、来源函数签名/SHA256、真实计时器组合快照和有限事件账本。检查脚本是 `scripts/check_014_request_deadline.py`；未新增 tests/CI。没有模型、GPU、真实网络、游戏引擎动作或历史模型代码执行。

## 实际实现边界

`install_request_deadline(tool_agent_class=None, session_class=None, *, max_events=256)` 返回带 `snapshot()` / `uninstall()` 的补丁。仅在原 `Session.play` 的线程作用域内，分别在原 `_maybe_handover` 返回后、逻辑 chat 入口、每次实际 `tool_agent.requests.post` 入口检查当前 session stop 与 shared soft deadline。HTTP 重试仍属于原方法，截止后的下一次尝试被阻止；截止前参数、payload、timeout、原 retry/backoff、响应消费和返回保持。

终止使用专用 `BaseException` 穿过原 retry 与 analyze 的普通异常捕获；只把仍 playing 的本 session 标 cancelled，由原 finally 收尾、释放 gate，最外层 play 消费本补丁的取消信号。不会设置整个账户/其他游戏的 stop event，不自行 release/acquire。原 `analyze` 的 summary 调用在其 try/finally 前，专用取消路径另补清除临时 callback/valid-actions。原异常及其他 cancellation 不吞；尚未观察到 stop 时如果权威检查失败，fail closed 并以 `RequestDeadlineCheckFailed` 保留原异常 cause。已观察到 stop 不再依赖可能失败的次级时间查询。

生产组合顺序是 deadline → inference_timing → scheduler observer，卸载严格逆序并在所有 worker drain 后执行；若有后来安装的 wrapper 尚未卸载，deadline 拒绝覆盖它。

## 核验覆盖

- 使用真实 `ToolAgent._chat_completion` 的 JSON/SSE路径、原 retries、真实 `_PriorityGate` 排队/hand-over、实际 `_HarnessGameSession.play/_play_inner` 与 `ToolAgent.analyze`；transport、grid/game及 viewer 为人工输入。没有用简化的替代 chat/scheduler 宣称实际路径通过。
- 截止前 payload/timeout 与未安装原方法一致，JSON/SSE 只被原方法消费一次；原返回与 transport exception identity 保留。
- 真实 gate 线程 A→B→A 等待：B 释放前推进受控 deadline，A 醒来后零 HTTP；gate 最终 free=1，无 waiting/admitted 遗留。
- chat 入口已截止、构造 payload 时刚截止、原 retry 前刚截止均不会新发请求；完整 analyze 取消后未标 crashed、原状态文件和临时 callback 清理正确、slot 未重复释放。
- 检查异常/其他取消不被吞掉，检查失败时零请求；已取消不因次级 clock 报错变成失败；诊断 clock 故障不能抑制取消。
- 已发出的请求允许原样完成，未丢弃结果。与 `inference_timing` 顺序组合正常，逆序卸载恢复实际函数和 requests 代理。
- 500 次人工请求 CPU 循环：有补丁 5.663ms、对照 4.065ms，约 **3.20µs/逻辑请求** 增量；有补丁侧还多一次返回 identity spy 的 list append。这不是 GPU/真实网络性能或实际节省估计。

## 复核环境

完整 harness 已在 Python 3.13.14 下通过：

```bash
/Users/zhaohuaxiang/ccjjllt/binance-quant/.venv/bin/python -B scripts/check_014_request_deadline.py \
  --sdk-path /private/tmp/arc3-010-sdk \
  --extra-python-path /Users/zhaohuaxiang/ccjjllt/quant-research-lab/.venv/lib/python3.13/site-packages \
  --extra-python-path /Users/zhaohuaxiang/.cache/uv/archive-v0/0NYjaDD0X1HZ1p_3 \
  --extra-python-path /Users/zhaohuaxiang/.cache/uv/archive-v0/GCIcB4ohHyKQ4LxX/lib/python3.13/site-packages
```

本地 Python 3.12.14 的 Notebook/IPython 环境另尝试完整导入，止于 `ModuleNotFoundError: matplotlib`；给定 Codex runtime 3.12 路径未提供 matplotlib，已找到 uv 缓存均为 CPython 3.13 二进制。未混用二进制或联网安装；不能把 Notebook 打包成功当成 3.12 完整 harness 运行通过。远端必须在 serving 前跑真实环境 preflight；环境事实由主线程记录。

## 不作出的保证

该补丁不终止在途生成、不缩短原 timeout，不保证服务器 `entry_time` 在截止前。最终客户端检查与真实 socket send 间仍存在微小竞态；CPU 检查证明受控边界拒绝，不能声称系统具备原子 wall-clock 截止。此修复对两臂共同启用，不能把资源边界修复算成 tail 策略提分。
