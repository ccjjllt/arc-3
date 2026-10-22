# 034 强制切点诊断

产物状态：complete；会话状态：completed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`None`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 0 | 31 | None | null |
| A | su15-1944f8ab | complete | 0 | 15 | None | null |
| B | ft09-0d8bbf25 | complete | 0 | 24 | 0 | 0/0/0 |
| B | su15-1944f8ab | complete | 1 | 28 | 0 | 0/0/0 |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1695623, "total_tokens": 1748580, "completion_tokens": 52957, "reasoning_tokens": 47900}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1334124, "total_tokens": 1388718, "completion_tokens": 54594, "reasoning_tokens": 52359}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`{"prompt_tokens": 742801, "total_tokens": 788556, "completion_tokens": 45755, "reasoning_tokens": 43060}`；额外usage：`{"prompt_tokens": 61612, "total_tokens": 65708, "completion_tokens": 4096, "reasoning_tokens": 4097}`；拒收：`1`。

B/su15-1944f8ab 主usage：`{"prompt_tokens": 2615861, "total_tokens": 2657547, "completion_tokens": 41686, "reasoning_tokens": 39099}`；额外usage：`{"prompt_tokens": 89613, "total_tokens": 93709, "completion_tokens": 4096, "reasoning_tokens": 4097}`；拒收：`1`。

配对差值：
```json
{
  "ft09-0d8bbf25": {
    "B_minus_A_added_levels": 0,
    "B_minus_A_continuation_action_count": -7,
    "B_minus_A_elapsed_seconds": -3.979751999999735,
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
    "B_minus_A_continuation_action_count": 13,
    "B_minus_A_elapsed_seconds": 0.044797673000175564,
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
  "elapsed_seconds": 3498.25040102005,
  "session_gpu_hours_wall_clock": 0.9717362225055695,
  "model_ready_seconds": 2571.2294692993164,
  "gpu_sampling": {
    "path": "/kaggle/working/gpu-utilization.jsonl",
    "interval_seconds": 10.0,
    "sample_count": 360,
    "error_count": 0,
    "stopped": true
  },
  "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."
}
```

详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。
