# 025/026 最小输入清单（2026-10-20，30 分钟项）

远程可直接读（Git 内）：`experiments/026-fork-inputs.json`、`experiments/026-fork-conv.json.gz.b64`、
`experiments/026-repair-cpu/`（四前缀 fork 态 + replay-fidelity）、`experiments/025-admission-cpu/admission-recompute.json`、
`scripts/analyze_025_admission.py`（重算即文档）。

仅原机本地（`runs/` 被 gitignore，不进 Git；大请求日志不搬）。位置：本仓库同级 `runs/`，机器 zhaohuaxiang 原工作机：

| 路径 | bytes | sha256 |
|---|---|---|
| runs/014-tail-allocation/baseline/scheduler-observer.json | 2343237 | 88419895…6ab5d31 |
| runs/014-tail-allocation/baseline/arm-metadata.json | 21063 | df3c258e…1adf24e |
| runs/016-pace-allocation-jiyujia/baseline/scheduler-observer.json | 2186958 | ef2aa888…4900fd |
| runs/016-pace-allocation-jiyujia/baseline/arm-metadata.json | 20988 | 643a7404…31a69 |
| runs/015-native-adoption/baseline/ft09-0d8bbf25_p0_requests.jsonl | 16657419 | f45c36b4…e66 |
| runs/015-native-adoption/baseline/benchmark.json | 132460 | 5562452e…24e |

（全哈希见 git log 本文件；此处为前缀，正文以 `sha256sum` 全串为准。）

完整 sha256：
- 88419895490c1edaf350f50bc12c82b47af9e13533f7ee264727e253f6ab5d31
- df3c258e477ffc0d30e381c3f689fb0a3ec16b6242a827592f4b802822a965e1
- ef2aa888474ff81dc4dd55b6bf1e9fdd21a5dad184f9c9cde7040ffbba4900fd
- 643a7404015b0d118c5150c036de255c412e24993f9d78285d0e7981f1e31a69
- f45c36b4bc9b6554cb32a8cc6dc8dc5495183a23439963231764de301f393e66
- 5562452e00a5ae551e0a62b1af642bf1a1a365889ab5eacb7dcae2f6e1adf24e

repositories：`research/runtime-bundle` git submodule 指针即源码版本；底座行号引用以 `arc3-026-failure-repair` v3 构建时补丁为准。
不需要重跑任何历史实验：下一次计划内基线运行时附带记录新规则“本来会选谁”即可完成筛查。
