# 034 强制切点诊断

产物状态：complete；会话状态：completed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`None`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 0 | 29 | None | null |
| A | su15-1944f8ab | complete | 1 | 23 | None | null |
| B | ft09-0d8bbf25 | complete | 0 | 16 | 0 | 0/0/0 |
| B | su15-1944f8ab | complete | 0 | 42 | 0 | 0/0/0 |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 961622, "total_tokens": 1016222, "completion_tokens": 54600, "reasoning_tokens": 49984}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1765378, "total_tokens": 1817082, "completion_tokens": 51704, "reasoning_tokens": 44539}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1422984, "total_tokens": 1468997, "completion_tokens": 46013, "reasoning_tokens": 40069}`；额外usage：`{"prompt_tokens": 24775, "total_tokens": 28847, "completion_tokens": 4072, "reasoning_tokens": 0}`；拒收：`2`。

B/su15-1944f8ab 主usage：`{"prompt_tokens": 2137933, "total_tokens": 2184285, "completion_tokens": 46352, "reasoning_tokens": 43527}`；额外usage：`{"prompt_tokens": 24649, "total_tokens": 29119, "completion_tokens": 4470, "reasoning_tokens": 0}`；拒收：`2`。

配对差值：
```json
{
  "ft09-0d8bbf25": {
    "B_minus_A_added_levels": 0,
    "B_minus_A_continuation_action_count": -13,
    "B_minus_A_elapsed_seconds": 7.559223956000096,
    "restored_equal": {
      "grid_sha256": true,
      "messages_sha256": true,
      "functions_sha256": true,
      "branch_source_code_sha256": true,
      "prefix_recorded_actions": true
    }
  },
  "su15-1944f8ab": {
    "B_minus_A_added_levels": -1,
    "B_minus_A_continuation_action_count": 19,
    "B_minus_A_elapsed_seconds": -0.00870261299996855,
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
  "elapsed_seconds": 2053.8741796016693,
  "session_gpu_hours_wall_clock": 0.5705206054449081,
  "model_ready_seconds": 1127.2154166698456,
  "gpu_sampling": {
    "path": "/kaggle/working/gpu-utilization.jsonl",
    "interval_seconds": 10.0,
    "sample_count": 216,
    "error_count": 0,
    "stopped": true
  },
  "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."
}
```

详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。

补充跨文件核对：上表逐题主usage未包含B共享`requests.jsonl`中的一条ft09尾响应，已按7个身份字段唯一匹配；补计60073 prompt／6274 completion／5963 reasoning tokens。逐题表面缺4条，跨文件后仍缺3条。原逐题计数保持，修正后的known B主usage和证据见[响应核对](main-response-reconciliation.json)及[独立审阅](integrity-independent-review.json)，不能当完整成本。
