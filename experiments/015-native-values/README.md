# 015 原生普通值交接：独立 CPU 原型

2026-10-17。依据 [013 本地证据](../../research/013-local-evidence.md) 的同观察跨 snippet 丢值病例，先验证普通 Python 数据能否按明确合同交接。**没有启动 GPU/模型、没有执行历史模型代码、没有游戏引擎动作；没有修改 `src/`、014 或 `run_arm.py`。** 原型不是可直接上线的插件，也没有采用或提分证据。

## 已实现的最窄语义

- 只收集**成功完成且没有 action 请求**的 snippet 的普通值。比“没有真实动作”更保守：动作被拒绝的 snippet 也不提交；明确拒绝且观察未变时，保留前一份已提交快照。
- 允许 `None/bool/int/finite float/str/list/tuple/dict/set/frozenset` 的**确切内置类型**；tuple/frozenset 可作 dict key。禁止 callable/module/frame、自定义类型及内置类型子类；不使用 pickle，不调用对象转换/序列化协议。
- 有界类型标签 JSON：最多32个候选名字、64 KiB快照、16层、4096个遍历节点、单scalar16 KiB、整数4096bit。预检也遍历别名路径，不能通过共享对象绕过深度限制。容量为保守上限，不等于RSS限制。
- 同一快照内及跨变量的容器别名保持，例如 `b is a`；恢复结果与旧子进程完全分离。循环结构拒绝。list/tuple/dict保留顺序，set/frozenset保持正常无序语义；wire不是跨进程canonical set hash。
- 成功快照替换整份名字集合：删除不复活，普通值重绑反映新值；重绑成不支持对象会删除旧保存值。单根不支持则跳过该根并记录原因。整份快照超过容量或格式校验失败时**清空前一快照**，避免成功代码删除/重绑后旧值又出现。
- 异常或timeout不提交部分修改；若没有动作或观察变化，前一份已提交快照保留，等价于回滚该snippet的数据修改。已经执行动作后发生异常/timeout时，快照仍为空。
- 身份严格绑定宿主提供的 `session/attempt/action/level/frame_sha256/revision`。每个宿主session一个store；任何身份变化都清空。真实动作（包括画面不变的no-op和RESET）立即清空；动作执行结果不确定时保守清空。只读检查不改变游戏状态。
- 新 `current_frame/history/action`、内置名字、已恢复函数/import等保留名字不得覆盖。**恢复函数时的 `_available_names` 不加入数据名字**：普通值只在原版函数恢复完成后注入，因此依赖隐式普通全局的函数仍按原合同拒绝保留。纯函数可在下一段显式接收恢复的数据参数。
- 从函数/import名字改成普通值仍受本段reserved集合保护，不保证这类名字重绑能跨段保持；这是原型的明确边界。动作后当前snippet内已读局部值不自动销毁，只有宿主后续快照被清空。

## 文件与复核

- `codec.py`：独立、stdlib-only、有界带类型数据图编码/解码、名字采集；对child wire重新校验。
- `prototype.py`：宿主一会话一快照的生命周期，以及**真实sandbox源码的内存副本**。源码锚点数量必须匹配；导入原sandbox文件时绕过会拉起完整ToolAgent依赖的包入口。原始模块与文件保持不变。
- `manual_probe.py`：人工合成值、人工snippet、人工动作反馈；没有重放保存日志中的模型代码。退出结果、每次sandbox代码/结果/提交状态、源hash在 `cpu-report.json`。

复核命令：

```bash
python3.12 -B experiments/015-native-values/manual_probe.py
```

原型验证的事实是类型/身份/事务合同及真实子进程接续，并非ARC真实游戏效果。小样本CPU耗时含子进程启动，不能外推110游戏GPU推理影响。

## 后续真实集成点

1. `python_tool_sandbox.py` 建立 `_available_names` 并执行 `restore_functions` 之后、运行用户代码之前：注入经验证数据；**不得把数据名加入 `_available_names`**。目前 `copied_runner()` 用唯一的 `_collect_retention_payload` 定义位置前插入实现。
2. 只在成功 `type='final'` 路径采集快照；`type='error'`、host timeout/进程死亡没有新快照。宿主最后返回字段需要显式传递快照。不能复用012即时 `put` 提交语义，因为本实验要求整段成功提交。
3. 宿主 `_HarnessGameSession._execute_action` 的实际动作边界负责失效和RESET attempt；action callback的执行失败也需检查实际history/identity，不能仅凭函数抛错判断“没动作”。`_run_python_tool` 开始/结束使用宿主身份比对，覆盖恢复帧、跨关、重置及session替换。
4. 当前carrier是 `SyntheticSession`；**完整ToolAgent/SDK生命周期尚未集成**。正式安装要有每session独立store、锁/有界session总内存、进程重启失效、批动作中途异常/自动RESET、host真实动作计数与结果对账。child不能自己决定observation身份。
5. 正式实验说明只准确陈述普通值的短期寿命，纠正原版“所有变量每段消失”的描述；不新增put/get、不强迫保存、不叠加World/Goal记忆段或提示策略。所有snapshot/rejection元数据先用于日志，不能不加区分地扩大模型上下文。

## ≤1h采用筛选前还缺什么

先完成独立完整调用链的CPU人工探针，覆盖真实ToolAgent反序列化、保留函数、批动作、RESET/death/levelup、超时及host观察失效。通过后才考虑不超过1小时的真实模型采用筛选，保持014调度实验完全独立。

采用必须出现模型自然生成的“计算→下一snippet原名消费”链；检查恢复结果和正确重算一致，并记录恢复字节、拒绝原因、CPU开销、少掉的重算/NameError。仅有54项以上工程检查通过不代表模型采用，更不代表增加通关。若可用机会太少、错误假设更易沿用、开销超过收益，则停止，不直接跑完整A/B。
