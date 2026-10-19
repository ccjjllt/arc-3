# 021 — 预测失配停批进展

日期：2026-10-19。状态：**jiyujia v1 COMPLETE。36.9270 → 29.3560（−7.5710），41 → 38 关，全通 3 → 0。停批接口没有被调用。不提交。** 计划见 [021计划](../plan/021-checked-execution.md)，结果见 [021分析](../../research/021-results-analysis.md)。

## 已接入

- 新模块 [checked_action.py](../../src/arc3_research/checked_action.py)。普通 `action(actions)` 保持原一批调用；`action(plan, pred=, extract=, scope=)` 每步调用原来的单动作入口。
- `run_arm`、配置校验、preflight 和 notebook 构建只在 `checked_execution` 臂安装该补丁和前缀。前缀 SHA256：`1a094fcb6175472208bb7e9d0a41bf78d6335e4658812b31d18aebfa08b1e535`。
- 冻结文件 `python_tool_sandbox.py` 的 SHA256 仍是 `3900b7255842df04be9ad08f91b521279a2e63f8226ac4bc77fb6de7a4e36943`。
- 研究 Notebook 已在本地生成：[notebooks/021-checked-execution](../../notebooks/021-checked-execution/experiment.ipynb)，32 cells，SHA256 `2f7a3ce5965c7301f4683d94cb9cf2d3e3711189b6bbaa1f4d8c1885d0105b49`。身份 `jiyujia/arc3-021-checked-execution`。没有 push，没有提交。

## CPU 证据

命令：

```bash
/Users/zhaohuaxiang/.local/bin/python3.12 -B scripts/check_021_checked_execution.py
```

[报告](../../experiments/021-checked-execution-cpu/report.json) 状态 **passed**。19 次真实 sandbox 子进程，18 个场景；preflight `passed`，网络调用 0，游戏动作 0。宿主动作是假的公开帧，不是一局 ARC，也不是模型修复。

- 普通 `action(["RIGHT","LEFT"])` 和 `action("RIGHT")` 仍是原入口，stdout 没有停批摘要。
- 两步预测一致时两步都执行，状态 `completed`。
- 三步计划在第 2 步 `col` 失配后停止；未执行后缀为 1。同一段代码随后单独执行了 `LEFT`。这是脚本安排的后续动作，只说明失配没有把进程卡死。
- `level_completed`、`game_over`、`done` 和无关卡旗标的换关都在比较前停止，状态是 `boundary`，不是 `mismatch`。`game_over` 的公开 level id 保持 `public-level:1`。
- `known_noop` 仍抛出 `KnownNoOpActionError`，第二步没有送出。
- 只声明 `{"ok": 1}` 时，画面变化不会停批。声明了边缘字符时，边缘变化会停批。
- 点击以 `{"action":"MOUSE","row":4,"col":7}` 进入 `pred` 和宿主。旧的 `x`/`y` 被原归一化拒绝，并且没有动作送出。
- 缺 `extract`、提取抛错、预测改字段、超过 32 步，都没有降级成一批未检查动作。
- 卸载后普通 `action(["UP"])` 恢复，前缀清空。

## GPU

2026-10-19 以 jiyujia 上传 v1，随后 COMPLETE。Notebook SHA256 `2f7a3ce5965c7301f4683d94cb9cf2d3e3711189b6bbaa1f4d8c1885d0105b49`。私有、离线、RTX PRO 6000。平台上限 7200 秒，内部硬限 5400 秒。没有比赛提交。

会话 70.11 分钟，启动 9.06 分钟。两臂各 1800 秒、12 游戏完整，退出码 0，缓存清理和排空通过，服务已关闭。求解 GPU 采样均值 90.74% / 95.51%，中位 98%。

均分 36.9270 → 29.3560。最大退分是 ft09（−55.45，6→4 关）和 tr87（−28.57）。ar25 多两关（+36.11）。候选请求 1438 条，助手没有调用 `action(..., pred=, extract=, scope=)`，工具输出里没有停批摘要。分数变化来自多出来的前缀，不是来自停批执行。

020 的 41.2112→26.5081 仍然有效，那一版不提交。正式成绩仍是 009 v2 / submission 57101330 / public 31.16。下一改动应换连接方式，不重复这一版前缀。
