# ARC-AGI-3 experiment summary

Generated: 2026-10-11T01:19:16.527689+00:00

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
| run005 | local-experiment | 25/25 | 49.90 | 50.38 | 106/183 | 9 | 4,311,602 | 4481732 (25/25) | 2.04 |
| run003 | local-experiment | 16/16 | 49.25 | 52.51 | 72/121 | 5 | 2,810,615 | 2856116 (16/16) | 1.30 |

## run005 − run003

Descriptive comparison under a shared GPU budget; observations are not independent replications. Game IDs match exactly; occurrence indices do not establish paired random seeds.

Common games: 16; mean game score delta: -4.88.

| Game | Runs A/B | Score A | Score B | Δ score | Δ ceiling | Δ completed levels | Recorded tokens/run A/B |
|---|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 138,249/120,474 |
| bp35-0a0ad940 | 1/1 | 2.22 | 1.85 | -0.37 | 0.00 | 0.00 | 180,624/108,249 |
| cd82-fb555c5d | 1/1 | 75.62 | 100.00 | 24.38 | 0.00 | 0.00 | 144,787/94,146 |
| ft09-0d8bbf25 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 105,112/171,254 |
| g50t-5849a774 | 1/1 | 2.68 | 10.71 | 8.03 | 7.14 | 1.00 | 172,628/212,938 |
| lf52-271a04aa | 1/1 | 7.73 | 10.91 | 3.18 | 0.00 | 0.00 | 176,221/247,589 |
| lp85-305b61c3 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 135,117/142,388 |
| ls20-9607627b | 1/1 | 34.07 | 29.21 | -4.86 | 0.00 | 0.00 | 207,912/240,037 |
| m0r0-492f87ba | 1/1 | 66.52 | 28.36 | -38.15 | -42.86 | -2.00 | 231,909/192,886 |
| r11l-495a7899 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 181,624/179,655 |
| sc25-635fd71a | 1/1 | 47.62 | 0.00 | -47.62 | -47.62 | -4.00 | 158,928/89,892 |
| sk48-d8078629 | 1/1 | 1.37 | 8.33 | 6.97 | 5.56 | 1.00 | 156,178/199,064 |
| su15-1944f8ab | 1/1 | 62.22 | 18.24 | -43.98 | -40.00 | -3.00 | 239,090/219,822 |
| tn36-ef4dde99 | 1/1 | 13.76 | 0.00 | -13.76 | -21.43 | -3.00 | 202,589/125,296 |
| tu93-0768757b | 1/1 | 71.98 | 100.00 | 28.02 | 20.00 | 1.00 | 223,225/222,117 |
| wa30-ee6fef47 | 1/1 | 2.22 | 2.22 | 0.00 | 0.00 | 0.00 | 156,422/149,012 |

candidate_only_games: cn04-2fe56bfb, dc22-fdcac232, ka59-38d34dbb, re86-8af5384d, s5i5-18d95033, sb26-7fbdac44, sp80-589a99af, tr87-cd924810, vc33-5430563c

## run005

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/005-full-baseline/baseline/benchmark.json`

States: `{"cancelled": 16, "won": 9}`. Stop reasons: `{"unknown": 16, "won": 9}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 120,474 | 120474 | 0 | 0.82 |
| bp35-0a0ad940 | 1 | 1.85 | 2.22 | 1/9 | 0 | 108,249 | 199756 | 91507 | 2.04 |
| cd82-fb555c5d | 1 | 100.00 | 100.00 | 6/6 | 1 | 94,146 | 94146 | 0 | 0.75 |
| cn04-2fe56bfb | 1 | 100.00 | 100.00 | 6/6 | 1 | 211,837 | 211837 | 0 | 1.77 |
| dc22-fdcac232 | 1 | 47.62 | 47.62 | 4/6 | 0 | 279,258 | 285679 | 6421 | 2.02 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 171,254 | 171254 | 0 | 1.40 |
| g50t-5849a774 | 1 | 10.71 | 10.71 | 2/7 | 0 | 212,938 | 212938 | 0 | 2.02 |
| ka59-38d34dbb | 1 | 53.57 | 53.57 | 5/7 | 0 | 235,496 | 248246 | 12750 | 2.02 |
| lf52-271a04aa | 1 | 10.91 | 10.91 | 3/10 | 0 | 247,589 | 247589 | 0 | 2.01 |
| lp85-305b61c3 | 1 | 100.00 | 100.00 | 8/8 | 1 | 142,388 | 142388 | 0 | 0.91 |
| ls20-9607627b | 1 | 29.21 | 35.71 | 4/7 | 0 | 240,037 | 240037 | 0 | 2.01 |
| m0r0-492f87ba | 1 | 28.36 | 28.57 | 3/6 | 0 | 192,886 | 198778 | 5892 | 2.02 |
| r11l-495a7899 | 1 | 100.00 | 100.00 | 6/6 | 1 | 179,655 | 179655 | 0 | 1.02 |
| re86-8af5384d | 1 | 58.33 | 58.33 | 6/8 | 0 | 249,126 | 256118 | 6992 | 2.02 |
| s5i5-18d95033 | 1 | 1.93 | 2.78 | 1/8 | 0 | 122,364 | 122799 | 435 | 2.02 |
| sb26-7fbdac44 | 1 | 100.00 | 100.00 | 8/8 | 1 | 29,749 | 29749 | 0 | 0.40 |
| sc25-635fd71a | 1 | 0.00 | 0.00 | 0/6 | 0 | 89,892 | 90378 | 486 | 2.02 |
| sk48-d8078629 | 1 | 8.33 | 8.33 | 2/8 | 0 | 199,064 | 200101 | 1037 | 2.02 |
| sp80-589a99af | 1 | 4.76 | 4.76 | 1/6 | 0 | 150,013 | 184496 | 34483 | 2.03 |
| su15-1944f8ab | 1 | 18.24 | 22.22 | 4/9 | 0 | 219,822 | 219822 | 0 | 2.01 |
| tn36-ef4dde99 | 1 | 0.00 | 0.00 | 0/7 | 0 | 125,296 | 126087 | 791 | 2.03 |
| tr87-cd924810 | 1 | 71.43 | 71.43 | 5/6 | 0 | 125,501 | 128778 | 3277 | 2.01 |
| tu93-0768757b | 1 | 100.00 | 100.00 | 9/9 | 1 | 222,117 | 222117 | 0 | 1.59 |
| vc33-5430563c | 1 | 100.00 | 100.00 | 7/7 | 1 | 193,439 | 193439 | 0 | 1.80 |
| wa30-ee6fef47 | 1 | 2.22 | 2.22 | 1/9 | 0 | 149,012 | 155071 | 6059 | 2.04 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 307 | 120,474 | 120474 | 0 | 0.82 | won | won |
| bp35-0a0ad940 | 0 | 1.85 | 2.22 | 1/9 | 62 | 108,249 | 199756 | 91507 | 2.04 | cancelled | unknown |
| cd82-fb555c5d | 0 | 100.00 | 100.00 | 6/6 | 143 | 94,146 | 94146 | 0 | 0.75 | won | won |
| cn04-2fe56bfb | 0 | 100.00 | 100.00 | 6/6 | 239 | 211,837 | 211837 | 0 | 1.77 | won | won |
| dc22-fdcac232 | 0 | 47.62 | 47.62 | 4/6 | 367 | 279,258 | 285679 | 6421 | 2.02 | cancelled | unknown |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 120 | 171,254 | 171254 | 0 | 1.40 | won | won |
| g50t-5849a774 | 0 | 10.71 | 10.71 | 2/7 | 207 | 212,938 | 212938 | 0 | 2.02 | cancelled | unknown |
| ka59-38d34dbb | 0 | 53.57 | 53.57 | 5/7 | 291 | 235,496 | 248246 | 12750 | 2.02 | cancelled | unknown |
| lf52-271a04aa | 0 | 10.91 | 10.91 | 3/10 | 183 | 247,589 | 247589 | 0 | 2.01 | cancelled | unknown |
| lp85-305b61c3 | 0 | 100.00 | 100.00 | 8/8 | 118 | 142,388 | 142388 | 0 | 0.91 | won | won |
| ls20-9607627b | 0 | 29.21 | 35.71 | 4/7 | 474 | 240,037 | 240037 | 0 | 2.01 | cancelled | unknown |
| m0r0-492f87ba | 0 | 28.36 | 28.57 | 3/6 | 230 | 192,886 | 198778 | 5892 | 2.02 | cancelled | unknown |
| r11l-495a7899 | 0 | 100.00 | 100.00 | 6/6 | 90 | 179,655 | 179655 | 0 | 1.02 | won | won |
| re86-8af5384d | 0 | 58.33 | 58.33 | 6/8 | 603 | 249,126 | 256118 | 6992 | 2.02 | cancelled | unknown |
| s5i5-18d95033 | 0 | 1.93 | 2.78 | 1/8 | 191 | 122,364 | 122799 | 435 | 2.02 | cancelled | unknown |
| sb26-7fbdac44 | 0 | 100.00 | 100.00 | 8/8 | 135 | 29,749 | 29749 | 0 | 0.40 | won | won |
| sc25-635fd71a | 0 | 0.00 | 0.00 | 0/6 | 196 | 89,892 | 90378 | 486 | 2.02 | cancelled | unknown |
| sk48-d8078629 | 0 | 8.33 | 8.33 | 2/8 | 147 | 199,064 | 200101 | 1037 | 2.02 | cancelled | unknown |
| sp80-589a99af | 0 | 4.76 | 4.76 | 1/6 | 48 | 150,013 | 184496 | 34483 | 2.03 | cancelled | unknown |
| su15-1944f8ab | 0 | 18.24 | 22.22 | 4/9 | 322 | 219,822 | 219822 | 0 | 2.01 | cancelled | unknown |
| tn36-ef4dde99 | 0 | 0.00 | 0.00 | 0/7 | 188 | 125,296 | 126087 | 791 | 2.03 | cancelled | unknown |
| tr87-cd924810 | 0 | 71.43 | 71.43 | 5/6 | 321 | 125,501 | 128778 | 3277 | 2.01 | cancelled | unknown |
| tu93-0768757b | 0 | 100.00 | 100.00 | 9/9 | 256 | 222,117 | 222117 | 0 | 1.59 | won | won |
| vc33-5430563c | 0 | 100.00 | 100.00 | 7/7 | 282 | 193,439 | 193439 | 0 | 1.80 | won | won |
| wa30-ee6fef47 | 0 | 2.22 | 2.22 | 1/9 | 191 | 149,012 | 155071 | 6059 | 2.04 | cancelled | unknown |

### Data notes

- run 1: analyzer-reported minus history+final generated tokens = 91507; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 6421; retain both accounting views
- run 7: analyzer-reported minus history+final generated tokens = 12750; retain both accounting views
- run 11: analyzer-reported minus history+final generated tokens = 5892; retain both accounting views
- run 13: analyzer-reported minus history+final generated tokens = 6992; retain both accounting views
- run 14: analyzer-reported minus history+final generated tokens = 435; retain both accounting views
- run 16: analyzer-reported minus history+final generated tokens = 486; retain both accounting views
- run 17: analyzer-reported minus history+final generated tokens = 1037; retain both accounting views
- run 18: analyzer-reported minus history+final generated tokens = 34483; retain both accounting views
- run 20: analyzer-reported minus history+final generated tokens = 791; retain both accounting views
- run 21: analyzer-reported minus history+final generated tokens = 3277; retain both accounting views
- run 24: analyzer-reported minus history+final generated tokens = 6059; retain both accounting views
- arm metadata records the shared budget deadline fired; 16 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged

## run003

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/003-goal-evidence-ab/baseline/benchmark.json`

States: `{"cancelled": 11, "won": 5}`. Stop reasons: `{"unknown": 11, "won": 5}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 138,249 | 138249 | 0 | 0.87 |
| bp35-0a0ad940 | 1 | 2.22 | 2.22 | 1/9 | 0 | 180,624 | 186514 | 5890 | 1.29 |
| cd82-fb555c5d | 1 | 75.62 | 100.00 | 6/6 | 1 | 144,787 | 144787 | 0 | 0.99 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 105,112 | 105112 | 0 | 0.72 |
| g50t-5849a774 | 1 | 2.68 | 3.57 | 1/7 | 0 | 172,628 | 175313 | 2685 | 1.29 |
| lf52-271a04aa | 1 | 7.73 | 10.91 | 3/10 | 0 | 176,221 | 179731 | 3510 | 1.30 |
| lp85-305b61c3 | 1 | 100.00 | 100.00 | 8/8 | 1 | 135,117 | 135117 | 0 | 0.80 |
| ls20-9607627b | 1 | 34.07 | 35.71 | 4/7 | 0 | 207,912 | 207912 | 0 | 1.29 |
| m0r0-492f87ba | 1 | 66.52 | 71.43 | 5/6 | 0 | 231,909 | 231909 | 0 | 1.29 |
| r11l-495a7899 | 1 | 100.00 | 100.00 | 6/6 | 1 | 181,624 | 181624 | 0 | 1.10 |
| sc25-635fd71a | 1 | 47.62 | 47.62 | 4/6 | 0 | 158,928 | 158928 | 0 | 1.29 |
| sk48-d8078629 | 1 | 1.37 | 2.78 | 1/8 | 0 | 156,178 | 171039 | 14861 | 1.30 |
| su15-1944f8ab | 1 | 62.22 | 62.22 | 7/9 | 0 | 239,090 | 239090 | 0 | 1.29 |
| tn36-ef4dde99 | 1 | 13.76 | 21.43 | 3/7 | 0 | 202,589 | 205271 | 2682 | 1.30 |
| tu93-0768757b | 1 | 71.98 | 80.00 | 8/9 | 0 | 223,225 | 239098 | 15873 | 1.29 |
| wa30-ee6fef47 | 1 | 2.22 | 2.22 | 1/9 | 0 | 156,422 | 156422 | 0 | 1.29 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| sk48-d8078629 | 0 | 1.37 | 2.78 | 1/8 | 112 | 156,178 | 171039 | 14861 | 1.30 | cancelled | unknown |
| lf52-271a04aa | 0 | 7.73 | 10.91 | 3/10 | 211 | 176,221 | 179731 | 3510 | 1.30 | cancelled | unknown |
| bp35-0a0ad940 | 0 | 2.22 | 2.22 | 1/9 | 32 | 180,624 | 186514 | 5890 | 1.29 | cancelled | unknown |
| wa30-ee6fef47 | 0 | 2.22 | 2.22 | 1/9 | 284 | 156,422 | 156422 | 0 | 1.29 | cancelled | unknown |
| g50t-5849a774 | 0 | 2.68 | 3.57 | 1/7 | 137 | 172,628 | 175313 | 2685 | 1.29 | cancelled | unknown |
| sc25-635fd71a | 0 | 47.62 | 47.62 | 4/6 | 371 | 158,928 | 158928 | 0 | 1.29 | cancelled | unknown |
| ls20-9607627b | 0 | 34.07 | 35.71 | 4/7 | 318 | 207,912 | 207912 | 0 | 1.29 | cancelled | unknown |
| su15-1944f8ab | 0 | 62.22 | 62.22 | 7/9 | 143 | 239,090 | 239090 | 0 | 1.29 | cancelled | unknown |
| tn36-ef4dde99 | 0 | 13.76 | 21.43 | 3/7 | 286 | 202,589 | 205271 | 2682 | 1.30 | cancelled | unknown |
| m0r0-492f87ba | 0 | 66.52 | 71.43 | 5/6 | 287 | 231,909 | 231909 | 0 | 1.29 | cancelled | unknown |
| cd82-fb555c5d | 0 | 75.62 | 100.00 | 6/6 | 184 | 144,787 | 144787 | 0 | 0.99 | won | won |
| tu93-0768757b | 0 | 71.98 | 80.00 | 8/9 | 241 | 223,225 | 239098 | 15873 | 1.29 | cancelled | unknown |
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 314 | 138,249 | 138249 | 0 | 0.87 | won | won |
| lp85-305b61c3 | 0 | 100.00 | 100.00 | 8/8 | 105 | 135,117 | 135117 | 0 | 0.80 | won | won |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 96 | 105,112 | 105112 | 0 | 0.72 | won | won |
| r11l-495a7899 | 0 | 100.00 | 100.00 | 6/6 | 105 | 181,624 | 181624 | 0 | 1.10 | won | won |

### Data notes

- run 0: analyzer-reported minus history+final generated tokens = 14861; retain both accounting views
- run 1: analyzer-reported minus history+final generated tokens = 3510; retain both accounting views
- run 2: analyzer-reported minus history+final generated tokens = 5890; retain both accounting views
- run 4: analyzer-reported minus history+final generated tokens = 2685; retain both accounting views
- run 8: analyzer-reported minus history+final generated tokens = 2682; retain both accounting views
- run 11: analyzer-reported minus history+final generated tokens = 15873; retain both accounting views
- arm metadata records the shared budget deadline fired; 11 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged
