# 007 — 未收到函数快照时保留最后一次有效代码集合

日期：2026-10-11（Asia/Shanghai）。本轮先核查源码与真实轨迹，再进行极小CPU手动复现；在缺口确认后实现独立opt-in补丁。未启动GPU、未执行日志中的模型代码或游戏动作、未读游戏引擎源码、未创建测试文件。

## 结论

**存在可复现的状态提交缺口：硬超时没有返回函数集合，host却把“没有快照”当成“合法空集合”，清空此前已保留的所有函数。** 这不是普通Python异常的一般行为，也不能归因于关卡切换。

已实现最小候选：`src/arc3_research/program_state.py`。仅在结果字典**缺少 `keepable_functions` 键**时保留当前已提交的函数源码/显式import集合；凡有该键——包括合法`[]`、正常Python异常携带的有效快照——仍走原代码。`run_arm.py`新增独立`program_state` arm和`program-state.json`诊断。尚未构建Notebook或运行GPU，不能作提分结论。

这里“最后一次有效集合”是指成功交付并被底座接纳的源码快照，不是“整个snippet无异常”，也不是“函数的游戏逻辑已经正确”。

## 真实轨迹证据

| 来源 | 原始请求行 / action | 实际反馈 |
|---|---|---|
| 005 tr87 | raw L133 / action292，analysis_step29 | `Tool timed out after 30s`；34个previous functions提示不再保留 |
| 006 A ar25 | raw L159 / action219，analysis_step44 | 相同timeout；39个旧函数不再保留 |
| 006 B ar25 | raw L91 / action136，analysis_step25 | 相同timeout；15个旧函数不再保留 |

ar25依据 `runs/006-compact/baseline__ar25-0c556536_p0_requests.compact.json` 与 `transient_history__ar25-0c556536_p0_requests.compact.json` 的对应source_line记录。计数只取各工具payload的`function_retention`一次，不对compact内重复展示的元数据重复累计。

005 tr87后续重建 `g5c` 输出ASCII字母、`sig`仍按字符`'1'`置位，产生全零编码；再改为`'B'→'1'`、恢复旋转归一化。这是一个具体的“工具丢失→重新编码产生错误”的后关病例。但保留旧函数是否足以避免重建、是否原函数适用第6关，尚未用GPU检验；更不能把该机制当作006全部回退原因。

## 源码链条

使用已应用Franzen补丁的 `research/runtime-bundle/src/ARC3-Inference/`，没有读取任何具体游戏实现。

1. `inference/agent/python_tool_sandbox.py:866–875`：host等待超过deadline就杀掉子进程，只返回`error/stdout/action_results`，**没有 `keepable_functions`**。启动失败、异常退出、非法协议响应也有缺键路径。
2. 同文件`665–680`、`698–727`：正常完成，或被sandbox捕获的普通Python异常，都会调用`_collect_retention_payload()`，从实际执行后的namespace收集函数。
3. 同文件`958–967`：收到child的`final/error`消息后，host转发`keepable_functions`列表。
4. `inference/agent/tool_agent.py:4614–4658`：`for item in sandbox_result.get("keepable_functions") or []`把缺键与空列表合并；随后无条件`self._kept_functions = kept`，因此硬超时清空所有旧函数，并生成“no longer retained”反馈。
5. `_run_python_tool`在约5913行先提交保留集合，再在约5944–5945行根据真实action_results更新作用域/关卡状态。

这最后的顺序很重要：修复应位于函数快照的提交点，不能在整个tool调用结束后盲目把旧集合写回，否则可能把底座刚执行的level/session清除也撤销。

## 现有语义：哪些变更应当保存

`inference/utils/retained_functions.py`只保留源码与可接受的显式imports，不序列化任意Python变量、帧对象或执行栈。每次snippet仍在新隔离子进程中运行。restore只执行允许的import与def，不重放旧函数体、旧赋值、旧动作。

`collect_functions`从实际namespace判断，而不是仅扫描最后一个同名def：

| 情形 | 原版实际行为 | 007行为 |
|---|---|---|
| 正常完成，未改旧函数 | 保留恢复的旧源码 | 不变 |
| 新def实际执行且满足保留规则 | 保存新def；未改旧def继续保留 | 不变 |
| 同名新def实际成功执行 | 替换旧源码 | 不变 |
| 异常发生在同名新def之前 | 旧函数仍为`<retained>`来源，保留旧源码 | 不变 |
| 新def默认值求值失败，尚未覆盖旧绑定 | 保留旧源码 | 不变 |
| 新def执行后发生普通ValueError等 | error消息仍含真实namespace快照；有效新定义可以提交 | 不变 |
| `del f`正常完成 | f删除；依赖f的g也被依赖检查剔除 | 不变，合法空集合不被“救回” |
| `f=7`等重绑定 | 不再是合格函数，剔除f及失效调用链 | 不变 |
| 新同名def引用不可保留的snippet变量 | 新定义被剔除，依赖链连带剔除；不恢复旧版本 | 不变 |
| 硬超时/child丢失，没有快照 | 原版清空所有旧函数 | **保留本次调用之前已提交的集合** |
| timeout前尝试新def、同名替换、删除或import变更 | 无法收集child的最终namespace | 不提交这些尝试；只保留旧集合 |

必须保留“有快照的异常”与“没快照的失败”的区别。简单写成 `if error: restore_old_functions` 会错误回滚已经有效执行的新定义或正常删除，不是本补丁的行为。

保留规则仍包括：只接受可识别的顶层def；不接受装饰器、参数/返回注解、非literal默认值、写global等；外部依赖必须是提供的runtime globals/builtins、合格import或同时保留的函数。依赖检查递归收敛，不能留一个已经失去依赖的wrapper。007没有放宽这些规则。

## 作用域、重置与现有开关

核查到的开关：

- `ARC3_PERSISTENT_FUNCTIONS`：是否启用函数源码保留。
- `ARC3_PERSISTENT_FUNCTIONS_SCOPE`：`turn` / `levelup` / `game`；默认`levelup`，本项目底座配置为`game`。
- `ARC3_PERSISTENT_FUNCTIONS_IMPORTS`：是否把可保留的显式imports与函数源码一起保存；本项目为1。
- `ARC3_PERSISTENT_FUNCTIONS_REPAIR_HINTS`：更具体的拒绝原因/修复说明，不改变硬超时缺键的提交语义。

没有找到现成的“timeout保留上一次快照”开关。把scope换为game也不能解决本缺口，本项目已经用了game。

作用域行为保持如下：

- `turn`：新的非resumption analyzer turn开始时清空；resumption仍算同一turn。
- `levelup`：summary的`level_transition`为真时清空。这个标记来自真实`level_completed`结果，不是简单比较frame.level数字。
- `game`：过关后保留，但原有反馈提醒重新检查关卡假设。
- 同关RESET或game-over本身没有独立清空函数池的分支；它们可能清理world-model文字，但不是同一份状态。若scope=turn，后续新turn仍会按turn规则清空。
- 新ToolAgent本身初始化空池；`_ensure_session`发现runtime目录变化也清空。现有Harness为每游戏建新agent，因此不同游戏不会共用函数池。

007在`_record_retained_functions`处决定是否提交，然后继续原始流程；之后发生的level/session清除仍优先。它不把旧函数集合越过边界恢复回来。

## 实现边界与诊断

新增 [`src/arc3_research/program_state.py`](../src/arc3_research/program_state.py)：

- `install_program_state(enabled=...)`，幂等安装，baseline disabled直接调用原方法。
- 薄包装`_run_python_tool`仅提供本次state_path/run_ref诊断上下文，finally恢复；不额外读取帧或执行代码。
- 包装`_record_retained_functions`，仅拦截缺键且原持久化已启用的路径。不修改现有集合对象，不合并未确认的新定义，不新增全局变量持久化。
- 使用既有`function_retention`反馈字段，明确没有收到快照、旧函数/import集合保留、本次失败调用的新定义/替换/删除未保存、已执行游戏动作不回滚、正常scope规则仍适用。
- 诊断记录missing snapshot次数、保留非空集合次数/函数数、present snapshot透传次数，以及对应state_path/run_ref、scope、旧函数名、sandbox错误、执行过的action calls、末action号/level与终局反馈。

[`run_arm.py`](../src/arc3_research/run_arm.py)已加入`program_state` arm、源码hash和最终`program-state.json`。没有改serving、调度、deadline、model或其他策略；没有构建/修改Notebook。

**第一版有意只处理缺键。** 若child的collector自己出错，会返回显式`keepable_functions=[]`加`retention_rejected: all`；若host收到格式错误的快照，原方法也可能清空。007仍遵循原版，不按错误文字猜测快照有效性。这些不是本轮已修复范围；若以后要区分，应让协议明确携带snapshot状态，而不是扩大为“所有error都保留”。

## CPU手动核对

使用现有 `/private/tmp/arc3-data-inspection-venv/bin/python`，真实底座`run_sandboxed_python`以及`ToolAgent._dispatch_tool`，timeout缩短到1秒，只运行人工写的纯函数片段；没有模型调用、游戏动作或日志轨迹代码。

1. **原版缺口复现：** 保留f/g后，定义h并进入短超时循环；返回缺少`keepable_functions`，原 `_record_retained_functions`清空f/g。
2. **补丁恢复：** 正常保存f/g及math import；失败调用尝试替换f、新增h与snippet变量后超时，原源码集合逐项保持不变。下一次新sandbox调用`g(2.9)`仍输出6，math import可用，而snippet变量不存在。
3. **合法空集合：** 正常`del f`后，f与依赖它的g都删除，池为空；007不复活它们。
4. **普通异常有效快照：** 新ok定义后抛ValueError，仍提交有效定义；下一调用`ok(1)`输出9。
5. **旧绑定行为：** 异常先于替换、或替换默认值求值失败，原版已经能保留旧函数；新定义引用不可用变量时仍剔除失效调用链。
6. **作用域元数据检查：** 使用人工构造的summary调用原边界处理，同关RESET不清空，levelup过关清空，game跨关保留，新session清空。这里没有真的执行游戏RESET。
7. **关闭补丁：** disabled后同样的硬超时恢复原版清空行为，工具dispatch的动作/进展标志未被改写。
8. `run_arm --help`已识别新增arm；没有启动runner模型实验。

这些检查证明的是源码集合/协议行为，不是游戏成绩。手动命令输出留在本次对话工具记录，未创建测试文件。

## 风险与后续研究条件

- 超时期间游戏动作可能已经执行并被host记录；函数状态保留不是环境事务，绝不能重放snippet或撤销真实动作。旧函数在新棋盘上仍可能有不适用的坐标/编码假设。
- 失败调用可能先删除或替换函数、再使用新函数执行动作，最后才超时。无快照时无法确认最终namespace；007选择回到最后提交的源码集合，工具反馈必须明确这一点，不能声称失败调用的新定义已保存。
- “代码仍在”并不证明旧表示正确。g5c/sig的具体编码一致性、re86的bbox中心假设，是更高层的表示问题；007只减少无必要的代码丢失与重建机会。
- 保存全部旧函数可能继续保留已经错误的旧逻辑，这是原game-scope本来就有的风险。成功重定义/删除以及正常有效异常快照仍应替换它们，不能一直钉死旧版本。
- 本轮没有把该机制当作006所有负例的解释。后续若有GPU实验，应使用包含真实timeout病例和成功代码复用对照的固定池、相同预算与两组共同运行条件；先看恢复触发、是否减少重建与表示漂移，再看真实关卡覆盖，不直接声称能提升分数。
