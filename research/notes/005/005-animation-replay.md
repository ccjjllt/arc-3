# 005 — tn36非末动作暂态的独立CPU复现

日期：2026-10-11（Asia/Shanghai）。对应数据：[005-animation-replay.json](../../../experiments/005-animation-replay.json)。

**观察缺口确实可以复现：四次探测中的第一次点击返回7帧、包含256个暂态像素，但最终棋盘区域不变；后面三次点击均没有暂态。** 只看最后一次action的动画或只保留稳定末帧，会丢掉第一次点击产生的信息。

这是新建公开环境中的独立CPU复现，不是恢复005当时没有保存的中间帧，也不是研究效果或提分实验。

## 动作来源与执行范围

来源：`runs/005-full-baseline/baseline/tn36-ef4dde99_p0_requests.jsonl` 第11行，analysis_step=3、action=6。这条请求包含上一个Python snippet及其工具结果。snippet明确列出四个探测坐标：

```text
(55,35), (45,21), (45,36), (20,20)   # (row, col)
```

为重建相同的可见起点，先执行日志中此前的唯一动作 `(14,31)`。因此总共只有 **5次明确的MOUSE动作**，不执行日志里的Python循环、规划、搜索、函数定义或后续轨迹。

通过SDK发送 `GameAction.ACTION6`，把 `(row,col)`转换为 `data={"x":col,"y":row}`。使用本地已安装的 `/private/tmp/arc3-data-inspection-venv/bin/python`，没有新增安装。环境为OFFLINE、游戏 `tn36-ef4dde99`、独立 seed=0；`make()`已有初始reset，没有再插入额外RESET。

只使用公开SDK返回的 `observation.frame`，没有读取游戏实现文件 `tn36.py`，没有访问环境内部对象，没有调用模型或GPU。

## 实测结果

| 日志动作号 | 坐标(row,col) | SDK原始帧数 | helper报告暂态像素 | 暂态bbox | 最终全画面变化像素 | 去除4格边框后变化 |
|---|---|---:|---:|---|---:|---:|
| 1，前缀 | (14,31) | 1 | 0 | 无 | 1 | 0 |
| 2，四探测的第一项 | **(55,35)** | **7** | **256** | **[13,19,59,43]** | **1** | **0** |
| 3，第二项 | (45,21) | 1 | 0 | 无 | 4 | 3 |
| 4，第三项 | (45,36) | 1 | 0 | 无 | 4 | 3 |
| 5，第四项 | (20,20) | 1 | 0 | 无 | 1 | 0 |

bbox采用底座格式：**[top row, left col, bottom row, right col]，两端包含**。

初始帧及5个动作的最终帧，均与005 `artifacts/tn36-ef4dde99_p0_events.jsonl`保存的对应board逐像素一致。5次动作后均为 `NOT_FINISHED`、levels_completed=0。动作重放与统计约0.010秒，不计Python启动/import。

第一探测的7帧加上动作前帧，折叠相邻重复后共有8个状态。全画面最终仅有边框中的1像素变化，棋盘主体完全回到动作前；中间过程却存在256个改变至少两次的像素。因此这些信息不能由该动作最终帧差分恢复。

## 算法与底座一致性

直接导入Fran­zen已应用patch的通用动画helper：

```python
from inference.utils.animation import (
    normalize_frames, collapse_frames, summarize_animation,
    build_animation_view,
)
chain = collapse_frames(before_grid, normalize_frames(observation.frame))
summary = summarize_animation(chain)
```

文件：`research/runtime-bundle/src/ARC3-Inference/inference/utils/animation.py`，其SHA-256记录在JSON。

`collapse_frames`先放入动作前的grid，只折叠相邻重复帧；`summarize_animation`把每个像素跨相邻状态变化至少两次定义为transient，并返回数量与bbox。另用numpy对同一chain独立累计逐像素变化次数，得到同样的256和bbox。JSON保留每帧hash、每个折叠状态转换的变化像素数、暂态坐标及底座生成的timeline摘要。

单帧动作的helper原始返回值为`None`；表格中将它显示为“0/无”，JSON保留原始`null`，没有捏造动画摘要。

## 对006实现的意义

005第11行工具输出给第一点击的描述是 `NO-OP (executed, no change inside the board area)`。模型的自定义`log`只保存 `no_op`、`gameplay_changed`和稳定帧差分，没有保存这次调用的animation摘要。其后第三、第四个调用已把“最近一次action”的上下文推进；最后调用又是无暂态动作。

这支持一个有具体触发事实的最小实验：**在同一Python snippet内，对每次真实action调用返回的暂态事实分别保留，避免后续action把非末调用的事实覆盖掉。** 最小事实可以包括动作引用、frames、transient_pixels、bbox和可检索引用；原版已能计算这些值，不需要新增模型调用、不需要游戏ID/颜色硬编码，也不必每次输出完整中间帧。

此复现只证明“有真实暂态被末帧视角遗漏”的前提。是否应额外保留完整动画链、如何限制证据长度，以及模型看到事实后能否正确解释并增加通关，还需要单独实施和同条件实验。不能据此断言tn36的胜利规则、宣称006会提分，或把公开诊断游戏当未见留出。

## 边界

- 独立seed=0环境的可见端点与005一致，但005此处没有记录显式环境seed；端点相同不等于恢复当时中间帧或证明所有内部状态完全相同。
- 本地核心包为arc-agi0.9.8、arcengine0.9.3；实际Python/numpy/pydantic版本记录在JSON，不能用本地墙钟推断Kaggle性能。
- 本轮没有执行完整轨迹代码、没有训练、没有新GPU实验、没有修改005输出或底座实现。
