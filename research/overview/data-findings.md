# ARC-AGI-3 比赛公开数据与接口实查

检查日期：2026-10-10（Asia/Shanghai）。本文依据实际下载的 Kaggle 比赛数据、其中 SDK 的通用接口/评分实现、公开元数据，以及一次手动启动的观察型随机策略实验。未检查各游戏的机制源码，未访问隐藏游戏，未编写或执行测试套件。

## 1. 下载内容与可复现定位

后续推荐使用 CLI 2.2.4 帮助页公开的规范调用：

```bash
kaggle competitions download arc-prize-2026-arc-agi-3 -p research/data
```

本次实际执行并成功下载的命令带旧式 `-c`：`kaggle competitions download -c arc-prize-2026-arc-agi-3 -p research/data`。已核对本机安装的 `kaggle/cli.py` 第 210–216 行：download parser 同时接受位置参数和 `-c/--competition`，后者使用 `help=argparse.SUPPRESS`，所以不会显示在帮助页。这是兼容别名，不是记错执行结果；新的使用说明统一采用位置参数。

首次普通沙盒联网调用因 `api.kaggle.com` DNS 不可达失败；下载通过正常网络审批后成功。没有修改 Kaggle 凭据。下载包为 `research/data/arc-prize-2026-arc-agi-3.zip`，44,339,942 bytes；解压前总大小 48,969,679 bytes，共 148 文件，SHA-256：

```text
c72400a32db5e48da9014baf893b48016b300e9a6a77bd5d505de2b1ec61d645
```

| 目录 | 文件数 | 实际用途 |
|---|---:|---|
| `environment_files` | 50 | 25 个公开游戏，各一个环境实现文件和一个 `metadata.json` |
| `arc_agi_3_wheels` | 31 | 离线安装包，核心为 `arc_agi==0.9.8`、`arcengine==0.9.3` |
| `ARC-AGI-3-Agents` | 67 | 官方 agent 模板快照，含 28 个 `.git` 元数据文件 |

解压目录为 `research/data/extracted/`，跳过所有路径包含 `.git` 的条目，并拒绝绝对路径和 `..` 路径。上游自带的测试文件只是数据包中的原始文件，没有执行或扩展。上游 agent 快照的 main commit（只读取 zip 中 ref 文本）为 `135f20aaf44f13341ebc425666bf03b5cac58d3c`。完整文件大小、wheel 版本/hash、game 元数据及观察汇总见 [data-inventory.json](../data-inventory.json)。

本包没有传统监督学习 `train.csv`/`test.csv`/`sample_submission.csv`。其训练资源是可交互环境和示例 agent。元数据内的 `date_downloaded` 均为 2026-04-08，这是上游生成资产的时间；本次获取日期是 2026-10-10，不能混为一谈。

## 2. 数据分布

25 个公开游戏，共 183 关；每游戏关卡数分布为 6 关 × 9、7 关 × 5、8 关 × 6、9 关 × 4、10 关 × 1。所有元数据的 `baseline_actions` 长度与运行后观察到的 `win_levels` 相同。

逐关 human baseline 总计 17,135 动作，中位数 60、均值 93.63、范围 6–578；首关 baseline 中位数 30。这些是官方元数据提供的基准，不是本次 agent 的成绩，不应据此推断人类轨迹或最优解。

元数据标签为 `keyboard_click` 13、`click` 7、`keyboard` 4、无标签 1。但标签与实际动作集不一一对应：`lf52` 的标签是 click，初始观察却允许 1/2/3/4/6/7；`re86` 标 keyboard_click，初始动作却没有 6；`tu93` 同样标 keyboard_click，但只有 1/2/3/4。策略必须每步读取 `available_actions`，不能用标签或游戏 ID 硬编码动作空间。

| game/version | 关卡 | 元数据标签 | 初始 available_actions | 全关 baseline 动作和 | 随机探针最终帧未变 |
|---|---:|---|---|---:|---:|
| ar25-0c556536 | 8 | keyboard_click | 1,2,3,4,5,6,7 | 748 | 15/80 |
| bp35-0a0ad940 | 9 | keyboard_click | 3,4,6,7 | 651 | 15/80 |
| cd82-fb555c5d | 6 | keyboard_click | 1,2,3,4,5,6 | 171 | 19/80 |
| cn04-2fe56bfb | 6 | keyboard_click | 1,2,3,4,5,6 | 789 | 11/80 |
| dc22-fdcac232 | 6 | keyboard_click | 1,2,3,4,6 | 1,228 | 22/80 |
| ft09-0d8bbf25 | 6 | 无 | 6 | 208 | 77/80 |
| g50t-5849a774 | 7 | keyboard | 1,2,3,4,5 | 879 | 13/80 |
| ka59-38d34dbb | 7 | keyboard_click | 1,2,3,4,6 | 730 | 7/80 |
| lf52-271a04aa | 10 | click | 1,2,3,4,6,7 | 1,339 | 58/80 |
| lp85-305b61c3 | 8 | click | 6 | 388 | 79/80 |
| ls20-9607627b | 7 | keyboard | 1,2,3,4 | 776 | 0/80 |
| m0r0-492f87ba | 6 | keyboard_click | 1,2,3,4,5,6 | 1,107 | 21/80 |
| r11l-495a7899 | 6 | click | 6 | 233 | 0/80 |
| re86-8af5384d | 8 | keyboard_click | 1,2,3,4,5 | 1,255 | 0/80 |
| s5i5-18d95033 | 8 | click | 6 | 638 | 0/80 |
| sb26-7fbdac44 | 8 | keyboard_click | 5,6,7 | 213 | 50/80 |
| sc25-635fd71a | 6 | keyboard_click | 1,2,3,4,6 | 350 | 23/80 |
| sk48-d8078629 | 8 | keyboard_click | 1,2,3,4,6,7 | 1,070 | 28/80 |
| sp80-589a99af | 6 | keyboard_click | 1,2,3,4,5,6 | 518 | 0/80 |
| su15-1944f8ab | 9 | click | 6,7 | 361 | 52/80 |
| tn36-ef4dde99 | 7 | click | 6 | 317 | 0/80 |
| tr87-cd924810 | 6 | keyboard | 1,2,3,4 | 414 | 0/80 |
| tu93-0768757b | 9 | keyboard_click | 1,2,3,4 | 462 | 0/80 |
| vc33-5430563c | 7 | click | 6 | 447 | 0/80 |
| wa30-ee6fef47 | 9 | keyboard | 1,2,3,4,5 | 1,843 | 14/80 |

19/25 个游戏的初始动作集中有 ACTION6，其中 6 个只有 ACTION6。以方向键为中心的通用 baseline 会遗漏公开数据中大部分可交互类型。表中“最终帧未变”仅表示两次返回的最后一帧像素完全相同，不能认定内部状态未变或动作无效。

## 3. 实际 SDK API 与观测约束

核心包需要 Python >=3.12。比赛 wheel 目录中二进制包为 Linux x86_64 / CPython 3.12，例如 numpy、pydantic_core、Pillow；不能直接把整个 wheel 目录离线安装到 macOS ARM。Kaggle 容器应优先使用比赛 wheel；本地探针固定两项核心 wheel，同时从包源安装 macOS 对应依赖，并记录实际版本。

最小公开环境交互：

```python
from pathlib import Path
import arc_agi
from arcengine import GameAction, GameState

arc = arc_agi.Arcade(
    operation_mode=arc_agi.OperationMode.OFFLINE,
    environments_dir=str(Path("research/data/extracted/environment_files").resolve()),
)
env = arc.make("ls20-9607627b", seed=0)
obs = env.observation_space  # make() 已自动 reset
legal_actions = env.action_space
obs = env.step(GameAction.ACTION1)
scorecard = arc.get_scorecard()
```

| 接口 | 事实与实现影响 |
|---|---|
| `Arcade.get_environments()` | 本地返回公开 EnvironmentInfo 列表；线上 competition API 会隐藏 `baseline_actions`、private tags 等字段 |
| `Arcade.make(game_id, seed=0, ...)` | 可给完整版本 ID；构造 Local/Remote wrapper 时已自动 reset，不要无理由多 reset |
| `env.observation_space` | 当前 `FrameDataRaw`，不是 Gym 的空间对象 |
| `env.action_space` | 由最新 observation 的 `available_actions` 转换为 GameAction 枚举列表 |
| `env.step(action, data={}, reasoning=None)` | 返回新 observation 或 `None`；ACTION6 的 data 为 `{"x": int, "y": int}`，坐标范围 0–63 |
| `obs.frame` | 一次动作返回的动画帧列表；本次所有最终帧均 64×64、int8，色号 0–15 |
| `obs.state` | `NOT_PLAYED`、`NOT_FINISHED`、`GAME_OVER`、`WIN` |
| `obs.levels_completed`, `obs.win_levels` | 已完成关卡数、全游戏关卡数；并非旧模板里的 score/win_score |
| `obs.full_reset` | reset 是否为全局重置；必须记录以正确解释动作计数与跨关记忆 |
| `GameAction` | RESET=0，ACTION1–5 简单动作，ACTION6 带点击坐标，ACTION7 简单动作；不能把 ACTION7 一律当 undo |
| `reasoning` | 通用 engine 要求 JSON 可序列化，最多 16 KiB；无需把全部历史塞入该字段 |

初始观察有 23 个游戏返回 1 帧、2 个返回 2 帧。本次 80 步探针中 14 个游戏出现多帧动作，最多一次动作 42 帧。最后一帧适合作为稳定状态输入，但中间帧可能揭示运动/碰撞机制，应允许压缩保留有信息量的变化，而不是误将帧数当动作数。

公开初始画面已按 SDK 原始 16 色映射导出供人工检查：[25 游戏初始帧拼图](../data/manual-probe-20261010-valid-scorecard/initial-frames-montage.png)。从画面可直接观察到细小符号、规则网格、分区画面以及边缘细条 UI；这支持对象/网格抽取和 UI 与主体分开建模的实验设计，但仅凭首帧不能确定各游戏规则。

本地 `OFFLINE` 使用公开环境文件；竞赛运行使用远程 wrapper 与被配置的比赛服务交互。`OPERATION_MODE=competition` 的环境变量优先级高于构造参数，不能用构造 OFFLINE 的代码绕过比赛模式。通用 competition API 禁止一局比赛创建多个 scorecard、禁止同一 scorecard 重新创建同一 game，以及比赛过程中查询隐藏 scorecard。策略只经公开 observation/action 接口与环境交互，不能把本地 `_game`、源代码、human baseline 当作隐藏评估输入。

## 4. 评分版本冲突：以下载 wheel 的实际实现单独记录

比赛 `data` 文本快照给出 `min(human_actions / agent_actions, 1)^2`。实际下载的 `arc_agi==0.9.8` 不是这个完整公式：

```text
若第 l 关完成且动作 a_l > 0：s_l = min((h_l / a_l)^2, 1.15)
否则：s_l = 0
游戏分数（0–1）= min( Σ_l l*s_l / Σ_l l,
                         Σ_{l: s_l>0} l / Σ_l l )
总分（0–100）= 100 * 各游戏分数的均值
```

证据：`research/data/sdk_inspection/arc_agi-0.9.8-py3-none-any/arc_agi/scorecard.py`，`EnvironmentScoreCalculator.add_level()` 第 148–183 行、`to_score()` 第 185–206 行、`from_scorecard()` 第 612–618 行。wheel METADATA changelog 明确写出 0.9.7（2026-04-14）将 level cap 从 100% 改为 115%，并增加按已完成关卡权重计算的 game cap；0.9.8（2026-04-17）修复 competition mode 全局 reset 问题。源码第 168 行“max 100”注释仍旧，执行代码第 171 行实际是 115，不应只读注释。

该实现与检查日官方 methodology 的新版表述一致，但尚未从私榜运行器确认隐藏评分版本。后续报告应写明 `SDK0.9.8 local AE`，保存每关完成/动作/重置原始记录，以便按照任一公式重算；不要把页面、SDK、隐藏评分三者强行视为同一版本。

研究含义：

- 8 关游戏只完成首关，即使达到 human baseline，最多只能获得该游戏 1/36≈2.78 分（0–100 刻度）；完成前 4 关的加权上限为 10/36≈27.78 分。持续通关与跨关学习比只刷首关更重要。
- 若一关花了 human baseline 的 2 倍动作，未触及 cap 时仅剩 25% 的关卡效率分。因此无限探索可以“发现规则”但伤害比赛指标，必须计算探索收益与动作成本。
- 超人表现的单关增益最多到 115%，并受完成进度的 game cap 限制；一味优化已会游戏的最短路径不应挤占扩大可解游戏覆盖面的资源。
- 普通 OFFLINE 多次完整游玩可能由 SDK 对同一游戏取最好 run；competition 不允许如此。验证不能通过反复 `make()` 同一游戏挑最高成绩来夸大效果。

## 5. 已完成的手动实验与真实结果

实验脚本：[data/manual_probe.py](../data/manual_probe.py)，它是可直接启动的观察型实验，不是测试文件。策略只在 `env.action_space` 内均匀选动作，ACTION6 的 x/y 在 0–63 独立均匀采样；每个 game 重建 `random.Random(20261010)`，environment seed=0，每游戏最多 80 次 step，GAME_OVER 后下一步 RESET。没有训练、搜索、提示模型或游戏专用逻辑。

本地安装的实际命令：

```bash
UV_CACHE_DIR=/private/tmp/arc3-data-uv-cache uv venv \
  --python /Users/zhaohuaxiang/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/bin/python3 \
  /private/tmp/arc3-data-inspection-venv

UV_CACHE_DIR=/private/tmp/arc3-data-uv-cache uv pip install \
  --python /private/tmp/arc3-data-inspection-venv/bin/python \
  research/data/extracted/arc_agi_3_wheels/arc_agi-0.9.8-py3-none-any.whl \
  research/data/extracted/arc_agi_3_wheels/arcengine-0.9.3-py3-none-any.whl

env -u ONLY_RESET_LEVELS MPLCONFIGDIR=/private/tmp/arc3-matplotlib \
  /private/tmp/arc3-data-inspection-venv/bin/python research/data/manual_probe.py
```

安装使用 Python 3.12.13、arc-agi 0.9.8、arcengine 0.9.3、numpy 2.5.3、pydantic 2.14.0、Flask 3.1.3。非核心依赖版本不同于 Kaggle 附带 wheel，因此本次数据反映公开 API 的本地行为；Kaggle 容器仍需用官方 wheel 手动运行一次以核对兼容性，不能把本地墙钟时间当线上吞吐指标。

有效结果目录：[manual-probe-20261010-valid-scorecard](../data/manual-probe-20261010-valid-scorecard/observations.json)。

| 指标 | 结果 |
|---|---:|
| scorecard 内游戏/关卡 | 25 / 183 |
| action 计数 | 2,000（含 11 次关卡 RESET，首次启动 RESET 不计入） |
| 完成关卡/完成游戏 | 0 / 0 |
| SDK 0.9.8 本地 AE | 0.0 |
| 与上一步最终帧完全相同 | 504/2,000 = 25.2% |
| GAME_OVER 后 RESET | 11 |
| 单次动作最大返回帧数 | 42 |

这是单 seed、很小预算的随机下界，只证明“接口可交互且盲目随机在本预算内没有完成关卡”；不证明某个研究方向无效，也不能外推所有随机策略都为 0。`ft09` 77/80、`lp85` 79/80 的最终帧未变化，说明全画布均匀点击在这些公开场景中很少改变可见画面。另一方面，若 UI 倒计时每步变化，低重复率并不表示有效探索，因此不能只优化像素新颖度。

输出包含：

- `observations.json`：版本、seed、预算、25 个 game 的观察统计。
- `events.jsonl`：每次 action/data、state、关卡完成数、帧数、变化像素数及最终帧 SHA-256。
- `scorecard.json`：SDK 实际返回的 25 游戏、183 关、2,000 动作完整计分记录。
- `initial-frames.npz` 与 `initial-frames-montage.png`：仅从公开 observation 导出的初始帧与人工检查图。

### 首次实验遇到并定位的问题

最初在 `OFFLINE + ONLY_RESET_LEVELS=true` 下执行同样策略，动作观察正常，但最终 SDK scorecard 为空（0 games、0 levels、0 actions）。结果保存在 `data/manual-probe-20261010/`，不能把它的 0 分当有效 baseline。

原因可由通用 SDK 直接解释：engine 在 `ONLY_RESET_LEVELS=true` 时首次 reset 也走 `level_reset()`，不产生 full_reset；离线 scorecard 因而没有注册首个 play。competition API 的初次创建路径有单独补偿，离线 wrapper 没有相同行为。取消该变量后手动重跑，得到非空有效 scorecard，25 游戏的观察统计一致。后续可使用干净环境变量的 OFFLINE 模式先完成首个 make；需要严格比赛 reset 语义时，优先经官方 competition server 手动核对，避免自行复制未验证的计分逻辑。

## 6. 官方示例模板的用途与局限

已读 agent base、Random 和 ReasoningAgent 的接口：

- `Random.MAX_ACTIONS=80`，但使用时间/hash 设 seed，并从整个 GameAction 枚举而非实际 available_actions 中选动作；不适合作为可复现的主要比较对象。本次合法动作随机 baseline 是独立写出的观察探针，不冒充官方 Random 的原样成绩。
- `ReasoningActionResponse.name` 只允许 ACTION1–4/RESET，漏掉 5/6/7；`ReasoningAgent` 使用外部 OpenAI client/o4-mini。该模板适合参考“假设/摘要/历史”结构，不能原样作为 Kaggle 离线推理器。
- 官方 README 仍有早期表单提交入口、旧模型/旧字段说明。提交路径与本轮比赛时限应以 Kaggle 当前官方 starter 和比赛页面为准。
- 本包不含 human demonstrations、逐步动作示范、自然语言规则或隐藏数据。human baseline 只有动作数量，不能代替轨迹监督。

## 7. 可选的低成本机制对照（尚未验证效果）

**项目研究主线以 [002-strategy-improvement](../../docs/plan/002-strategy-improvement.md) 为准：先复现 dfranzen v3 强基线，再依照失败轨迹研究目标/机制发现与证据复用。** 本节只提供可选、低成本的机制对照，不要求从零重写 agent，也不能把强基线已有的动画、差分、工具和规划能力算成新贡献。

若主线失败轨迹明确指向点击候选或观察表示问题，可用本次合法随机探针作机制下界，再增加一个最小对象候选对照：按最新 available_actions 分流；点击候选来自颜色连通域、网格单元、端点及边缘，保留少量全图探索避免漏掉无明显边界的控制区。用动作前后对象变化辅助区分主体、动画与 UI，并保留有信息量的中间帧。它们是本次观察提出的假设，尚无提升成绩。

可选对照保留逐关动作数与完成率、点击覆盖和最终帧变化，最终结论仍需回到固定 dfranzen v3 底座的同条件改动实验。参数只在部分公开游戏调整，按游戏而非按帧留出；公开本地分与 hidden leaderboard 分开报告。

不应仅因这个随机探针为 0 就扩大随机预算、从零训练或推断强基线的瓶颈。它只提供接口证据与低成本观察线索；对象候选是否值得加入主线、是否提升跨游戏完成率，需要强基线真实失败轨迹和人工启动的消融结果支持。
