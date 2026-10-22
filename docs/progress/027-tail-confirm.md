# 027 进展 — COMPLETE，未复现，关闭

日期：2026-10-20。状态：**v2 COMPLETE，-5.98，未过预注册门，关闭014线**。

- 推送：`qingyu1232/arc3-027-tail-confirm v2`（teammateb），候选→基线，7254s/臂。
- v1曾因臂名`tail_80k_confirm`未进冻结白名单在preflight 43秒失败；v2改回`tail_80k`后跑满。
- 结果：baseline 50.43（112关8胜） vs tail_80k 44.45（101关7胜）；vc33 -32.14，历史驱动未复现。详见`research/notes/027/027-tail-confirm-results.md`，分析`experiments/027-analysis/summary.{json,md}`。
- 不建候选提交构建器，不提交。正式仍为009 v2 / 57101330 / public 31.16。
- 剩余探索预算只做028单案例（≤1h、≤2次调用），不阻塞。
