# 027 — 014 tail 单因素确认（一次，不做参数搜索）

状态：**已准备，未推送**。配置 `experiments/027-tail-confirm.json`，`build_experiment` 已过（16 cells）。

## 为何再做一次
- 014历史：47.1991→48.6390（+1.4399），改动集中，值得有限复核。
- 风险：vc33单题贡献+3.1611，去掉后其余24题-1.7929。当时按原规则淘汰合理；本次为新的单次确认，不改判旧结果。

## 固定配置
- 全25题、10路并行、每臂7254秒，`hard_limit 18000`，与014/025同预算口径。
- 只切一个tail参数：`tail_80k_confirm（ARC3_PRIORITY_TAIL_LOOKUP=1）vs baseline（remaining）`，PACE=0，其余干预全关。
- 执行顺序改为**候选→基线**，减固定顺序影响。`arm_order` 已反转。
- 预估约4.3–4.8 GPU小时（排期估算，非计费承诺）。

## 预注册标准（看结果前固定）
- 主指标：官方计分口径平均分（RHAE/AE）。
- 同时报告关键胜负题、完成度、运行风险；不要求所有辅助指标同时上涨；结果出来后不换标准。
- 只确认一次：复现收益→保留为正式提交候选；转负/优势消失→关闭，不做第三轮搜索。
- vc33敏感性必披露。

## 提交封装（与实验并行）
- 以009 v2构建器为底座（`scripts/build_submission.py` + `experiments/009-baseline-submission.json`），已在`/tmp/arc3-009-check`离线验出25 cells notebook。
- 检查：离线启动、评测接口、超时退出、sb26+cd82 300s save smoke、placeholder仅smoke通过后写。
- 只有027复现收益才定制候选提交构建器并走save smoke→正式submission；否则不花提交次数。

## 当前产物
- `experiments/027-tail-confirm.json`（新建）
- `/tmp/arc3-027-check/experiment.ipynb`（构建验证，未推送）
- 未创建competition submission；正式基线仍为009 v2 / 31.16。
