# ARC-AGI-3 experiment summary

Generated: 2026-10-11T04:16:20.696998+00:00

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
| baseline | local-experiment | 12/12 | 28.39 | 31.10 | 36/91 | 3 | 2,109,258 | 2206200 (12/12) | 0.97 |
| transient_history | local-experiment | 12/12 | 21.92 | 24.05 | 31/91 | 1 | 2,164,426 | 2209966 (12/12) | 0.97 |

## transient_history − baseline

Descriptive comparison under a shared GPU budget; observations are not independent replications. Game IDs match exactly; occurrence indices do not establish paired random seeds.

Common games: 12; mean game score delta: -6.46.

| Game | Runs A/B | Score A | Score B | Δ score | Δ ceiling | Δ completed levels | Recorded tokens/run A/B |
|---|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1/1 | 100.00 | 58.33 | -41.67 | -41.67 | -2.00 | 153,068/161,515 |
| bp35-0a0ad940 | 1/1 | 2.22 | 0.76 | -1.47 | 0.00 | 0.00 | 111,010/229,974 |
| ft09-0d8bbf25 | 1/1 | 95.07 | 100.00 | 4.93 | 0.00 | 0.00 | 81,138/54,330 |
| g50t-5849a774 | 1/1 | 21.43 | 0.00 | -21.43 | -21.43 | -3.00 | 223,166/189,688 |
| lf52-271a04aa | 1/1 | 9.99 | 1.82 | -8.18 | -9.09 | -2.00 | 181,856/136,358 |
| m0r0-492f87ba | 1/1 | 0.08 | 28.57 | 28.49 | 23.81 | 2.00 | 161,248/167,906 |
| sc25-635fd71a | 1/1 | 81.57 | 32.92 | -48.65 | -52.38 | -2.00 | 189,832/193,332 |
| sk48-d8078629 | 1/1 | 16.67 | 8.33 | -8.33 | -8.33 | -1.00 | 211,390/179,539 |
| sp80-589a99af | 1/1 | 4.76 | 4.76 | 0.00 | 0.00 | 0.00 | 194,589/233,373 |
| su15-1944f8ab | 1/1 | 5.15 | 12.81 | 7.67 | 6.67 | 1.00 | 214,618/218,186 |
| tn36-ef4dde99 | 1/1 | 1.46 | 12.53 | 11.07 | 17.86 | 2.00 | 202,463/204,363 |
| wa30-ee6fef47 | 1/1 | 2.22 | 2.22 | 0.00 | 0.00 | 0.00 | 184,880/195,862 |

## baseline

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/006-transient-history/baseline/benchmark.json`

States: `{"cancelled": 9, "won": 3}`. Stop reasons: `{"unknown": 9, "won": 3}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 153,068 | 153068 | 0 | 0.96 |
| bp35-0a0ad940 | 1 | 2.22 | 2.22 | 1/9 | 0 | 111,010 | 196555 | 85545 | 0.97 |
| ft09-0d8bbf25 | 1 | 95.07 | 100.00 | 6/6 | 1 | 81,138 | 81138 | 0 | 0.69 |
| g50t-5849a774 | 1 | 21.43 | 21.43 | 3/7 | 0 | 223,166 | 223166 | 0 | 0.97 |
| lf52-271a04aa | 1 | 9.99 | 10.91 | 3/10 | 0 | 181,856 | 184726 | 2870 | 0.97 |
| m0r0-492f87ba | 1 | 0.08 | 4.76 | 1/6 | 0 | 161,248 | 161248 | 0 | 0.97 |
| sc25-635fd71a | 1 | 81.57 | 100.00 | 6/6 | 1 | 189,832 | 189832 | 0 | 0.90 |
| sk48-d8078629 | 1 | 16.67 | 16.67 | 3/8 | 0 | 211,390 | 217141 | 5751 | 0.97 |
| sp80-589a99af | 1 | 4.76 | 4.76 | 1/6 | 0 | 194,589 | 194589 | 0 | 0.97 |
| su15-1944f8ab | 1 | 5.15 | 6.67 | 2/9 | 0 | 214,618 | 214618 | 0 | 0.97 |
| tn36-ef4dde99 | 1 | 1.46 | 3.57 | 1/7 | 0 | 202,463 | 205239 | 2776 | 0.97 |
| wa30-ee6fef47 | 1 | 2.22 | 2.22 | 1/9 | 0 | 184,880 | 184880 | 0 | 0.97 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| tn36-ef4dde99 | 0 | 1.46 | 3.57 | 1/7 | 178 | 202,463 | 205239 | 2776 | 0.97 | cancelled | unknown |
| sc25-635fd71a | 0 | 81.57 | 100.00 | 6/6 | 341 | 189,832 | 189832 | 0 | 0.90 | won | won |
| sp80-589a99af | 0 | 4.76 | 4.76 | 1/6 | 116 | 194,589 | 194589 | 0 | 0.97 | cancelled | unknown |
| bp35-0a0ad940 | 0 | 2.22 | 2.22 | 1/9 | 51 | 111,010 | 196555 | 85545 | 0.97 | cancelled | unknown |
| sk48-d8078629 | 0 | 16.67 | 16.67 | 3/8 | 305 | 211,390 | 217141 | 5751 | 0.97 | cancelled | unknown |
| lf52-271a04aa | 0 | 9.99 | 10.91 | 3/10 | 200 | 181,856 | 184726 | 2870 | 0.97 | cancelled | unknown |
| su15-1944f8ab | 0 | 5.15 | 6.67 | 2/9 | 83 | 214,618 | 214618 | 0 | 0.97 | cancelled | unknown |
| wa30-ee6fef47 | 0 | 2.22 | 2.22 | 1/9 | 159 | 184,880 | 184880 | 0 | 0.97 | cancelled | unknown |
| g50t-5849a774 | 0 | 21.43 | 21.43 | 3/7 | 191 | 223,166 | 223166 | 0 | 0.97 | cancelled | unknown |
| m0r0-492f87ba | 0 | 0.08 | 4.76 | 1/6 | 234 | 161,248 | 161248 | 0 | 0.97 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 95.07 | 100.00 | 6/6 | 123 | 81,138 | 81138 | 0 | 0.69 | won | won |
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 314 | 153,068 | 153068 | 0 | 0.96 | won | won |

### Data notes

- run 0: analyzer-reported minus history+final generated tokens = 2776; retain both accounting views
- run 3: analyzer-reported minus history+final generated tokens = 85545; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 5751; retain both accounting views
- run 5: analyzer-reported minus history+final generated tokens = 2870; retain both accounting views
- arm metadata records the shared budget deadline fired; 9 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged

## transient_history

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/006-transient-history/transient_history/benchmark.json`

States: `{"cancelled": 11, "won": 1}`. Stop reasons: `{"unknown": 11, "won": 1}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 58.33 | 58.33 | 6/8 | 0 | 161,515 | 161515 | 0 | 0.97 |
| bp35-0a0ad940 | 1 | 0.76 | 2.22 | 1/9 | 0 | 229,974 | 229974 | 0 | 0.97 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 54,330 | 54330 | 0 | 0.23 |
| g50t-5849a774 | 1 | 0.00 | 0.00 | 0/7 | 0 | 189,688 | 189688 | 0 | 0.97 |
| lf52-271a04aa | 1 | 1.82 | 1.82 | 1/10 | 0 | 136,358 | 136358 | 0 | 0.97 |
| m0r0-492f87ba | 1 | 28.57 | 28.57 | 3/6 | 0 | 167,906 | 167906 | 0 | 0.97 |
| sc25-635fd71a | 1 | 32.92 | 47.62 | 4/6 | 0 | 193,332 | 202502 | 9170 | 0.97 |
| sk48-d8078629 | 1 | 8.33 | 8.33 | 2/8 | 0 | 179,539 | 198802 | 19263 | 0.97 |
| sp80-589a99af | 1 | 4.76 | 4.76 | 1/6 | 0 | 233,373 | 233373 | 0 | 0.97 |
| su15-1944f8ab | 1 | 12.81 | 13.33 | 3/9 | 0 | 218,186 | 220326 | 2140 | 0.97 |
| tn36-ef4dde99 | 1 | 12.53 | 21.43 | 3/7 | 0 | 204,363 | 204998 | 635 | 0.97 |
| wa30-ee6fef47 | 1 | 2.22 | 2.22 | 1/9 | 0 | 195,862 | 210194 | 14332 | 0.97 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| tn36-ef4dde99 | 0 | 12.53 | 21.43 | 3/7 | 155 | 204,363 | 204998 | 635 | 0.97 | cancelled | unknown |
| sc25-635fd71a | 0 | 32.92 | 47.62 | 4/6 | 382 | 193,332 | 202502 | 9170 | 0.97 | cancelled | unknown |
| sp80-589a99af | 0 | 4.76 | 4.76 | 1/6 | 107 | 233,373 | 233373 | 0 | 0.97 | cancelled | unknown |
| bp35-0a0ad940 | 0 | 0.76 | 2.22 | 1/9 | 89 | 229,974 | 229974 | 0 | 0.97 | cancelled | unknown |
| sk48-d8078629 | 0 | 8.33 | 8.33 | 2/8 | 151 | 179,539 | 198802 | 19263 | 0.97 | cancelled | unknown |
| lf52-271a04aa | 0 | 1.82 | 1.82 | 1/10 | 169 | 136,358 | 136358 | 0 | 0.97 | cancelled | unknown |
| su15-1944f8ab | 0 | 12.81 | 13.33 | 3/9 | 162 | 218,186 | 220326 | 2140 | 0.97 | cancelled | unknown |
| wa30-ee6fef47 | 0 | 2.22 | 2.22 | 1/9 | 227 | 195,862 | 210194 | 14332 | 0.97 | cancelled | unknown |
| g50t-5849a774 | 0 | 0.00 | 0.00 | 0/7 | 88 | 189,688 | 189688 | 0 | 0.97 | cancelled | unknown |
| m0r0-492f87ba | 0 | 28.57 | 28.57 | 3/6 | 197 | 167,906 | 167906 | 0 | 0.97 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 79 | 54,330 | 54330 | 0 | 0.23 | won | won |
| ar25-0c556536 | 0 | 58.33 | 58.33 | 6/8 | 273 | 161,515 | 161515 | 0 | 0.97 | cancelled | unknown |

### Data notes

- run 0: analyzer-reported minus history+final generated tokens = 635; retain both accounting views
- run 1: analyzer-reported minus history+final generated tokens = 9170; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 19263; retain both accounting views
- run 6: analyzer-reported minus history+final generated tokens = 2140; retain both accounting views
- run 7: analyzer-reported minus history+final generated tokens = 14332; retain both accounting views
- arm metadata records the shared budget deadline fired; 11 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged
