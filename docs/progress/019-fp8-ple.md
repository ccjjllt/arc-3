# 019 — FP8 PLE 实现与验证进展

2026-10-18。**实现与本地CPU检查已完成；jiyujia CPU-only实际权重预检已提交，GPU microbench尚未启动。** 当前运行状态以[CPU启动记录](../../experiments/019-preparation/cpu-launch.json)及后续远端状态为准。正式009保持原样，没有创建比赛提交。

## 已实现

- [ple_weights.py](../../src/arc3_research/ple_weights.py)：纯标准库解析safetensors header及范围读取，核config/tokenizer/template、222587个非PLE键、分层小样本、128×8行PLE及BF16全局scale。180秒内部、240秒父进程硬边界，逻辑payload约651KB，不载整张量、不导torch。
- [ple_microbench.py](../../src/arc3_research/ple_microbench.py)：冻结10个真实公开请求与10个合成精确工具题，三阶段各34次请求；1/10并发、冷/热cache、流式时间、usage、speculation与服务指标。HTTP仅loopback，绝对deadline，保存全部原件；不执行生成代码。
- [ple_session.py](../../src/arc3_research/ple_session.py)：先CPU合同，再顺序BF16a/FP8/BF16b；不同目标之外服务参数一致，来源hash校验、显式seed、独立进程组清理、hard watchdog、GPU及主机内存采样。失败不自动扩跑或缩短后冒充完整比较。
- [build_019_microbench.py](../../scripts/build_019_microbench.py)：沿用原Franzen precache/serving源码，增加固定seed、来源核验、prefetch join及生命周期记录；原模型服务参数保留。分别构建私有断网CPU和GPU Notebook，账号固定jiyujia。

## 已完成的本地核验

[构建检查](../../experiments/019-preparation/cpu-build-check.json)通过：Notebook schema、代码cell真实IPython转换后编译、全部原生writefile重定向临时目录写入后逐字节hash、固定配置拒绝修改、模型路径解析、wheel ZIP源码hash接受/拒绝路径。另外实际运行了静态XZ→JSON解码cell，并与4.3MB原suite逐字节/hash比对；未执行安装、serving或模型生成代码。

[客户端检查](../../experiments/019-client-cpu.json)覆盖stream分片tool args、最终usage/spec单独chunk、严格非有限JSON、loopback边界、绝对deadline；三阶段×34请求的模拟transport流程通过。没有真实HTTP/模型测量，模拟耗时不作速度结果。权重模块的合成正常输入与错误scale、非PLE损坏、NaN、误差超界、缺片、config pin和draft量化不对称等7类负例按预期通过/拒绝；实际镜像仍由远端CPU预检验证。

独立代码审阅检查了客户端/runner接口、CPU-only分支和异常清理；已补四个关键runtime文件中的loader及最外层server PGID清理。最终源hash在两个build-manifest中逐项匹配。

本地检查命令：

```bash
PYTHONPATH=/private/tmp/arc3-018-check-deps \
  /Users/zhaohuaxiang/.local/bin/python3.12 -B scripts/build_019_microbench.py --mode weights_only
PYTHONPATH=/private/tmp/arc3-018-check-deps \
  /Users/zhaohuaxiang/.local/bin/python3.12 -B scripts/build_019_microbench.py --mode microbench
PYTHONPATH=/private/tmp/arc3-018-check-deps \
  /Users/zhaohuaxiang/.local/bin/python3.12 -B scripts/check_019_preparation.py
```

临时依赖只用于本机nbformat/IPython构建检查，CPU/GPU远端实际模块均为标准库，不把本地临时库上传。

## 冻结与执行

请求suite标识`f42e6b9c309432735fd5ff5e08d1344758d09fae7c689c311bba5e3d518391c1`。源与Notebook已存入[019-source](../../experiments/019-source/source-hashes.json)，CPU-v1-final和GPU-prepared-final分别保留；较早目录属于未被接受的上传尝试，不能冒充运行版本。

- [CPU Notebook](../../notebooks/019-fp8-ple-cpu/experiment.ipynb)：17cells；仅权重及wheel核验，enable_gpu=false，Kaggle外层上限900秒。
- [GPU Notebook](../../notebooks/019-fp8-ple/experiment.ipynb)：17cells；硬限4800秒，每服务启动≤900秒、每固定suite≤360秒，尚未执行。先CPU过门再决定启动，不把准备完成写成性能成功。

10/18 18:33北京只读查询：jiyujia最近018和ARC2作业都COMPLETE，无reserved秒；通用GPU quota仍显示total6h且used超额。这不能证明RTX无法使用或承诺可用余额。资源统计原件见[账户状态](../../experiments/019-preparation/account-status-before.json)。

最终推进门在[019计划](../plan/019-fp8-ple.md)：权重/运行完整性、合成质量不回退、两个10并发组均超过两个BF16且较均值≥10%、BF16漂移≤10%、无解释不了的资源恶化。通过也还需要游戏质量A/B，不能直接替换正式基线。

## 上传记录

第一次/第二次保存返回HTTP400，进一步读取API正文确认源码必须小于1MB；已修正标题与id一致性，并只对静态suite JSON做XZ+base64封装。可执行helper与launcher仍是原生可读writefile。还原后的suite字节与标识不变，最终Notebook约530KB。第三次保存成功，CPU kernel139403754 / v1，enable_gpu=false。所有失败响应和最终冻结源均保留，没有因上传失败占用GPU。

离线结果检查已实现：`scripts/analyze_019_results.py --root <下载的019-results目录> --output-dir <独立派生目录>`。按冻结门槛判断请求/缓存/速度/漂移/质量，资源异常仍需单独审阅；不会自动启动下一实验。当前Qwen4Exp不支持现成的loaded-weight读取接口，内部scale实值没有被直接测量。
