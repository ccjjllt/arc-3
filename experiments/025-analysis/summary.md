# ARC-AGI-3 experiment summary

Generated: 2026-10-20T01:58:46.163041+00:00

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
| baseline | unknown | 25/25 | 45.88 | 48.83 | 106/183 | 7 | 4,449,839 | 4528520 (25/25) | 2.02 |
| admission_009 | unknown | 25/25 | 45.46 | 46.13 | 103/183 | 5 | 4,404,089 | 4600032 (25/25) | 2.02 |

## admission_009 − baseline

Descriptive comparison under a shared GPU budget; observations are not independent replications. Game IDs match exactly; occurrence indices do not establish paired random seeds.

Common games: 25; mean game score delta: -0.42.

| Game | Runs A/B | Score A | Score B | Δ score | Δ ceiling | Δ completed levels | Recorded tokens/run A/B |
|---|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1/1 | 100.00 | 41.67 | -58.33 | -58.33 | -3.00 | 111,365/183,250 |
| bp35-0a0ad940 | 1/1 | 2.22 | 0.85 | -1.37 | 0.00 | 0.00 | 184,463/147,498 |
| cd82-fb555c5d | 1/1 | 84.71 | 45.07 | -39.64 | -52.38 | -2.00 | 164,994/177,593 |
| cn04-2fe56bfb | 1/1 | 71.43 | 4.76 | -66.67 | -66.67 | -4.00 | 230,277/62,392 |
| dc22-fdcac232 | 1/1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 83,550/98,932 |
| ft09-0d8bbf25 | 1/1 | 100.00 | 99.91 | -0.09 | 0.00 | 0.00 | 82,841/116,742 |
| g50t-5849a774 | 1/1 | 10.71 | 10.71 | 0.00 | 0.00 | 0.00 | 164,729/226,628 |
| ka59-38d34dbb | 1/1 | 49.69 | 69.11 | 19.41 | 21.43 | 1.00 | 245,376/294,863 |
| lf52-271a04aa | 1/1 | 1.82 | 1.82 | 0.00 | 0.00 | 0.00 | 123,034/89,228 |
| lp85-305b61c3 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 140,492/204,496 |
| ls20-9607627b | 1/1 | 12.10 | 35.71 | 23.62 | 14.29 | 1.00 | 224,163/179,590 |
| m0r0-492f87ba | 1/1 | 97.23 | 0.00 | -97.23 | -100.00 | -6.00 | 280,831/97,281 |
| r11l-495a7899 | 1/1 | 4.76 | 47.62 | 42.86 | 42.86 | 3.00 | 144,688/194,343 |
| re86-8af5384d | 1/1 | 41.67 | 77.78 | 36.11 | 36.11 | 2.00 | 164,586/214,223 |
| s5i5-18d95033 | 1/1 | 2.93 | 58.33 | 55.40 | 50.00 | 4.00 | 244,082/326,560 |
| sb26-7fbdac44 | 1/1 | 95.32 | 100.00 | 4.68 | 0.00 | 0.00 | 73,491/60,385 |
| sc25-635fd71a | 1/1 | 47.62 | 71.43 | 23.81 | 23.81 | 1.00 | 162,096/213,996 |
| sk48-d8078629 | 1/1 | 27.78 | 1.15 | -26.63 | -25.00 | -3.00 | 318,388/100,857 |
| sp80-589a99af | 1/1 | 18.61 | 47.62 | 29.01 | 19.05 | 1.00 | 157,843/225,605 |
| su15-1944f8ab | 1/1 | 22.22 | 13.33 | -8.89 | -8.89 | -1.00 | 228,670/181,751 |
| tn36-ef4dde99 | 1/1 | 62.15 | 21.43 | -40.72 | -53.57 | -3.00 | 250,132/235,772 |
| tr87-cd924810 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 135,246/123,434 |
| tu93-0768757b | 1/1 | 70.57 | 74.82 | 4.25 | 0.00 | 0.00 | 274,139/310,235 |
| vc33-5430563c | 1/1 | 21.31 | 100.00 | 78.69 | 78.57 | 4.00 | 160,975/138,127 |
| wa30-ee6fef47 | 1/1 | 2.05 | 13.33 | 11.29 | 11.11 | 2.00 | 99,388/200,308 |

## baseline

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/025-admission-order/baseline/benchmark.json`

States: `{"cancelled": 18, "won": 7}`. Stop reasons: `{"unknown": 18, "won": 7}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 111,365 | 111365 | 0 | 0.87 |
| bp35-0a0ad940 | 1 | 2.22 | 2.22 | 1/9 | 0 | 184,463 | 184463 | 0 | 2.02 |
| cd82-fb555c5d | 1 | 84.71 | 100.00 | 6/6 | 1 | 164,994 | 164994 | 0 | 1.71 |
| cn04-2fe56bfb | 1 | 71.43 | 71.43 | 5/6 | 0 | 230,277 | 230277 | 0 | 2.02 |
| dc22-fdcac232 | 1 | 0.00 | 0.00 | 0/6 | 0 | 83,550 | 96267 | 12717 | 2.02 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 82,841 | 82841 | 0 | 0.83 |
| g50t-5849a774 | 1 | 10.71 | 10.71 | 2/7 | 0 | 164,729 | 172238 | 7509 | 2.02 |
| ka59-38d34dbb | 1 | 49.69 | 53.57 | 5/7 | 0 | 245,376 | 245376 | 0 | 2.02 |
| lf52-271a04aa | 1 | 1.82 | 1.82 | 1/10 | 0 | 123,034 | 123034 | 0 | 2.02 |
| lp85-305b61c3 | 1 | 100.00 | 100.00 | 8/8 | 1 | 140,492 | 140492 | 0 | 1.38 |
| ls20-9607627b | 1 | 12.10 | 21.43 | 3/7 | 0 | 224,163 | 224163 | 0 | 2.01 |
| m0r0-492f87ba | 1 | 97.23 | 100.00 | 6/6 | 1 | 280,831 | 280831 | 0 | 1.95 |
| r11l-495a7899 | 1 | 4.76 | 4.76 | 1/6 | 0 | 144,688 | 144688 | 0 | 2.01 |
| re86-8af5384d | 1 | 41.67 | 41.67 | 5/8 | 0 | 164,586 | 164586 | 0 | 2.01 |
| s5i5-18d95033 | 1 | 2.93 | 8.33 | 2/8 | 0 | 244,082 | 244082 | 0 | 2.01 |
| sb26-7fbdac44 | 1 | 95.32 | 100.00 | 8/8 | 1 | 73,491 | 73491 | 0 | 1.12 |
| sc25-635fd71a | 1 | 47.62 | 47.62 | 4/6 | 0 | 162,096 | 162096 | 0 | 2.01 |
| sk48-d8078629 | 1 | 27.78 | 27.78 | 4/8 | 0 | 318,388 | 326275 | 7887 | 2.01 |
| sp80-589a99af | 1 | 18.61 | 28.57 | 3/6 | 0 | 157,843 | 203941 | 46098 | 2.02 |
| su15-1944f8ab | 1 | 22.22 | 22.22 | 4/9 | 0 | 228,670 | 228670 | 0 | 2.01 |
| tn36-ef4dde99 | 1 | 62.15 | 75.00 | 6/7 | 0 | 250,132 | 250132 | 0 | 2.01 |
| tr87-cd924810 | 1 | 100.00 | 100.00 | 6/6 | 1 | 135,246 | 135246 | 0 | 1.13 |
| tu93-0768757b | 1 | 70.57 | 80.00 | 8/9 | 0 | 274,139 | 278609 | 4470 | 2.01 |
| vc33-5430563c | 1 | 21.31 | 21.43 | 3/7 | 0 | 160,975 | 160975 | 0 | 2.01 |
| wa30-ee6fef47 | 1 | 2.05 | 2.22 | 1/9 | 0 | 99,388 | 99388 | 0 | 2.01 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 273 | 111,365 | 111365 | 0 | 0.87 | won | won |
| bp35-0a0ad940 | 0 | 2.22 | 2.22 | 1/9 | 38 | 184,463 | 184463 | 0 | 2.02 | cancelled | unknown |
| cd82-fb555c5d | 0 | 84.71 | 100.00 | 6/6 | 170 | 164,994 | 164994 | 0 | 1.71 | won | won |
| cn04-2fe56bfb | 0 | 71.43 | 71.43 | 5/6 | 272 | 230,277 | 230277 | 0 | 2.02 | cancelled | unknown |
| dc22-fdcac232 | 0 | 0.00 | 0.00 | 0/6 | 220 | 83,550 | 96267 | 12717 | 2.02 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 92 | 82,841 | 82841 | 0 | 0.83 | won | won |
| g50t-5849a774 | 0 | 10.71 | 10.71 | 2/7 | 187 | 164,729 | 172238 | 7509 | 2.02 | cancelled | unknown |
| ka59-38d34dbb | 0 | 49.69 | 53.57 | 5/7 | 288 | 245,376 | 245376 | 0 | 2.02 | cancelled | unknown |
| lf52-271a04aa | 0 | 1.82 | 1.82 | 1/10 | 103 | 123,034 | 123034 | 0 | 2.02 | cancelled | unknown |
| lp85-305b61c3 | 0 | 100.00 | 100.00 | 8/8 | 139 | 140,492 | 140492 | 0 | 1.38 | won | won |
| ls20-9607627b | 0 | 12.10 | 21.43 | 3/7 | 479 | 224,163 | 224163 | 0 | 2.01 | cancelled | unknown |
| m0r0-492f87ba | 0 | 97.23 | 100.00 | 6/6 | 351 | 280,831 | 280831 | 0 | 1.95 | won | won |
| r11l-495a7899 | 0 | 4.76 | 4.76 | 1/6 | 37 | 144,688 | 144688 | 0 | 2.01 | cancelled | unknown |
| re86-8af5384d | 0 | 41.67 | 41.67 | 5/8 | 391 | 164,586 | 164586 | 0 | 2.01 | cancelled | unknown |
| s5i5-18d95033 | 0 | 2.93 | 8.33 | 2/8 | 259 | 244,082 | 244082 | 0 | 2.01 | cancelled | unknown |
| sb26-7fbdac44 | 0 | 95.32 | 100.00 | 8/8 | 155 | 73,491 | 73491 | 0 | 1.12 | won | won |
| sc25-635fd71a | 0 | 47.62 | 47.62 | 4/6 | 189 | 162,096 | 162096 | 0 | 2.01 | cancelled | unknown |
| sk48-d8078629 | 0 | 27.78 | 27.78 | 4/8 | 269 | 318,388 | 326275 | 7887 | 2.01 | cancelled | unknown |
| sp80-589a99af | 0 | 18.61 | 28.57 | 3/6 | 106 | 157,843 | 203941 | 46098 | 2.02 | cancelled | unknown |
| su15-1944f8ab | 0 | 22.22 | 22.22 | 4/9 | 172 | 228,670 | 228670 | 0 | 2.01 | cancelled | unknown |
| tn36-ef4dde99 | 0 | 62.15 | 75.00 | 6/7 | 331 | 250,132 | 250132 | 0 | 2.01 | cancelled | unknown |
| tr87-cd924810 | 0 | 100.00 | 100.00 | 6/6 | 311 | 135,246 | 135246 | 0 | 1.13 | won | won |
| tu93-0768757b | 0 | 70.57 | 80.00 | 8/9 | 223 | 274,139 | 278609 | 4470 | 2.01 | cancelled | unknown |
| vc33-5430563c | 0 | 21.31 | 21.43 | 3/7 | 103 | 160,975 | 160975 | 0 | 2.01 | cancelled | unknown |
| wa30-ee6fef47 | 0 | 2.05 | 2.22 | 1/9 | 178 | 99,388 | 99388 | 0 | 2.01 | cancelled | unknown |

### Data notes

- run 4: analyzer-reported minus history+final generated tokens = 12717; retain both accounting views
- run 6: analyzer-reported minus history+final generated tokens = 7509; retain both accounting views
- run 17: analyzer-reported minus history+final generated tokens = 7887; retain both accounting views
- run 18: analyzer-reported minus history+final generated tokens = 46098; retain both accounting views
- run 22: analyzer-reported minus history+final generated tokens = 4470; retain both accounting views
- arm metadata records the shared budget deadline fired; 18 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged

## admission_009

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/025-admission-order/admission_009/benchmark.json`

States: `{"cancelled": 20, "won": 5}`. Stop reasons: `{"unknown": 20, "won": 5}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 41.67 | 41.67 | 5/8 | 0 | 183,250 | 191443 | 8193 | 2.02 |
| bp35-0a0ad940 | 1 | 0.85 | 2.22 | 1/9 | 0 | 147,498 | 159535 | 12037 | 2.02 |
| cd82-fb555c5d | 1 | 45.07 | 47.62 | 4/6 | 0 | 177,593 | 183967 | 6374 | 2.02 |
| cn04-2fe56bfb | 1 | 4.76 | 4.76 | 1/6 | 0 | 62,392 | 113470 | 51078 | 2.02 |
| dc22-fdcac232 | 1 | 0.00 | 0.00 | 0/6 | 0 | 98,932 | 114136 | 15204 | 2.02 |
| ft09-0d8bbf25 | 1 | 99.91 | 100.00 | 6/6 | 1 | 116,742 | 116742 | 0 | 0.49 |
| g50t-5849a774 | 1 | 10.71 | 10.71 | 2/7 | 0 | 226,628 | 226628 | 0 | 2.02 |
| ka59-38d34dbb | 1 | 69.11 | 75.00 | 6/7 | 0 | 294,863 | 298130 | 3267 | 2.02 |
| lf52-271a04aa | 1 | 1.82 | 1.82 | 1/10 | 0 | 89,228 | 89228 | 0 | 2.01 |
| lp85-305b61c3 | 1 | 100.00 | 100.00 | 8/8 | 1 | 204,496 | 204496 | 0 | 1.69 |
| ls20-9607627b | 1 | 35.71 | 35.71 | 4/7 | 0 | 179,590 | 179590 | 0 | 2.01 |
| m0r0-492f87ba | 1 | 0.00 | 0.00 | 0/6 | 0 | 97,281 | 108548 | 11267 | 2.01 |
| r11l-495a7899 | 1 | 47.62 | 47.62 | 4/6 | 0 | 194,343 | 197519 | 3176 | 2.02 |
| re86-8af5384d | 1 | 77.78 | 77.78 | 7/8 | 0 | 214,223 | 214223 | 0 | 2.02 |
| s5i5-18d95033 | 1 | 58.33 | 58.33 | 6/8 | 0 | 326,560 | 351151 | 24591 | 2.01 |
| sb26-7fbdac44 | 1 | 100.00 | 100.00 | 8/8 | 1 | 60,385 | 60385 | 0 | 0.83 |
| sc25-635fd71a | 1 | 71.43 | 71.43 | 5/6 | 0 | 213,996 | 213996 | 0 | 2.01 |
| sk48-d8078629 | 1 | 1.15 | 2.78 | 1/8 | 0 | 100,857 | 119506 | 18649 | 2.02 |
| sp80-589a99af | 1 | 47.62 | 47.62 | 4/6 | 0 | 225,605 | 236239 | 10634 | 2.02 |
| su15-1944f8ab | 1 | 13.33 | 13.33 | 3/9 | 0 | 181,751 | 181751 | 0 | 2.01 |
| tn36-ef4dde99 | 1 | 21.43 | 21.43 | 3/7 | 0 | 235,772 | 235772 | 0 | 2.01 |
| tr87-cd924810 | 1 | 100.00 | 100.00 | 6/6 | 1 | 123,434 | 123434 | 0 | 0.87 |
| tu93-0768757b | 1 | 74.82 | 80.00 | 8/9 | 0 | 310,235 | 319424 | 9189 | 2.01 |
| vc33-5430563c | 1 | 100.00 | 100.00 | 7/7 | 1 | 138,127 | 138127 | 0 | 1.14 |
| wa30-ee6fef47 | 1 | 13.33 | 13.33 | 3/9 | 0 | 200,308 | 222592 | 22284 | 2.02 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| ar25-0c556536 | 0 | 41.67 | 41.67 | 5/8 | 174 | 183,250 | 191443 | 8193 | 2.02 | cancelled | unknown |
| bp35-0a0ad940 | 0 | 0.85 | 2.22 | 1/9 | 74 | 147,498 | 159535 | 12037 | 2.02 | cancelled | unknown |
| cd82-fb555c5d | 0 | 45.07 | 47.62 | 4/6 | 154 | 177,593 | 183967 | 6374 | 2.02 | cancelled | unknown |
| cn04-2fe56bfb | 0 | 4.76 | 4.76 | 1/6 | 56 | 62,392 | 113470 | 51078 | 2.02 | cancelled | unknown |
| dc22-fdcac232 | 0 | 0.00 | 0.00 | 0/6 | 101 | 98,932 | 114136 | 15204 | 2.02 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 99.91 | 100.00 | 6/6 | 142 | 116,742 | 116742 | 0 | 0.49 | won | won |
| g50t-5849a774 | 0 | 10.71 | 10.71 | 2/7 | 193 | 226,628 | 226628 | 0 | 2.02 | cancelled | unknown |
| ka59-38d34dbb | 0 | 69.11 | 75.00 | 6/7 | 324 | 294,863 | 298130 | 3267 | 2.02 | cancelled | unknown |
| lf52-271a04aa | 0 | 1.82 | 1.82 | 1/10 | 109 | 89,228 | 89228 | 0 | 2.01 | cancelled | unknown |
| lp85-305b61c3 | 0 | 100.00 | 100.00 | 8/8 | 146 | 204,496 | 204496 | 0 | 1.69 | won | won |
| ls20-9607627b | 0 | 35.71 | 35.71 | 4/7 | 307 | 179,590 | 179590 | 0 | 2.01 | cancelled | unknown |
| m0r0-492f87ba | 0 | 0.00 | 0.00 | 0/6 | 57 | 97,281 | 108548 | 11267 | 2.01 | cancelled | unknown |
| r11l-495a7899 | 0 | 47.62 | 47.62 | 4/6 | 51 | 194,343 | 197519 | 3176 | 2.02 | cancelled | unknown |
| re86-8af5384d | 0 | 77.78 | 77.78 | 7/8 | 571 | 214,223 | 214223 | 0 | 2.02 | cancelled | unknown |
| s5i5-18d95033 | 0 | 58.33 | 58.33 | 6/8 | 216 | 326,560 | 351151 | 24591 | 2.01 | cancelled | unknown |
| sb26-7fbdac44 | 0 | 100.00 | 100.00 | 8/8 | 156 | 60,385 | 60385 | 0 | 0.83 | won | won |
| sc25-635fd71a | 0 | 71.43 | 71.43 | 5/6 | 315 | 213,996 | 213996 | 0 | 2.01 | cancelled | unknown |
| sk48-d8078629 | 0 | 1.15 | 2.78 | 1/8 | 104 | 100,857 | 119506 | 18649 | 2.02 | cancelled | unknown |
| sp80-589a99af | 0 | 47.62 | 47.62 | 4/6 | 99 | 225,605 | 236239 | 10634 | 2.02 | cancelled | unknown |
| su15-1944f8ab | 0 | 13.33 | 13.33 | 3/9 | 217 | 181,751 | 181751 | 0 | 2.01 | cancelled | unknown |
| tn36-ef4dde99 | 0 | 21.43 | 21.43 | 3/7 | 120 | 235,772 | 235772 | 0 | 2.01 | cancelled | unknown |
| tr87-cd924810 | 0 | 100.00 | 100.00 | 6/6 | 321 | 123,434 | 123434 | 0 | 0.87 | won | won |
| tu93-0768757b | 0 | 74.82 | 80.00 | 8/9 | 272 | 310,235 | 319424 | 9189 | 2.01 | cancelled | unknown |
| vc33-5430563c | 0 | 100.00 | 100.00 | 7/7 | 225 | 138,127 | 138127 | 0 | 1.14 | won | won |
| wa30-ee6fef47 | 0 | 13.33 | 13.33 | 3/9 | 448 | 200,308 | 222592 | 22284 | 2.02 | cancelled | unknown |

### Data notes

- run 0: analyzer-reported minus history+final generated tokens = 8193; retain both accounting views
- run 1: analyzer-reported minus history+final generated tokens = 12037; retain both accounting views
- run 2: analyzer-reported minus history+final generated tokens = 6374; retain both accounting views
- run 3: analyzer-reported minus history+final generated tokens = 51078; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 15204; retain both accounting views
- run 7: analyzer-reported minus history+final generated tokens = 3267; retain both accounting views
- run 11: analyzer-reported minus history+final generated tokens = 11267; retain both accounting views
- run 12: analyzer-reported minus history+final generated tokens = 3176; retain both accounting views
- run 14: analyzer-reported minus history+final generated tokens = 24591; retain both accounting views
- run 17: analyzer-reported minus history+final generated tokens = 18649; retain both accounting views
- run 18: analyzer-reported minus history+final generated tokens = 10634; retain both accounting views
- run 22: analyzer-reported minus history+final generated tokens = 9189; retain both accounting views
- run 24: analyzer-reported minus history+final generated tokens = 22284; retain both accounting views
- arm metadata records the shared budget deadline fired; 20 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged
