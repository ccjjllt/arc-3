# 034 强制切点诊断

产物状态：complete；会话状态：completed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`None`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 0 | 11 | None | null |
| A | su15-1944f8ab | complete | 0 | 24 | None | null |
| B | ft09-0d8bbf25 | complete | 0 | 24 | 0 | 0/0/0 |
| B | su15-1944f8ab | complete | 1 | 24 | 0 | 0/0/0 |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 941487, "total_tokens": 995795, "completion_tokens": 54308, "reasoning_tokens": 49567}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1931629, "total_tokens": 1986762, "completion_tokens": 55133, "reasoning_tokens": 52862}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`{"prompt_tokens": 996838, "total_tokens": 1046371, "completion_tokens": 49533, "reasoning_tokens": 45371}`；额外usage：`{"prompt_tokens": 12709, "total_tokens": 16124, "completion_tokens": 3415, "reasoning_tokens": 0}`；拒收：`1`。

B/su15-1944f8ab 主usage：`{"prompt_tokens": 1389235, "total_tokens": 1440171, "completion_tokens": 50936, "reasoning_tokens": 48840}`；额外usage：`{"prompt_tokens": 11580, "total_tokens": 14791, "completion_tokens": 3211, "reasoning_tokens": 0}`；拒收：`1`。

配对差值：
```json
{
  "ft09-0d8bbf25": {
    "B_minus_A_added_levels": 0,
    "B_minus_A_continuation_action_count": 13,
    "B_minus_A_elapsed_seconds": 0.020885897999960434,
    "restored_equal": {
      "grid_sha256": true,
      "messages_sha256": true,
      "functions_sha256": true,
      "branch_source_code_sha256": true,
      "prefix_recorded_actions": true
    }
  },
  "su15-1944f8ab": {
    "B_minus_A_added_levels": 1,
    "B_minus_A_continuation_action_count": 0,
    "B_minus_A_elapsed_seconds": 1.7340359949998856,
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
  "elapsed_seconds": 2654.299731492996,
  "session_gpu_hours_wall_clock": 0.7373054809702767,
  "model_ready_seconds": 1733.534568309784,
  "gpu_sampling": {
    "path": "/kaggle/working/gpu-utilization.jsonl",
    "interval_seconds": 10.0,
    "sample_count": 276,
    "error_count": 0,
    "stopped": true
  },
  "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."
}
```

详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。
