# 030 关内持久 Python 独立能力候选

2026-10-20。状态：**真实CPU sandbox演示已通过，GPU全25题对照v2已启动，尚无提分结论。** 此候选独立接009，不能与029程序修复叠加。它不新增模型工具，模型仍照常调用同一个 `python` 工具。

## 解决的故障

009每次工具调用启动新解释器，只传递安全顶层函数；普通变量、导入、搜索队列和已算路径会丢失。030为每个agent的当前关卡保留一个解释器，使模型已有的计算进度可直接复用。换关、换游戏、工具超时、会话结束时清理。它与015有限字面量值缓存的区别是保留真实Python对象与计算进程，模型无需调用保存API。

实现源自[Heliosli v6](https://www.kaggle.com/code/heliosli/try-merging-it-you-might-get-lucky-and-win-gold)的公开worker；已保存[原模块](../../notebooks/2026-10-20/heliosli__try-merging-it-you-might-get-lucky-and-win-gold/persistent_python.py)和[原接入脚本](../../notebooks/2026-10-20/heliosli__try-merging-it-you-might-get-lucky-and-win-gold/patch_persistent_python.py)。上游Notebook hash为 `210f3f4dd1d50d5aa3da5cd597b0f74891f449c26b67b56dacff106e81f456e5`。本地模块保留来源说明，用可卸载wrapper接入，不改写runtime原文件。

## 最小接入

[persistent_python.py](../../../src/arc3_research/persistent_python.py)提供 `install_persistent_python()`，返回 `snapshot()`／`uninstall()`。

| 接入位置 | 作用 |
|---|---|
| `ToolAgent._run_python_tool`与模块内`run_sandboxed_python` | 线程局部绑定当前agent，将原调用路由到该agent／该关worker |
| 原sandbox bootstrap | 保留模型globals；每次工具调用仍重建runtime frame、history、action和animation回调，每次真实动作继续刷新观察 |
| 函数保留上下文与工具输出 | 继续维护原跨关安全函数池；关内显示真实保留的名称，避免错误宣称依赖普通变量的函数已消失 |
| 同一python工具说明及系统提示 | 说明关内持久、换关和超时清理、缓存画面必须核对；没有新增工具API或额外模型请求 |
| `_HarnessGameSession.play`的finally | 会话结束关闭worker；卸载也关闭剩余worker |

原逐次CPU累计限制不能直接套在长期解释器上；实现保留每工具调用的原宿主墙钟超时，改为申请1GiB解释器地址空间上限。模型允许导入的模块与内置名称保持原限制。action/animation仍经原宿主IPC，真实动作和计分不转到worker内部。

## 已运行的一次演示

[sandbox-demo.json](../../../experiments/030-persistent-python/sandbox-demo.json)记录一套连续的真实 `ToolAgent._run_python_tool`／子进程sandbox调用，无模型请求。环境动作回调是确定性的宿主状态更新器，用来隔离验证执行语义，未冒充游戏得分实验。

- 第一调用创建普通list和math导入；第二调用直接使用它们，并执行LEFT后立即读到更新的frame／history。
- 第三调用仍读到原list，同时执行新绑定的RIGHT回调；两个回调标签不同，证明没有继续调用上次工具的旧callback。
- 更换level后旧list不存在；1秒工具超时后新list也不存在，状态丢失被明确写进工具结果。
- 卸载后活动worker为0；最终演示约1.10秒，GPU和模型调用均为0。

实现中已纠正超时结果缺少`live_name_count`导致工具输出未带`python_state.lost`的问题。没有新增测试套件，也没有扩大到随机环境或模型跑分。

## 独立研究与正式封装

root负责研究runner与A/B配置；正式候选使用[build_030_submission.py](../../../scripts/build/build_030_submission.py)及[030-persistent-submission.json](../../../experiments/030-persistent-submission.json)，owner为zhuating。只打包本模块和空包初始化文件，不带program_repair、request_deadline、观察通道或新调度。保留009模型、服务、动态gateway、31920秒solver、9小时Notebook及原save smoke。

下一次模型运行应观察普通变量／搜索队列是否真实跨调用被再次使用、重建调用是否减少，以及是否增加关卡深度和净分。持久的缓存也可能保留错误假设或旧画面，因此“变量存活”不能替代解题收益。记录worker状态丢失、CPU耗时和内存；出现正常游戏阻塞或反复超时便停用本版，不扩展成通用持久化框架。

## GPU执行

`zhuating/arc3-030-capability-comparison` v1首次启动的185GB预读耗时1047.52秒，未在1200秒启动分配内ready，因此退出；没有求解臂或分数。等待时发现清理wrapper未保留Session.play签名，已用标准functools.wraps修正，一次实际CPU hook组合安装／卸载通过，不改变求解机制。

v2将启动等待改为1800秒，两臂仍各7254秒、全25题、10路并发、无额外程序修复。Notebook SHA256为 `265ed9a9b84f118190a4262b96f85c6204be031de613f64a6fd4ca755ab8a994`，冻结源码位于 `experiments/030-capability-source-v2/`，已确认单张97887MiB RTX PRO6000。结果必须以本版本原件为准；[启动记录](../../../experiments/030-capability-launch.json)与[v1记录](../../../experiments/030-capability-launch-v1.json)分开保存。
