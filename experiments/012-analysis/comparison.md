# 012 公开13游戏结果复算

baseline先、current_data后，差值始终为候选−基线。已知诊断池，不是正式排行榜成绩。

| 指标 | baseline | current_data | 差值 |
|---|---:|---:|---:|
| mean_AE | 45.076431 | 27.758211 | -17.318220 |
| mean_completion_ceiling | 47.581863 | 29.816295 | -17.765568 |
| mean_efficiency_gap | 2.505432 | 2.058084 | -0.447348 |
| levels_completed | 51.000000 | 38.000000 | -13.000000 |
| wins | 3.000000 | 1.000000 | -2.000000 |
| actions | 2633.000000 | 2356.000000 | -277.000000 |
| analyzer_tokens | 2364169.000000 | 2378190.000000 | +14021.000000 |
| recorded_tokens | 2292625.000000 | 2243619.000000 | -49006.000000 |
| unattached_tokens | 71544.000000 | 134571.000000 | +63027.000000 |

| 游戏 | AE基线→候选 | 关卡基线→候选 | 均分贡献 | put请求 / get请求 |
|---|---:|---:|---:|---:|
| tn36-ef4dde99 | 66.4023→3.5714 | 6→1/7 | -4.8331 | 0 / 0 |
| sc25-635fd71a | 63.8229→31.9464 | 5→4/6 | -2.4520 | 0 / 0 |
| sp80-589a99af | 47.6190→4.7619 | 4→1/6 | -3.2967 | 0 / 0 |
| bp35-0a0ad940 | 2.2222→5.2006 | 1→2/9 | +0.2291 | 0 / 0 |
| sk48-d8078629 | 2.7778→2.7778 | 1→1/8 | +0.0000 | 0 / 0 |
| lf52-271a04aa | 1.8182→1.8182 | 1→1/10 | +0.0000 | 0 / 0 |
| su15-1944f8ab | 24.6707→13.3333 | 5→3/9 | -0.8721 | 0 / 0 |
| wa30-ee6fef47 | 2.2222→5.9088 | 1→2/9 | +0.2836 | 0 / 0 |
| g50t-5849a774 | 10.7143→2.8059 | 2→1/7 | -0.6083 | 0 / 0 |
| m0r0-492f87ba | 71.4286→71.4286 | 5→5/6 | +0.0000 | 0 / 0 |
| ft09-0d8bbf25 | 100.0000→47.6190 | 6→4/6 | -4.0293 | 2 / 0 |
| cd82-fb555c5d | 92.2953→91.9071 | 6→6/6 | -0.0299 | 0 / 0 |
| ar25-0c556536 | 100.0000→77.7778 | 8→7/8 | -1.7094 | 0 / 0 |

- 13 known public games, one baseline-first pair; no significance or causal-harm claim.
- Do not directly compare these13-game means to010/01112-game means or the official leaderboard.
- Only2 put attempts,1 stored,0 get/context: no cross-snippet model data-reuse chain observed.
- Equal wall budgets do not guarantee equal per-game compute; timing audit distinguishes late requests from late actions.
- Common action-attached-token prefixes are descriptive, not equal GPU cost or a replacement score.
