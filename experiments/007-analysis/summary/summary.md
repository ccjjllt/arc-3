# ARC-AGI-3 experiment summary

Generated: 2026-10-11T09:49:01.613793+00:00

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
| baseline | local-experiment | 12/12 | 46.36 | 49.36 | 51/89 | 4 | 2,025,627 | 2107894 (12/12) | 0.97 |
| program_state | local-experiment | 12/12 | 40.32 | 45.34 | 50/89 | 2 | 2,114,430 | 2159836 (12/12) | 0.98 |

## program_state − baseline

Descriptive comparison under a shared GPU budget; observations are not independent replications. Game IDs match exactly; occurrence indices do not establish paired random seeds.

Common games: 12; mean game score delta: -6.03.

| Game | Runs A/B | Score A | Score B | Δ score | Δ ceiling | Δ completed levels | Recorded tokens/run A/B |
|---|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 150,337/171,343 |
| bp35-0a0ad940 | 1/1 | 0.80 | 1.17 | 0.37 | 0.00 | 0.00 | 160,069/159,296 |
| ft09-0d8bbf25 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 88,590/66,195 |
| lf52-271a04aa | 1/1 | 10.91 | 3.55 | -7.36 | -5.45 | -1.00 | 195,521/146,030 |
| ls20-9607627b | 1/1 | 21.67 | 8.60 | -13.07 | -14.29 | -1.00 | 216,007/201,814 |
| m0r0-492f87ba | 1/1 | 13.38 | 30.37 | 16.99 | 33.33 | 2.00 | 194,538/207,958 |
| re86-8af5384d | 1/1 | 36.25 | 41.67 | 5.42 | 0.00 | 0.00 | 212,072/204,965 |
| sc25-635fd71a | 1/1 | 100.00 | 44.28 | -55.72 | -52.38 | -2.00 | 116,223/149,937 |
| sk48-d8078629 | 1/1 | 1.50 | 2.78 | 1.28 | 0.00 | 0.00 | 169,029/206,275 |
| sp80-589a99af | 1/1 | 4.76 | 47.62 | 42.86 | 42.86 | 3.00 | 198,812/204,864 |
| tr87-cd924810 | 1/1 | 100.00 | 47.62 | -52.38 | -52.38 | -2.00 | 106,791/176,480 |
| tu93-0768757b | 1/1 | 67.02 | 56.23 | -10.79 | 0.00 | 0.00 | 217,638/219,273 |

## baseline

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/007-program-state/baseline/benchmark.json`

States: `{"cancelled": 8, "won": 4}`. Stop reasons: `{"unknown": 8, "won": 4}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 150,337 | 150337 | 0 | 0.70 |
| bp35-0a0ad940 | 1 | 0.80 | 2.22 | 1/9 | 0 | 160,069 | 169063 | 8994 | 0.97 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 88,590 | 88590 | 0 | 0.38 |
| lf52-271a04aa | 1 | 10.91 | 10.91 | 3/10 | 0 | 195,521 | 198416 | 2895 | 0.97 |
| ls20-9607627b | 1 | 21.67 | 35.71 | 4/7 | 0 | 216,007 | 216007 | 0 | 0.97 |
| m0r0-492f87ba | 1 | 13.38 | 14.29 | 2/6 | 0 | 194,538 | 202069 | 7531 | 0.97 |
| re86-8af5384d | 1 | 36.25 | 41.67 | 5/8 | 0 | 212,072 | 212072 | 0 | 0.97 |
| sc25-635fd71a | 1 | 100.00 | 100.00 | 6/6 | 1 | 116,223 | 116223 | 0 | 0.77 |
| sk48-d8078629 | 1 | 1.50 | 2.78 | 1/8 | 0 | 169,029 | 188495 | 19466 | 0.97 |
| sp80-589a99af | 1 | 4.76 | 4.76 | 1/6 | 0 | 198,812 | 236675 | 37863 | 0.97 |
| tr87-cd924810 | 1 | 100.00 | 100.00 | 6/6 | 1 | 106,791 | 106791 | 0 | 0.48 |
| tu93-0768757b | 1 | 67.02 | 80.00 | 8/9 | 0 | 217,638 | 223156 | 5518 | 0.97 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 288 | 150,337 | 150337 | 0 | 0.70 | won | won |
| tr87-cd924810 | 0 | 100.00 | 100.00 | 6/6 | 261 | 106,791 | 106791 | 0 | 0.48 | won | won |
| re86-8af5384d | 0 | 36.25 | 41.67 | 5/8 | 586 | 212,072 | 212072 | 0 | 0.97 | cancelled | unknown |
| m0r0-492f87ba | 0 | 13.38 | 14.29 | 2/6 | 121 | 194,538 | 202069 | 7531 | 0.97 | cancelled | unknown |
| sp80-589a99af | 0 | 4.76 | 4.76 | 1/6 | 50 | 198,812 | 236675 | 37863 | 0.97 | cancelled | unknown |
| sk48-d8078629 | 0 | 1.50 | 2.78 | 1/8 | 122 | 169,029 | 188495 | 19466 | 0.97 | cancelled | unknown |
| ls20-9607627b | 0 | 21.67 | 35.71 | 4/7 | 350 | 216,007 | 216007 | 0 | 0.97 | cancelled | unknown |
| tu93-0768757b | 0 | 67.02 | 80.00 | 8/9 | 275 | 217,638 | 223156 | 5518 | 0.97 | cancelled | unknown |
| lf52-271a04aa | 0 | 10.91 | 10.91 | 3/10 | 210 | 195,521 | 198416 | 2895 | 0.97 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 93 | 88,590 | 88590 | 0 | 0.38 | won | won |
| sc25-635fd71a | 0 | 100.00 | 100.00 | 6/6 | 217 | 116,223 | 116223 | 0 | 0.77 | won | won |
| bp35-0a0ad940 | 0 | 0.80 | 2.22 | 1/9 | 82 | 160,069 | 169063 | 8994 | 0.97 | cancelled | unknown |

### Data notes

- run 3: analyzer-reported minus history+final generated tokens = 7531; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 37863; retain both accounting views
- run 5: analyzer-reported minus history+final generated tokens = 19466; retain both accounting views
- run 7: analyzer-reported minus history+final generated tokens = 5518; retain both accounting views
- run 8: analyzer-reported minus history+final generated tokens = 2895; retain both accounting views
- run 11: analyzer-reported minus history+final generated tokens = 8994; retain both accounting views
- arm metadata records the shared budget deadline fired; 8 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged

## program_state

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/007-program-state/program_state/benchmark.json`

States: `{"cancelled": 10, "won": 2}`. Stop reasons: `{"unknown": 10, "won": 2}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 171,343 | 171343 | 0 | 0.78 |
| bp35-0a0ad940 | 1 | 1.17 | 2.22 | 1/9 | 0 | 159,296 | 159296 | 0 | 0.97 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 66,195 | 66195 | 0 | 0.28 |
| lf52-271a04aa | 1 | 3.55 | 5.45 | 2/10 | 0 | 146,030 | 160928 | 14898 | 0.98 |
| ls20-9607627b | 1 | 8.60 | 21.43 | 3/7 | 0 | 201,814 | 206019 | 4205 | 0.97 |
| m0r0-492f87ba | 1 | 30.37 | 47.62 | 4/6 | 0 | 207,958 | 207958 | 0 | 0.97 |
| re86-8af5384d | 1 | 41.67 | 41.67 | 5/8 | 0 | 204,965 | 204965 | 0 | 0.97 |
| sc25-635fd71a | 1 | 44.28 | 47.62 | 4/6 | 0 | 149,937 | 153900 | 3963 | 0.97 |
| sk48-d8078629 | 1 | 2.78 | 2.78 | 1/8 | 0 | 206,275 | 212370 | 6095 | 0.97 |
| sp80-589a99af | 1 | 47.62 | 47.62 | 4/6 | 0 | 204,864 | 221109 | 16245 | 0.97 |
| tr87-cd924810 | 1 | 47.62 | 47.62 | 4/6 | 0 | 176,480 | 176480 | 0 | 0.97 |
| tu93-0768757b | 1 | 56.23 | 80.00 | 8/9 | 0 | 219,273 | 219273 | 0 | 0.97 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 324 | 171,343 | 171343 | 0 | 0.78 | won | won |
| tr87-cd924810 | 0 | 47.62 | 47.62 | 4/6 | 171 | 176,480 | 176480 | 0 | 0.97 | cancelled | unknown |
| re86-8af5384d | 0 | 41.67 | 41.67 | 5/8 | 351 | 204,965 | 204965 | 0 | 0.97 | cancelled | unknown |
| m0r0-492f87ba | 0 | 30.37 | 47.62 | 4/6 | 298 | 207,958 | 207958 | 0 | 0.97 | cancelled | unknown |
| sp80-589a99af | 0 | 47.62 | 47.62 | 4/6 | 121 | 204,864 | 221109 | 16245 | 0.97 | cancelled | unknown |
| sk48-d8078629 | 0 | 2.78 | 2.78 | 1/8 | 133 | 206,275 | 212370 | 6095 | 0.97 | cancelled | unknown |
| ls20-9607627b | 0 | 8.60 | 21.43 | 3/7 | 408 | 201,814 | 206019 | 4205 | 0.97 | cancelled | unknown |
| tu93-0768757b | 0 | 56.23 | 80.00 | 8/9 | 301 | 219,273 | 219273 | 0 | 0.97 | cancelled | unknown |
| lf52-271a04aa | 0 | 3.55 | 5.45 | 2/10 | 165 | 146,030 | 160928 | 14898 | 0.98 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 84 | 66,195 | 66195 | 0 | 0.28 | won | won |
| sc25-635fd71a | 0 | 44.28 | 47.62 | 4/6 | 194 | 149,937 | 153900 | 3963 | 0.97 | cancelled | unknown |
| bp35-0a0ad940 | 0 | 1.17 | 2.22 | 1/9 | 41 | 159,296 | 159296 | 0 | 0.97 | cancelled | unknown |

### Data notes

- run 4: analyzer-reported minus history+final generated tokens = 16245; retain both accounting views
- run 5: analyzer-reported minus history+final generated tokens = 6095; retain both accounting views
- run 6: analyzer-reported minus history+final generated tokens = 4205; retain both accounting views
- run 8: analyzer-reported minus history+final generated tokens = 14898; retain both accounting views
- run 10: analyzer-reported minus history+final generated tokens = 3963; retain both accounting views
- arm metadata records the shared budget deadline fired; 10 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged
