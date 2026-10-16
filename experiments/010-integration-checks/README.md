# 010 实际工具链 CPU 交付检查

日期：2026-10-13。最终冻结版产物：[cpu-20261013T012311Z/summary.json](cpu-20261013T012311Z/summary.json)。

脚本为 `scripts/check_010_animation_integration.py`，不是新增测试套件或 CI。原版、候选、合成边界分别在独立 Python 子进程运行；共 97 条通过记录，包含重复的通信成功、未执行动作等断言，不应解释为 97 个独立游戏或性能样本。

原版与候选使用实际 `GameAPI → _HarnessGameSession._execute_action → step_env → ToolAgent._run_python_tool → Python -I -S sandbox`。只有工具代码是手写固定探针，没有模型请求。HTTP 方法设为拒绝调用，三进程均零 HTTP 尝试。只读取公开 observation，不读取游戏实现、隐藏状态或执行历史日志代码。

| 检查 | 已取得证据 |
| --- | --- |
| 真实多动作 capture | tn36 五个固定 MOUSE；动作 3—5 在同一实际 batch，五个动作均有独立引用。 |
| 旧动作像素与接口 | 动作 2 原始返回 7 帧；动作 5 返回 1 帧。后续动作后经 callback 与 sandbox FrameView 逐帧 ASCII 完全相等，并核对原像素 uint8 SHA256、API grid JSON SHA256 和整条 archive SHA256。 |
| ROI / 分割 / 原当前帧 | 在旧帧中读取 16×16 ROI 与 segmentation；结果与公开帧一致，查询前后当前 runtime-state 文件字节完全相同，action count 不变。 |
| RESET 作用域 | 实际 RESET 为动作 6、attempt 1；同 session 的完整旧 attempt 0 引用仍命中。将动作 2 错标为 attempt 1 明确返回 `wrong_attempt`。 |
| 错误引用与第二会话 | 错 action 为 `missing`，错 game/session 为 `wrong_scope`，不完整 ref 为 `invalid_ref`；第二个真实 SDK session 不可读取第一个 session 的旧引用。 |
| 旧接口不变 / disabled | 未安装 patch 的独立原版，与候选在动作 1、2、5 后的 `last_animation_frames` 数据完全一致。原版没有新 API/说明。另将 `ARC3_ANIMATION=0`，两组旧 frames/timeline 均不出现，候选新 archive 仍能命中历史。 |
| 现有 retained functions | 手写函数调用新 `animation_at`，使用原函数保留机制在下一段 sandbox 调用仍返回 7 帧。仅这一兼容性探针开启该原有开关。 |
| 合成边界 | 小容量独立进程：记录、单会话字节、全局字节、会话数量淘汰；重复帧保留；空链、超大链、非法颜色、非法 limit 明确返回状态，没有 latest 替代。已无 metadata 的旧引用返回 `outside_retained_history`，不声称仍知道它曾存在。 |

候选公开序列捕获 6 个实际动作、12 个原始返回帧（不含初始 observation；每动作另存 before frame）。存储 JSON 为 150,531 bytes。6 次 capture 的累计线程 CPU 约 5.20 ms，18 次查询合计约 20.03 ms；这些数字不是 RSS，也不含游戏动作或模型计算。两次 7 帧 sandbox 检索的响应各 102,542 bytes，整次调用约 0.131 / 0.132 秒，原超时为 30 秒。探针只打印 ROI、hash 和校验字段，结果 1,044 chars；完整链通过 IPC 的成本仍在，不能把这个数字当作直接打印所有帧的上下文成本。

最终模块 SHA256：`ea4bb1a77433e2ccefbb9d46abe9e82e6eac8ae5c058828662e4732a940ca875`。脚本 SHA256：`41d7397d77901b6ed9609d134e3e4b1da43c0fdbf63057de485fa06ac97ef35d`。summary SHA256：`dd1ecbce60567e84813560b52e9c0d006ad8b884d8b703bf3513cd9bd166c3b9`。三 worker 的源文件 hash 与结束时再次计算结果完全一致。早期子目录是开发过程中旧版本的检查记录；最终结论只绑定上述冻结版。

完整原始工具输入、stdout、dispatch、计时与边界输出在各 worker 目录；`public-observation-oracle.npz` 保存公开帧副本（不包含隐藏状态）。复算命令使用已有本机环境与离线 SDK 解包目录，脚本不安装任何包：

```sh
/Users/zhaohuaxiang/ccjjllt/binance-quant/.venv/bin/python scripts/check_010_animation_integration.py \
  --sdk-path /private/tmp/arc3-010-sdk \
  --extra-python-path /Users/zhaohuaxiang/ccjjllt/quant-research-lab/.venv/lib/python3.13/site-packages \
  --extra-python-path /Users/zhaohuaxiang/.cache/uv/archive-v0/0NYjaDD0X1HZ1p_3 \
  --extra-python-path /Users/zhaohuaxiang/.cache/uv/archive-v0/GCIcB4ohHyKQ4LxX/lib/python3.13/site-packages
```

本次没有真实跨关、死亡后自动 RESET、并发压力、长运行内存峰值或跨进程存档恢复验证。第二会话隔离是两个真实实例的顺序检查，不是生产并发隔离证明。容量与空链等输入为 synthetic，不是游戏结果。没有模型采用、策略修正、token 收益、关卡增益、GPU 性能或榜单提分结论。
