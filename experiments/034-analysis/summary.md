# 034 强制切点诊断

产物状态：partial；会话状态：failed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`RuntimeError('Cache flush failed before executable_plan_B; refusing unmatched cache state.')`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 0 | 26 | None | null |
| A | su15-1944f8ab | complete | 0 | 16 | None | null |
| B | ft09-0d8bbf25 | not_started | None | None | None | null |
| B | su15-1944f8ab | not_started | None | None | None | null |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1035344, "total_tokens": 1088944, "completion_tokens": 53600, "reasoning_tokens": 49437}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1414469, "total_tokens": 1461733, "completion_tokens": 47264, "reasoning_tokens": 45057}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`null`；额外usage：`null`；拒收：`None`。

B/su15-1944f8ab 主usage：`null`；额外usage：`null`；拒收：`None`。

配对差值：
```json
{
  "ft09-0d8bbf25": {
    "B_minus_A_added_levels": null,
    "B_minus_A_continuation_action_count": null,
    "B_minus_A_elapsed_seconds": null,
    "restored_equal": {
      "grid_sha256": null,
      "messages_sha256": null,
      "functions_sha256": null,
      "branch_source_code_sha256": null,
      "prefix_recorded_actions": null
    }
  },
  "su15-1944f8ab": {
    "B_minus_A_added_levels": null,
    "B_minus_A_continuation_action_count": null,
    "B_minus_A_elapsed_seconds": null,
    "restored_equal": {
      "grid_sha256": null,
      "messages_sha256": null,
      "functions_sha256": null,
      "branch_source_code_sha256": null,
      "prefix_recorded_actions": null
    }
  }
}
```

成本：
```json
{
  "elapsed_seconds": 2739.144251346588,
  "session_gpu_hours_wall_clock": 0.76087340315183,
  "model_ready_seconds": 2274.734953403473,
  "gpu_sampling": {
    "path": "/kaggle/working/gpu-utilization.jsonl",
    "interval_seconds": 10.0,
    "sample_count": 282,
    "error_count": 0,
    "stopped": true
  },
  "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."
}
```

详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。
