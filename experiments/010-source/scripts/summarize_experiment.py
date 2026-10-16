#!/usr/bin/env python3
"""Summarize TAAF/Franzen benchmark JSON without loading frames or HTML traces.

Examples:
  python3 scripts/summarize_experiment.py \
      author=research/notebooks/dfranzen-v3-output/benchmark.json \
      --source-kind author-reference --output-dir /tmp/arc-author-summary
  python3 scripts/summarize_experiment.py experiments/downloaded-output \
      --source-kind local-experiment --reference baseline \
      --output-dir experiments/downloaded-output/summary

An input is a benchmark.json file or a directory searched recursively for that
filename. LABEL=PATH gives one input a label; when a directory contains several
benchmarks their relative parent paths are appended. Comparisons match exact
game_id values and average repeated runs within each game. They are descriptive,
not independent replications or significance tests.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import statistics


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def mean(values):
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


def duration(start, end):
    if not start or not end:
        return None
    try:
        seconds = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
    except (TypeError, ValueError):
        return None
    return seconds if seconds >= 0 else None


def token_sum(history, field):
    return sum(number(entry.get(field)) or 0 for entry in history)


def summarize_run(raw, index, occurrence):
    history = raw.get("history") or []
    n = raw.get("number_of_levels", 0)
    k = raw.get("levels_completed", 0)
    if not isinstance(n, int) or not isinstance(k, int) or not 0 <= k <= n:
        raise ValueError(f"Invalid level counts in run {index}: {k}/{n}")
    actions = raw.get("actions_per_level") or []
    baselines = raw.get("base_actions_per_level")
    ceiling = 100 * k * (k + 1) / (n * (n + 1)) if n else None
    recomputed = None
    if n and baselines is not None and len(baselines) >= n:
        weighted_score = 0.0
        scoring_weights = 0
        for i in range(k):
            action_count = actions[i] if i < len(actions) else 0
            level_score = min(115, (baselines[i] / action_count) ** 2 * 100) if action_count > 0 else 0
            weighted_score += (i + 1) * level_score
            if level_score > 0:
                scoring_weights += i + 1
        weight_sum = n * (n + 1) / 2
        recomputed = min(weighted_score / weight_sum, scoring_weights / weight_sum * 100)
    reported = number(raw.get("final_score"))
    score = reported if reported is not None else recomputed
    history_generated = token_sum(history, "generated_tokens")
    final_generated = number(raw.get("final_generated_tokens")) or 0
    recorded_generated = history_generated + final_generated
    analyzer_generated = number(raw.get("analyzer_reported_generated_tokens"))
    analyzer_source = "explicit_field" if analyzer_generated is not None else "not_recorded"
    note_match = re.fullmatch(r"tokens=(\d+)", str(raw.get("solver_note") or "").strip())
    if analyzer_generated is None and note_match:
        analyzer_generated = int(note_match.group(1))
        analyzer_source = "solver_note_exact_tokens_format"
    unattached_generated = analyzer_generated - recorded_generated if analyzer_generated is not None else None
    history_input = token_sum(history, "uncached_input_tokens")
    final_input = number(raw.get("final_uncached_input_tokens")) or 0
    last_action = max((number(item.get("wallclock_seconds")) or 0 for item in history), default=0)
    final_wallclock = number(raw.get("final_wallclock_seconds"))
    elapsed = max(last_action, final_wallclock or 0)
    explicit_reason = raw.get("stop_reason") or raw.get("termination_reason")
    state = raw.get("state", "unknown")
    reason = str(explicit_reason) if explicit_reason else ("won" if state == "won" else "unknown")
    warnings = []
    if sum(actions) != len(history):
        warnings.append("actions_per_level total differs from history length")
    if reported is not None and recomputed is not None and abs(reported - recomputed) > 1e-6:
        warnings.append("reported score differs from local TAAF formula")
    if unattached_generated:
        warnings.append(f"analyzer-reported minus history+final generated tokens = {unattached_generated}; retain both accounting views")
    return {
        "game_id": raw["game_id"], "run_index": index, "game_occurrence": occurrence,
        "score": score, "reported_score": reported, "recomputed_score": recomputed,
        "score_source": "final_score" if reported is not None else ("recomputed" if recomputed is not None else "unavailable"),
        "completion_ceiling": ceiling, "efficiency_gap": ceiling - score if ceiling is not None and score is not None else None,
        "levels_completed": k, "number_of_levels": n, "completion_fraction": k / n if n else None,
        "actions": sum(actions), "history_actions": len(history), "actions_per_level": actions,
        "generated_tokens": recorded_generated,
        "action_attached_generated_tokens": history_generated,
        "analyzer_reported_generated_tokens": analyzer_generated,
        "analyzer_reported_generated_tokens_source": analyzer_source,
        "unattached_generated_tokens": unattached_generated,
        "history_generated_tokens": history_generated, "final_generated_tokens": final_generated,
        "uncached_input_tokens": history_input + final_input,
        "history_uncached_input_tokens": history_input, "final_uncached_input_tokens": final_input,
        "run_elapsed_seconds": elapsed, "final_wallclock_seconds": final_wallclock,
        "last_action_seconds": last_action, "started_at": raw.get("started_at"),
        "state": state, "stop_reason": reason,
        "stop_reason_source": "explicit_field" if explicit_reason else ("state" if state == "won" else "not_recorded"),
        "solver_note": str(raw.get("solver_note") or "")[:500], "warnings": warnings,
    }


def aggregate(runs):
    analyzer_values = [r["analyzer_reported_generated_tokens"] for r in runs if r["analyzer_reported_generated_tokens"] is not None]
    unattached_values = [r["unattached_generated_tokens"] for r in runs if r["unattached_generated_tokens"] is not None]
    return {
        "run_count": len(runs), "scored_run_count": sum(r["score"] is not None for r in runs),
        "mean_score": mean(r["score"] for r in runs),
        "mean_completion_ceiling": mean(r["completion_ceiling"] for r in runs),
        "mean_efficiency_gap": mean(r["efficiency_gap"] for r in runs),
        "levels_completed": sum(r["levels_completed"] for r in runs),
        "levels_available": sum(r["number_of_levels"] for r in runs),
        "mean_levels_completed": mean(r["levels_completed"] for r in runs),
        "mean_completion_fraction": mean(r["completion_fraction"] for r in runs),
        "wins": sum(r["state"] == "won" for r in runs),
        "actions": sum(r["actions"] for r in runs),
        "generated_tokens": sum(r["generated_tokens"] for r in runs),
        "action_attached_generated_tokens": sum(r["action_attached_generated_tokens"] for r in runs),
        "analyzer_reported_generated_tokens": sum(analyzer_values) if analyzer_values else None,
        "analyzer_reported_run_count": len(analyzer_values),
        "unattached_generated_tokens": sum(unattached_values) if unattached_values else None,
        "final_generated_tokens": sum(r["final_generated_tokens"] for r in runs),
        "uncached_input_tokens": sum(r["uncached_input_tokens"] for r in runs),
        "sum_run_elapsed_seconds": sum(r["run_elapsed_seconds"] for r in runs),
        "mean_run_elapsed_seconds": mean(r["run_elapsed_seconds"] for r in runs),
        "state_counts": dict(sorted(Counter(r["state"] for r in runs).items())),
        "stop_reason_counts": dict(sorted(Counter(r["stop_reason"] for r in runs).items())),
    }


def summarize_benchmark(label, path, source_kind):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("game_runs"), list):
        raise ValueError(f"{path}: expected a TAAF object with a game_runs list")
    occurrences = Counter()
    runs = []
    for index, raw in enumerate(data["game_runs"]):
        game_id = raw.get("game_id")
        if not isinstance(game_id, str):
            raise ValueError(f"{path}: game_runs[{index}] has no string game_id")
        occurrence = occurrences[game_id]
        occurrences[game_id] += 1
        runs.append(summarize_run(raw, index, occurrence))
    groups = defaultdict(list)
    for run in runs:
        groups[run["game_id"]].append(run)
    games = []
    for game_id, group in sorted(groups.items()):
        scores = [r["score"] for r in group if r["score"] is not None]
        games.append({"game_id": game_id, **aggregate(group),
                      "min_score": min(scores) if scores else None,
                      "max_score": max(scores) if scores else None})
    overall = aggregate(runs)
    overall["game_count"] = len(games)
    overall["mean_game_score"] = mean(g["mean_score"] for g in games)
    overall["benchmark_elapsed_seconds"] = duration(data.get("start_time"), data.get("end_time"))
    elapsed = overall["benchmark_elapsed_seconds"]
    overall["generated_tokens_per_benchmark_second"] = overall["generated_tokens"] / elapsed if elapsed else None
    warnings = [f"run {r['run_index']}: {w}" for r in runs for w in r["warnings"]]
    if data.get("game_weights") is not None:
        warnings.append("game_weights is present; displayed means are unweighted and are not an official weighted aggregate")
    if data.get("end_time") is None:
        warnings.append("end_time is absent: benchmark may be an in-progress checkpoint")
    arm_context = None
    metadata_path = path.with_name("arm-metadata.json")
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        context_fields = ("status", "budget_seconds", "soft_deadline_fired", "soft_end_local",
                          "benchmark_wall_seconds", "exit_code", "forced_cpu_process_exit")
        arm_context = {key: metadata.get(key) for key in context_fields}
        arm_context["path"] = str(metadata_path.resolve())
        if metadata.get("soft_deadline_fired"):
            warnings.append(f"arm metadata records the shared budget deadline fired; {overall['state_counts'].get('cancelled', 0)} cancelled runs are observed in this budget context, not evidence of random crashes; exact per-run stop reasons remain unchanged")
    return {
        "label": label, "path": str(path.resolve()), "source_kind": source_kind,
        "benchmark_label": data.get("label"), "solver_label": data.get("solver_label"),
        "n_passes": data.get("n_passes"), "start_time": data.get("start_time"), "end_time": data.get("end_time"),
        "game_weights": data.get("game_weights"), "summary": overall, "games": games, "runs": runs,
        "arm_context": arm_context,
        "warnings": warnings,
    }


def compare(reference, candidate):
    left = {g["game_id"]: g for g in reference["games"]}
    right = {g["game_id"]: g for g in candidate["games"]}
    rows = []
    for game_id in sorted(left.keys() & right.keys()):
        a, b = left[game_id], right[game_id]
        row = {"game_id": game_id, "reference_runs": a["run_count"], "candidate_runs": b["run_count"]}
        for metric in ("mean_score", "mean_completion_ceiling", "mean_levels_completed",
                       "mean_completion_fraction", "mean_run_elapsed_seconds"):
            av, bv = a[metric], b[metric]
            row["reference_" + metric] = av
            row["candidate_" + metric] = bv
            row["delta_" + metric] = bv - av if av is not None and bv is not None else None
        for side, value in (("reference", a), ("candidate", b)):
            row[side + "_generated_tokens_per_run"] = value["generated_tokens"] / value["run_count"]
            row[side + "_analyzer_reported_generated_tokens_per_run"] = (value["analyzer_reported_generated_tokens"] / value["run_count"]
                if value["analyzer_reported_run_count"] == value["run_count"] else None)
        rows.append(row)
    return {
        "reference": reference["label"], "candidate": candidate["label"],
        "alignment": "exact game_id; mean over available repetitions, not paired random seeds",
        "inference": "descriptive_only_non_independent_shared_gpu_budget",
        "common_game_count": len(rows),
        "reference_only_games": sorted(left.keys() - right.keys()),
        "candidate_only_games": sorted(right.keys() - left.keys()),
        "mean_game_score_delta": mean(r["delta_mean_score"] for r in rows),
        "mean_game_completion_ceiling_delta": mean(r["delta_mean_completion_ceiling"] for r in rows),
        "games": rows,
    }


def inputs(specs):
    found = []
    seen = set()
    for spec in specs:
        if "=" in spec:
            label, raw_path = spec.split("=", 1)
        else:
            label, raw_path = None, spec
        path = Path(raw_path).expanduser()
        matches = [path] if path.is_file() else sorted(path.rglob("benchmark.json")) if path.is_dir() else []
        if not matches:
            raise ValueError(f"No benchmark JSON found: {raw_path}")
        for match in matches:
            resolved = match.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if path.is_file():
                item_label = label or path.parent.name
            else:
                relative = match.parent.relative_to(path).as_posix()
                item_label = (label or path.name) if relative == "." else (f"{label}/{relative}" if label else relative)
            found.append((item_label, match))
    labels = [label for label, _ in found]
    if len(set(labels)) != len(labels):
        raise ValueError("Duplicate labels; supply unique LABEL=PATH arguments")
    return found


def fmt(value, digits=2):
    if value is None:
        return "—"
    return f"{value:,.{digits}f}" if isinstance(value, float) else str(value)


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown(report):
    lines = ["# ARC-AGI-3 experiment summary", "", f"Generated: {report['created_at']}", ""]
    for note in report["method_notes"]:
        lines.append(f"- {note}")
    lines.extend(["", "## Benchmark overview", "",
                  "| Source | Kind | Games/runs | Mean score | Completion ceiling | Levels | Wins | Recorded tokens | Analyzer tokens (runs reported) | Benchmark hours |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for item in report["benchmarks"]:
        s = item["summary"]
        hours = s["benchmark_elapsed_seconds"] / 3600 if s["benchmark_elapsed_seconds"] is not None else None
        lines.append(f"| {cell(item['label'])} | {item['source_kind']} | {s['game_count']}/{s['run_count']} | {fmt(s['mean_score'])} | {fmt(s['mean_completion_ceiling'])} | {s['levels_completed']}/{s['levels_available']} | {s['wins']} | {s['generated_tokens']:,} | {fmt(s['analyzer_reported_generated_tokens'], 0)} ({s['analyzer_reported_run_count']}/{s['run_count']}) | {fmt(hours)} |")
    for comparison in report["comparisons"]:
        lines.extend(["", f"## {comparison['candidate']} − {comparison['reference']}", "",
                      "Descriptive comparison under a shared GPU budget; observations are not independent replications. Game IDs match exactly; occurrence indices do not establish paired random seeds.", "",
                      f"Common games: {comparison['common_game_count']}; mean game score delta: {fmt(comparison['mean_game_score_delta'])}.", "",
                      "| Game | Runs A/B | Score A | Score B | Δ score | Δ ceiling | Δ completed levels | Recorded tokens/run A/B |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|"])
        for r in comparison["games"]:
            lines.append(f"| {cell(r['game_id'])} | {r['reference_runs']}/{r['candidate_runs']} | {fmt(r['reference_mean_score'])} | {fmt(r['candidate_mean_score'])} | {fmt(r['delta_mean_score'])} | {fmt(r['delta_mean_completion_ceiling'])} | {fmt(r['delta_mean_levels_completed'])} | {fmt(r['reference_generated_tokens_per_run'], 0)}/{fmt(r['candidate_generated_tokens_per_run'], 0)} |")
        for key in ("reference_only_games", "candidate_only_games"):
            if comparison[key]:
                lines.extend(["", f"{key}: {', '.join(comparison[key])}"])
    for item in report["benchmarks"]:
        lines.extend(["", f"## {item['label']}", "", f"Source: `{item['path']}`", "",
                      f"States: `{json.dumps(item['summary']['state_counts'], ensure_ascii=False)}`. Stop reasons: `{json.dumps(item['summary']['stop_reason_counts'], ensure_ascii=False)}`.", "",
                      "### By game", "",
                      "| Game | Runs | Mean score | Ceiling | Levels total | Wins | Recorded tokens | Analyzer tokens | Unattached tokens | Mean run hours |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
        for g in item["games"]:
            lines.append(f"| {cell(g['game_id'])} | {g['run_count']} | {fmt(g['mean_score'])} | {fmt(g['mean_completion_ceiling'])} | {g['levels_completed']}/{g['levels_available']} | {g['wins']} | {g['generated_tokens']:,} | {fmt(g['analyzer_reported_generated_tokens'], 0)} | {fmt(g['unattached_generated_tokens'], 0)} | {fmt(g['mean_run_elapsed_seconds'] / 3600)} |")
        lines.extend(["", "### By run", "",
                      "Occurrence is the zero-based appearance of this game in the file, not a verified seed/pass identifier.", "",
                      "| Game | Occurrence | Score | Ceiling | Levels | Actions | Recorded tokens | Analyzer tokens | Unattached tokens | Run hours | State | Stop reason |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"])
        for r in item["runs"]:
            lines.append(f"| {cell(r['game_id'])} | {r['game_occurrence']} | {fmt(r['score'])} | {fmt(r['completion_ceiling'])} | {r['levels_completed']}/{r['number_of_levels']} | {r['actions']} | {r['generated_tokens']:,} | {fmt(r['analyzer_reported_generated_tokens'], 0)} | {fmt(r['unattached_generated_tokens'], 0)} | {fmt(r['run_elapsed_seconds'] / 3600)} | {cell(r['state'])} | {cell(r['stop_reason'])} |")
        if item["warnings"]:
            lines.extend(["", "### Data notes", ""] + [f"- {w}" for w in item["warnings"]])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", metavar="[LABEL=]PATH")
    parser.add_argument("--output-dir", required=True, type=Path, help="Write summary.json and summary.md here")
    parser.add_argument("--reference", help="Exact label used as the A/B reference; defaults to the first source")
    parser.add_argument("--source-kind", choices=("author-reference", "local-experiment", "unknown"), default="unknown")
    args = parser.parse_args()
    try:
        benchmarks = [summarize_benchmark(label, path, args.source_kind) for label, path in inputs(args.inputs)]
        reference = next((b for b in benchmarks if b["label"] == args.reference), None) if args.reference else benchmarks[0]
        if reference is None:
            raise ValueError(f"Unknown reference {args.reference!r}; labels: {[b['label'] for b in benchmarks]}")
        report = {
            "schema_version": 2, "created_at": datetime.now(timezone.utc).isoformat(),
            "method_notes": [
                "Author-reference data is historical public evidence, not a new GPU run or our leaderboard result.",
                "Scores use final_score when available. Recomputed scores use the bundled TAAF formula; means are unweighted descriptive means, not official leaderboard scores.",
                "Completion ceiling = 100 × k(k+1) / n(n+1), for completed sequential levels k out of n. It holds completion fixed and represents the ceiling from action efficiency alone.",
                "Recorded tokens / generated_tokens retain the original accounting: sum(history.generated_tokens) + final_generated_tokens. This may undercount generation after the last action. action_attached_generated_tokens is history only; it excludes final tokens.",
                "analyzer_reported_generated_tokens comes from an explicit same-named field or, if absent, the exact solver_note format tokens=N. Missing reports remain null. Aggregate analyzer totals cover only analyzer_reported_run_count runs; do not interpret partial sums as complete totals.",
                "unattached_generated_tokens = analyzer-reported minus recorded history+final tokens, only where analyzer reports exist. It measures the signed accounting residual, excludes already-recorded final tokens, and is not added to or substituted for the original generated_tokens field.",
                "Generated and uncached-input counts are solver-reported, not billing records. Zero can mean untracked usage; this harness may report zero uncached-input tokens even when prefill occurs.",
                "Action wallclock fields are cumulative; never sum them. Run duration is max(final_wallclock_seconds, last action timestamp). Concurrent run durations must not be added to estimate GPU quota.",
                "Benchmark elapsed is end_time − start_time and excludes setup/model-loading outside the benchmark; actual Kaggle GPU quota requires session accounting. Run durations include queue/wait time, not just GPU compute.",
                "Absent per-run stop reasons remain unknown. gave_up, cancelled, and crashed are lifecycle states. Sibling arm-metadata.json, when present, supplies shared deadline context without overwriting raw run states or inferring individual request failures.",
                "A/B aligns exact game IDs and averages available repeats. Shared GPU budget, scheduling, order, unequal exposure, and game difficulty confound comparisons; no independence or statistical significance is claimed.",
            ],
            "benchmarks": benchmarks,
            "comparisons": [compare(reference, candidate) for candidate in benchmarks if candidate is not reference],
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        json_path, md_path = args.output_dir / "summary.json", args.output_dir / "summary.md"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        md_path.write_text(markdown(report), encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, f"error: {error}\n")
    for benchmark in benchmarks:
        s = benchmark["summary"]
        print(f"{benchmark['label']}: {s['game_count']} games, {s['run_count']} runs, score={fmt(s['mean_score'])}, ceiling={fmt(s['mean_completion_ceiling'])}, levels={s['levels_completed']}, recorded_tokens={s['generated_tokens']:,}, analyzer_tokens={fmt(s['analyzer_reported_generated_tokens'], 0)}, unattached_tokens={fmt(s['unattached_generated_tokens'], 0)}")
    print(f"JSON: {json_path.resolve()}")
    print(f"Markdown: {md_path.resolve()}")


if __name__ == "__main__":
    main()
