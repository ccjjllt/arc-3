# 032 成功经验记忆短跑

实际采用需审阅请求和后续行为，计数器不代表采用。

| 臂 | 官方均分 | 完成关 | 全通 | 动作 | benchmark生成token | response生成token |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 45.0060 | 40 | 3 | 2153 | 1511955 | 1517784 |
| solved_level_memory | 70.6612 | 53 | 4 | 2257 | 1541913 | 1549942 |

配对平均分差：25.6552

| 游戏 | baseline | memory | 分差 | 关差 | 动作差 |
|---|---:|---:|---:|---:|---:|
| ar25-0c556536 | 100.0000 | 100.0000 | 0.0000 | 0 | 5 |
| cd82-fb555c5d | 1.5592 | 99.6087 | 98.0495 | 4 | 29 |
| ft09-0d8bbf25 | 100.0000 | 100.0000 | 0.0000 | 0 | -18 |
| m0r0-492f87ba | 0.0000 | 71.4286 | 71.4286 | 5 | 16 |
| r11l-495a7899 | 21.1195 | 71.4286 | 50.3090 | 2 | -60 |
| re86-8af5384d | 41.6667 | 41.6667 | 0.0000 | 0 | 134 |
| sc25-635fd71a | 47.6190 | 71.0505 | 23.4314 | 1 | -112 |
| sp80-589a99af | 4.7619 | 4.7619 | 0.0000 | 0 | 56 |
| tr87-cd924810 | 100.0000 | 100.0000 | 0.0000 | 0 | 125 |
| tu93-0768757b | 33.3333 | 46.6667 | 13.3333 | 1 | -71 |

交付/摘要计数：

```json
{
  "sessions": 10,
  "fact_records": 49,
  "records_with_rule": 40,
  "metrics": {
    "preparation_seconds": 4.547736931986947,
    "request_attempts": 837,
    "observed_request_seconds": 22724.41500773799,
    "all_request_prompt_tokens": 59069680,
    "all_request_completion_tokens": 1549942,
    "all_request_total_tokens": 60619622,
    "observed_completions_recorded": 49,
    "requests_with_rule_instruction": 133,
    "rule_instructions_successfully_sent": 62,
    "rules_captured": 40,
    "memory_refreshes": 25,
    "memory_characters_written": 116423,
    "requests_with_memory": 420,
    "system_memory_characters_attempted": 1764984,
    "successful_responses_with_memory": 415,
    "request_failures": 5
  },
  "note": "Facts/asks/refresh/delivery counters only; no semantic adoption verdict."
}
```

成本口径互相重叠不可相加；超时未返回usage不是零成本。详见summary.json及review-index.md。
