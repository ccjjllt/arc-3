# 021 — 预测失配停批

日期：2026-10-19。依据 [021实施交接](../handoff/021-implementation-handoff.md) 与 [020行为机制](../../research/020-behavior-mechanisms.md)。020 区域通道已经完整跑完并回退，本候选不叠加那条通道、018 提示、FP8 或有限探索。GPU 短筛尚未启动。

## 要回答的问题

基线已经会写预测、执行、再比较。016 的 m0r0 在第 2 步预测失配后仍执行了剩余动作。021 只检验一件事：当模型把自己的 `pred` / `extract` 交给现有 `action` 时，第一次声明字段失配是否停下未执行后缀，并把反例留给后续代码。

这不证明模型会主动调用新参数，也不把少走几步换成官方分数。

## 唯一干预

生产补丁在 [checked_action.py](../../src/arc3_research/checked_action.py)。核心仍是未改写的 [checked_execution.py](../../src/arc3_research/checked_execution.py)。冻结运行库 `python_tool_sandbox.py` 不改；子进程脚本在内存里替换。

- `action(actions)` 仍是原来的一批动作，归一化、点击 `row`/`col`、no-op / terminal 异常和终局闩锁都走原函数。
- `action(plan, pred=pred, extract=extract, scope="...")` 才进入停批。`extract(frame)` 与 `pred(values, action)` 都返回同一组非空 JSON 字段。`action` 是完整动作字典。框架内部包成 `ComparableState`，调用方不用自己造这个类型。
- 每一步把一个动作列表交给原来的 `action`。点击坐标不重新解释。
- 动作返回并刷新 `current_frame` 之后，先读公开的 `level_completed`、`game_over`、`done` / `run_complete`、`stop_reason`，再比较预测。`FrameView` 没有终局字段。观察事件号按本调用计数，no-op 只要真正返回就算新事件。公开结果里没有 episode id，所以 episode 保持常量 `public-session`；RESET 由 `game_over` 表示，不另造一集。
- 首次字段失配停止本计划剩余后缀，打印 `status`、已执行数、未执行数和最多 8 处差异。提取失败、预测改字段、计划超过 32 步都不降级成普通一批动作。`KnownNoOpActionError` 等原 `BaseException` 继续抛出。
- 候选进程使用原有 `ARC3_SYSTEM_PROMPT_PREFIX`。baseline 提示逐字保持。不新增工具，不增加模型调用，不加 UNDO。

## 冻结短筛

配置 [021-checked-execution.json](../../experiments/021-checked-execution.json)。与 020 相同的 12 个官方开发游戏，baseline → checked_execution，各 1800 秒，10 路、1 pass、warmup 0、remaining/pace 0。硬限 5400 秒。账号沿用 jiyujia。这是同预算对照，不是隐藏分预测，也不是全 25 游戏回归。

若请求日志里完全没有 `pred=` / `extract=` 这条路径，先改连接方式，不把同一问题再打满整池。采用和分数分开记。关数和全通数只作解释。

正式提交仍等这轮同预算结果。当前 020 研究 Notebook 不提交。009 v2 / submission 57101330 / public 31.16 保持正式成绩。
