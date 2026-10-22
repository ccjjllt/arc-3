# 020 社区验证集：固定来源、家族划分与 CPU 接口检查

日期：2026-10-19，Asia/Shanghai。**固定的 40 个社区游戏全部通过本地 CPU 加载/接口 smoke：12 个开发、12 个预留、16 个冻结。** 没有调用模型、启动 GPU、读取游戏实现来编写解法，或计算“官方分数”。这个结果只说明测试过的 API 路径可运行，不证明游戏可解、足够难或适合隐藏榜单。

## 来源与 inventory

来源为 [theredbluepill/arc-interactive](https://github.com/theredbluepill/arc-interactive/tree/02152bc4806869ace6ef167468970ca84bac0c5a)，固定 commit `02152bc4806869ace6ef167468970ca84bac0c5a`。压缩包 6,189,547 bytes，SHA256 `2a0bb24cf1fc1c9db4da71048d0e9641610969d6735c494e5f60bb8c49119949`；本次临时解压目录为 `/tmp/arc3-community-02152bc48068`。完整 GitHub tree 未截断，含 1,404 个条目；所有普通文件均在正式 smoke 前以 Git blob SHA1 对照固定 tree，未展开 archive symlink。

根目录 [LICENSE](https://github.com/theredbluepill/arc-interactive/blob/02152bc4806869ace6ef167468970ca84bac0c5a/LICENSE) 为 MIT，版权行是 ARC Interactive 2026。本地保留了原件；这是仓库许可证记录，不替代参赛资格判断。

| 口径 | 数量 |
|---|---:|
| `environment_files/<stem>/<version>/metadata.json` | 252 |
| 安装包 / stem 目录 / 唯一完整 game_id | 各 252 |
| 两字母前缀族 | 153 |
| `GAMES.md` 有效表格行 / 唯一 stem | 各 249 |
| metadata 有、registry 无 | `ft09`、`ls20`、`vc33` |
| 排除 | 3 个熟悉官方游戏 + `ez01`–`ez04` 四个教程 |
| 剩余包 | 245 |
| 保守合并后的族组 | 47 |
| 本轮筛选 | 40 个族组各 1 个代表 |

不要把 README/registry 的宣传数量当可安装数量。计数来自目录与 metadata；`GAMES.md` 只用来核对 registry、教程和分组。metadata 的 `baseline_actions` 与 `training_metadata.action_space` 也不是运行时合法动作表：**只信当前 observation 的 `available_actions`**。作者的 baseline 数列尚无可信人类最优动作依据，本轮不据此汇报 AE、官方分数或排行榜等价值。

完整来源账本与结果在 [020-community](../../../experiments/020-community/)：`acquisition.json`、`source-tree.json`、`inventory.json`、`split-frozen.json`、`smoke-summary.json` 和 `validation.json`。`source-metadata/` 中的 LICENSE、GAMES、README、pyproject 和模板是研究者资料，不能传入 solver prompt。

## 家族与冻结规则

先将所有相同两字母前缀绑定，再按公开 registry/metadata 加保守跨前缀组，例如推箱相关、连线、沙堆、桥建造等。完整 merge 表和每个成员 ID 都在机器文件中。这里有意采用较宽分组，**不是阅读实现后证明的代码谱系或严格统计独立性**；仍可能存在未识别的跨族相似性。

代表选择和分组抽样均使用固定 `SHA256` 排序种子 `arc3-community-020-family-split-v1`；按七个宽类别轮转选择 40 个族组各 1 代表，再固定 16 个冻结、12 个开发、12 个预留。分组覆盖全部 245 个合格 ID：一个族的未选变体也绑定同一侧；剩余 7 个未筛族列为 `unscreened_reserve`。不因 smoke 输赢、画面变化或错误重选游戏。

划分在首次 reset 前保存；SHA256 为 **`ad16158ca664daaf107e228837ec6861566ad047aabec36ea15fc280c56d6230`**。最终验证确认所有 40 个代表家族不重叠，12/12/16 数量一致，全部排除项均未进入。

| 用途 | 完整 game_id |
|---|---|
| 开发 12 | `tt03-63be02fb`, `wk01-63be02fb`, `tg01-63be02fb`, `ms04-v1`, `ll04-v1`, `ff03-63be02fb`, `sp01-63be02fb`, `sn01-63be02fb`, `cr01-63be02fb`, `pt01-63be02fb`, `hn01-v1`, `ih01-v1` |
| 预留 12 | `dv01-63be02fb`, `lk01-v1`, `ml02-63be02fb`, `rn01-v1`, `ng04-v1`, `lw01-63be02fb`, `rs04-v1`, `tw01-63be02fb`, `em01-63be02fb`, `ck04-v1`, `ex01-63be02fb`, `rz01-63be02fb` |
| 冻结 16 | `sv02-63be02fb`, `mm03-63be02fb`, `av01-63be02fb`, `as01-63be02fb`, `at01-v1`, `wm01-63be02fb`, `bn01-63be02fb`, `gp03-63be02fb`, `ph04-v1`, `mc01-63be02fb`, `wa01-63be02fb`, `cx01-v1`, `eg01-v1`, `fe02-v1`, `pk01-v1`, `sr01-v1` |

模型实验先限于开发 12。预留 12 的使用需在看其模型结果前明确用途；冻结 16 应在候选、预算、指标、停止规则全部锁定后才运行，不能用冻结表现回头选择提示或阈值。它们是本项目未调参的公开社区 holdout，不是模型预训练绝对未见或官方私有测试集。

## 实际 CPU 检查与边界

每游戏独立 CPU 子进程，seed `200019`，最多 30 秒，最多四并发。仅调用 SDK 正常 `Arcade(...OFFLINE).make()`、`reset()`、最多 3 次 `step()` 和再次 `reset()`。动作优先序固定为 `6,1,5,7,2,3,4`，只挑当前合法项；ACTION6 固定点当前完整画面中心，显式传 `x/y`。不解释画面、不看目标或搜索解法。终态即停止后续动作；落盘只有画面 hash/尺寸及公共状态，不保存像素内容供研究者挑题。

| 检查 | 实际结果 |
|---|---:|
| 首次 reset 成功 | 40/40 |
| 完成合法交互和再次 reset | 40/40 |
| 合法 step 调用 | 118 |
| 初始画面 | 全部 1 帧、64×64、整数色板 0–15 |
| 至少一次像素改变 | 35/40 |
| 再次 reset 像素与首次完全一致 | 29/40 |
| timeout / 模型调用 / GPU 启动 | 0 / 0 / 0 |
| 四并发 smoke 墙钟 | 约 2.74 秒（不含此前下载/准备） |

一个游戏在首个合法动作后进入 `GAME_OVER`，因此总动作数为 118。这是合法 API 结果，不是加载失败，更不是该游戏不可解。五个游戏在这些固定动作后画面不变，也没有被筛掉。再次 reset 的像素不同不自动证明引擎不确定：reset 不一定重建或重播随机数状态；未来 paired A/B 应新建相同 seed 的环境，而不是假定一次 reset 恢复完全相同局面。当前没有做 fresh-instance 确定性研究。

运行环境为 Python 3.12.14、`arc-agi 0.9.8`、`arcengine 0.9.3`、NumPy 2.3.5、Pydantic 2.14.1，复用 `/tmp/arc3-018-sdk` 与 `/tmp/arc3-018-check-deps`。**社区 pyproject 声明 NumPy ≥2.4.3，而本次用的是 2.3.5**：本报告仅证明当前复用环境可执行这些接口，不声称满足上游完整依赖约束。转入最终部署环境后，应按冻结依赖再跑同一 40 项 smoke。

首次 smoke 的适配器把 SDK `GameAction` 当成 IntEnum，导致所有游戏 reset 成功后、实际 step 前报错。已改成 SDK 明确的 `GameAction.ACTIONn` 成员并保留 `smoke-v0-adapter-enum/`、对应 summary；随后原 40 项全部通过，未改变 split、seed 或动作规则。此失败属于我们的接口实现，不能算成社区游戏不兼容。

## 接入现有 Agent 与文件边界

[community.py](../../../src/arc3_research/community.py) 提供可运行的 `CommunityEnvironment.reset/step` 和 `PublicObservation.to_solver()`。公开字段只有 `frames`、`available_actions`、`state`、`levels_completed`；保留所有返回帧和完整画面，删除标题、描述、`physics_rules`、registry、解法与内部 level data。它目前是独立 CPU API 适配器，**不是已经接入 ToolAgent 的完整 TAAF `Game` 替代类**。

现有 [run_arm.py](../../../src/arc3_research/run_arm.py:160) 已通过 `ARC3_RESEARCH_ENV_DIR` 选择离线环境目录，并按完整 ID 构造 `taaf.game_api.GameAPI(..., ArcadeSpec(...OFFLINE))`。后续独立社区 runner 可沿用该 GameAPI/ToolAgent 链：把目录设为固定源码的 `environment_files`，让引擎进程能导入仓库共享 helper，只从 `solver-allowlists.json` 取允许的 ID；保持默认 `hint=None`，不给模型 metadata 描述。需要另行禁止把社区 `base_actions_per_level` 自动计算的数当研究评分。主指标应明确为完成关卡数、全通、动作/tokens/墙钟，以及同条件 paired 差值；如使用公开总关数归一化，应命名为完成比例，不能冒称官方 AE。

上游 Kaggle 模板不直接复用：它将 `info.title/description` 写进模型 prompt，只截左上默认 8×8 区域，并在通用 `step` 调用时未为 ACTION6 传坐标。这里只把模板作为 API 合同证据；没有运行其中的 LLM 或 kbench 任务。

**删提示不等于强文件隔离。** 同机允许任意 Python 的 solver 若能访问引擎源目录，仍可能读实现；Python 私有属性也不是安全边界。当前 smoke 无 solver，子进程使用只保留 PATH/临时目录/locale 的环境，不传账户凭据；这不是容器化强隔离验证。后续盲测应把游戏引擎与有源文件的挂载放在独立进程/容器，通过只返回公共观测的协议交互，solver 的可读文件中不含社区源码、GAMES、metadata 描述和冻结结果；若暂未实现，应如实标明仅有协议/行为约束，不宣称已阻断任意读取。

## 可复现命令

源码压缩包固定 URL 记录于 `acquisition.json`；解压时拒绝路径逃逸且不展开 symlink。`inventory` 会核对 Git blob hash、创建新冻结划分；已有划分禁止覆盖。`smoke` 也拒绝覆盖现有结果，复跑时应使用新输出目录并复制相同 frozen manifest/tree/inventory，不能重选。

```bash
python3 scripts/prepare/prepare_020_community.py inventory \
  --source-root /tmp/arc3-community-02152bc48068

python3 scripts/prepare/prepare_020_community.py smoke \
  --source-root /tmp/arc3-community-02152bc48068 \
  --python /Users/zhaohuaxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  --dependency-path /tmp/arc3-018-sdk \
  --dependency-path /tmp/arc3-018-check-deps \
  --extra-path /Users/zhaohuaxiang/Library/Python/3.9/lib/python/site-packages \
  --workers 4
```

最后一条额外搜索路径只用来复用当前机器的纯 Python 请求依赖，放在 Python 3.12 标准 site-packages 之后；不建议作为部署依赖锁。CPU 报告保留了实际版本、进程耗时、输出 hash 和测试模块 hash。没有测试游戏全解、长期运行、模型工具调用或候选收益；这些仍是后续实验。
