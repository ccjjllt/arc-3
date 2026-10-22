# 034 强制切点诊断

产物状态：complete；会话状态：completed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`None`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 2 | 33 | None | null |
| A | su15-1944f8ab | complete | 0 | 42 | None | null |
| B | ft09-0d8bbf25 | complete | 1 | 60 | 4 | 2/2/0 |
| B | su15-1944f8ab | complete | 0 | 41 | 0 | 0/0/0 |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1523033, "total_tokens": 1577557, "completion_tokens": 54524, "reasoning_tokens": 48006}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1972405, "total_tokens": 2023464, "completion_tokens": 51059, "reasoning_tokens": 48485}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1160734, "total_tokens": 1196577, "completion_tokens": 35843, "reasoning_tokens": 31923}`；额外usage：`{"prompt_tokens": 19449, "total_tokens": 22963, "completion_tokens": 3514, "reasoning_tokens": 0}`；拒收：`0`。

B/su15-1944f8ab 主usage：`{"prompt_tokens": 1156881, "total_tokens": 1192283, "completion_tokens": 35402, "reasoning_tokens": 33841}`；额外usage：`{"prompt_tokens": 9166, "total_tokens": 12449, "completion_tokens": 3283, "reasoning_tokens": 0}`；拒收：`1`。

配对差值：
```json
{
  "ft09-0d8bbf25": {
    "B_minus_A_added_levels": -1,
    "B_minus_A_continuation_action_count": 27,
    "B_minus_A_elapsed_seconds": -122.18383191800012,
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
    "B_minus_A_continuation_action_count": -1,
    "B_minus_A_elapsed_seconds": -0.027119214999856922,
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
  "elapsed_seconds": 3551.5422768592834,
  "session_gpu_hours_wall_clock": 0.9865395213498009,
  "model_ready_seconds": 2629.654679298401,
  "gpu_sampling": {
    "path": "/kaggle/working/gpu-utilization.jsonl",
    "interval_seconds": 10.0,
    "sample_count": 366,
    "error_count": 0,
    "stopped": true
  },
  "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."
}
```

详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。
