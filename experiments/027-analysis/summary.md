# ARC-AGI-3 experiment summary

Generated: 2026-10-20T11:13:41.185489+00:00

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
| baseline | local-experiment | 25/25 | 50.43 | 52.92 | 112/183 | 8 | 4,444,779 | 4501302 (25/25) | 2.02 |
| tail_80k | local-experiment | 25/25 | 44.45 | 45.47 | 101/183 | 7 | 4,450,786 | 4624444 (25/25) | 2.02 |

## tail_80k − baseline

Descriptive comparison under a shared GPU budget; observations are not independent replications. Game IDs match exactly; occurrence indices do not establish paired random seeds.

Common games: 25; mean game score delta: -5.98.

| Game | Runs A/B | Score A | Score B | Δ score | Δ ceiling | Δ completed levels | Recorded tokens/run A/B |
|---|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 169,924/246,710 |
| bp35-0a0ad940 | 1/1 | 0.00 | 2.22 | 2.22 | 2.22 | 1.00 | 110,046/95,729 |
| cd82-fb555c5d | 1/1 | 67.10 | 100.00 | 32.90 | 0.00 | 0.00 | 233,538/115,987 |
| cn04-2fe56bfb | 1/1 | 4.76 | 14.29 | 9.52 | 9.52 | 1.00 | 190,037/164,324 |
| dc22-fdcac232 | 1/1 | 47.62 | 47.62 | 0.00 | 0.00 | 0.00 | 305,091/258,663 |
| ft09-0d8bbf25 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 101,842/109,250 |
| g50t-5849a774 | 1/1 | 10.71 | 0.00 | -10.71 | -10.71 | -2.00 | 167,527/70,919 |
| ka59-38d34dbb | 1/1 | 53.57 | 10.71 | -42.86 | -42.86 | -3.00 | 244,432/238,574 |
| lf52-271a04aa | 1/1 | 4.73 | 0.92 | -3.82 | -3.64 | -1.00 | 139,419/87,072 |
| lp85-305b61c3 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 128,708/240,228 |
| ls20-9607627b | 1/1 | 3.57 | 20.22 | 16.65 | 17.86 | 2.00 | 110,124/241,571 |
| m0r0-492f87ba | 1/1 | 100.00 | 39.51 | -60.49 | -52.38 | -2.00 | 212,804/209,270 |
| r11l-495a7899 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 198,733/259,770 |
| re86-8af5384d | 1/1 | 58.33 | 41.67 | -16.67 | -16.67 | -1.00 | 217,906/198,838 |
| s5i5-18d95033 | 1/1 | 2.78 | 58.33 | 55.56 | 55.56 | 5.00 | 130,612/302,497 |
| sb26-7fbdac44 | 1/1 | 100.00 | 26.62 | -73.38 | -72.22 | -4.00 | 32,667/124,846 |
| sc25-635fd71a | 1/1 | 47.62 | 86.91 | 39.29 | 52.38 | 2.00 | 162,799/145,114 |
| sk48-d8078629 | 1/1 | 2.78 | 2.78 | 0.00 | 0.00 | 0.00 | 119,154/107,763 |
| sp80-589a99af | 1/1 | 47.62 | 28.57 | -19.05 | -19.05 | -1.00 | 225,878/143,605 |
| su15-1944f8ab | 1/1 | 42.14 | 22.22 | -19.92 | -24.44 | -2.00 | 295,000/266,905 |
| tn36-ef4dde99 | 1/1 | 29.28 | 2.82 | -26.46 | -32.14 | -3.00 | 166,295/124,302 |
| tr87-cd924810 | 1/1 | 100.00 | 71.43 | -28.57 | -28.57 | -1.00 | 105,816/109,223 |
| tu93-0768757b | 1/1 | 68.05 | 99.75 | 31.71 | 20.00 | 1.00 | 321,873/287,247 |
| vc33-5430563c | 1/1 | 53.57 | 21.43 | -32.14 | -32.14 | -2.00 | 183,410/135,298 |
| wa30-ee6fef47 | 1/1 | 16.49 | 13.33 | -3.16 | -8.89 | -1.00 | 171,144/167,081 |

## baseline

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/027-tail-confirm/baseline/benchmark.json`

States: `{"cancelled": 17, "won": 8}`. Stop reasons: `{"unknown": 17, "won": 8}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 169,924 | 169924 | 0 | 1.04 |
| bp35-0a0ad940 | 1 | 0.00 | 0.00 | 0/9 | 0 | 110,046 | 110046 | 0 | 2.02 |
| cd82-fb555c5d | 1 | 67.10 | 100.00 | 6/6 | 1 | 233,538 | 233538 | 0 | 1.67 |
| cn04-2fe56bfb | 1 | 4.76 | 4.76 | 1/6 | 0 | 190,037 | 195199 | 5162 | 2.02 |
| dc22-fdcac232 | 1 | 47.62 | 47.62 | 4/6 | 0 | 305,091 | 309853 | 4762 | 2.02 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 101,842 | 101842 | 0 | 1.20 |
| g50t-5849a774 | 1 | 10.71 | 10.71 | 2/7 | 0 | 167,527 | 169862 | 2335 | 2.01 |
| ka59-38d34dbb | 1 | 53.57 | 53.57 | 5/7 | 0 | 244,432 | 248816 | 4384 | 2.02 |
| lf52-271a04aa | 1 | 4.73 | 5.45 | 2/10 | 0 | 139,419 | 139419 | 0 | 2.02 |
| lp85-305b61c3 | 1 | 100.00 | 100.00 | 8/8 | 1 | 128,708 | 128708 | 0 | 0.83 |
| ls20-9607627b | 1 | 3.57 | 3.57 | 1/7 | 0 | 110,124 | 110124 | 0 | 2.01 |
| m0r0-492f87ba | 1 | 100.00 | 100.00 | 6/6 | 1 | 212,804 | 212804 | 0 | 1.50 |
| r11l-495a7899 | 1 | 100.00 | 100.00 | 6/6 | 1 | 198,733 | 198733 | 0 | 1.75 |
| re86-8af5384d | 1 | 58.33 | 58.33 | 6/8 | 0 | 217,906 | 217906 | 0 | 2.01 |
| s5i5-18d95033 | 1 | 2.78 | 2.78 | 1/8 | 0 | 130,612 | 130612 | 0 | 2.01 |
| sb26-7fbdac44 | 1 | 100.00 | 100.00 | 8/8 | 1 | 32,667 | 32667 | 0 | 0.43 |
| sc25-635fd71a | 1 | 47.62 | 47.62 | 4/6 | 0 | 162,799 | 174547 | 11748 | 2.01 |
| sk48-d8078629 | 1 | 2.78 | 2.78 | 1/8 | 0 | 119,154 | 119154 | 0 | 2.01 |
| sp80-589a99af | 1 | 47.62 | 47.62 | 4/6 | 0 | 225,878 | 228475 | 2597 | 2.02 |
| su15-1944f8ab | 1 | 42.14 | 46.67 | 6/9 | 0 | 295,000 | 295000 | 0 | 2.01 |
| tn36-ef4dde99 | 1 | 29.28 | 35.71 | 4/7 | 0 | 166,295 | 166295 | 0 | 2.01 |
| tr87-cd924810 | 1 | 100.00 | 100.00 | 6/6 | 1 | 105,816 | 105816 | 0 | 1.75 |
| tu93-0768757b | 1 | 68.05 | 80.00 | 8/9 | 0 | 321,873 | 344278 | 22405 | 2.01 |
| vc33-5430563c | 1 | 53.57 | 53.57 | 5/7 | 0 | 183,410 | 186540 | 3130 | 2.02 |
| wa30-ee6fef47 | 1 | 16.49 | 22.22 | 4/9 | 0 | 171,144 | 171144 | 0 | 2.01 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 287 | 169,924 | 169924 | 0 | 1.04 | won | won |
| bp35-0a0ad940 | 0 | 0.00 | 0.00 | 0/9 | 100 | 110,046 | 110046 | 0 | 2.02 | cancelled | unknown |
| cd82-fb555c5d | 0 | 67.10 | 100.00 | 6/6 | 214 | 233,538 | 233538 | 0 | 1.67 | won | won |
| cn04-2fe56bfb | 0 | 4.76 | 4.76 | 1/6 | 98 | 190,037 | 195199 | 5162 | 2.02 | cancelled | unknown |
| dc22-fdcac232 | 0 | 47.62 | 47.62 | 4/6 | 327 | 305,091 | 309853 | 4762 | 2.02 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 124 | 101,842 | 101842 | 0 | 1.20 | won | won |
| g50t-5849a774 | 0 | 10.71 | 10.71 | 2/7 | 257 | 167,527 | 169862 | 2335 | 2.01 | cancelled | unknown |
| ka59-38d34dbb | 0 | 53.57 | 53.57 | 5/7 | 234 | 244,432 | 248816 | 4384 | 2.02 | cancelled | unknown |
| lf52-271a04aa | 0 | 4.73 | 5.45 | 2/10 | 159 | 139,419 | 139419 | 0 | 2.02 | cancelled | unknown |
| lp85-305b61c3 | 0 | 100.00 | 100.00 | 8/8 | 123 | 128,708 | 128708 | 0 | 0.83 | won | won |
| ls20-9607627b | 0 | 3.57 | 3.57 | 1/7 | 270 | 110,124 | 110124 | 0 | 2.01 | cancelled | unknown |
| m0r0-492f87ba | 0 | 100.00 | 100.00 | 6/6 | 308 | 212,804 | 212804 | 0 | 1.50 | won | won |
| r11l-495a7899 | 0 | 100.00 | 100.00 | 6/6 | 102 | 198,733 | 198733 | 0 | 1.75 | won | won |
| re86-8af5384d | 0 | 58.33 | 58.33 | 6/8 | 555 | 217,906 | 217906 | 0 | 2.01 | cancelled | unknown |
| s5i5-18d95033 | 0 | 2.78 | 2.78 | 1/8 | 56 | 130,612 | 130612 | 0 | 2.01 | cancelled | unknown |
| sb26-7fbdac44 | 0 | 100.00 | 100.00 | 8/8 | 130 | 32,667 | 32667 | 0 | 0.43 | won | won |
| sc25-635fd71a | 0 | 47.62 | 47.62 | 4/6 | 191 | 162,799 | 174547 | 11748 | 2.01 | cancelled | unknown |
| sk48-d8078629 | 0 | 2.78 | 2.78 | 1/8 | 76 | 119,154 | 119154 | 0 | 2.01 | cancelled | unknown |
| sp80-589a99af | 0 | 47.62 | 47.62 | 4/6 | 76 | 225,878 | 228475 | 2597 | 2.02 | cancelled | unknown |
| su15-1944f8ab | 0 | 42.14 | 46.67 | 6/9 | 266 | 295,000 | 295000 | 0 | 2.01 | cancelled | unknown |
| tn36-ef4dde99 | 0 | 29.28 | 35.71 | 4/7 | 224 | 166,295 | 166295 | 0 | 2.01 | cancelled | unknown |
| tr87-cd924810 | 0 | 100.00 | 100.00 | 6/6 | 264 | 105,816 | 105816 | 0 | 1.75 | won | won |
| tu93-0768757b | 0 | 68.05 | 80.00 | 8/9 | 276 | 321,873 | 344278 | 22405 | 2.01 | cancelled | unknown |
| vc33-5430563c | 0 | 53.57 | 53.57 | 5/7 | 199 | 183,410 | 186540 | 3130 | 2.02 | cancelled | unknown |
| wa30-ee6fef47 | 0 | 16.49 | 22.22 | 4/9 | 542 | 171,144 | 171144 | 0 | 2.01 | cancelled | unknown |

### Data notes

- run 3: analyzer-reported minus history+final generated tokens = 5162; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 4762; retain both accounting views
- run 6: analyzer-reported minus history+final generated tokens = 2335; retain both accounting views
- run 7: analyzer-reported minus history+final generated tokens = 4384; retain both accounting views
- run 16: analyzer-reported minus history+final generated tokens = 11748; retain both accounting views
- run 18: analyzer-reported minus history+final generated tokens = 2597; retain both accounting views
- run 22: analyzer-reported minus history+final generated tokens = 22405; retain both accounting views
- run 23: analyzer-reported minus history+final generated tokens = 3130; retain both accounting views
- arm metadata records the shared budget deadline fired; 17 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged

## tail_80k

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/027-tail-confirm/tail_80k/benchmark.json`

States: `{"cancelled": 18, "won": 7}`. Stop reasons: `{"unknown": 18, "won": 7}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 246,710 | 246710 | 0 | 1.69 |
| bp35-0a0ad940 | 1 | 2.22 | 2.22 | 1/9 | 0 | 95,729 | 127083 | 31354 | 2.02 |
| cd82-fb555c5d | 1 | 100.00 | 100.00 | 6/6 | 1 | 115,987 | 115987 | 0 | 0.87 |
| cn04-2fe56bfb | 1 | 14.29 | 14.29 | 2/6 | 0 | 164,324 | 164324 | 0 | 2.01 |
| dc22-fdcac232 | 1 | 47.62 | 47.62 | 4/6 | 0 | 258,663 | 289632 | 30969 | 2.02 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 109,250 | 109250 | 0 | 1.02 |
| g50t-5849a774 | 1 | 0.00 | 0.00 | 0/7 | 0 | 70,919 | 73136 | 2217 | 2.01 |
| ka59-38d34dbb | 1 | 10.71 | 10.71 | 2/7 | 0 | 238,574 | 265453 | 26879 | 2.02 |
| lf52-271a04aa | 1 | 0.92 | 1.82 | 1/10 | 0 | 87,072 | 87072 | 0 | 2.01 |
| lp85-305b61c3 | 1 | 100.00 | 100.00 | 8/8 | 1 | 240,228 | 240228 | 0 | 1.74 |
| ls20-9607627b | 1 | 20.22 | 21.43 | 3/7 | 0 | 241,571 | 241571 | 0 | 2.01 |
| m0r0-492f87ba | 1 | 39.51 | 47.62 | 4/6 | 0 | 209,270 | 209270 | 0 | 2.01 |
| r11l-495a7899 | 1 | 100.00 | 100.00 | 6/6 | 1 | 259,770 | 259770 | 0 | 1.88 |
| re86-8af5384d | 1 | 41.67 | 41.67 | 5/8 | 0 | 198,838 | 198838 | 0 | 2.01 |
| s5i5-18d95033 | 1 | 58.33 | 58.33 | 6/8 | 0 | 302,497 | 302497 | 0 | 2.01 |
| sb26-7fbdac44 | 1 | 26.62 | 27.78 | 4/8 | 0 | 124,846 | 128484 | 3638 | 2.01 |
| sc25-635fd71a | 1 | 86.91 | 100.00 | 6/6 | 1 | 145,114 | 145114 | 0 | 1.25 |
| sk48-d8078629 | 1 | 2.78 | 2.78 | 1/8 | 0 | 107,763 | 127057 | 19294 | 2.01 |
| sp80-589a99af | 1 | 28.57 | 28.57 | 3/6 | 0 | 143,605 | 185521 | 41916 | 2.01 |
| su15-1944f8ab | 1 | 22.22 | 22.22 | 4/9 | 0 | 266,905 | 274531 | 7626 | 2.01 |
| tn36-ef4dde99 | 1 | 2.82 | 3.57 | 1/7 | 0 | 124,302 | 124302 | 0 | 2.01 |
| tr87-cd924810 | 1 | 71.43 | 71.43 | 5/6 | 0 | 109,223 | 109223 | 0 | 2.01 |
| tu93-0768757b | 1 | 99.75 | 100.00 | 9/9 | 1 | 287,247 | 287247 | 0 | 1.74 |
| vc33-5430563c | 1 | 21.43 | 21.43 | 3/7 | 0 | 135,298 | 135298 | 0 | 2.01 |
| wa30-ee6fef47 | 1 | 13.33 | 13.33 | 3/9 | 0 | 167,081 | 176846 | 9765 | 2.02 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 282 | 246,710 | 246710 | 0 | 1.69 | won | won |
| bp35-0a0ad940 | 0 | 2.22 | 2.22 | 1/9 | 31 | 95,729 | 127083 | 31354 | 2.02 | cancelled | unknown |
| cd82-fb555c5d | 0 | 100.00 | 100.00 | 6/6 | 125 | 115,987 | 115987 | 0 | 0.87 | won | won |
| cn04-2fe56bfb | 0 | 14.29 | 14.29 | 2/6 | 122 | 164,324 | 164324 | 0 | 2.01 | cancelled | unknown |
| dc22-fdcac232 | 0 | 47.62 | 47.62 | 4/6 | 301 | 258,663 | 289632 | 30969 | 2.02 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 204 | 109,250 | 109250 | 0 | 1.02 | won | won |
| g50t-5849a774 | 0 | 0.00 | 0.00 | 0/7 | 35 | 70,919 | 73136 | 2217 | 2.01 | cancelled | unknown |
| ka59-38d34dbb | 0 | 10.71 | 10.71 | 2/7 | 122 | 238,574 | 265453 | 26879 | 2.02 | cancelled | unknown |
| lf52-271a04aa | 0 | 0.92 | 1.82 | 1/10 | 160 | 87,072 | 87072 | 0 | 2.01 | cancelled | unknown |
| lp85-305b61c3 | 0 | 100.00 | 100.00 | 8/8 | 157 | 240,228 | 240228 | 0 | 1.74 | won | won |
| ls20-9607627b | 0 | 20.22 | 21.43 | 3/7 | 282 | 241,571 | 241571 | 0 | 2.01 | cancelled | unknown |
| m0r0-492f87ba | 0 | 39.51 | 47.62 | 4/6 | 222 | 209,270 | 209270 | 0 | 2.01 | cancelled | unknown |
| r11l-495a7899 | 0 | 100.00 | 100.00 | 6/6 | 104 | 259,770 | 259770 | 0 | 1.88 | won | won |
| re86-8af5384d | 0 | 41.67 | 41.67 | 5/8 | 384 | 198,838 | 198838 | 0 | 2.01 | cancelled | unknown |
| s5i5-18d95033 | 0 | 58.33 | 58.33 | 6/8 | 298 | 302,497 | 302497 | 0 | 2.01 | cancelled | unknown |
| sb26-7fbdac44 | 0 | 26.62 | 27.78 | 4/8 | 131 | 124,846 | 128484 | 3638 | 2.01 | cancelled | unknown |
| sc25-635fd71a | 0 | 86.91 | 100.00 | 6/6 | 302 | 145,114 | 145114 | 0 | 1.25 | won | won |
| sk48-d8078629 | 0 | 2.78 | 2.78 | 1/8 | 112 | 107,763 | 127057 | 19294 | 2.01 | cancelled | unknown |
| sp80-589a99af | 0 | 28.57 | 28.57 | 3/6 | 61 | 143,605 | 185521 | 41916 | 2.01 | cancelled | unknown |
| su15-1944f8ab | 0 | 22.22 | 22.22 | 4/9 | 98 | 266,905 | 274531 | 7626 | 2.01 | cancelled | unknown |
| tn36-ef4dde99 | 0 | 2.82 | 3.57 | 1/7 | 108 | 124,302 | 124302 | 0 | 2.01 | cancelled | unknown |
| tr87-cd924810 | 0 | 71.43 | 71.43 | 5/6 | 343 | 109,223 | 109223 | 0 | 2.01 | cancelled | unknown |
| tu93-0768757b | 0 | 99.75 | 100.00 | 9/9 | 236 | 287,247 | 287247 | 0 | 1.74 | won | won |
| vc33-5430563c | 0 | 21.43 | 21.43 | 3/7 | 142 | 135,298 | 135298 | 0 | 2.01 | cancelled | unknown |
| wa30-ee6fef47 | 0 | 13.33 | 13.33 | 3/9 | 318 | 167,081 | 176846 | 9765 | 2.02 | cancelled | unknown |

### Data notes

- run 1: analyzer-reported minus history+final generated tokens = 31354; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 30969; retain both accounting views
- run 6: analyzer-reported minus history+final generated tokens = 2217; retain both accounting views
- run 7: analyzer-reported minus history+final generated tokens = 26879; retain both accounting views
- run 15: analyzer-reported minus history+final generated tokens = 3638; retain both accounting views
- run 17: analyzer-reported minus history+final generated tokens = 19294; retain both accounting views
- run 18: analyzer-reported minus history+final generated tokens = 41916; retain both accounting views
- run 19: analyzer-reported minus history+final generated tokens = 7626; retain both accounting views
- run 24: analyzer-reported minus history+final generated tokens = 9765; retain both accounting views
- arm metadata records the shared budget deadline fired; 18 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged
