# 033 控制器纠错实际诊断

候选单臂，无新配对基线；不计算A/B涨分。

修复状态：`full_frame_pixel_contract_passed_and_delivered`。全帧像素合同两次通过：**True**；这不代表P4/pieces/target语义修好。

真实新增关：0；续跑动作：26；下一真实主请求含准确结果：True。

续跑耗时：450.04435483999987秒，其中修复：28.70655129700026秒；二者不可相加。

| token口径 | 记录usage |
|---|---|
| 修复请求 | {"prompt_tokens": 58774, "completion_tokens": 3191, "total_tokens": 61965} |
| 随后主请求 | {"prompt_tokens": 1340900, "completion_tokens": 61089, "total_tokens": 1401989} |

超时未返回usage成本未知。完整响应、实际执行输出、验收拒因、函数回滚、计划/预测、真实动作与来源hash见summary.json。

人工审阅已完成：任务重建错分为17行/14列、59个图案、2个普通格子；后续主循环没有调用extract/rebuild。后续独立ASCII读取虽显示正确P4，但未见据此重算旧目标。实际26个动作、新增0关，本版不扩跑或提交。详见semantic-review.json及research/033-results-analysis.md。
