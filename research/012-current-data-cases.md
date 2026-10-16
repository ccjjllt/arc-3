# 012 current_data：两份保存公开帧的 CPU 实用探针

2026-10-13。两例均通过原 ToolAgent → Python sandbox → session callback 的真实数据通道：第一段从当前帧程序计算并 `put(..., at=binding_before)`；第二段 `get` 后直接消费原值。baseline 重算结果、candidate 计算结果、宿主提交确认 hash、candidate 读回值 hash 四者相等。比较清单见 [`comparison.json`](../experiments/012-current-data/check-cases/comparison.json)，最终报告为 [baseline](../experiments/012-current-data/check-cases/cpu-20261013T083209Z-baseline/report.json) 与 [candidate](../experiments/012-current-data/check-cases/cpu-20261013T083813Z-candidate/report.json)。冻结 `current_data.py` 的 SHA256 为 `0d6f825d65cb091203e590cc6777d402f5cf1a6fa5cdd3b92f3d0c5f29f05c4c`。这仅证明跨 snippet 数据交接保真，未证明模型采用、避免原轨迹错误或提高成绩。

## 来源与手写探针

所有坐标均为零起点。输入是历史公开事件的 settled board，未读取游戏引擎或隐藏状态，未执行历史 requests 中的代码。

| 案例 | 原始公开事件 | 程序测量与第二段消费 |
| --- | --- | --- |
| 009 cd82 action 21 / L1 | [`cd82-fb555c5d_p0_events.jsonl:33`](../runs/009-v2-smoke/artifacts/cd82-fb555c5d_p0_events.jsonl#L33) | 对历史诊断区域 rows `[18,62)` 扫描 ASCII `g`，由实际像素算出 30 个前景像素，包含端点的 bbox `[45,25,53,38]`。第二段仅用读回 bbox/pixel_count 算出高 9、宽 14、填充率 `30/126`。 |
| 010 ft09 action 11 / L3 | [`ft09-0d8bbf25_p0_events.jsonl:16`](../runs/010-retrievable-animation/retrievable_animation/artifacts/ft09-0d8bbf25_p0_events.jsonl#L16) | 从现有 segmentation 推断出现最多的实心方块尺寸，再推断行列起点；选其中最上方非背景混色块。实际推得 6 像素格、列起点 `[12,20,28,36,44]`、目标像素起点 `[12,28]`、逻辑行列 `[1,2]`。第二段直接读逻辑列并用同一份行列表索引回像素，round trip 相等。 |

cd82 输入文件 SHA256：`0062ff7be33dcb4d02252e75f6a087b05b0b1a43b8261535e10d1851c3d7de7c`；规范 grid JSON hash：`4c99f21295c646fdf16f337a52bdb9e9258ff7f0fb2fde7e55f03a60804a3509`。

ft09 输入文件 SHA256：`20a69817baef6fc6b9116083bf6ac7d12c9868657fcc2bb82cb4889ea6065753`；规范 grid JSON hash：`12b42753f4af6b72d9c9a52328e95a0763295ab1ae414c9039266e3edfb00608`。

每次执行都核对原文件 hash、原事件 board 与复制 grid 逐值相等、action/level 一致。两例 [`compute.py`](../experiments/012-current-data/check-cases/cd82/compute.py) / [`compute.py`](../experiments/012-current-data/check-cases/ft09/compute.py) 为手写诊断提取器；cd82 的历史 ROI/颜色选择及 ft09 的格点假设仅用于本次探针，没有进入 agent、runner 或提交 Notebook。第二段 [`cd82/consume.py`](../experiments/012-current-data/check-cases/cd82/consume.py) / [`ft09/consume.py`](../experiments/012-current-data/check-cases/ft09/consume.py) 不含测量结果字面量，也不重新提取像素。

## 对照与证据

两臂使用独立 Python 进程。baseline 第二段访问普通 `measurement` 触发 `NameError`，但已有 retained pure function 能重新计算且逐值相等。current_data 没有带来新的视觉信息；它补的是“已算出的 JSON 值”跨 snippet 的直接交接接口，避免必须由模型重新抄写或调用纯函数重算。

candidate 在计算前获取 `current_data.context()['context']`，将其作为 `at` 传给 `put`；两例均收到 `stored`，第二段均为 `current`。共同 value hash 为：

| 案例 | baseline compute = candidate compute = host ack = candidate get |
| --- | --- |
| cd82 | `d42401958c570a3d7bf268591f81c5da5d3ae205e4145f5b263abcfbb95dd378` |
| ft09 | `5c86cd8207475ca304805e4c7a75e715a81eb84b8d6b26a63b9dee7118a4c288` |

候选四次 snippet 均返回成功；原 runtime-state 文件不变，`step_executed=false`，生成 token 为 0；HTTP 与 action 入口拦截计数均为 0。候选两例合计 6 次 context/put/get 查询，2 次宿主提交、2 次成功读取，共存储 335 字节规范 JSON。最终报告记录宿主 query CPU 时间；它不包含完整 Python sandbox 启动与计算开销，不能用作模型节省算力的估计。

每个输出目录保存完整手写执行代码、原 dispatch 输出和状态文件 hash。`report.json` 记录原 ToolAgent/sandbox/solver、current_data、输入帧、探针源码及所有 trace 的 SHA256；`comparison.json` 对这些 hash 做了再次核对。历史首次检查输出保留，最终有效两臂以 comparison 指向为准。

## 可复算范围

入口为 [`run_cases.py`](../experiments/012-current-data/check-cases/run_cases.py)，`--arm baseline` 或 `--arm candidate`。本机离线复算使用已有 Python、SDK 和依赖：

```sh
/Users/zhaohuaxiang/ccjjllt/binance-quant/.venv/bin/python \
  experiments/012-current-data/check-cases/run_cases.py \
  --arm candidate --sdk-path /private/tmp/arc3-010-sdk \
  --extra-python-path /Users/zhaohuaxiang/ccjjllt/quant-research-lab/.venv/lib/python3.13/site-packages \
  --extra-python-path /Users/zhaohuaxiang/.cache/uv/archive-v0/0NYjaDD0X1HZ1p_3 \
  --extra-python-path /Users/zhaohuaxiang/.cache/uv/archive-v0/GCIcB4ohHyKQ4LxX/lib/python3.13/site-packages
```

session 的 game carrier 为人工创建，仅装入对应公开帧及 action/level 标记；没有恢复旧运行、启动 SDK 游戏或补造完整游戏历史。数据交接经过真实 sandbox IPC，但两例没有执行动作，因此不验证 no-op/RESET/跨关失效、容量淘汰或生产并发。这些属于独立合同检查。`written_at` 只能证明提交时观察绑定，不能证明值的来源或正确性；此处来源正确性由手写计算及源帧核对另行建立。探针无法证明模型会使用接口，也无法阻止模型再次错误重写坐标、绕过缓存或形成错误机制假设。
