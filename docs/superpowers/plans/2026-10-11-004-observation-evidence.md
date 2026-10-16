# 004 Observation Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use existing 003 traces to decide whether a compact observation-evidence tool return is justified, then implement only if a recurring visible-transfer defect is found.

**Architecture:** Phase A is CPU-only attribution of su15/tn36/lf52/sk48 request traces. Phase B implements `src/arc3_research/observation_evidence.py` and a new 004 experiment directory only if Phase A names a defect that compact local temporal facts in the existing Python tool return can address. Baseline stays unmodified; 003 goal-evidence marker stays off.

**Tech Stack:** Python 3, existing Franzen v3 ToolAgent patch style, Kaggle notebook builder, no test suite.

**Spec:** [docs/plan/004-observation-evidence.md](../../plan/004-observation-evidence.md)

## Global Constraints

- GPU budget for this phase is 0. Do not `kaggle kernels push`, do not submit the competition, do not start a new GPU job.
- Do not create a git worktree. Work in `/Users/zhaohuaxiang/ccjjllt/arc-3`.
- Do not add test files or CI.
- Do not read game engine / environment source to infer mechanics. Attribute only from tool stdout, user prompts, assistant reasoning, and events actually received.
- Distinguish three stages: (1) animation API/prompt already provided, (2) model actually read relevant frames, (3) model updated hypotheses from them. Do not treat another “please look at animation” reminder as a new capability.
- Keep 003 goal-evidence v1 off. Do not re-run it. Do not relax correct frame-binding.
- Do not add extra LLM calls, do not rewrite serving, do not hard-code game IDs as solutions.
- Do not overwrite `notebooks/003-goal-evidence-ab/` or `experiments/003-source/`.
- If no recurring defect describable by visible transfer facts is found, do not implement a forced prompt; document that and stop at research notes + progress.
- Candidate output, if implemented, is compact local temporal facts from real `last_animation_frames` / action metadata, injected into existing Python tool returns. Observation facts only; no victory-rule announcement.
- Event logs must include game/runtime path, real step/level, event facts, and whether they were given to the model. Adoption is judged from later code/reasoning, not model self-report.
- Both future arms would use the recorded research warmup RESET fix (`ARC3_WARMUP_ACTION_GAMES=0`). This phase does not launch them.
- Verification is manual: read traces, compile-check Python, build notebook locally. No pytest.

---

### Task 1: Compact 003 diagnostic traces

**Files:**
- Create: `scripts/compact_requests.py`
- Create (gitignored under `runs/`): `runs/003-compact/{baseline,goal_evidence}__{su15,tn36,lf52,sk48}-*_p0_requests.compact.json`

**Interfaces:**
- Consumes: downloaded `runs/003-goal-evidence-ab/{baseline,goal_evidence}/*_p0_requests.jsonl`
- Produces: compact JSON with only new messages per event; user prompts reduced to animation cues + prefix; assistant reasoning and tool stdout retained.

- [x] **Step 1: Download traces** — done by controller via `kaggle kernels output` with file-pattern for su15/tn36/lf52/sk48 requests and events.
- [x] **Step 2: Compact** — `python3 scripts/compact_requests.py ... --output-dir runs/003-compact`
- [x] **Step 3: Confirm both arms exist as separate files**

---

### Task 2: Attribute sk48 traces

**Files:**
- Create: `research/004-trace-sk48.md`

See shared analysis rubric in Task 2–5 notes below. Game scores: baseline 1.37 (1/8 levels), goal_evidence 0.00 (0/8). Compact: `runs/003-compact/baseline__sk48-d8078629_p0_requests.compact.json`, `runs/003-compact/goal_evidence__sk48-d8078629_p0_requests.compact.json`. Events: `runs/003-goal-evidence-ab/{baseline,goal_evidence}/artifacts/sk48-d8078629_p0_events.jsonl`.

### Task 3: Attribute lf52 traces

**Files:**
- Create: `research/004-trace-lf52.md`

Scores: baseline 7.73 (3/10), goal_evidence 10.91 (3/10). Compact: `baseline__lf52-271a04aa_p0_requests.compact.json`, `goal_evidence__lf52-271a04aa_p0_requests.compact.json`.

### Task 4: Attribute su15 traces

**Files:**
- Create: `research/004-trace-su15.md`

Scores: baseline 62.22 (7/9), goal_evidence 13.33 (3/9). Largest delta; one-run fluctuation. Compact: `baseline__su15-1944f8ab_p0_requests.compact.json`, `goal_evidence__su15-1944f8ab_p0_requests.compact.json`.

### Task 5: Attribute tn36 traces

**Files:**
- Create: `research/004-trace-tn36.md`

Scores: baseline 13.76 (3/7), goal_evidence 3.57 (1/7). Compact: `baseline__tn36-ef4dde99_p0_requests.compact.json`, `goal_evidence__tn36-ef4dde99_p0_requests.compact.json`.

### Task 2–5 shared rubric

Each note must:

1. Cite compact JSON `analysis_step`/`action` and quote tool stdout or reasoning. Do not invent mechanics from engine source.
2. Count, with examples: user-prompt animation cues; code that reads `last_animation_timeline` / `last_animation_frames`; cases where those reads changed a later hypothesis vs were ignored.
3. Label failures as one of: observation miss, goal-hypothesis error, dynamics error, memory loss, budget termination. A row may have more than one label if evidence supports it.
4. State whether the 004 candidate (inject compact temporal facts into existing python tool return) would have changed a specific listed episode. If not, say so.
5. Do not recommend “remind the model to look at animation” as a new factor.
6. Do not commit GPU jobs or overwrite 003 notebooks.

### Task 6: Synthesize defect or stop

**Files:**
- Create: `research/004-observation-attribution.md`
- Create: `docs/progress/004-observation-evidence.md` (code complete vs run complete vs effect; this phase has no GPU run)

Decide one of:

- A recurring visible-transfer defect exists across games/episodes → proceed to Task 7 with explicit thresholds taken from trace magnitudes.
- No such defect, or the model already consumes animation APIs and the remaining failures are goal/dynamics/budget → do not implement observation_evidence; recommend 25-game baseline or further CPU study. Write progress accordingly and stop.

### Task 7: Implement observation_evidence only if Task 6 selected it

**Files:**
- Create: `src/arc3_research/observation_evidence.py`
- Modify: `src/arc3_research/run_arm.py` to install the patch when arm is `observation_evidence`, keep baseline unmodified, keep goal-evidence disabled.
- Create: `experiments/004-observation-evidence.json`
- Modify: `scripts/build_experiment.py` or a 004-specific builder so 004 notebook generation cannot overwrite 003.

Must wrap `_run_python_tool` after baseline, inject compact facts from real animation/action metadata into the existing tool payload, log game/runtime path, real step/level, facts, and whether they were attached. Length/dedup/condition thresholds come from Task 6, not invented switches. Manual `python3 -m py_compile` only.

### Task 8: Build 004 notebook locally, do not push

**Files:**
- Create: `notebooks/004-observation-evidence-ab/` (experiment.ipynb, kernel-metadata.json, build-manifest.json)

Equal wall-clock, 10 active streams, shared one model load, independent CPU processes, cache flush, warmup RESET fix. Do not push.

---
