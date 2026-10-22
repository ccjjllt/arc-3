# 009 — 首次正式基线提交进展

日期：2026-10-12；最新结果核验：2026-10-13 08:56（Asia/Shanghai）。对应[计划](../plan/009-baseline-submission.md)。

状态：**Notebook v2的正式 submission 57101330 已 COMPLETE，public score 31.16。** 10/13公开榜快照为第247名、4221队；按当前队数估计金牌附近第18名36.98，前五门槛42.66。最终以有效队数、私榜和获奖条件为准。v1两次失败记录57092815/57096804保留；已修复补丁缺末尾换行的确定性构建错误，恢复原生Notebook cells。

## 正式成绩（10/13更新）

通过比赛 submission API 确认 COMPLETE及31.16，而非仅查询Notebook保存状态。正式版本仍为v2，SHA256 `203da467cb0534fdf50b5683a55a524e647023e0d490524c59f2fda9a73b5dd5`。平台未返回完成时间、私榜成绩或隐藏逐游戏轨迹；核验时间不是完成时间。[正式结果记录](../../experiments/009-public-result.json)与[原始API快照](../../research/snapshots/2026-10-13/submission-57101330.json)已保存。

榜单连续读取5页/500队，排名按返回顺序推导，不宣称下载了全部4221队。距当前金牌附近5.82分，距当前第五名11.50分，仅用于定位。005公开25游戏49.8997与此处隐藏public LB使用不同游戏，不能按差值定位某个机制或估计退化幅度。

另复核cd82：005成功运行在608秒才过首关；首300秒同样0关。009启动验证的300秒0关不构成性能回退证据。具体轨迹归因见[010本地诊断](../../research/notes/010/010-local-diagnostics.md)。本轮未再次提交同一版本；后续研究见[010决策](../../research/notes/010/010-research-decision.md)。

## v2实际GPU验证与正式提交（10/12 16:29更新）

Kaggle保存状态COMPLETE，`save-smoke-report.json`为passed。回拉全部25个cells与本地冻结版本逐项一致，GPU/断网/私有metadata正确。实际日志6.39秒确认`harness patch applied successfully`，GPU为NVIDIA RTX PRO 6000 Blackwell Server Edition；源配置、模型路径与manifest一致。模型health成功约591.03秒，随后开始300秒公开游戏窗口；含清理共912.66秒（约15.21分钟）。这次实际经过了v1缺陷所在的git apply步骤。

| 公开游戏 | 非RESET动作 | 完成关卡 | 结束状态 |
|---|---:|---:|---|
| sb26-7fbdac44 | 131 | 7/8 | 300秒预算结束后排空，cancelled |
| cd82-fb555c5d | 25 | 0/6 | 300秒预算结束，cancelled |

两局最后动作分别在250.79秒、289.11秒，均在预算内。sb26结束约311.36秒，其中约11秒为请求排空，没有预算后的真实动作。服务有连续生成和HTTP200，未发现OOM或致命异常；最终SIGTERM/exit -15为保存分支主动清理。既有启动告警不影响本轮实际模型调用。sb26动作账tokens28945、analyzer note35818，两口径分开保留；cd82为35255。此处用于验证实际执行，不能作为提分或隐藏榜成绩。

原始输出在`runs/009-v2-smoke/`，来源哈希、逐局数据和验证范围在`experiments/009-v2-smoke-analysis.json`。save结束后账户GPU快照余8.38h，见`009-v2-quota-after-smoke.json`，不是正式评测剩余时长。

确认旧两份均ERROR、无活动提交且当日允许1次后，提交准确的**Notebook v2**，不是再次提交v1。新ID57101330，已从提交历史确认PENDING、分数为空。见`experiments/009-v2-formal-submit.json`、`009-v2-submissions-after.json`及`009-v2-launch.json`。`009-launch.json`现指向v2，旧v1最终状态另存`009-v1-launch-final.json`。本轮没有重新push或修改已验证源码。

10/12 15:06查询确认第二次仍为同样的系统错误，原件`experiments/009-retry-failure-detail.json`。平台未提供正式rerun traceback。随后CPU复现找到了足以阻止v1启动的具体构建缺陷；这比平台笼统错误更具体，不能继续仅按平台故障处理。v1仅验证过save与CPU模拟，未实际执行git apply和完整GPU路径；这是此前验证范围的不足。

## v1补丁构建缺陷与v2验证

原始Notebook的`%%writefile`会由IPython处理代码单元文本。v1用`Path.write_text(patch_source)`直接保存了单元源码内容，而该源码最后没有换行。保持源字符串相同不等于保持实际生成文件相同。

CPU手动对照：v1生成补丁的`git apply --stat`和`git apply --check`均退出128，报告`corrupt patch ...:10086`；在同一补丁后追加换行后，临时源码树的`--check`通过。这是确定性代码错误，不需要模型或隐藏游戏即可复现。平台没有给出隐藏运行阶段，故不宣称它解释了所有平台内部细节。

此前“补丁源码哈希一致”的核对漏掉了IPython magic实际写文件的语义；这是本项目构建器引入的问题。v2恢复原`%%writefile`及普通代码单元，去掉所有新增的exec/compile/eval外壳。另一项发现是本地IPython9.6还会整理部分空白，因此仍须以Kaggle实际git apply成功及GPU运行作为验证，不能仅凭本地magic字节比较宣告成功。

v2源码：`203da467cb0534fdf50b5683a55a524e647023e0d490524c59f2fda9a73b5dd5`，25个cells（两个可读辅助单元加原23个单元）。nbformat格式检查和实际IPython转换后的13个code cells编译通过，顶层无新增exec/compile/eval调用。证据见`experiments/009-v2-manual-checks.json`。原v1归档保持不变；v2归档在`experiments/009-source-v2/`。

v2保存运行会真正加载同一模型，health返回200后才开始两个公开游戏sb26/cd82的300秒窗口；每局必须有生成tokens、非RESET动作且状态为won/cancelled，才生成官方保存占位文件。save启动最多1500秒、总上限2400秒，只清理该会话自己启动的模型进程组。正式评测仍原gateway、1pass/120逻辑并发/31920秒，平台上限32400秒。实际运行状态见`experiments/009-v2-launch.json`；未通过该GPU验证前不再正式提交。

[私有Notebook](https://www.kaggle.com/code/ccjjllt/arc3-009-baseline-submission)；[比赛提交记录](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/submissions)。

## 首次失败诊断与有限重试（10/12 13:29更新）

Kaggle SDK GetSubmission返回57092815为ERROR，具体`error_description`为：

> A system error. Please try resubmitting to resolve the error and contact Kaggle Support if it persists.

原件在`experiments/009-failure-detail.json`。平台没有提供Python traceback、OOM或具体运行阶段，因此目前只能确认平台将其归类为系统错误，不能断言模型尚未运行，也不能证明所有代码路径没有潜在问题。

本次复核未发现可复现的009包装错误：真实本地deploy_target.pkl为32400秒；sandbox从真实模块读取inspect源码成功；精简CPU正式入口检查中globals和顶层await正常，正式配置为1 pass/120逻辑并发/31920秒每游戏。这些检查不替代GPU或真实gateway运行。

失败后`submission-limits`恢复为`numAllowedNow=1`。再次查询确认只有该失败记录、没有活动提交后，于13:29:38对**完全相同的v1**重试一次，submission ID57096804，已从提交历史确认PENDING。未修改算法、源码、模型或metadata，未重新push/save Notebook。证据：`experiments/009-system-error-retry.json`、`009-submission-latest.json`。首轮完整记录保留于`009-first-submission-record.json`；launch顶层指向当前重试。

本轮不循环重提。如同样系统错误再次出现，应继续取平台错误细节并判断是否需要联系Kaggle Support；本次没有代用户发送支持消息。

## 已核对

- 本赛CLI查询无提交记录，`submission-limits`返回`numAllowedNow=1`。原件：`experiments/009-submission-limits-before.json`。
- 启动前账户GPU余额约8.64h，原件：`experiments/009-quota-before.json`。这是全账户快照，不是009消耗。
- 两个已知近期其它项目Notebook只读检查为COMPLETE；未停止或修改它们。
- Kaggle MCP本轮传输失败，已切换到本机配置的CLI，读取成功。
- 官方starter支持普通save占位文件、正式gateway重新生成真实提交的分支。占位文件不是模型成绩。

## v1历史实现（已被v2替代）

- `scripts/build_submission.py`从固定Franzen v3完整23个cells构建独立正式Notebook；`src/arc3_research/submission_inputs.py`只定位附件，不导入研究干预。
- 普通save和正式rerun均核对输入marker；正式模式不依赖公开environment_files。save仅生成官方starter格式的非评分占位文件，模型和游戏均不运行。
- 正式模式保留原patch、serving、warmup RESET、1 pass、120逻辑并发/10活跃、每游戏31920秒和平台32400秒上限。仅通过真实COMPETITION gateway枚举游戏并生成最终提交。
- 原cell正文通过compile/exec保存，含顶层await的cell通过await eval执行，避免缩进外层if改变内嵌脚本字符串。两处shell magic改为checked subprocess。
- metadata移除原作者id_no，准确设置自己的私有ID、RTX PRO 6000、断网及原镜像。003/006/007/008均未接入。

Notebook 584125 bytes，SHA256：`f5fab5275d54b1f84817bd86e07f4eaf307dd604a11ad7286f943998543735e6`。构建与源码归档：`notebooks/009-baseline-submission/build-manifest.json`及`experiments/009-source/`。原003—007产物未覆盖。

## v1历史手动验证

全部11个code cells及内层代码编译通过；原patch完全一致，原cell6/10/12/14/18/22正文逐字一致。源、配置、Notebook及metadata哈希与manifest核对一致。独立审查未发现阻断问题。

本地执行全部生成cells的save分支，两种平台flag值（空字符串、false），使用仅marker的临时挂载目录；没有environment_files。输入成功定位，parquet可读取，mode为save_only，模型/benchmark全局未初始化。审计钩子拒绝网络和子进程，实际调用次数为0。见`experiments/009-build-manual-checks.json`、`experiments/009-save-manual-checks.json`。这些验证不代表GPU推理和隐藏评测已完成；未新增测试文件或CI。

## v1历史保存及正式提交

推送v1成功，准确源码全部23个cells已pull回逐项核对。实际保存metadata为私有、GPU开启、NvidiaRtxPro6000、断网。附件解析0.00935秒成功，采用嵌套路径；日志约10秒结束Notebook/HTML转换，没有加载模型或采取游戏动作。保存输出在`runs/009-baseline-submission-save/`，占位文件只有一行且明确标记为非评分。

实际命令：

```bash
kaggle kernels push -p notebooks/009-baseline-submission -t 32400 --accelerator NvidiaRtxPro6000
kaggle competitions submit arc-prize-2026-arc-agi-3 \
  -k ccjjllt/arc3-009-baseline-submission -v 1 -f submission.parquet \
  -m '009 frozen Franzen v3 baseline; no research interventions; notebook sha256 f5fab5275d54b1f84817bd86e07f4eaf307dd604a11ad7286f943998543735e6'
```

CLI提交响应只显示今日剩余0次，随后查询历史确认57092815已接受、状态PENDING、描述内hash匹配；没有重复提交。正式分数尚空，不将占位文件中的数值当成成绩。启动/提交证据：`experiments/009-launch.json`、`009-submissions-after.json`、`009-submission-limits-after.json`。

保存后账户快照剩余8.63h，见`experiments/009-quota-after-save.json`；账户差额不作为本次精确GPU耗时。尚未设置自动监控、未发起新的研究GPU任务。后续查询应使用比赛submissions状态；kernels status只会再次显示已完成的save运行。

## 下一步

首次正式评测链路及public score已确认。下一轮研究优先验证按旧动作检索完整动画的观察接口，008作为底层读取组件，不能因CPU表示检查通过而直接混入正式候选。调度经验表单独评估，不与观察改动叠加。奖金模型许可问题尚未在已核对讨论中获得主办方澄清，本次没有代用户发消息。详细证据与预算见010。
