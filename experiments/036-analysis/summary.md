# ARC-AGI-3 experiment summary

Generated: 2026-10-24T17:47:52.610984+00:00

- Author-reference data is historical public evidence, not a new GPU run or our leaderboard result.
- Scores use final_score when available. Recomputed scores use the bundled TAAF formula; means are unweighted descriptive means, not official leaderboard scores.
- Completion ceiling = 100 × k(k+1) / n(n+1), for completed sequential levels k out of n. It holds completion fixed and represents the ceiling from action efficiency alone.
- Recorded tokens / generated_tokens retain the original accounting: sum(history.generated_tokens) + final_generated_tokens. This may undercount generation after the last action. action_attached_generated_tokens is history only; it excludes final tokens.
- analyzer_reported_generated_tokens comes from an explicit same-named field or, if absent, the exact solver_note format tokens=N. Missing reports remain null. Aggregate analyzer totals cover only analyzer_reported_run_count runs; do not interpret partial sums as complete totals.
- unattached_generated_tokens = analyzer-reported minus recorded history+final tokens, only where analyzer reports exist. It measures the signed accounting residual, excludes already-recorded final tokens, and is not added to or substituted for the original generated_tokens field.
- Generated and uncached-input counts are solver-reported, not billing records. Zero can mean untracked usage; this harness may report zero uncached-input tokens even when prefill occurs.
- Action wallclock fields are cumulative; never sum them. Run duration is max(final_wallclock_seconds, last action timestamp). Concurrent run durations must not be added to estimate GPU quota.
- Benchmark elapsed is end_time − start_time and excludes setup/model-loading outside the benchmark; actual Kaggle GPU quota requires session accounting. Run durations include queue/wait time, not just GPU compute.
- Absent per-run stop reasons remain unknown. gave_up, cancelled, and crashed are lifecycle states. Sibling arm-metadata.json, when present, supplies shared deadline context without overwriting raw run states or inferring individual request failures.
- A/B aligns exact game IDs and averages available repeats. Shared GPU budget, scheduling, order, unequal exposure, and game difficulty confound comparisons; no independence or statistical significance is claimed.

## Benchmark overview

| Source | Kind | Games/runs | Mean score | Completion ceiling | Levels | Wins | Recorded tokens | Analyzer tokens (runs reported) | Benchmark hours |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | local-experiment | 25/25 | 39.44 | 41.59 | 97/183 | 4 | 4,381,408 | 4049761 (22/25) | 2.05 |
| main_medium | local-experiment | 25/25 | 40.64 | 42.88 | 100/183 | 5 | 4,293,084 | 4492815 (25/25) | 2.05 |

## main_medium − baseline

Descriptive comparison under a shared GPU budget; observations are not independent replications. Game IDs match exactly; occurrence indices do not establish paired random seeds.

Common games: 25; mean game score delta: 1.21.

| Game | Runs A/B | Score A | Score B | Δ score | Δ ceiling | Δ completed levels | Recorded tokens/run A/B |
|---|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1/1 | 77.78 | 100.00 | 22.22 | 22.22 | 1.00 | 220,702/183,200 |
| bp35-0a0ad940 | 1/1 | 0.39 | 0.72 | 0.32 | 0.00 | 0.00 | 157,531/173,827 |
| cd82-fb555c5d | 1/1 | 47.62 | 19.23 | -28.39 | -19.05 | -1.00 | 150,290/176,909 |
| cn04-2fe56bfb | 1/1 | 14.29 | 4.76 | -9.52 | -9.52 | -1.00 | 157,238/109,443 |
| dc22-fdcac232 | 1/1 | 47.62 | 13.75 | -33.87 | -33.33 | -2.00 | 232,792/164,493 |
| ft09-0d8bbf25 | 1/1 | 97.58 | 100.00 | 2.42 | 0.00 | 0.00 | 144,892/71,164 |
| g50t-5849a774 | 1/1 | 10.71 | 10.71 | 0.00 | 0.00 | 0.00 | 268,435/205,160 |
| ka59-38d34dbb | 1/1 | 10.71 | 51.96 | 41.25 | 42.86 | 3.00 | 167,734/203,304 |
| lf52-271a04aa | 1/1 | 5.45 | 5.45 | 0.00 | 0.00 | 0.00 | 103,877/120,627 |
| lp85-305b61c3 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 148,976/125,693 |
| ls20-9607627b | 1/1 | 27.24 | 3.57 | -23.67 | -50.00 | -4.00 | 248,856/84,587 |
| m0r0-492f87ba | 1/1 | 47.16 | 26.16 | -21.00 | -19.05 | -1.00 | 186,247/232,002 |
| r11l-495a7899 | 1/1 | 14.29 | 100.00 | 85.71 | 85.71 | 4.00 | 135,522/208,243 |
| re86-8af5384d | 1/1 | 58.33 | 58.33 | 0.00 | 0.00 | 0.00 | 303,906/239,957 |
| s5i5-18d95033 | 1/1 | 2.10 | 58.33 | 56.23 | 55.56 | 5.00 | 141,188/306,916 |
| sb26-7fbdac44 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 78,801/77,294 |
| sc25-635fd71a | 1/1 | 37.94 | 47.62 | 9.68 | 0.00 | 0.00 | 177,292/152,293 |
| sk48-d8078629 | 1/1 | 0.00 | 1.33 | 1.33 | 2.78 | 1.00 | 119,181/119,484 |
| sp80-589a99af | 1/1 | 22.95 | 4.76 | -18.19 | -23.81 | -2.00 | 225,446/129,023 |
| su15-1944f8ab | 1/1 | 13.33 | 22.22 | 8.89 | 8.89 | 1.00 | 193,849/206,553 |
| tn36-ef4dde99 | 1/1 | 53.57 | 16.70 | -36.87 | -32.14 | -2.00 | 180,847/130,881 |
| tr87-cd924810 | 1/1 | 100.00 | 31.73 | -68.27 | -52.38 | -2.00 | 103,141/201,371 |
| tu93-0768757b | 1/1 | 73.57 | 61.43 | -12.14 | 0.00 | 0.00 | 286,694/310,766 |
| vc33-5430563c | 1/1 | 21.02 | 75.00 | 53.98 | 53.57 | 3.00 | 136,244/204,428 |
| wa30-ee6fef47 | 1/1 | 2.22 | 2.22 | 0.00 | 0.00 | 0.00 | 111,727/155,466 |

## baseline

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/036-main-reasoning-medium/baseline/benchmark.json`

States: `{"cancelled": 21, "won": 4}`. Stop reasons: `{"unknown": 21, "won": 4}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 77.78 | 77.78 | 7/8 | 0 | 220,702 | 221656 | 954 | 2.02 |
| bp35-0a0ad940 | 1 | 0.39 | 2.22 | 1/9 | 0 | 157,531 | 157964 | 433 | 2.02 |
| cd82-fb555c5d | 1 | 47.62 | 47.62 | 4/6 | 0 | 150,290 | 150376 | 86 | 2.03 |
| cn04-2fe56bfb | 1 | 14.29 | 14.29 | 2/6 | 0 | 157,238 | 179169 | 21931 | 2.01 |
| dc22-fdcac232 | 1 | 47.62 | 47.62 | 4/6 | 0 | 232,792 | 233881 | 1089 | 2.03 |
| ft09-0d8bbf25 | 1 | 97.58 | 100.00 | 6/6 | 1 | 144,892 | 144892 | 0 | 1.56 |
| g50t-5849a774 | 1 | 10.71 | 10.71 | 2/7 | 0 | 268,435 | 270464 | 2029 | 2.03 |
| ka59-38d34dbb | 1 | 10.71 | 10.71 | 2/7 | 0 | 167,734 | — | — | 2.05 |
| lf52-271a04aa | 1 | 5.45 | 5.45 | 2/10 | 0 | 103,877 | 167981 | 64104 | 2.04 |
| lp85-305b61c3 | 1 | 100.00 | 100.00 | 8/8 | 1 | 148,976 | 148976 | 0 | 0.94 |
| ls20-9607627b | 1 | 27.24 | 53.57 | 5/7 | 0 | 248,856 | 262135 | 13279 | 2.02 |
| m0r0-492f87ba | 1 | 47.16 | 47.62 | 4/6 | 0 | 186,247 | 186247 | 0 | 2.01 |
| r11l-495a7899 | 1 | 14.29 | 14.29 | 2/6 | 0 | 135,522 | 151799 | 16277 | 2.01 |
| re86-8af5384d | 1 | 58.33 | 58.33 | 6/8 | 0 | 303,906 | 303906 | 0 | 2.01 |
| s5i5-18d95033 | 1 | 2.10 | 2.78 | 1/8 | 0 | 141,188 | 141188 | 0 | 2.01 |
| sb26-7fbdac44 | 1 | 100.00 | 100.00 | 8/8 | 1 | 78,801 | 78801 | 0 | 0.97 |
| sc25-635fd71a | 1 | 37.94 | 47.62 | 4/6 | 0 | 177,292 | 180231 | 2939 | 2.01 |
| sk48-d8078629 | 1 | 0.00 | 0.00 | 0/8 | 0 | 119,181 | 122166 | 2985 | 2.04 |
| sp80-589a99af | 1 | 22.95 | 28.57 | 3/6 | 0 | 225,446 | 225446 | 0 | 2.03 |
| su15-1944f8ab | 1 | 13.33 | 13.33 | 3/9 | 0 | 193,849 | — | — | 2.05 |
| tn36-ef4dde99 | 1 | 53.57 | 53.57 | 5/7 | 0 | 180,847 | 184882 | 4035 | 2.04 |
| tr87-cd924810 | 1 | 100.00 | 100.00 | 6/6 | 1 | 103,141 | 103141 | 0 | 1.99 |
| tu93-0768757b | 1 | 73.57 | 80.00 | 8/9 | 0 | 286,694 | 295668 | 8974 | 2.01 |
| vc33-5430563c | 1 | 21.02 | 21.43 | 3/7 | 0 | 136,244 | 138792 | 2548 | 2.04 |
| wa30-ee6fef47 | 1 | 2.22 | 2.22 | 1/9 | 0 | 111,727 | — | — | 2.05 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| ar25-0c556536 | 0 | 77.78 | 77.78 | 7/8 | 283 | 220,702 | 221656 | 954 | 2.02 | cancelled | unknown |
| bp35-0a0ad940 | 0 | 0.39 | 2.22 | 1/9 | 96 | 157,531 | 157964 | 433 | 2.02 | cancelled | unknown |
| cd82-fb555c5d | 0 | 47.62 | 47.62 | 4/6 | 179 | 150,290 | 150376 | 86 | 2.03 | cancelled | unknown |
| cn04-2fe56bfb | 0 | 14.29 | 14.29 | 2/6 | 82 | 157,238 | 179169 | 21931 | 2.01 | cancelled | unknown |
| dc22-fdcac232 | 0 | 47.62 | 47.62 | 4/6 | 339 | 232,792 | 233881 | 1089 | 2.03 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 97.58 | 100.00 | 6/6 | 129 | 144,892 | 144892 | 0 | 1.56 | won | won |
| g50t-5849a774 | 0 | 10.71 | 10.71 | 2/7 | 230 | 268,435 | 270464 | 2029 | 2.03 | cancelled | unknown |
| ka59-38d34dbb | 0 | 10.71 | 10.71 | 2/7 | 200 | 167,734 | — | — | 2.05 | cancelled | unknown |
| lf52-271a04aa | 0 | 5.45 | 5.45 | 2/10 | 102 | 103,877 | 167981 | 64104 | 2.04 | cancelled | unknown |
| lp85-305b61c3 | 0 | 100.00 | 100.00 | 8/8 | 158 | 148,976 | 148976 | 0 | 0.94 | won | won |
| ls20-9607627b | 0 | 27.24 | 53.57 | 5/7 | 604 | 248,856 | 262135 | 13279 | 2.02 | cancelled | unknown |
| m0r0-492f87ba | 0 | 47.16 | 47.62 | 4/6 | 312 | 186,247 | 186247 | 0 | 2.01 | cancelled | unknown |
| r11l-495a7899 | 0 | 14.29 | 14.29 | 2/6 | 39 | 135,522 | 151799 | 16277 | 2.01 | cancelled | unknown |
| re86-8af5384d | 0 | 58.33 | 58.33 | 6/8 | 426 | 303,906 | 303906 | 0 | 2.01 | cancelled | unknown |
| s5i5-18d95033 | 0 | 2.10 | 2.78 | 1/8 | 45 | 141,188 | 141188 | 0 | 2.01 | cancelled | unknown |
| sb26-7fbdac44 | 0 | 100.00 | 100.00 | 8/8 | 162 | 78,801 | 78801 | 0 | 0.97 | won | won |
| sc25-635fd71a | 0 | 37.94 | 47.62 | 4/6 | 204 | 177,292 | 180231 | 2939 | 2.01 | cancelled | unknown |
| sk48-d8078629 | 0 | 0.00 | 0.00 | 0/8 | 100 | 119,181 | 122166 | 2985 | 2.04 | cancelled | unknown |
| sp80-589a99af | 0 | 22.95 | 28.57 | 3/6 | 141 | 225,446 | 225446 | 0 | 2.03 | cancelled | unknown |
| su15-1944f8ab | 0 | 13.33 | 13.33 | 3/9 | 172 | 193,849 | — | — | 2.05 | cancelled | unknown |
| tn36-ef4dde99 | 0 | 53.57 | 53.57 | 5/7 | 263 | 180,847 | 184882 | 4035 | 2.04 | cancelled | unknown |
| tr87-cd924810 | 0 | 100.00 | 100.00 | 6/6 | 338 | 103,141 | 103141 | 0 | 1.99 | won | won |
| tu93-0768757b | 0 | 73.57 | 80.00 | 8/9 | 284 | 286,694 | 295668 | 8974 | 2.01 | cancelled | unknown |
| vc33-5430563c | 0 | 21.02 | 21.43 | 3/7 | 128 | 136,244 | 138792 | 2548 | 2.04 | cancelled | unknown |
| wa30-ee6fef47 | 0 | 2.22 | 2.22 | 1/9 | 100 | 111,727 | — | — | 2.05 | cancelled | unknown |

### Data notes

- run 0: analyzer-reported minus history+final generated tokens = 954; retain both accounting views
- run 1: analyzer-reported minus history+final generated tokens = 433; retain both accounting views
- run 2: analyzer-reported minus history+final generated tokens = 86; retain both accounting views
- run 3: analyzer-reported minus history+final generated tokens = 21931; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 1089; retain both accounting views
- run 6: analyzer-reported minus history+final generated tokens = 2029; retain both accounting views
- run 8: analyzer-reported minus history+final generated tokens = 64104; retain both accounting views
- run 10: analyzer-reported minus history+final generated tokens = 13279; retain both accounting views
- run 12: analyzer-reported minus history+final generated tokens = 16277; retain both accounting views
- run 16: analyzer-reported minus history+final generated tokens = 2939; retain both accounting views
- run 17: analyzer-reported minus history+final generated tokens = 2985; retain both accounting views
- run 20: analyzer-reported minus history+final generated tokens = 4035; retain both accounting views
- run 22: analyzer-reported minus history+final generated tokens = 8974; retain both accounting views
- run 23: analyzer-reported minus history+final generated tokens = 2548; retain both accounting views
- arm metadata records the shared budget deadline fired; 21 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged

## main_medium

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/036-main-reasoning-medium/main_medium/benchmark.json`

States: `{"cancelled": 20, "won": 5}`. Stop reasons: `{"unknown": 20, "won": 5}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 183,200 | 183200 | 0 | 1.39 |
| bp35-0a0ad940 | 1 | 0.72 | 2.22 | 1/9 | 0 | 173,827 | 173827 | 0 | 2.03 |
| cd82-fb555c5d | 1 | 19.23 | 28.57 | 3/6 | 0 | 176,909 | 176909 | 0 | 2.02 |
| cn04-2fe56bfb | 1 | 4.76 | 4.76 | 1/6 | 0 | 109,443 | 132731 | 23288 | 2.02 |
| dc22-fdcac232 | 1 | 13.75 | 14.29 | 2/6 | 0 | 164,493 | 180065 | 15572 | 2.03 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 71,164 | 71164 | 0 | 1.59 |
| g50t-5849a774 | 1 | 10.71 | 10.71 | 2/7 | 0 | 205,160 | 228780 | 23620 | 2.04 |
| ka59-38d34dbb | 1 | 51.96 | 53.57 | 5/7 | 0 | 203,304 | 203989 | 685 | 2.03 |
| lf52-271a04aa | 1 | 5.45 | 5.45 | 2/10 | 0 | 120,627 | 136933 | 16306 | 2.03 |
| lp85-305b61c3 | 1 | 100.00 | 100.00 | 8/8 | 1 | 125,693 | 125693 | 0 | 1.82 |
| ls20-9607627b | 1 | 3.57 | 3.57 | 1/7 | 0 | 84,587 | 87147 | 2560 | 2.04 |
| m0r0-492f87ba | 1 | 26.16 | 28.57 | 3/6 | 0 | 232,002 | 232002 | 0 | 2.02 |
| r11l-495a7899 | 1 | 100.00 | 100.00 | 6/6 | 1 | 208,243 | 208243 | 0 | 1.16 |
| re86-8af5384d | 1 | 58.33 | 58.33 | 6/8 | 0 | 239,957 | 240150 | 193 | 2.03 |
| s5i5-18d95033 | 1 | 58.33 | 58.33 | 6/8 | 0 | 306,916 | 335742 | 28826 | 2.03 |
| sb26-7fbdac44 | 1 | 100.00 | 100.00 | 8/8 | 1 | 77,294 | 77294 | 0 | 0.60 |
| sc25-635fd71a | 1 | 47.62 | 47.62 | 4/6 | 0 | 152,293 | 152293 | 0 | 2.01 |
| sk48-d8078629 | 1 | 1.33 | 2.78 | 1/8 | 0 | 119,484 | 156348 | 36864 | 2.05 |
| sp80-589a99af | 1 | 4.76 | 4.76 | 1/6 | 0 | 129,023 | 129266 | 243 | 2.02 |
| su15-1944f8ab | 1 | 22.22 | 22.22 | 4/9 | 0 | 206,553 | 232361 | 25808 | 2.03 |
| tn36-ef4dde99 | 1 | 16.70 | 21.43 | 3/7 | 0 | 130,881 | 130881 | 0 | 2.01 |
| tr87-cd924810 | 1 | 31.73 | 47.62 | 4/6 | 0 | 201,371 | 202007 | 636 | 2.02 |
| tu93-0768757b | 1 | 61.43 | 80.00 | 8/9 | 0 | 310,766 | 327696 | 16930 | 2.02 |
| vc33-5430563c | 1 | 75.00 | 75.00 | 6/7 | 0 | 204,428 | 212194 | 7766 | 2.01 |
| wa30-ee6fef47 | 1 | 2.22 | 2.22 | 1/9 | 0 | 155,466 | 155900 | 434 | 2.03 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 307 | 183,200 | 183200 | 0 | 1.39 | won | won |
| bp35-0a0ad940 | 0 | 0.72 | 2.22 | 1/9 | 112 | 173,827 | 173827 | 0 | 2.03 | cancelled | unknown |
| cd82-fb555c5d | 0 | 19.23 | 28.57 | 3/6 | 152 | 176,909 | 176909 | 0 | 2.02 | cancelled | unknown |
| cn04-2fe56bfb | 0 | 4.76 | 4.76 | 1/6 | 73 | 109,443 | 132731 | 23288 | 2.02 | cancelled | unknown |
| dc22-fdcac232 | 0 | 13.75 | 14.29 | 2/6 | 200 | 164,493 | 180065 | 15572 | 2.03 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 105 | 71,164 | 71164 | 0 | 1.59 | won | won |
| g50t-5849a774 | 0 | 10.71 | 10.71 | 2/7 | 194 | 205,160 | 228780 | 23620 | 2.04 | cancelled | unknown |
| ka59-38d34dbb | 0 | 51.96 | 53.57 | 5/7 | 355 | 203,304 | 203989 | 685 | 2.03 | cancelled | unknown |
| lf52-271a04aa | 0 | 5.45 | 5.45 | 2/10 | 110 | 120,627 | 136933 | 16306 | 2.03 | cancelled | unknown |
| lp85-305b61c3 | 0 | 100.00 | 100.00 | 8/8 | 145 | 125,693 | 125693 | 0 | 1.82 | won | won |
| ls20-9607627b | 0 | 3.57 | 3.57 | 1/7 | 350 | 84,587 | 87147 | 2560 | 2.04 | cancelled | unknown |
| m0r0-492f87ba | 0 | 26.16 | 28.57 | 3/6 | 463 | 232,002 | 232002 | 0 | 2.02 | cancelled | unknown |
| r11l-495a7899 | 0 | 100.00 | 100.00 | 6/6 | 103 | 208,243 | 208243 | 0 | 1.16 | won | won |
| re86-8af5384d | 0 | 58.33 | 58.33 | 6/8 | 506 | 239,957 | 240150 | 193 | 2.03 | cancelled | unknown |
| s5i5-18d95033 | 0 | 58.33 | 58.33 | 6/8 | 207 | 306,916 | 335742 | 28826 | 2.03 | cancelled | unknown |
| sb26-7fbdac44 | 0 | 100.00 | 100.00 | 8/8 | 135 | 77,294 | 77294 | 0 | 0.60 | won | won |
| sc25-635fd71a | 0 | 47.62 | 47.62 | 4/6 | 293 | 152,293 | 152293 | 0 | 2.01 | cancelled | unknown |
| sk48-d8078629 | 0 | 1.33 | 2.78 | 1/8 | 251 | 119,484 | 156348 | 36864 | 2.05 | cancelled | unknown |
| sp80-589a99af | 0 | 4.76 | 4.76 | 1/6 | 89 | 129,023 | 129266 | 243 | 2.02 | cancelled | unknown |
| su15-1944f8ab | 0 | 22.22 | 22.22 | 4/9 | 176 | 206,553 | 232361 | 25808 | 2.03 | cancelled | unknown |
| tn36-ef4dde99 | 0 | 16.70 | 21.43 | 3/7 | 185 | 130,881 | 130881 | 0 | 2.01 | cancelled | unknown |
| tr87-cd924810 | 0 | 31.73 | 47.62 | 4/6 | 354 | 201,371 | 202007 | 636 | 2.02 | cancelled | unknown |
| tu93-0768757b | 0 | 61.43 | 80.00 | 8/9 | 367 | 310,766 | 327696 | 16930 | 2.02 | cancelled | unknown |
| vc33-5430563c | 0 | 75.00 | 75.00 | 6/7 | 174 | 204,428 | 212194 | 7766 | 2.01 | cancelled | unknown |
| wa30-ee6fef47 | 0 | 2.22 | 2.22 | 1/9 | 249 | 155,466 | 155900 | 434 | 2.03 | cancelled | unknown |

### Data notes

- run 3: analyzer-reported minus history+final generated tokens = 23288; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 15572; retain both accounting views
- run 6: analyzer-reported minus history+final generated tokens = 23620; retain both accounting views
- run 7: analyzer-reported minus history+final generated tokens = 685; retain both accounting views
- run 8: analyzer-reported minus history+final generated tokens = 16306; retain both accounting views
- run 10: analyzer-reported minus history+final generated tokens = 2560; retain both accounting views
- run 13: analyzer-reported minus history+final generated tokens = 193; retain both accounting views
- run 14: analyzer-reported minus history+final generated tokens = 28826; retain both accounting views
- run 17: analyzer-reported minus history+final generated tokens = 36864; retain both accounting views
- run 18: analyzer-reported minus history+final generated tokens = 243; retain both accounting views
- run 19: analyzer-reported minus history+final generated tokens = 25808; retain both accounting views
- run 21: analyzer-reported minus history+final generated tokens = 636; retain both accounting views
- run 22: analyzer-reported minus history+final generated tokens = 16930; retain both accounting views
- run 23: analyzer-reported minus history+final generated tokens = 7766; retain both accounting views
- run 24: analyzer-reported minus history+final generated tokens = 434; retain both accounting views
- arm metadata records the shared budget deadline fired; 20 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged
