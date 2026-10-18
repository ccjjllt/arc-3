# 019 FP8 PLE：权重与数值合同

2026-10-18，最后固定公开 header 核对时间 10:30 UTC。当前完成的是 CPU 合同及合成数据验证；**尚未验证 Kaggle 镜像实际样本，也没有本机 GPU 速度或模型质量结果**。机器合同为 [019-weight-contract.json](../experiments/019-weight-contract.json)，执行模块为 [ple_weights.py](../src/arc3_research/ple_weights.py)。

这项实验可保持 AutoRound target、独立 drafter、KV/Mamba、上下文、并发、采样、缓存和调度不变，单独比较 PLE 的 BF16 与 FP8 存储/数值。它不是无损优化；更小的 host 表和一次抽查通过，都不保证推理更快或答案质量不变。

## 来源与同作业输入

| 角色 | 固定 Kaggle model source | 本地目录 |
|---|---|---|
| BF16 target | `dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1`（native version 1007514） | `/kaggle/input/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1` |
| FP8 target | `dfranzen/albucino-qwen3.8-flash-next-w4a16-fp8ple/Transformers/default/1`（native version 1026228） | `/kaggle/input/models/dfranzen/albucino-qwen3.8-flash-next-w4a16-fp8ple/transformers/default/1` |
| 独立 MTP | `dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1` | `/kaggle/input/models/dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1` |

三者可作为同一个 Notebook 的三个 `model_sources` 声明，抽查读取只读挂载文件，不需要先下载数百 GB 到用户电脑。挂载是否实际可用、路径是否唯一、文件是否齐全，仍须在作业的 CPU 阶段证实；这里不承诺平台输入容量或账户权限。服务应顺序加载两种 target，避免同时保留两份 host table 和两套 GPU 权重。

现有离线资料的 HF target revision 分别是 Intel `4c67bf686b7f7fd386bae6b07ab59e8ff1d5b897` 和 Albucino `c6af9fee7ad2cb8ef44b534a99b8c1b81fb0f6da`。Albucino 的 `hybrid_sources.json` 声明非 PLE target 组装源为 Intel `861536dda5bcb208376fc4cd879b2bf76bece9fe`，FP8 PLE 为 RadixArk `7b719225242aacd3dbd3f9407468c2ee9a9d2594`。这些 assembly revision 与此次读取的仓库 revision 是不同字段，不能混写。

递归 config 比较只有 `text_config.ple_embedding_dtype="float8_e4m3fn"` 一处差异。15 个非 PLE 文件的 HF LFS SHA256 一致，合计 73,581,002,608 bytes；这仍是上游元数据证据，不是本地重算全部文件，也不是 Kaggle 镜像完整性证明。FP8 target 少了 1,565 个 `mtp.*` 键；019 使用同一独立 INT4/group32 drafter，不能悄悄改用 target 自带 MTP。

**物理分片不能从 HF index 搬到 Kaggle。** Intel HF index 的 128 个 PLE 键指向单个 `model-00016-of-00017.safetensors`；Kaggle 镜像已改成 22 个 `model-ple-*.safetensors`。FP8 镜像为 10 个 `model-plefp8-*.safetensors`。模块从每个挂载目录自己的 index 解析，再验证所有 header 与 index 映射一致。不要硬编码文件序号来寻找 shard，也不要把 shard 的字典序当数值行序。

## 已读取的真实 header 与 scale

本轮对上述固定 HF revision 执行严格 HTTP Range：先读 8 字节长度，再读有限的 JSON header；只接受精确 `206/Content-Range`，未下载权重主体。读取了全部 10 个 FP8 PLE header、1 个 Intel BF16 PLE header，以及 2 个 scale payload 字节。header SHA256 和公开源文件 SHA256 保存在机器合同中。此前的 metadata-only 状态不能冒充已读 scale；这里新增了实际 scale 字节证据，但 Kaggle 值仍待核对。

| 项目 | 实测合同 |
|---|---|
| 权重键 | `model.language_model.layers.1.ple.ple_embedding.ngram_embedding.shard_{0..127}.weight` |
| 每个 shard shape | `[2500012, 160]`；128 个均相同 |
| 总行数 / 元素 | 320,001,536 / 51,200,245,760 |
| BF16 / FP8 header dtype | `BF16` / `F8_E4M3`（PyTorch `float8_e4m3fn`） |
| scale 键 | 同前缀的 `weight_scale`，在 `model-plefp8-00009.safetensors` |
| scale dtype / shape / 原字节 | `BF16` / `[1]` / little-endian `51 39` |
| scale 精确值 | **0.00019931793212890625** |
| 数值语义 | **`BF16(FP8_value × BF16_scale)`**，整表一个直接乘法 scale |

FP8 E4M3FN 的 `0x7f/0xff` 为 NaN；最大有限绝对值是 448。按本 scale，相乘后、最终 BF16 舍入前的最大绝对值为 0.08929443359375。模块实现了标准库 E4M3FN 解码、BF16 位级解码及 round-to-nearest-even 重建，不导入 torch。

128 个 BF16 表张量 payload 为 102,400,491,520 bytes，FP8 为 51,200,245,760 bytes（另加 2 字节 scale）。这减少的是约 47.68 GiB **host 表**，不是释放同等显存。Kaggle 整个模型输入目录的差额还包含省略的 MTP 等文件，不能全算成 PLE 节省。

## Pennyroyal 加载与 kernel 约束

审计源固定为 `jpezzulli/sglang-rtxpro6000@d00d88efc8d6281b12be4f4073126aec95038c55`，与现有 `pennyroyal-v253` 路线匹配；实际安装文件的哈希仍须由 runner 验证。

- [qwen4_exp.py:492](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:492) 在 offload 模式先创建 meta 模板，按 config 分配 BF16/FP8 的 pinned host 表；[第765行](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:765) 使用 mmap 与 `cudaHostRegister`。scale 留在模型设备。
- [第509行](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:509) 初始化 BF16 shape `(1,)` scale，默认值为 1；[第1960行](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:1960) 加载时严格检查 shape 并转换到 BF16，但不检查正值/finite。**缺失 scale 可能保留 1，因此 CPU audit 必须拒绝缺失或错误 scale。**
- [第733行](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:733) 与 [qwen4_ple.py:133](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/kernels/ops/qwen4_ple.py:133) 只 gather 并转 BF16；[第1257行](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:1257) 在调用侧乘 scale。不能把它解释为 inverse scale 或 row/block scale。
- [第2133行](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:2133) 对 offload 后发现 FP8 而初始配置为 BF16 的情况硬报错。反方向 `.to(dtype)` 只是 lossy cast，不会替用户计算正确的量化 scale。019 不允许加载器的自动 downcast 充当对照实验。
- [qwen4_ple.py:209](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/kernels/ops/qwen4_ple.py:209) 的 fused 路径要求 SM120、TP1、FP8 pinned contiguous 表、width160 和特定 4/16 contexts。默认启用不等于每个请求都命中；吞吐收益须实际测量。

## 无整权重下载的抽查协议

[Safetensors 官方文档](https://huggingface.co/docs/safetensors/index)支持 `safe_open(...).get_slice(...)` 局部访问。019 为减少依赖，采用等价的只读字节范围方案：8 字节 little-endian header 长度、JSON `dtype/shape/data_offsets`、再按 `8+header_length+tensor_offset` 用 `os.pread` 取样。输入必须为 C-order 连续标准 safetensors；shape、跨度、文件边界、重叠、重复 JSON/key 和 index/header 不一致均停止。

1. 对两个 target 做 config 等价检查，只允许 FP8 PLE dtype 差异；另与冻结的规范化 config SHA256 比较。tokenizer、tokenizer config、chat template、generation config 必须逐字节相同；tokenizer 还必须匹配现有 FR-Spec 固定哈希。
2. 检查所有 index/header，不载大张量。排除 `mtp.*` 和 PLE 表后，222,587 个 target 键的集合、dtype、shape、字节长度必须相同，并匹配冻结上游 key-set SHA256。确认准确的 128 张表和一个 scale，严格检查源 dtype，避免加载时默默转换。
3. 非 PLE payload 固定分层抽查最多 **96 个张量**：关键键类别、各物理文件、各模型层，再按固定 SHA256 排序填充。每张量取首/中/末各不超过 256 bytes，逐对比较。独立 draft 记录最多 16 个相同方式的样本及 config/index/header 指纹。**不是逐 tensor payload 或全文件 hash 验证。**
4. 每个 PLE shard 取首行、中间行、尾行，加 5 个由 `SHA256(seed|key|counter)` 得到的唯一行。每行完整 width160，不随机只取几个列。两臂共读取 491,520 个 PLE payload 字节，覆盖每臂 1,024 行、163,840 元素。所有 payload 抽样上界约 651,264 bytes，另加 scale；header、index、tokenizer 元数据单独计入每来源 128 MiB 上限。
5. 报告各 shard 的行号及样本 hash；按 FP8×scale 重建后报告全局 NRMSE、最大绝对误差、finite、饱和/零计数及每元素误差边界违反数。同时计算“不乘 scale”和“除 scale”的 NRMSE，帮助定位方向错误。不能仅凭相关性高就称无损。

冻结的工程初筛门为：零 nonfinite，NRMSE ≤ 0.06，且每个抽样元素 `abs(reconstructed−reference) ≤ 0.07×abs(reference)+scale/512`。这是容纳 E4M3 与 BF16 舍入的保守 smoke 阈值，**不是来自任务质量实验的安全保证**。若不通过，停止并检查量化源/scale/样本，不得看完结果再放宽阈值。即使通过，仍要做固定请求有限输出、工具格式、质量、prefill/decode 与 drafter 接受率验证。

## API、超时与验证

`run_weight_audit(bf16_dir, fp8_dir, draft_dir, contract, out)` 接受合同 dict 或文件名，`out` 是 JSON 文件路径；成功返回 `passed=true`，检查失败也尽量写出阶段和错误并返回 `passed=false`。命令行返回码为成功 0 / 失败 1：

```bash
python -m arc3_research.ple_weights \
  --bf16-dir "$BF16_DIR" --fp8-dir "$FP8_DIR" --draft-dir "$DRAFT_DIR" \
  --contract experiments/019-weight-contract.json --output weight-audit.json
```

内部默认 180 秒检查预算，父 runner 以独立子进程 240 秒 timeout 兜底；I/O 调用前后检查预算，但单次挂起的文件系统读取仍需父进程终止。未完成、缺报告或 `passed!=true` 都不得启动服务。CPU 路径不导入 serving 库、不初始化 CUDA、不执行远程代码、不访问游戏机制，也不解 pickle。

已用临时合成 safetensors 手动检查正常样本、错误 scale、非 PLE 样本损坏、FP8 NaN、超界重建误差和缺少 PLE shard；预期通过/失败均一致。合成验证不能替代实际 Kaggle 权重检查。

抽查会触及文件页缓存。随后启动必须标为“抽查后加载”，不能写成未触碰的冷 I/O 测试；不要为了这一标签在共享主机清空全机缓存。保留实际 I/O、elapsed、source hashes、runtime hashes 和顺序；任何加载差额都应与 steady-state prefill/decode 分开报告。
