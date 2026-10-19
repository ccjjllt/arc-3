# 022 — 社区开发集上的现有 Agent

日期：2026-10-19。状态：**v4 COMPLETE。** RTX PRO 6000，97887 MiB。12 个开发游戏、1800 秒，退出码 0。全通 10/12，完成 55/64 关，动作 2133。没走完的是 ih01（0/7）和 tt03（1/3）。score 0.00 是因为开局前丢掉了不可靠的社区基线，不是官方效率。详见 [社区结果](../../research/022-community-dev-results.md)。冻结 16 和预留 12 没有挂上。

数据集 `jiyujia/arc3-community-dev-02152bc` 只含开发 12 个家族的环境目录，没有 GAMES.md，也没有冻结游戏。本地 CPU 用离线 Arcade 对 `tt03` 和 `pt01` 做了 reset 加一次合法动作，观察只有 `frames`、`available_actions`、`state`、`levels_completed`。配置若混入冻结 ID 会被拒绝。

v1 失败原因：preflight 在 Kaggle 上读取仓库里的 allowlist 文件，该文件没有打进 Notebook。v2 改为使用配置里已经嵌入的开发名单，本地有分割文件时再对照。Notebook SHA256 `36ebe69a0f865eefac8d3b6502adbfb190d7d5d50486338154f20f06126236d6`。022 探针或 019 GPU 结束后再上传这一版。引擎分数不能当成官方 AE。
