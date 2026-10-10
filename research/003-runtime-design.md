# 003 — 单次模型加载的公开 paired A/B 运行设计

日期：2026-10-10（Asia/Shanghai）。这是源码核查与运行建议，**没有启动 GPU，没有实际实验成绩**。

## 结论

可以只加载一次 SGLang 模型，在同一 Kaggle GPU session 中依次跑 baseline 和 goal-evidence。推荐 **一个长期存活的 SGLang 进程 + 每个实验组一个新的 CPU Python 子进程**。更换 Python 子进程不会重载模型，调用仍指向 `http://127.0.0.1:8001/v1`。这样自动隔离 Franzen 的进程全局调度器、import-time 环境配置、代理记忆和残留线程，代价远小于重新启动 Notebook。

同一 Python 进程也能实现，但不能简单地 `await bm.run()` 两次：必须分别创建新的 Benchmark，确认前组游戏线程已经停止，重置全局 priority gate，并清理可诊断的全局状态。后文给出精确依据。

首轮推荐 **16 游戏 × A/B、每组 4642 秒**，十个 active streams，总解题时间 154.7 分钟，加一次模型初始化及收尾约 2.8–3 小时；若希望更多启动余量，可改 **12 游戏 × A/B、每组 3482 秒**，总解题时间 116.1 分钟。选择游戏后在启动前写死列表，两个实验组按完全相同顺序运行。诊断游戏和其余覆盖游戏分开报告；这不是全 25 游戏复现，也不能用其均分与作者全 25 游戏均分直接比较。

原版按 110 游戏预算归一化：

```python
n_games = len(game_ids)
active_streams = 10
solver_wall_s = 532 * 60 * n_games // 110
solver.concurrency = n_games       # 所有游戏会话同时打开，包含调度等待
solver.max_runtime_s_per_game = solver_wall_s
os.environ['ARC3_MAX_ACTIVE_STREAMS'] = '10'  # 实际并行模型流
```

最终已采用16游戏，代码 `src/arc3_research/run_arm.py` 支持逗号分隔prefix和JSON文件，逐个解析唯一完整ID；父launcher为 `session_runner.py`。子进程soft deadline精确设为组开始+budget，父进程上限budget+150秒，整体10800秒。

这里 `max_runtime_s_per_game` 包含 priority-gate 等待时间，不能解读为每个游戏独享 77 分钟 GPU。12/16/25 游戏的分组总算力都与原版公式一致；缩小组的调度动态仍有差异，需要记录。

## 已取得的精确源码

公开数据集：<https://www.kaggle.com/datasets/dfranzen/taaf-kaggle-source-bundle-copy>，CLI 下载量 439 KiB。已保存到 `research/runtime-bundle/`，并应用 `research/notebooks/cli-baseline/arc-agi-3-milestone-2-solution.ipynb` 第 2 个 cell 中的 Franzen patch。所有文件成功应用；只有 `inference/framework/run.py` 的两处 hunk 使用 +48 行 offset，其余直接匹配。

关键文件：

- `research/runtime-bundle/src/tufa-arc-agi-framework/src/taaf/benchmark.py`
- `research/runtime-bundle/src/tufa-arc-agi-framework/src/taaf/solver.py`
- `research/runtime-bundle/src/ARC3-Inference/inference/framework/solver.py`
- `research/runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py`

该目录是第三方源码快照与运行调研材料，不是本项目独立算法实现。

## 为什么 server 可以共享

`Benchmark.run`（`taaf/benchmark.py:73`）只将 `runtime_environment=target` 交给 solver，随后调用 played solver 的 `setup`、`run_games`、`teardown`。它**不会执行** `target.teardown_commands`，也不会根据 `target.max_runtime_s` 自动结束当前进程。

Franzen `HarnessSolver._teardown`（`inference/framework/solver.py:1516`）只在 `_local_server_started` 为真时停止 solver 自己启动的模型 server。原 bundle preamble 已记录 `start_local_server=False`；运行时也应明确保留 `False`。Notebook 的 SGLang cell 独立使用 `subprocess.Popen(..., start_new_session=True)`，不归 solver 管理。因此 A 完成不需要停 SGLang；只有整个 A/B job 完成或失败后才关闭它。

`target.max_runtime_s` 可保留 32400 以符合原版 customization 的校验。首轮的三小时配额控制要靠我们自己的 job deadline 和子进程 timeout，而不能依赖这个字段。

## 推荐执行流程

1. 原版离线依赖安装、模型与 draft 只加载一次；保持模型版本、Pennyroyal 配置、十个 active streams、采样参数和上下文策略一致。
2. 公开 OFFLINE 实验必须等待 server ready 后才开始计入 A 的解题预算。原版 12 分钟 startup 后释放 harness 是为比赛首动作时限设计；公开实验若让 A 等模型而 B 不等，会破坏比较。可设一个有上限的就绪等待；失败直接落盘错误并结束，避免耗完数小时配额。
3. 可在 A 前执行极短的通用 warmup，使已有 CUDA 图与常见 batch 工作路径处于 ready 状态；warmup 不包含任何游戏、目标或解法。记录耗时。原版 serving 的 structured-output warmup 与显式 warmup区分记录。
4. 读取 `/get_server_info` 或可用的 server info endpoint、`/metrics`，记录实际版本/config；不要以最新 upstream 的字段名假定 Pennyroyal 一定一致。
5. A 启动前调用 server root `/flush_cache`，成功后启动 baseline CPU 子进程。子进程使用 fresh pickle 和 fresh OFFLINE `GameAPI` 列表。
6. A 自然结束或 deadline 到达后，确认子进程退出、结果落盘、server 没有残留请求。再 flush cache；成功后启动 B 子进程，仅开启 goal-evidence 开关。
7. B 使用相同 game list/order、预算、硬件、模型、API、采样、调度、diagnostics 配置。不要把 A 的节省时间自动加给 B。
8. 两组结束后立即保存 summaries、运行清单、server metrics、GPU utilization；关闭 server，Notebook 结束。无需让 GPU 等待人工分析。

## 子进程中可用的核心调用

以下是调用结构，外层 launcher 可按项目布局包装。环境开关必须在导入 inference 之前设置，尤其是许多 Franzen 常量在 import 时读取。

```python
# group runner: standard Python process; inherited PYTHONPATH points at bundle/src trees
import asyncio
import json
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path

# group_dir, game_ids, env_dir, bundle_dir, solver_wall_s, variant provided by launcher.
# The inherited setup_env should be identical apart from this intervention switch.
os.environ['ARC3_GOAL_EVIDENCE'] = '1' if variant == 'goal_evidence' else '0'
os.environ['ARC3_MAX_ACTIVE_STREAMS'] = '10'
os.environ['RECORDINGS_DIR'] = str(group_dir / 'server_recording')
# Do not use setdefault for per-group paths.

import arc_agi
import taaf.game_api

with open(bundle_dir / 'deploy_target.pkl', 'rb') as f:
    target = pickle.load(f)
target.actual_run_as_submission = False
target.is_competition_rerun = False
with open(bundle_dir / 'benchmark_initial.pkl', 'rb') as f:
    bm = pickle.load(f)

bm.job_dir = group_dir
bm.label = variant
bm.n_passes = 1
bm.game_weights = None
bm.solver.start_local_server = False
bm.solver.concurrency = len(game_ids)
bm.solver.max_runtime_s_per_game = solver_wall_s
bm.solver.max_actions_per_game = None
bm.solver.max_generated_tokens_per_game = None
bm.solver.analyzer_timeout = 900.0
bm.solver.save_request_logs = True
bm.solver.cancel_drain_timeout_s = 120.0
spec = taaf.game_api.ArcadeSpec(
    operation_mode=arc_agi.OperationMode.OFFLINE,
    environments_dir=env_dir,
)
bm.games = [taaf.game_api.GameAPI(env_name=g, arcade_spec=spec) for g in game_ids]

# One timer for every group, started immediately before benchmark execution.
# Group deadline also limits late-started sessions to the same group window.
async def main():
    import signal
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGUSR1, bm.request_stop)
    soft_end = datetime.now() + timedelta(seconds=solver_wall_s)
    await bm.run(
        soft_end_time=soft_end,
        runtime_environment=target,
        minimal_diagnostics=False,
    )

asyncio.run(main())
```

`ARC3_GOAL_EVIDENCE` 在这里仅示意项目开关名，必须与实际 intervention 模块统一。如果模块是 monkeypatch，baseline 完全不安装；B 在 fresh process 安装一次即可。

父进程的每组 timeout 应覆盖 `solver_wall_s + 120 + 少量文件收尾`；最终采用 `solver_wall_s + 150`。到期先 SIGUSR1 请求 TAAF 正常保存；若此前 soft deadline 已触发，则不要反复 cancel teardown。额外有限宽限后终止子进程，记录 `hard_timeout`。不要在 A 子进程尚未退出时启动 B。整体 timeout 要保留一次初始化和两次 drain 的余量；最终停止仍以约三小时整机预算为约束。

## 取消行为与容易漏掉的状态

- `Benchmark.run` 在入口会 deepcopy pristine solver/games，再运行 played copies。所以 Solver one-shot assertions本身可通过 pristine snapshot绕开，但 `Benchmark.game_runs` 是追加式、`_deadline_fired` 不在入口重置，仍应 fresh unpickle 每一组。
- `HarnessSolver._run_games` 为所有游戏建线程任务；发生 `CancelledError` 后设置 `_stop_event`，最多 drain 120 秒，再 `finish_game`。`_teardown` 使用 `_worker_pool.shutdown(wait=False)`，**返回不代表所有 Python 线程已经退出**。
- `_PriorityGate` 的 `_clock_start/_clock_deadline` 取本进程所有 session 中最早值。在 A 后直接启动 B 会继承 A 的过期 deadline，导致 B 从 tail-fade末尾起跑。fresh process 自动解决。
- priority gate 等待用 `threading.Condition.wait()`，无独立超时；只能依赖持有者退出/release唤醒。所以强制取消后同进程重置 gate 必须先确认旧线程完全停止。
- `HarnessGameSession.started_at` 在 gate.acquire 之前生成；预算含排队。
- `request_timeout_seconds()` 会取 analyzer_timeout、每游戏剩余时间、soft deadline剩余时间的最小值。正常运行尾部 HTTP 请求通常不会再占完整 900 秒。
- `Benchmark.run` 会吞下 solver 的普通 Exception，然后标记 surviving games 为 crashed。**父进程 exit code=0不等于实验有效**；人工读取 benchmark中的状态、完成数和solver_note，特别是 endpoint failed次数。
- 每组有独立 `RunSession`，Arcade/scorecard缓存属于该 session；`session.close()` 执行，不需要人为复用引擎。

如果最终仍用 Notebook 同一 Python 进程，前一组完成并确认所有 `harness-game*` 线程都已退出后，可执行：

```python
import threading
from inference.agent import tool_agent
live = [t.name for t in threading.enumerate()
        if t.name.startswith('harness-game') and t.is_alive()]
if live:
    raise RuntimeError(f'Previous group is not drained: {live}')
with tool_agent._PRIORITY_GATE_LOCK:
    tool_agent._PRIORITY_GATE = None
for key in tool_agent._GATE_STATS:
    tool_agent._GATE_STATS[key] = 0
with tool_agent._DIAG_LOCK:
    tool_agent._DIAG_STATE.clear()
    tool_agent._DIAG_LAST[0] = 0.0
```

随后重新 unpickle bm，设置新的 job_dir与flags。import-time配置不能靠改os.environ更新，需要 intervention 使用调用时开关，或提前保存并显式恢复patch。

## 冷 cache 与公平边界

Upstream SGLang 官方 benchmark 文档指定 `--flush-cache` 在 warmup 后调用 `/flush_cache`；所以 A/B 两组开始前均 flush，而不是关闭 prefix caching。关闭缓存会改变原版算法的吞吐与调度。

参考：<https://docs.sglang.ai/developer_guide/bench_serving>，<https://github.com/sgl-project/sglang/blob/main/docs/docs/developer_guide/bench_serving.mdx>。本项目实际使用 Pennyroyal pinned wheel，仍应记录运行时 endpoint 返回，不宣称仅根据 upstream 已完成验证。

建议 `POST http://127.0.0.1:8001/flush_cache`。最终父launcher在接口不可用或非2xx时记录限制并继续，避免重载模型；这时本轮不能宣称冷cache公平，必须把warm-cache影响作为条件比较限制。若存在残留生成请求，可先有限等待再重试。不得无声忽略失败。

冷 cache 只指请求相关 KV/prefix/multimodal可清理缓存，不包括已经编译的 CUDA kernels和操作系统文件cache；共享编译结果正是节省加载开销的方法。A先跑仍可能有少量编译/温度/采样顺序效应，因此本轮是低成本方向筛选。有效果后另一个session反转B/A顺序验证；不要把单次12/16游戏paired结果称为稳定提升。

固定随机种子可减少部分噪声，但多线程、sampling GPU stream、服务器调度和环境种子的影响需要如实记录，不宣称固定一个 Python seed 后完全可复现。

## 建议落盘

```text
/kaggle/working/
  run_manifest.json       # source hash, game IDs/order, exact configs, runtime accounting
  server.log
  gpu_metrics.csv        # 每30秒utilization.gpu, memory.used, power.draw等
  metrics_before_A.txt
  metrics_after_A.txt
  metrics_before_B.txt
  metrics_after_B.txt
  A_baseline/
    runner.log
    benchmark.json
    artifacts/
    transcripts/
    solver_analysis/
    diagnostics.html
  B_goal_evidence/
    ...
  paired_summary.json
  submission.parquet     # 仅满足offline Notebook产物约定的dummy，不提交比赛
```

原版 notebook 把 `PREFIX` 依赖环境放在 `/kaggle/working`，容易把大venv纳入输出；可以保留逻辑但将运行依赖目录放到非working的scratch路径，把server log明确放working。在不改serving实现的前提下，这是降低产物体积和收尾时间的有效方法。

人工检查即可，不需要写任何测试文件：开始时确认确实10 active streams、游戏数量和两组预算一致；结束时检查每组benchmark非空且每游戏都有final状态，汇总failed/crashed/timeout，保存首个未解关轨迹。代码完成与研究成效分开记录。

## 已完成的本地人工配置核查

`src/arc3_research/run_arm.py` 已实现。2026-10-10在临时Python3.12环境，用真实patched bundle完成：两种arm入口、实际pickle恢复、16个prefix唯一匹配到完整ID、solver deepcopy与setup/teardown、真实ToolAgent构造、goal patch开关、soft deadline参数、metadata和goal-evidence输出。为避免任何模型请求，本次仅在内存把`Benchmark.run`替换为配置检查coroutine；未运行游戏动作，未启动GPU，不能当作效果实验。没有创建测试文件。

最终16游戏顺序：`sk48,lf52,bp35,wa30,g50t,sc25,ls20,su15,tn36,m0r0,cd82,tu93,ar25,lp85,ft09,r11l`。

父launcher需要：安装包的`src`进入PYTHONPATH，继承Notebook baseline setup_env，模型已ready；每arm输出单独目录；完成后检查`arm-metadata.json`中的`game_state_counts`、`game_results`及`forced_cpu_process_exit`。CPU runner强退不会停止共享SGLang，下一arm的cache flush结果仍需记录。
