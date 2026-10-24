# 034 强制切点诊断

产物状态：complete；会话状态：completed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`None`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 0 | 8 | None | null |
| A | su15-1944f8ab | complete | 0 | 27 | None | null |
| B | ft09-0d8bbf25 | complete | 0 | 29 | 0 | 0/0/0 |
| B | su15-1944f8ab | complete | 0 | 22 | 0 | 0/0/0 |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1044187, "total_tokens": 1096161, "completion_tokens": 51974, "reasoning_tokens": 48468}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1234215, "total_tokens": 1286888, "completion_tokens": 52673, "reasoning_tokens": 50910}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1153519, "total_tokens": 1202754, "completion_tokens": 49235, "reasoning_tokens": 42430}`；额外usage：`{"prompt_tokens": 24316, "total_tokens": 28137, "completion_tokens": 3821, "reasoning_tokens": 0}`；拒收：`2`。

B/su15-1944f8ab 主usage：`{"prompt_tokens": 1352368, "total_tokens": 1400999, "completion_tokens": 48631, "reasoning_tokens": 47037}`；额外usage：`{"prompt_tokens": 23636, "total_tokens": 27864, "completion_tokens": 4228, "reasoning_tokens": 0}`；拒收：`2`。

配对差值：
```json
{
  "ft09-0d8bbf25": {
    "B_minus_A_added_levels": 0,
    "B_minus_A_continuation_action_count": 21,
    "B_minus_A_elapsed_seconds": -0.03127433100007693,
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
    "B_minus_A_continuation_action_count": -5,
    "B_minus_A_elapsed_seconds": -0.02847461099963766,
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
  "elapsed_seconds": 2554.8297295570374,
  "session_gpu_hours_wall_clock": 0.7096749248769548,
  "model_ready_seconds": 1631.9739072322845,
  "gpu_sampling": {
    "path": "/kaggle/working/gpu-utilization.jsonl",
    "interval_seconds": 10.0,
    "sample_count": 266,
    "error_count": 0,
    "stopped": true
  },
  "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."
}
```

详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。
