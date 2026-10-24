# 034 强制切点诊断

产物状态：complete；会话状态：completed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`None`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 1 | 51 | None | null |
| A | su15-1944f8ab | complete | 0 | 20 | None | null |
| B | ft09-0d8bbf25 | complete | 0 | 26 | 0 | 0/0/0 |
| B | su15-1944f8ab | complete | 0 | 11 | 0 | 0/0/0 |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 955009, "total_tokens": 1006787, "completion_tokens": 51778, "reasoning_tokens": 47799}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1556047, "total_tokens": 1603975, "completion_tokens": 47928, "reasoning_tokens": 39695}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`{"prompt_tokens": 884206, "total_tokens": 929328, "completion_tokens": 45122, "reasoning_tokens": 39986}`；额外usage：`{"prompt_tokens": 26572, "total_tokens": 30834, "completion_tokens": 4262, "reasoning_tokens": 0}`；拒收：`2`。

B/su15-1944f8ab 主usage：`{"prompt_tokens": 1582754, "total_tokens": 1629882, "completion_tokens": 47128, "reasoning_tokens": 38241}`；额外usage：`{"prompt_tokens": 25446, "total_tokens": 30066, "completion_tokens": 4620, "reasoning_tokens": 0}`；拒收：`1`。

配对差值：
```json
{
  "ft09-0d8bbf25": {
    "B_minus_A_added_levels": -1,
    "B_minus_A_continuation_action_count": -25,
    "B_minus_A_elapsed_seconds": -0.012699147999910565,
    "restored_equal": {
      "grid_sha256": true,
      "messages_sha256": true,
      "functions_sha256": true,
      "branch_source_code_sha256": true,
      "prefix_recorded_actions": true
    }
  },
  "su15-1944f8ab": {
    "B_minus_A_added_levels": 0,
    "B_minus_A_continuation_action_count": -9,
    "B_minus_A_elapsed_seconds": -2.0129678440002863,
    "restored_equal": {
      "grid_sha256": true,
      "messages_sha256": true,
      "functions_sha256": true,
      "branch_source_code_sha256": true,
      "prefix_recorded_actions": true
    }
  }
}
```

成本：
```json
{
  "elapsed_seconds": 2173.854351758957,
  "session_gpu_hours_wall_clock": 0.6038484310441546,
  "model_ready_seconds": 1248.2175436019897,
  "gpu_sampling": {
    "path": "/kaggle/working/gpu-utilization.jsonl",
    "interval_seconds": 10.0,
    "sample_count": 228,
    "error_count": 0,
    "stopped": true
  },
  "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."
}
```

详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。

跨文件补记：A共享requests.jsonl中一条尾响应按7字段唯一匹配su15最后请求，补计94089输入／8447输出／8370推理tokens。逐题4条表面缺口校正为3，仍非完整usage，不称4次超时。详见main-response-reconciliation.json。
