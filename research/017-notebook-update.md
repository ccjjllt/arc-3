# 017 — 公开 Notebook、自然采用证据与 FP8 PLE 更新审计

检索日期：2026-10-18，Asia/Shanghai。刷新本赛 `scoreDescending` / `dateRun` 各前 40 项，6 个主要作者的公开 Notebook 与模型列表；取得 **19 本**完整源码和当前版本元数据。仅读取公开 API、JSON、源码、静态字面值与已存在输出，未执行下载的 Notebook/模块，未运行 GPU、游戏、模型请求或提交。原始材料、可读 cell、diff、hash 和提取资产集中在 [2026-10-18](notebooks/2026-10-18/)，索引为 [audit.json](notebooks/2026-10-18/audit.json)。

本轮没有发现可据证据直接替换 009 的金牌方案。真正新增的是：**Lexicon 的多色对象视图有历史引用计数，但没有当前版本的采用链；FP8 PLE 有可核对的配置、上游文件哈希与既有 serving 代码路径，可进入独立的资源/数值审计。** Sujan/DF-WM 的真实转移校验仍是合理研究机制，但公开产物没有证明模型自然采用，更没有单因素收益。

## 1. 当前源码、版本与分数边界

[ScoreDescending](notebooks/2026-10-18/ScoreDescending.json) 前八仍为 Franzen、Fu 原版、Heliosli、Fu v3、Greenalgeria、Amatlas、Sujan、Habanwer；Code 顺序不是本轮核验的数字榜分。列表无 submission ID、数值 score 或与 native scriptVersionId 的绑定。详情 `lastRunTime` 与搜索时间仍不一致，故版本更新以返回的版本号和 cell 内容为准，不能把一次新 run、标题中的 Champion/Gold 或团队榜分绑定到当前源码。

| 对象 | 当前 Kaggle 版本 | 与已有存档的源码关系 / 新观察 | source SHA256 前 12 位 |
|---|---:|---|---|
| Franzen Milestone 2 | 3 | 与 10/17 全 cells 一致 | `88a379f17c3a` |
| Fu 原版 / v2 / v3 | 1 / 2 / 1 | 均一致；v2 是 tail、v3 是 pace，不能重复当新发现 | `87d279b3d6c7` / `20f0072959f6` / `b338d78e3b8e` |
| Heliosli | 4 | 与 10/17 一致；仍是 98,304 token 停滞重启 | `94907c4828b2` |
| Sujan | 29 | 与 10/17 一致；world-model + UND + 多调度修改 | `c1f976bc419b` |
| Jeroen / Scott / Lord / sirikilohit | 6 / 1 / 306 / 5 | 四个既有家族全部一致 | 见 audit |
| Amatlas D-prime | 2 | 与旧存档一致 | `779b5f61f55a` |
| Habanwer Lexicon | 6 | 本轮新增完整深审；不能把 10/17 run 当作下面的 10/08 输出 | `343b125179de` |
| Yukailiu Champion | 34 | Lexicon v6 + D-prime + 路径/driver适配，非独立新规划器 | `40a7610372ef` |
| Zhangyues fork | 2 | 新增可疑的 closure 级 death ledger | `9814bca257ca` |
| DF-WM | 12 | check_sim / search / act_checked 与 Sujan 同一实现家族 | `8e4e1c07dfc4` |
| Action7 Shadow | 22 | 从单动作 canary 升为原版十游戏验证器；没有算法增益证据 | `900514bd99e0` |
| Greenalgeria final | 2 | 对 Franzen v3 的差异主要是去掉开头说明 | `59d74065f12d` |
| 最新 Graft v4 / Cohezion | 2 / 16 | 预探索+记忆多机制组合 / 启发式 MCTS；均无版本绑定收益 | `cb4067219a96` / `d08f7b4c84ac` |

完整 SHA256 在 audit 中。全部输出清单 SDK 请求均失败（17 本两个接口均 404；另两本 file 接口分别 404 / SSL 错误），对 Lexicon 另试公开旧端点也 404。这只能说明**本次接口未取得产物**，不说明远端没有产物。错误记录在 [output-index](notebooks/2026-10-18/output-index.json)、各目录 `output-files-error.json` 和 [legacy-output-probe](notebooks/2026-10-18/legacy-output-probe.json)。

## 2. Lexicon：已接入，但不是默认 observation 替换

来源：[Habanwer v6](https://www.kaggle.com/code/habanwer/arcaid3-lexicon-view-dfranzen-m2)。完整入口在 [cell 21](notebooks/2026-10-18/habanwer__arcaid3-lexicon-view-dfranzen-m2/cells/021.txt:1684)。

**它保留原 `.segmentation` 和原图像输入，增加 `.code/.objects/.native/.rules/.changes_since` 属性。内容只有模型主动在 Python 中读取后才进入工具输出。** 自动加入的是成员说明、每个新关的 `print(current_frame.code)` 提示，以及 no-op/6、15、30、60、120 动作时读 `.rules` 的提示；没有每回合自动计算并插入完整 `.code` 或 `.rules`。（cell 21 L1684–1769、L1819–1873。）

三层内容应拆开看：

1. **对象表示**：估计画面放大倍数，恢复低分辨率格子；用八邻接、多色连通对象与大面板分层，输出内容命名、形状图例、位置和显式像素坐标变换。默认只列最多 24 种对象、每种 8 个位置。
2. **跨帧稳定性**：每关尺度锁和对象接触后的拆分；每个 sandbox 是新进程，因此每次按当前 history 重算，调用内再缓存。`.code` 会沿最多 8 个不同的先驱画面建立恒常性。
3. **规则推断**：最近最多 60 步，基于 move/recolor/turn/resize/reshape/vanish/appear 的语法，选择解释事件较多、反例及描述成本较小的规则；最后一步先用旧规则预测，再展示未解释变化，最后才加入该步学习。它不是完整游戏模拟器，也未定义正确胜利目标。

静态资产：[Lexicon](notebooks/2026-10-18/habanwer__arcaid3-lexicon-view-dfranzen-m2/extracted-assets/cell021-ARCAID3_LEXICON_SOURCE.literal.txt)、[规则语法](notebooks/2026-10-18/habanwer__arcaid3-lexicon-view-dfranzen-m2/extracted-assets/cell021-ARCAID3_RULES_SOURCE.literal.txt)、[规则报告](notebooks/2026-10-18/habanwer__arcaid3-lexicon-view-dfranzen-m2/extracted-assets/cell021-ARCAID3_RULES_VIEW_SOURCE.literal.txt:60)。

### 历史输出可以说明什么

本轮源码响应里有 21 个 outputs，提取出 [嵌入日志](notebooks/2026-10-18/habanwer__arcaid3-lexicon-view-dfranzen-m2/embedded-outputs.txt:232) 与 [诊断 HTML](notebooks/2026-10-18/habanwer__arcaid3-lexicon-view-dfranzen-m2/embedded-diagnostics.html)。日志时间明确为 **2026-10-08 18:51:32–19:16:54**（原文未声明时区），10 游戏、每局 1500 秒、10 streams、1 pass：mean 55.36，50/72 关，3 个全通，832,174 个 action-attached tokens。它是可读的作者历史输出，不是当前 v6 的新运行证据，也不是可与本项目 25 游戏直接比较的对照。

历史总计：576 个工具调用中 98 次包含视图引用；`.code` 60，`.rules` 40，`.native` 2，`.objects` / `.changes_since` 均 0。**计数器扫描的是工具代码中的子串**（cell 21 L2077–2086），不是属性成功求值或下游消费的宿主事件。两类引用会重叠。

进一步检查诊断 HTML 发现它只有分数/成本图、每局结果和 movie 链接，没有请求原文、工具输出或属性访问记录。因而本轮仍无法给出两款不同游戏的“`.code` 返回可用对象 → 代码消费 → 后续动作 → 新关卡”链，也不能证明 `.rules` 的内容被用于修正模型。原文的离线 45/55 plays 或 generated games 表格没有本轮可取得的逐例材料，不能把作者汇总宣称当本项目复算。

### 开销与错误边界

- `scale_lock` 最多读 256 个不同帧；超限保留开头至多 32 个加末尾帧。每次新进程重算，若唯一否定粗尺度的中段帧被丢弃，注释所称“永久拒绝、不再回跳”没有完整的跨调用状态保证。
- `.rules` 的 8 秒预算只在读取历史/编码循环检查，后续 `Learner.observe/rules` 没有同一个硬时限，不能承诺工具全程 ≤8 秒。
- 八邻接合并、多色并块、最多三层且 ≥24 格的局部“地板”剥离、半径 6 的对象恒常性都是启发式。细小文字、接触同色对象、远距离移动、形变和身份歧义仍会出错。
- `native_grid` 对块作多数表决，返回 residue；正文把 residue 统一称 HUD 不可靠，真实机制也可能在残余像素中。低分辨率视图不应代替可追溯原始像素。
- `.code` 的 24 kinds/8 positions 是输出截断，不是所有对象完整性保证。不能直接让搜索把未列对象视为不存在。

**可裁剪候选**是“code 对象视图 + 新关一次提示”，显式关闭 grammar、规则提示和额外调度，保留原 segmentation 和原始像素。它比全量 Lexicon 更容易测采用/开销，但仍不具备晋升依据。008 已有的 RegionReader 可作为**按模型指定区域验证形状、前景、姿态、坐标和裁剪**的保真层；它不能自动解决 Lexicon 的对象分割，更不能把 008 人工标注槽位写进在线策略。若选表征方向，应优先复用 008 的明确合同并缩短输出，先验证自然采用，不同时叠加两套新 API。

## 3. 世界模型校验和停滞重启：没有新实测

Sujan v29 与昨天完全相同，DF-WM v12 则提供同族 `check_sim/search/act_checked`。可复核 [world_model.py](notebooks/2026-10-18/sujanmajhisuzan__arc-agi-3-m2-top-submission/extracted-assets/patch-files/ARC3-Inference/inference/utils/world_model.py:203) 与 [sandbox patch](notebooks/2026-10-18/sujanmajhisuzan__arc-agi-3-m2-top-submission/cells/002.txt:2177)。

真正有价值的是：用真实同关转移给模型自己写出的模拟器提供坐标反例，并在批动作首次偏离预测时停止。它并未解决模型是否会写/调用指定模拟器、目标是否正确或测试是否覆盖后续计划。新增静态边界：

- `act_checked` 只把 action 名传给模拟器，丢失 MOUSE 的 row/col；`check_sim` 则读历史 action 字符串，二者合同不一致。
- 没有 simulate 时静默降为普通 action，不是“验证通过”。默认边缘 4px 不比较，可能漏机制。
- `PredictionMismatchError` 继承 `Exception`（cell 2 L1927）；模型可用普通 `except Exception` 吞掉，不是宿主强制不可继续的 stop。
- BFS 以默认忽略边缘的画面 hash 去重，无法代表隐藏状态/计时；validator 可接受 sparse dict，BFS 的 `extract_grid(dict)` 却不能恢复该格式。
- 当前可取得产物没有真实 `check_sim` 调用链。CPU 工程合同通过不能替代模型自然采用，也不能反证它没有价值。

Heliosli 的 98,304 token 清空 `_history_messages/_kept_functions` 仍会触发历史淘汰及 handover；推理重启和调度变化混杂。没有新的可查配对收益，继续后排。

## 4. 其他新近高排源码的实际增量

- **Yukailiu v34**：[对 Lexicon v6 的精确 diff](notebooks/2026-10-18/yukailiu__arc-agi-3-champion-solution/lexicon.diff) 显示是加入 D-prime、更改 mount/driver 适配和 1 游戏 5 分钟 rehearsal。不能把 Champion 标题当新推理机制或成绩证明。
- **Zhangyues v2**：累积 death ledger 的 list 位于 `install()` closure（[提取模块](notebooks/2026-10-18/zhangyues0000__arc-agi-3-m2-franzen-fork/extracted-assets/cell017-write_text-line10.py)）。同一类所有 agent 共享它；多游戏并发下一个游戏的失败可被另一个游戏读到、另一游戏过关还会清空它。这是静态可见的会话隔离错误，不能直接移植。
- **Action7 v22**：最终 cell 解压 hash 绑定的十游戏 full-workload 检查器，旧 launchers 保持惰性；本轮静态解出 [13 个新增文件](notebooks/2026-10-18/prvsiyan__arc-agi-3-stock-taaf-action7-shadow/extracted-assets/v22-new-files/)。其目的为原版 serving/模型动作/进程清理验证，不是已经取得新榜分。
- **Graft v4**：新近 DateRun 条目组合独立环境预探索说明书、已过关路径重放、跨关 solved-level memory 与知识提示（cells 11–14、21–23）。这些同时改动作/时间/知识来源，需核计分协议和在线执行账本，不能将“预探索不耗 benchmark action”当免费通用收益。本轮没有执行其代码或验证其分数。
- **Cohezion v16**：是启发式对象/MCTS路线，正文自身引用历史 0.15–0.22 分而无当前版本结果；其 `hash_frame` 把颜色 clip 到 0–9，ARC 的 10–15 色会发生状态混叠。不是现有强模型基线的直接替代。

## 5. FP8 PLE：新增且可分离的吞吐研究候选

公开镜像：[dfranzen/albucino FP8 PLE v1](https://www.kaggle.com/models/dfranzen/albucino-qwen3.8-flash-next-w4a16-fp8ple/Transformers/default/1)，native model version **1026228**，更新 **10/12**，总文件 **124,825,216,916 bytes**；当前 009 的 Intel BF16 PLE v1，native **1007514**，总文件 **181,240,184,163 bytes**。两者都仍受上游 Qwen 许可约束；本轮没有做奖金资格法律判断。

[原始 metadata、Kaggle 文件清单、HF config/index 与 serving 源码](notebooks/2026-10-18/fp8-ple/)，[比较结果](notebooks/2026-10-18/fp8-ple/comparison.json)。没有下载 tensor；每份约 23.7 MB 的 index 仅为键到文件名映射。

### 已核实的差异及未核实之处

取回 HF 作者上游的固定 revision：Albucino `c6af9fee7ad2cb8ef44b534a99b8c1b81fb0f6da`，Intel `4c67bf686b7f7fd386bae6b07ab59e8ff1d5b897`。递归比较 config，**唯一字段差异**是 `text_config.ple_embedding_dtype="float8_e4m3fn"`，其余配置含 AutoRound W4A16/group128 相同。

HF API 提供的 **15 个非 PLE safetensors 文件 LFS SHA256 全部相同**，合计 73,581,002,608 bytes；这比“作者说 unchanged”更强，但仍是仓库哈希元数据核对，没有本地重算 73 GB tensor。其余变化：

- 128 个 BF16 PLE shard tensor 被替换为同名 128 个 FP8 shard tensor，新增一个全局 `ngram_embedding.weight_scale`。Kaggle清单中 PLE 文件从 22 个 BF16 重分片、102,400,512,024 bytes，降为 10 个 FP8 文件、51,200,267,901 bytes。
- Intel 索引自带的 1,565 个 `mtp.*` tensor（`model_extra_tensors.safetensors`，5,214,492,152 bytes）不在 Albucino target 索引中。009 已使用独立 Albucino drafter，应保留它，不能把删除附带 MTP 当作禁用 speculative decoding。
- [hybrid_sources.json](notebooks/2026-10-18/fp8-ple/albucino/hybrid_sources.json) 声明以 hardlink 组装非 PLE target，FP8 PLE 来自 `RadixArk/Qwen3.8-Flash-Next-NVFP4@7b719225242aacd3dbd3f9407468c2ee9a9d2594`；这是作者 provenance 声明。Kaggle镜像的文件名/大小吻合对应上游，但 API 不给文件 hash，未证明镜像逐文件/逐tensor完全一致。
- 原 Intel index 的 metadata.total_size 与文件列表总大小不一致，不能拿它算实体磁盘/内存。报告使用 Kaggle file sizes 与 HF LFS sizes。

### 当前 009 实际走哪条数值路径

[009 smoke 实际 server args](notebooks/2026-10-18/fp8-ple/009-effective-server-args.json) 由保存的 [serve.log](../runs/009-v2-smoke/serve.log:12) 解析：`ple_offload_embedding=True`、139264 context、10 requests、BF16 compute、AutoRound target、FP8 KV、Mamba BF16 / extra_buffer、无 hierarchical cache、MTP 3 steps、accept thresholds 均 1。外部命令写 NEXTN，SGLang运行参数规范化显示 EAGLE，不能把它误读成模型换掉。

保存日志报告 `sglang 0.5.19+gd00d88efc8d6`。本轮读取作者仓库同 commit `d00d88efc8d6281b12be4f4073126aec95038c55` 的源码（未证明安装 wheel 的每个源文件 hash 等于该 commit）：

- [qwen4_exp.py L492](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:492)：配置字段选择 FP8 或 BF16 存储；scale 保留在设备。
- [L771](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:771)：整张 PLE 按 checkpoint dtype 分配精确大小的 pinned host table；不是普通 CPU Python 查表，也不把全表放显存。
- [L733](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:733)：GPU Triton 从 host UVA 指针读取 FP8/BF16，转 BF16；[L1257](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:1257) 再乘 checkpoint 全局 weight_scale，前层运算期间另流预取。
- [L2133](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/models/qwen4_exp.py:2133)：offload 开启却未设置 FP8 config 时，FP8 shard 自动切换会显式报错。因此不能只替换权重文件、不带对应 config/scale。
- [qwen4_ple.py L209](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/kernels/ops/qwen4_ple.py:209)：FP8 pinned table 在 SM120、TP1、head width160、target-verify contexts 为 4 或16 时可走一 warp 的 fused hash+gather；其他形状走 split。`SGLANG_ENABLE_QWEN4_PLE_FUSION` 在 [environ.py L301](notebooks/2026-10-18/fp8-ple/pennyroyal/python/sglang/srt/environ.py:301) 默认 True。**实际命中率/耗时尚未测**，不能说所有 decode 都加速。

### 性能推断与下一验证门槛

确定缩小的是模型输入文件、checkpoint prefetch/I/O、PLE host pin memory；PLE row 的 host→GPU 读取带宽有减小潜力，特殊 target-verify 形状还有融合路径。**不会因此释放 51 GB 显存或直接扩大 KV**，因为 baseline PLE 已 offload；非 PLE专家、KV格式、Mamba、history trim/handover均可保持不变。当前服务的高 GPU 利用率也不能辨别是计算、内存等待还是并发掩蔽，更不能从少56.4 GB文件推断通关上涨。

这是“相同 harness 的 PLE 精度/存储变化”，仍改变模型数值，不能叫完全无损的系统优化。作者 [3090性能README](https://huggingface.co/albucino/Qwen3.8-Flash-Next-W4A16-FP8PLE/blob/c6af9fee7ad2cb8ef44b534a99b8c1b81fb0f6da/README.md) 的 43–111 tok/s 基于不同vLLM、多卡/CPU expert offload配置，不可外推RTX PRO6000+Pennyroyal的10并发速度。sirikilohit v5 源码确有 W4A16+FP8 PLE 组装及旧启动记录说明，但还叠加不同runtime、cache、context、调度；本轮无等配置两臂日志。

后续有算力时先做 **同公共prompt、同输出长度、同sampling/seed/ctx/并发/独立drafter的 BF16→FP8→BF16 microbench**，区分冷启动/预取、冷prefill、同前缀热prefill、decode和MTP接受率，记录host RSS/pinned、GPU memory及错误。先查随机/极端 token row 的 dequant/scale、输出有限性和工具格式；采样轨迹不会因为专家hash相同而保证逐字一致。只有加载、长期服务和数值/质量回归通过且节省的是预算关键段，再按原门槛做同预算游戏 A/B。当前资源不足时只完成上述CPU/源码审计，不启动GPU。

## 6. 对下一研究轮的建议

不能继续把 tail/pace 的单次小增益或“更多状态保存成功”当突破。候选应同时回答“改善哪个真实失败”“模型是否实际使用”“扣除开销后是否多过关”。

1. **独立系统候选：FP8 PLE。** 本轮证据最可核查、改动面清楚，可先完成配置/加载合同与固定prompt基准设计；未实测前保留原权重和009。
2. **推理候选：真实转移反例。** 优先从模型已经写出的搜索/模拟器错误确定触发点，再做最小预测—动作—比较；不能先整套加入UND/BFS再期待自然采用。完整 action、会话隔离、显式mask及no-evidence状态必须正确。
3. **表征备选：只读多色对象/区域。** Lexicon历史有引用迹象，尚无两游戏消费链；先复用008保真诊断和本项目失败帧做可解释、成本有界的最小表示，避免先引入60步grammar。正式晋升仍要求同预算复现和跨游戏关卡覆盖，不用作者Code位置或单次公共分数代替。

本报告只支持这些候选的研究优先级，**不支持任何“合并公开高分Notebook即可金牌/奖金”的结论**。
