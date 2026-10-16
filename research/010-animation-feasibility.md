# 010 — 旧动作完整动画归档：最小 CPU 可行性

日期：2026-10-13（Asia/Shanghai）。已通过公开 SDK 新建 `tn36-ef4dde99`、seed=0，独立执行 005 观察病例的五个固定 MOUSE 动作，再执行一次 RESET。**旧 action 的完整帧可以在后续动作和同 session RESET 后按原索引准确读回。** 这证明归档/查询的技术前提，不是模型采用或提分结果。

脚本：[analyze_010_animation_archive.py](../scripts/analyze_010_animation_archive.py)。本次 [报告](../experiments/010-animation-archive/tn36-cpu-20261013T010144Z-5152df13/report.json)、[归档索引](../experiments/010-animation-archive/tn36-cpu-20261013T010144Z-5152df13/archive/index.jsonl)、[七帧局部查询](../experiments/010-animation-archive/tn36-cpu-20261013T010144Z-5152df13/roi-action2.json) 均已保存；[latest.json](../experiments/010-animation-archive/latest.json) 保存报告路径及 SHA256。

## 实际执行范围

仅执行以下明确动作，顺序及坐标均固定，未运行原模型代码：

| 本次 step | 动作，坐标为 row/col | attempt | 返回帧数 |
|---|---|---:|---:|
| 0 | SDK make 返回初始 observation | 0 | 1 |
| 1 | MOUSE(14,31) | 0 | 1 |
| 2 | MOUSE(55,35) | 0 | **7** |
| 3 | MOUSE(45,21) | 0 | 1 |
| 4 | MOUSE(45,36) | 0 | 1 |
| 5 | MOUSE(20,20) | 0 | **1** |
| 6 | RESET | **1** | 1 |

索引包含 `session_id + attempt + step + frame_index`。step 是本研究显式 SDK 动作的全局序号，包含 RESET；不是读取到的引擎内部计数。frame_index 为原始 `observation.frame` 的零起点位置，**不折叠重复帧**。RESET 的结果保存于 attempt1/step6，旧 attempt0 不删除。每条索引另存 action、公开 level/state、shape、原始 dtype 和每帧 hash。

单次 action 的完整帧以紧凑 uint8 stack 写入独立压缩 NPZ；dtype 转换前后数值逐格检查。文件名在本次独立 session 目录内使用 attempt/step，完整逻辑键仍带 session。查询使用 `allow_pickle=False`，按索引核对 SHA256，不依赖写入器仍持有原数组。

## 已核对的事实

- step3、4、5 完成后，分别读取旧 action2 的七帧，三次均 **7/7 数值相等**。
- RESET 后丢弃读取器状态、从磁盘索引重新建立 reader，初始 observation 及六次动作共 **13/13 帧**与本次 SDK 返回的原始观察逐格、逐 hash 相符。
- 请求错误 attempt1/step2、错误 session 字符串均被拒绝，不把它们重定向到“最近一次动画”。这是错误键检查，**未创建第二个真实环境 session，也未证明生产并发隔离**。
- action2 的七帧加动作前帧，独立计算得到 **256 个变化后又变化的像素**，bbox `[13,19,59,43]`。末帧全画面只有 1 像素变化，去掉四格边缘后变化为 0；最后一次 MOUSE 只有 1 帧。只查询末动作不能恢复 action2 的时序信息。
- 五次 MOUSE 的稳定终点与 005 保存 events 对应 board 均逐格一致。**这不等于恢复 005 当时未保存的中间帧，也不证明内部隐藏状态相同。**
- 所有动作仍在首关，本次没有真实过关、跨关、自然死亡或多个并发游戏；没有模型、GPU 或策略评价。

## 实测资源

| 项目 | 本次值 | 解释范围 |
|---|---:|---|
| 13 帧 uint8 原始数据 | 53,248 B | 64×64×13，不含对象包装 |
| 七个 NPZ payload 合计 | **3,129 B** | 小型、颜色重复较多病例；不可线性外推压缩率 |
| JSONL 索引 | **5,918 B** | payload+index 合计 **9,047 B**；不含研究报告、ROI示例 |
| action2 七帧 payload | 912 B | 一次查询需解压整条 action stack |
| reader 索引 Python 对象深度大小 | 27,293 B | `sys.getsizeof` 递归口径，不含解释器/SDK/分配器空隙 |
| 最大单动作 uint8 stack | 28,672 B | action2 的 7 帧；不是整个程序峰值 |
| 人工核对保留的原观察副本 | 53,248 B | 研究 oracle，生产归档不必保留 |
| 全研究 tracemalloc 峰值 | 26,961,904 B | 含 SDK 初始化、oracle、压缩及查询；不是归档净开销或 RSS |
| SDK 六次动作累计 | 0.00676 s | 不含启动/import/SDK初始化 |
| 每条归档写入 | 0.304–0.518 ms | 本机小样本 |
| 16×16 ROI 查询中位 / P95 | **0.297 / 0.327 ms** | 100 次热文件读、解压、hash和ASCII构造 |
| 整帧查询中位 / P95 | **1.190 / 1.231 ms** | 同样 100 次热读；不含json.dumps、IPC或模型 |
| 单帧 16×16 ROI 紧凑 JSON | **688 字符** | 含动作/帧来源、bbox、hash及像素 |
| 单整帧紧凑 JSON | **4,670 字符** | 不是 tokenizer 输入成本 |
| 七帧 ROI 一起返回 | **4,824 字符** | 说明即使小裁剪，自动全量回传仍有上下文代价 |

ROI 为当前已观察暂态区域内的 `[13,19,28,34]`，直接只读 NumPy 切片并保留全部颜色字符；不设置对象身份、目标或机制标签。本次不必修改 008 模块；这是历史原始帧的访问证明，不是另一轮形状工具实现。

## 环境与复算

原 `/tmp/arc3-data-inspection-venv` 在本次环境已不存在。使用应用现成 Python3.12.14、numpy2.3.5、pydantic2.13.5，并把**已经下载的比赛 wheel**离线提取到 `/private/tmp/arc3-010-sdk`；没有网络下载或安装。核心 SDK 为 arc-agi0.9.8、arcengine0.9.3、Flask3.1.3。报告记录每份实际 wheel 路径及 hash。二进制 wheel 扩展未提取，通用依赖使用已有本机模块或纯 Python 路径。

本次执行命令：

```bash
/Users/zhaohuaxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/analyze_010_animation_archive.py --sdk-path /private/tmp/arc3-010-sdk
```

若 SDK 已在当前解释器安装，可省略 `--sdk-path`。临时目录可能被清理；脚本本身不会安装任何依赖。每次运行使用新 session 子目录，不覆盖已有原始归档。输入来源包括已保存 005 观察报告与 events；前后 hash 一致。

## 对下一步的意义

目前只证明：保存完整公开返回帧很便宜的这个小病例可以正确实现，且旧动画信息确实不同于最新动作。**不能从亚毫秒热读或不到10KB数据推断110游戏实际I/O开销，更不能推断模型会查、会理解或会提分。** 在线接入还需要核对每次 action 的捕获位置、RESET/跨关作用域、序列化方式与真实模型使用。

后续最小变量仍是旧 action 的完整动画可按需查询；不自动追加七帧，不改变模型/调度/提示策略，不叠加 006 摘要、007 或显式状态参数研究。当前未修改 solver、runner、Notebook；没有新增测试/CI。
