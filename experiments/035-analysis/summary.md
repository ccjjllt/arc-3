# 035 强制切点诊断

产物状态：complete；会话状态：completed。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。

会话错误：`None`。

| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |
|---|---|---|---|---|---|---|
| A | ft09-0d8bbf25 | complete | 0 | 45 | None | null |
| A | su15-1944f8ab | complete | 0 | 24 | None | null |
| B | ft09-0d8bbf25 | complete | 0 | 28 | 0 | 0/0/0 |
| B | su15-1944f8ab | complete | 0 | 36 | 0 | 0/0/0 |
| C | ft09-0d8bbf25 | complete | 0 | 39 | 0 | 0/0/0 |
| C | su15-1944f8ab | complete | 0 | 29 | 0 | 0/0/0 |

A/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1331691, "total_tokens": 1383982, "completion_tokens": 52291, "reasoning_tokens": 45729}`；额外usage：`null`；拒收：`None`。

A/su15-1944f8ab 主usage：`{"prompt_tokens": 1792992, "total_tokens": 1848533, "completion_tokens": 55541, "reasoning_tokens": 53134}`；额外usage：`null`；拒收：`None`。

B/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1107529, "total_tokens": 1157627, "completion_tokens": 50098, "reasoning_tokens": 45990}`；额外usage：`{"prompt_tokens": 25671, "total_tokens": 29542, "completion_tokens": 3871, "reasoning_tokens": 0}`；拒收：`2`。

B/su15-1944f8ab 主usage：`{"prompt_tokens": 1973086, "total_tokens": 2021857, "completion_tokens": 48771, "reasoning_tokens": 46001}`；额外usage：`{"prompt_tokens": 25003, "total_tokens": 30038, "completion_tokens": 5035, "reasoning_tokens": 0}`；拒收：`2`。

C/ft09-0d8bbf25 主usage：`{"prompt_tokens": 1061264, "total_tokens": 1109430, "completion_tokens": 48166, "reasoning_tokens": 45146}`；额外usage：`{"prompt_tokens": 27458, "total_tokens": 35650, "completion_tokens": 8192, "reasoning_tokens": 7115}`；拒收：`2`。

C/su15-1944f8ab 主usage：`{"prompt_tokens": 1544304, "total_tokens": 1588065, "completion_tokens": 43761, "reasoning_tokens": 42183}`；额外usage：`{"prompt_tokens": 26627, "total_tokens": 32533, "completion_tokens": 5906, "reasoning_tokens": 4743}`；拒收：`2`。

各臂两题均分：`{"A": 18.253968253968253, "B": 18.253968253968253, "C": 18.253968253968253}`。
均分差：`{"B_minus_A": 0.0, "C_minus_A": 0.0, "C_minus_B": 0.0}`。

配对差值：
```json
{
  "B_minus_A": {
    "ft09-0d8bbf25": {
      "B_minus_A_added_levels": 0,
      "B_minus_A_continuation_action_count": -17,
      "B_minus_A_elapsed_seconds": -7.75956678700004,
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
      "B_minus_A_continuation_action_count": 12,
      "B_minus_A_elapsed_seconds": 0.05041169100059051,
      "restored_equal": {
        "grid_sha256": true,
        "messages_sha256": true,
        "functions_sha256": true,
        "branch_source_code_sha256": true,
        "prefix_recorded_actions": true
      }
    }
  },
  "C_minus_A": {
    "ft09-0d8bbf25": {
      "C_minus_A_added_levels": 0,
      "C_minus_A_continuation_action_count": -6,
      "C_minus_A_elapsed_seconds": -6.258094823000192,
      "restored_equal": {
        "grid_sha256": true,
        "messages_sha256": true,
        "functions_sha256": true,
        "branch_source_code_sha256": true,
        "prefix_recorded_actions": true
      }
    },
    "su15-1944f8ab": {
      "C_minus_A_added_levels": 0,
      "C_minus_A_continuation_action_count": 5,
      "C_minus_A_elapsed_seconds": 3.927082357000245,
      "restored_equal": {
        "grid_sha256": true,
        "messages_sha256": true,
        "functions_sha256": true,
        "branch_source_code_sha256": true,
        "prefix_recorded_actions": true
      }
    }
  },
  "C_minus_B": {
    "ft09-0d8bbf25": {
      "C_minus_B_added_levels": 0,
      "C_minus_B_continuation_action_count": 11,
      "C_minus_B_elapsed_seconds": 1.5014719639998475,
      "restored_equal": {
        "grid_sha256": true,
        "messages_sha256": true,
        "functions_sha256": true,
        "branch_source_code_sha256": true,
        "prefix_recorded_actions": true
      }
    },
    "su15-1944f8ab": {
      "C_minus_B_added_levels": 0,
      "C_minus_B_continuation_action_count": -7,
      "C_minus_B_elapsed_seconds": 3.8766706659996544,
      "restored_equal": {
        "grid_sha256": true,
        "messages_sha256": true,
        "functions_sha256": true,
        "branch_source_code_sha256": true,
        "prefix_recorded_actions": true
      }
    }
  }
}
```

成本：
```json
{
  "elapsed_seconds": 3073.661779165268,
  "session_gpu_hours_wall_clock": 0.8537949386570188,
  "model_ready_seconds": 1662.132842540741,
  "gpu_sampling": {
    "path": "/kaggle/working/gpu-utilization.jsonl",
    "interval_seconds": 10.0,
    "sample_count": 321,
    "error_count": 0,
    "stopped": true
  },
  "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."
}
```

详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。

跨文件补记：C共享日志一条su15尾响应按7字段唯一匹配，补计93503输入／5721输出／5161推理tokens；逐题5条缺口校正为4，仍非完整usage，不直接称超时。两条reported reasoning4098大于completion4096的原始计数异常保留，不裁剪。
