# r11l：有真实消费，但没有收益结论

静态复核候选原始请求 `runs/020-candidate-logs/grounded_state/r11l-495a7899_p0_requests.jsonl`，没有执行日志代码。来源 hash 见同目录 `adoption-index.json`。行号是调用与结果首次进入后续历史快照的位置，不当作精确生成/执行时刻。

- **原27行，seq13，`call_b2b51d39538e4470a012dc71`**：`current_frame.region((45,10,62,35), foreground='B') → reg.positions() → cands → t → MOUSE(row=t[0],col=t[1])`。结果显示275个黑色像素，选中 `(row=54,col=30)` 并真实执行，`executed=True`，但为 **NO-OP**。这证明返回数据进入动作坐标；不证明选点正确、推进关卡或减少动作。
- **原37行，seq18，`call_75f9e001e5de41eaa6a290c6`**：定义 `blocked_mask(frame)`，内部对四个32×32区块和两种颜色调用 `frame.region(...).positions()`；本条确实执行 `blocked_mask(current_frame)`，输出阻挡计数1200。结果明确报告该函数被保留。本条随后 `(28,44)` 点击是硬编码；不能声称该坐标由 mask 搜索或自动选择。
- **原73行，seq36，`call_e5f38d3dd0e54f3c805ff48b`**：后续 `(26,40)` 点击返回 effect 后，`if res['gameplay_changed']` 分支再次调用保留的 `blocked_mask(current_frame)`，再用 `m[c[0]][c[1]]` 检查推导线段，输出 `segments over blue now: []`。因此这里有跨调用函数复用和后续诊断消费；只搜直接 `.region` 会漏掉它。它不是事前动作拦截，也不证明推导规则正确。

错误应分别描述：原25行/seq12把 bbox 的四个坐标作为四个位置参数，触发 TypeError；下一条改为单个 tuple 后可读。原41行/seq20调用 `blocked_mask(previous_frame)`，按接口只允许 live current frame 的合同被拒绝，随后同条里的 `mcur` 和直接 region 表达式不能算执行。原35行/seq17在构造 mask 后尝试 `import pickle` 被 sandbox 拒绝，其后动作没有执行。这些是调用格式、观察生命周期或工具限制问题，不能据此认定 region 的像素实现错误。

可支持的判断是：**r11l 确有新接口返回值进入实际动作，以及保留函数的后续诊断使用；各游戏采用并不一致。** 当前仅为检索与人工证据说明，没有自动采用 pass、正确率或因果收益结论。整局分数下降也不能单独归因为这几次 region 使用。
