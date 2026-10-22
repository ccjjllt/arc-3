# 034 强制切点诊断

产物状态：complete；会话状态：completed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`None`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 2 | 46 | None | null |
| A | su15-1944f8ab | complete | 0 | 17 | None | null |
| B | ft09-0d8bbf25 | complete | 0 | 17 | 2 | 0/2/0 |
| B | su15-1944f8ab | complete | 1 | 33 | 0 | 0/0/0 |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1715604, "total_tokens": 1769858, "completion_tokens": 54254, "reasoning_tokens": 46674}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1440748, "total_tokens": 1490309, "completion_tokens": 49561, "reasoning_tokens": 45501}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`{"prompt_tokens": 894055, "total_tokens": 945794, "completion_tokens": 51739, "reasoning_tokens": 48356}`；额外usage：`{"prompt_tokens": 13690, "total_tokens": 18569, "completion_tokens": 4879, "reasoning_tokens": 0}`；拒收：`0`。

B/su15-1944f8ab 主usage：`{"prompt_tokens": 1772317, "total_tokens": 1823094, "completion_tokens": 50777, "reasoning_tokens": 48386}`；额外usage：`{"prompt_tokens": 6551, "total_tokens": 8782, "completion_tokens": 2231, "reasoning_tokens": 0}`；拒收：`1`。

配对差值：
```json
{
  "ft09-0d8bbf25": {
    "B_minus_A_added_levels": -2,
    "B_minus_A_continuation_action_count": -29,
    "B_minus_A_elapsed_seconds": 0.04454029399948922,
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
    "B_minus_A_continuation_action_count": 16,
    "B_minus_A_elapsed_seconds": -13.769395707999593,
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
  "elapsed_seconds": 3495.83549284935,
  "session_gpu_hours_wall_clock": 0.971065414680375,
  "model_ready_seconds": 2559.5315248966217,
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
