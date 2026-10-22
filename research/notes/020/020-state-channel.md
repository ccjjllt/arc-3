# 020：从可见像素直接到程序输入

实现日期：2026-10-19。原交付包含接入代码和两例真实CPU sandbox演示。**后续020 v1已完成：41.2112→26.5081，整体回退；详见[在线结果](020-results-analysis.md)。** 下文CPU证据仅证明数据路径可执行，不能代替在线采用或收益。

018 的 ar25 轨迹已经把 L6 黑色块读对，但之后重新手写 `pieces` 时把 `(8,18)` 改成 `(8,17)`。020 将入口放到现有 `current_frame`，使模型编写的提取/求解程序直接消费当前帧字符，不必先打印坐标表，再由模型转抄回来。复用 008 的 `RegionReader`；没有另起跨调用缓存。

## 接口

候选的现有 Python 工具中可直接使用：

```python
region = current_frame.region((top, left, bottom, right), foreground="B")
plan = solve(region.cells)  # solve 是模型编写的函数，实际接收观察所得字符矩阵
source = region.source
```

若算法需要全局坐标，可直接传 `solve(region.cells, region.origin)`；若算法消费二值图或坐标集合，传 `solve(region.mask)` 或 `solve(region.positions())`。不要在中间重新手写像素/坐标表。

从分割节点选区时，不用转抄包围盒：

```python
node = next(n for n in current_frame.segmentation["nodes"] if relevant(n))
region = current_frame.region_from_node(node, foreground="B", inset=0)
plan = solve(region.mask)
```

这里 `relevant` 是模型依据当前任务编写的选择条件。`node` 必须是当前分割列表中的节点字典对象，不能传裸数字 ID、旧帧节点或复制字典；相同 ID 在新帧复用不会被悄悄当作同一个节点。节点只提供**选区边界**，实际颜色始终重新读取 ASCII；默认不内缩、不填充、不旋转。

| 属性/方法 | 原生 Python 返回值及含义 |
|---|---|
| `raw_rows` | `tuple[str]`，原始字符逐行保留 |
| `cells` | `tuple[tuple[str]]`，每个字符一个格子 |
| `mask` | `tuple[tuple[bool]]`，仅显式 `foreground` 字符为真 |
| `positions()` | 真像素的全局 `(row,col)` 元组，行优先顺序 |
| `origin` / `bbox` / `shape` | `(top,left)` / 四边界 / `(rows,cols)` |
| `source` | 普通字典：step、level、全帧 ASCII SHA256、形状、边界、前景；节点选区还记录 node ID、原边界与 inset |

坐标从零开始，边界顺序为 `(top,left,bottom,right)`，四边均包含，最多 1024 格。不传 `foreground` 时可以读字符，但调用 `mask` 或 `positions()` 会明确报错。越界、未知颜色、不可用节点、过大区域等也报错，不返回一个看似可用的空矩阵。

每次 getter 验证其 FrameView 仍是运行时 `current_frame`，且 step/level/shape/ASCII 摘要没变。既有 `action()` 刷新当前帧后，旧 FrameView 和旧 region getter 失效。已经取出的普通 tuple/dict **继续是合法历史数据**，不会使既定计划失效；需要跨行动建模时自行保留 `source`。本实现没有跨调用值存储，也没有试图追踪用户后来对普通值的所有变换。

## 接入点与打包

- 新模块：`src/arc3_research/grounded_state.py`。依赖项目内的 `src/arc3_research/observation_representation.py`，其他新增依赖均为 Python 标准库。这两个模块加现有 package 基础文件足够；不依赖 018 的 `observation_grounding.py`。
- `install_grounded_state()` 在候选 CPU 进程安装。它把维护中的 008 源码嵌入原隔离子进程 bootstrap，只给 FrameView 增加两个方法，并在既有 `_refresh_state` 尾部绑定当前帧 getter。子进程仍是原来的 `python -I -S`，不需要从 repo 导入模块。
- 使用原 `ARC3_SYSTEM_PROMPT_PREFIX` 告知这两个入口及直接消费方式；拒绝非空外部 prefix 和重复安装。候选同时包含能力和必要接口说明，不能把后续变化解释成纯提示作用或纯代码作用。
- `run_arm.py` 的 `grounded_state` 分支在 `bm.run` 和每局 ToolAgent 构造前安装；baseline 分支不安装。记录两个源码摘要和 `grounded-state.json`，工作线程退出后恢复 bootstrap/prefix。
- `experiment_config.py` 支持 `baseline → grounded_state`，保留基线调度、10 流容量、单 pass、warmup 0 和已有预算/观测设置，不硬编码游戏池或 1800 秒预算。
- `preflight.py` 在服务启动前拒绝环境 prefix 冲突，检查既有 prompt hook、安装/卸载和 Python runner 对象身份。构建 Notebook 由主任务负责。

没有增加工具 schema、模型请求、游戏动作或执行拦截；框架不主动插入调用。自然请求次数、tokens、行动数可能因模型选择而改变。此次没有修改原 runtime-bundle 文件、游戏源码或模型服务。

## 已完成的两例实际程序消费

运行命令：

```bash
/Users/zhaohuaxiang/.local/bin/python3.12 -B experiments/020-state-channel/demo.py \
  --extra-python-path /private/tmp/arc3-018-check-deps
```

默认 SDK 路径为 `/private/tmp/arc3-018-sdk`，可用 `--sdk-path` 替换。它复用 018 CPU helper 对原 Notebook `setup_env` 字面量的静态读取，没有执行 Notebook cell。报告在 `experiments/020-state-channel/cpu-demo-report.json`，保存输入帧、来源文件摘要和行号、作者新写的 consumer 代码以及完整 sandbox 输出。

1. **ar25 L6**：018 候选 `artifacts/ar25-0c556536_p0_events.jsonl:177`，公开保存帧 action 140。`region.cells` 与 `region.origin` 在同一次真实 Python sandbox 调用中直接传给通用“按显式格距统计颜色像素”函数，得到 13 个块坐标，包含 `(8,18)`，不包含 `(8,17)`。独立局部读取全局行 24–26、列 51–56，原字符为 `bbbBBB / bbbBbB / bbbBBB`；左三列 B 数为 0，右三列为 8，保留中央 `b` 孔洞。格距 3、阈值 7 是这个手工演示的明确参数，不是通道自动发现的游戏规则。没有编写摆放求解器或执行行动。
2. **tr87 字符图案**：007 保存帧 `artifacts/tr87-cd924810_p0_events.jsonl:34`。两个有界区域的 `mask` 原生元组直接传给通用精确比较函数，得到 `True`；原字符 `PPBBB / PPBPB / BBBBB / BPBPP / BBBPP` 全部保留。没有采用旋转/镜像等价。相同 sandbox 调用还实际运行了当前节点对象的 `region_from_node`，没有转抄节点边界。

两次 sandbox 调用均成功；网络尝试、模型调用、游戏动作均为 0。另有少量手工检查确认旧 getter、越界、未知前景明确报错且已提取历史值仍可使用。真实 ToolAgent 构造确认 candidate prompt 精确等于 prefix 加 baseline，工具 schema、Python runner、`_run_python_tool` 函数对象不变；卸载恢复基线 bootstrap。不是 AST 代替真实导入，也没有执行历史日志中的模型代码。`notebook_frontier` 对接入做了独立只读审阅，未发现阻断。

## 研究边界

这个实现消除的是**观察值到程序参数之间的一次人工转抄机会**，并不保证裁剪范围、前景选择、格距、对象分组、规则或求解器正确。颜色掩码不等于碰撞足迹；保留孔洞不意味着物理对象必然可穿过孔洞。008 已证明不触边也可能漏掉断开部分，020 没有把边缘统计包装成完整性证明。

每个 accessor 会校验完整现有 ASCII 摘要，008 reader 也计算区域连通/边缘信息，因此 CPU 成本不是零；最大区域约束针对返回和处理的选区，来源仍是已合法提供给工具的当前帧。没有新增引擎查询。

CPU 演示证明数据链能够执行，不能证明模型会自然使用，也不能证明 018 的具体失败必然被避免。后续完整轨迹应寻找“当前 region 数据 → 实际函数参数 → 真实后续计算/行动”的证据，并单独解释保留了哪些错误和增加了哪些成本；分数变化仍要结合关卡覆盖、动作效率及预算看。不会以 API 名称出现次数代替真实程序消费。
