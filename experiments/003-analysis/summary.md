# ARC-AGI-3 experiment summary

Generated: 2026-10-10T16:13:52.392032+00:00

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
| baseline | local-experiment | 16/16 | 49.25 | 52.51 | 72/121 | 5 | 2,810,615 | 2856116 (16/16) | 1.30 |
| goal_evidence | local-experiment | 16/16 | 46.88 | 49.30 | 68/121 | 5 | 2,813,917 | 2922797 (16/16) | 1.29 |

## goal_evidence − baseline

Descriptive comparison under a shared GPU budget; observations are not independent replications. Game IDs match exactly; occurrence indices do not establish paired random seeds.

Common games: 16; mean game score delta: -2.37.

| Game | Runs A/B | Score A | Score B | Δ score | Δ ceiling | Δ completed levels | Recorded tokens/run A/B |
|---|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 138,249/153,717 |
| bp35-0a0ad940 | 1/1 | 2.22 | 2.22 | 0.00 | 0.00 | 0.00 | 180,624/180,439 |
| cd82-fb555c5d | 1/1 | 75.62 | 82.55 | 6.93 | 0.00 | 0.00 | 144,787/121,122 |
| ft09-0d8bbf25 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 105,112/82,595 |
| g50t-5849a774 | 1/1 | 2.68 | 10.71 | 8.03 | 7.14 | 1.00 | 172,628/170,353 |
| lf52-271a04aa | 1/1 | 7.73 | 10.91 | 3.18 | 0.00 | 0.00 | 176,221/238,898 |
| lp85-305b61c3 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 135,117/132,266 |
| ls20-9607627b | 1/1 | 34.07 | 35.71 | 1.65 | 0.00 | 0.00 | 207,912/188,100 |
| m0r0-492f87ba | 1/1 | 66.52 | 71.43 | 4.91 | 0.00 | 0.00 | 231,909/249,967 |
| r11l-495a7899 | 1/1 | 100.00 | 100.00 | 0.00 | 0.00 | 0.00 | 181,624/217,133 |
| sc25-635fd71a | 1/1 | 47.62 | 38.93 | -8.69 | 0.00 | 0.00 | 158,928/167,220 |
| sk48-d8078629 | 1/1 | 1.37 | 0.00 | -1.37 | -2.78 | -1.00 | 156,178/100,819 |
| su15-1944f8ab | 1/1 | 62.22 | 13.33 | -48.89 | -48.89 | -4.00 | 239,090/218,558 |
| tn36-ef4dde99 | 1/1 | 13.76 | 3.57 | -10.19 | -17.86 | -2.00 | 202,589/149,968 |
| tu93-0768757b | 1/1 | 71.98 | 67.35 | -4.63 | 0.00 | 0.00 | 223,225/242,233 |
| wa30-ee6fef47 | 1/1 | 2.22 | 13.33 | 11.11 | 11.11 | 2.00 | 156,422/200,529 |

## baseline

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

## goal_evidence

Source: `/Users/zhaohuaxiang/ccjjllt/arc-3/runs/003-goal-evidence-ab/goal_evidence/benchmark.json`

States: `{"cancelled": 11, "won": 5}`. Stop reasons: `{"unknown": 11, "won": 5}`.

### By game

| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ar25-0c556536 | 1 | 100.00 | 100.00 | 8/8 | 1 | 153,717 | 153717 | 0 | 0.96 |
| bp35-0a0ad940 | 1 | 2.22 | 2.22 | 1/9 | 0 | 180,439 | 216708 | 36269 | 1.29 |
| cd82-fb555c5d | 1 | 82.55 | 100.00 | 6/6 | 1 | 121,122 | 121122 | 0 | 0.76 |
| ft09-0d8bbf25 | 1 | 100.00 | 100.00 | 6/6 | 1 | 82,595 | 82595 | 0 | 0.62 |
| g50t-5849a774 | 1 | 10.71 | 10.71 | 2/7 | 0 | 170,353 | 170353 | 0 | 1.29 |
| lf52-271a04aa | 1 | 10.91 | 10.91 | 3/10 | 0 | 238,898 | 247596 | 8698 | 1.29 |
| lp85-305b61c3 | 1 | 100.00 | 100.00 | 8/8 | 1 | 132,266 | 132266 | 0 | 0.84 |
| ls20-9607627b | 1 | 35.71 | 35.71 | 4/7 | 0 | 188,100 | 188100 | 0 | 1.29 |
| m0r0-492f87ba | 1 | 71.43 | 71.43 | 5/6 | 0 | 249,967 | 278471 | 28504 | 1.29 |
| r11l-495a7899 | 1 | 100.00 | 100.00 | 6/6 | 1 | 217,133 | 217133 | 0 | 1.20 |
| sc25-635fd71a | 1 | 38.93 | 47.62 | 4/6 | 0 | 167,220 | 167220 | 0 | 1.29 |
| sk48-d8078629 | 1 | 0.00 | 0.00 | 0/8 | 0 | 100,819 | 133440 | 32621 | 1.29 |
| su15-1944f8ab | 1 | 13.33 | 13.33 | 3/9 | 0 | 218,558 | 218558 | 0 | 1.29 |
| tn36-ef4dde99 | 1 | 3.57 | 3.57 | 1/7 | 0 | 149,968 | 149968 | 0 | 1.29 |
| tu93-0768757b | 1 | 67.35 | 80.00 | 8/9 | 0 | 242,233 | 245021 | 2788 | 1.29 |
| wa30-ee6fef47 | 1 | 13.33 | 13.33 | 3/9 | 0 | 200,529 | 200529 | 0 | 1.29 |

### By run

Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.

| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| sk48-d8078629 | 0 | 0.00 | 0.00 | 0/8 | 61 | 100,819 | 133440 | 32621 | 1.29 | cancelled | unknown |
| lf52-271a04aa | 0 | 10.91 | 10.91 | 3/10 | 182 | 238,898 | 247596 | 8698 | 1.29 | cancelled | unknown |
| bp35-0a0ad940 | 0 | 2.22 | 2.22 | 1/9 | 83 | 180,439 | 216708 | 36269 | 1.29 | cancelled | unknown |
| wa30-ee6fef47 | 0 | 13.33 | 13.33 | 3/9 | 365 | 200,529 | 200529 | 0 | 1.29 | cancelled | unknown |
| g50t-5849a774 | 0 | 10.71 | 10.71 | 2/7 | 144 | 170,353 | 170353 | 0 | 1.29 | cancelled | unknown |
| sc25-635fd71a | 0 | 38.93 | 47.62 | 4/6 | 368 | 167,220 | 167220 | 0 | 1.29 | cancelled | unknown |
| ls20-9607627b | 0 | 35.71 | 35.71 | 4/7 | 421 | 188,100 | 188100 | 0 | 1.29 | cancelled | unknown |
| su15-1944f8ab | 0 | 13.33 | 13.33 | 3/9 | 126 | 218,558 | 218558 | 0 | 1.29 | cancelled | unknown |
| tn36-ef4dde99 | 0 | 3.57 | 3.57 | 1/7 | 109 | 149,968 | 149968 | 0 | 1.29 | cancelled | unknown |
| m0r0-492f87ba | 0 | 71.43 | 71.43 | 5/6 | 242 | 249,967 | 278471 | 28504 | 1.29 | cancelled | unknown |
| cd82-fb555c5d | 0 | 82.55 | 100.00 | 6/6 | 217 | 121,122 | 121122 | 0 | 0.76 | won | won |
| tu93-0768757b | 0 | 67.35 | 80.00 | 8/9 | 235 | 242,233 | 245021 | 2788 | 1.29 | cancelled | unknown |
| ar25-0c556536 | 0 | 100.00 | 100.00 | 8/8 | 290 | 153,717 | 153717 | 0 | 0.96 | won | won |
| lp85-305b61c3 | 0 | 100.00 | 100.00 | 8/8 | 131 | 132,266 | 132266 | 0 | 0.84 | won | won |
| ft09-0d8bbf25 | 0 | 100.00 | 100.00 | 6/6 | 80 | 82,595 | 82595 | 0 | 0.62 | won | won |
| r11l-495a7899 | 0 | 100.00 | 100.00 | 6/6 | 115 | 217,133 | 217133 | 0 | 1.20 | won | won |

### Data notes

- run 0: analyzer-reported minus history+final generated tokens = 32621; retain both accounting views
- run 1: analyzer-reported minus history+final generated tokens = 8698; retain both accounting views
- run 2: analyzer-reported minus history+final generated tokens = 36269; retain both accounting views
- run 9: analyzer-reported minus history+final generated tokens = 28504; retain both accounting views
- run 11: analyzer-reported minus history+final generated tokens = 2788; retain both accounting views
- arm metadata records the shared budget deadline fired; 11 cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged
