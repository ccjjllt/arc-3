# 034 强制切点诊断

产物状态：complete；会话状态：completed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`None`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 0 | 25 | None | null |
| A | su15-1944f8ab | complete | 0 | 31 | None | null |
| B | ft09-0d8bbf25 | complete | 0 | 24 | 0 | 0/0/0 |
| B | su15-1944f8ab | complete | 0 | 40 | 0 | 0/0/0 |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 694576, "total_tokens": 750886, "completion_tokens": 56310, "reasoning_tokens": 53489}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1302903, "total_tokens": 1347259, "completion_tokens": 44356, "reasoning_tokens": 42737}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1198156, "total_tokens": 1251301, "completion_tokens": 53145, "reasoning_tokens": 47263}`；额外usage：`{"prompt_tokens": 4435, "total_tokens": 4574, "completion_tokens": 139, "reasoning_tokens": 0}`；拒收：`1`。

B/su15-1944f8ab 主usage：`{"prompt_tokens": 1569482, "total_tokens": 1614520, "completion_tokens": 45038, "reasoning_tokens": 43431}`；额外usage：`{"prompt_tokens": 6564, "total_tokens": 6695, "completion_tokens": 131, "reasoning_tokens": 0}`；拒收：`1`。

配对差值：
```json
{
  "ft09-0d8bbf25": {
    "B_minus_A_added_levels": 0,
    "B_minus_A_continuation_action_count": -1,
    "B_minus_A_elapsed_seconds": 13.444857361000686,
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
    "B_minus_A_continuation_action_count": 9,
    "B_minus_A_elapsed_seconds": -7.762687356999777,
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
  "elapsed_seconds": 4780.174383401871,
  "session_gpu_hours_wall_clock": 1.3278262176116307,
  "model_ready_seconds": 3828.870164871216,
  "gpu_sampling": {
    "path": "/kaggle/working/gpu-utilization.jsonl",
    "interval_seconds": 10.0,
    "sample_count": 488,
    "error_count": 0,
    "stopped": true
  },
  "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."
}
```

详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。
