# 019 实际 wheel 审计与 CPU v2 修复

审计日期：2026-10-19。只读取实际下载的 wheel ZIP 和保存的上游源码，没有安装/执行该 Linux CUDA 包。

实际附件为 `dfranzen/pennyroyal-v253` 中的 `sglang-0.5.19+gd00d88efc8d6-cp312-cp312-linux_x86_64.whl`，24,833,268 bytes，SHA256 `d0620216732b82b6efd4f8a78cc9b5f55343a4d3837fdfa3bcbb841b7718a225`。完整证据在 `experiments/019-actual-wheel-audit.json`，解出的源码和两个 unified diff 在 `research/019-actual-wheel/`。原 `research/notebooks/2026-10-18/fp8-ple/pennyroyal/` 上游文件保持原样。

原审计基于上游 revision `d00d88efc8d6281b12be4f4073126aec95038c55`；wheel 名称中的同一 commit 后缀不能证明包里每个文件与该 revision 一致。四个指定文件中：

| 文件 | 实际结果 |
|---|---|
| `sglang/srt/models/qwen4_exp.py` | 与原上游逐字相同，SHA256 `35a1785ce4c287821f00f1518b3880ab6838ef58d42fd51ece86d8098b2ed666` |
| `sglang/kernels/ops/qwen4_ple.py` | 与原上游逐字相同，SHA256 `7f64e896c1f00f46ab6c4cd8c5c90cedc528555d1cc7401e9c7a5a3a31b87f16` |
| `sglang/srt/environ.py` | 多出 one-shard lookahead 和 SM120 low-M BF16 GEMM 两个默认 True 开关；实际 SHA256 `7431c4e0e679d1983ade2c3d9a8689c0ac78666d166d6743188434f2f25c5ed1` |
| `sglang/srt/model_loader/loader.py` | 接入 lookahead，要求 standard safetensors mmap 并设 serial consumer；实际 SHA256 `d12e619c9a334f1af61d79d1958c59554e0931986da4942b1f570562d0752bb1` |

进一步只读检查了 wheel 内 `startup_weight_load.py:478`、`weight_utils.py:1182` 和 `unquant.py:243`。lookahead 会延后独立全 checkpoint 预取，由迭代器最多提前一个 shard；实际 tensor 仍通过 `safe_open(..., device='cpu')` / `get_tensor(name)` 返回。这项改动影响 I/O 和缓存时序，静态差异没有新增权重转换。SM120 小矩阵路径要求 CUDA、计算能力恰为 `(12,0)`、关闭 deterministic inference；它是 BF16 GEMM 分支，不是开启 online FP8。原 009/019 launcher 已显式设置 `SGLANG_ENABLE_SM120_LOWM_BF16_GEMM=1`，三个 phase 保持相同设置。没有由此宣称浮点结果严格等价；数值和性能仍由实际 microbench 观测。

修复保留原重量契约中的来源摘要，将 `runtime.revision` 改名为 `upstream_reference_revision`，另存实际 wheel 身份。builder 从本次审计读取实际四文件摘要，将审计 JSON 一同打包；`ple_session` 先检查整体 wheel SHA256 和四文件，再运行有界 CPU 权重审计。GPU launcher 继续检查安装后的四文件。没有忽略差异或关闭校验。

顺手修复分析器三个范围明确的问题：失败 phase 的 `quality10=None` 不再崩溃；CPU complete 必须有两个已通过的实际审计文件且未启动 GPU；格式/截断新增失败按同一 case 和失败类别逐项对照两次 BF16，不能用不同 case 或不同类别的失败抵消。原 10% 吞吐和 BF16 漂移判定未改变。这些是既有语义的修正，不增加新的研究晋级标准。

本地准备报告和远端 CPU v2 上传/身份/版本记录写入 `experiments/019-preparation/cpu-v2/`。CPU 成功只证明挂载与权重契约可执行；没有 GPU 吞吐或解题质量结论。GPU Notebook 仅重建，不由本支线启动。
