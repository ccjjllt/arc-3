#!/usr/bin/env python3
"""Read 031 recorded-state continuations and index new Python calls for review.

No model calls or replay. Static runs/boundary references are review candidates,
not proof that the field was executed, correctly consumed or improved solving.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARM_DIRS = {"A": "segmentation_forks_A", "B": "segmentation_forks_B"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_text(content):
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content
                       if isinstance(p, dict) and p.get("type") == "text")
    return str(content or "")


def seeded_call_ids(fork):
    ids = set()
    for message in fork["messages"]:
        for call in message.get("tool_calls", []):
            if call.get("id"):
                ids.add(call["id"])
        if message.get("tool_call_id"):
            ids.add(message["tool_call_id"])
    return ids


def field_candidates(code):
    """Literal field accesses only; retain nested/conditional scope caveats."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, TypeError) as exc:
        return {"parse_error": str(exc), "references": []}
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    references = []
    for node in ast.walk(tree):
        field, kind = None, None
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
            if isinstance(node.slice, ast.Constant):
                field, kind = node.slice.value, "subscript_load"
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            field, kind = node.attr, "attribute_load"
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr == "get" and node.args and isinstance(node.args[0], ast.Constant)):
            field, kind = node.args[0].value, "dict_get_candidate"
        if field not in ("runs", "boundary"):
            continue
        ancestors, parent = [], parents.get(node)
        while parent is not None:
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                                   ast.If, ast.For, ast.While, ast.Try, ast.comprehension)):
                ancestors.append(type(parent).__name__)
            parent = parents.get(parent)
        references.append({"field": field, "kind": kind, "code_line": node.lineno,
                           "expression": ast.get_source_segment(code, node),
                           "enclosing_scopes": ancestors})
    return {"parse_error": None, "references": references,
            "note": "Static syntax only; a successful surrounding tool result does not prove this expression ran"}


def analyze_requests(path, seed_ids):
    if not path.is_file():
        return {"path": str(path), "exists": False, "new_python_calls": [],
                "limitations": ["Request log unavailable; no zero-call or zero-token inference"]}
    calls, results = {}, {}
    counts = {"request": 0, "response": 0}
    usage, usage_responses, malformed, conflicts = {}, 0, [], []
    historical_ids = set()
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            malformed.append(line_number)
            continue
        event = record.get("event")
        if event in counts:
            counts[event] += 1
        if event == "response" and isinstance(record.get("usage"), dict):
            usage_responses += 1
            for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = record["usage"].get(name)
                if isinstance(value, (int, float)):
                    usage[name] = usage.get(name, 0) + value
        for message in record.get("messages", []):
            if not isinstance(message, dict):
                continue
            for call in message.get("tool_calls", []):
                call_id = call.get("id")
                if not call_id:
                    continue
                if call_id in seed_ids:
                    historical_ids.add(call_id)
                    continue
                function = call.get("function", {})
                if function.get("name") != "python":
                    continue
                arguments = function.get("arguments", {})
                try:
                    arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
                    code = arguments.get("code", "") if isinstance(arguments, dict) else ""
                except ValueError:
                    code = ""
                if not isinstance(code, str):
                    code = ""
                if call_id in calls:
                    if calls[call_id]["code"] != code:
                        conflicts.append({"call_id": call_id, "line": line_number})
                    continue
                calls[call_id] = {"call_id": call_id, "first_snapshot_line": line_number,
                    "analysis_step": record.get("analysis_step"),
                    "snapshot_action": record.get("action"), "code": code,
                    "static_field_candidates": field_candidates(code),
                    "segmentation_text_present": "segmentation" in code}
            if message.get("role") == "tool" and message.get("tool_call_id") not in seed_ids:
                call_id = message.get("tool_call_id")
                if call_id and call_id not in results:
                    text = content_text(message.get("content"))
                    try:
                        payload = json.loads(text)
                    except ValueError:
                        payload = None
                    results[call_id] = {"first_snapshot_line": line_number,
                        "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "content_chars": len(text), "payload": payload,
                        "text_if_unparsed": text if payload is None else None}
    for call_id, call in calls.items():
        result = results.get(call_id)
        payload = result.get("payload") if result else None
        call["tool_result_present"] = result is not None
        call["tool_result"] = result
        call["successful_tool_result"] = (isinstance(payload, dict)
            and payload.get("returncode") == 0 and not payload.get("error"))
        call["adoption_status"] = "unreviewed; no adoption or pixel-correction inference"
    return {"path": str(path), "exists": True, "sha256": digest(path),
        "bytes": path.stat().st_size, "records": counts, "recorded_usage": usage,
        "responses_with_usage": usage_responses, "malformed_lines": malformed,
        "historical_call_ids_excluded": len(historical_ids),
        "new_python_call_count": len(calls), "call_id_conflicts": conflicts,
        "new_python_calls": list(calls.values()), "limitations": [
            "New means call ID absent from the frozen input messages, not merely first seen in a snapshot.",
            "Deduplicated by call ID; generated last calls/results absent from subsequent snapshots require transcript review.",
            "Usage sums returned response records only; timed-out requests may have unreported cost."]}


def analyze(root, package):
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Single recorded-state public diagnostic, not full-pool or formal leaderboard score",
        "review_status": "static_candidates_unreviewed", "arms": {}, "sessions": [], "comparisons": [],
        "limitations": ["One observation per arm and checkpoint; order and serving variation remain.",
            "Static fields and successful tool return are not proof of executed exact-pixel consumption.",
            "Correction of ft09 row46/col32 must be established from actual code and output, not this scanner."]}
    for label, dirname in ARM_DIRS.items():
        arm_dir = root / dirname
        source = arm_dir / "segmentation-forks.json"
        if not source.is_file():
            report["arms"][label] = {"exists": False, "path": str(source)}
            continue
        data = json.loads(source.read_text())
        report["arms"][label] = {"exists": True, "path": str(source), "sha256": digest(source),
            "input_sha256": data.get("input_sha256"), "dry_run": data.get("dry_run"),
            "elapsed_seconds": data.get("elapsed_seconds"), "use_runs": data.get("use_runs"),
            "fork_count": len(data.get("forks", [])), "patch_uninstalled": data.get("patch_uninstalled")}
        for entry in data.get("forks", []):
            game = entry["game_id"]
            request_path = arm_dir / f"{game}_{label}_requests.jsonl"
            request_data = analyze_requests(request_path, seeded_call_ids(package["forks"][game]))
            # Runtime export preserves actual ActionRecord ID and all data fields.
            actions = entry.get("continuation_actions")
            count = entry.get("continuation_action_count")
            if actions is not None and len(actions) != count:
                raise ValueError(f"{game} {label}: action list/count mismatch")
            candidates = [call for call in request_data["new_python_calls"]
                          if call["static_field_candidates"]["references"]]
            session = {key: entry.get(key) for key in (
                "game_id", "arm", "state", "error", "cut", "initial_levels_completed",
                "levels_completed", "added_levels", "final_score", "actions_per_level",
                "elapsed_seconds", "budget_seconds", "continuation_action_count",
                "continuation_actions", "continuation_history", "solver_note",
                "grid_sha256", "messages_sha256", "kept_functions_sha256", "restored_functions")}
            session.update(source=str(source), requests=request_data,
                field_candidate_call_ids=[call["call_id"] for call in candidates],
                artifact_recorded_usage=(entry.get("requests") or {}).get("recorded_usage"))
            report["sessions"].append(session)
    for game in package["forks"]:
        sessions = {s["arm"]: s for s in report["sessions"] if s["game_id"] == game}
        if set(sessions) != {"A", "B"}:
            report["comparisons"].append({"game_id": game, "complete_pair": False})
            continue
        a, b = sessions["A"], sessions["B"]
        same_inputs = {key: (a[key] == b[key] if a[key] is not None and b[key] is not None else None) for key in (
            "grid_sha256", "messages_sha256", "kept_functions_sha256", "initial_levels_completed", "budget_seconds")}
        comparison = {"game_id": game, "complete_pair": True, "input_equality": same_inputs,
            "added_levels_A": a["added_levels"], "added_levels_B": b["added_levels"],
            "delta_added_levels": b["added_levels"] - a["added_levels"],
            "actions_A": a["continuation_action_count"], "actions_B": b["continuation_action_count"],
            "actions_id_and_data_equal": a["continuation_actions"] == b["continuation_actions"],
            "elapsed_A": a["elapsed_seconds"], "elapsed_B": b["elapsed_seconds"],
            "recorded_usage_A": a["requests"].get("recorded_usage"),
            "recorded_usage_B": b["requests"].get("recorded_usage"),
            "new_python_calls_A": a["requests"].get("new_python_call_count"),
            "new_python_calls_B": b["requests"].get("new_python_call_count")}
        report["comparisons"].append(comparison)
    report["aggregates"] = {}
    for arm in ARM_DIRS:
        sessions = [s for s in report["sessions"] if s["arm"] == arm]
        usage = {}
        for session in sessions:
            for key, value in session["requests"].get("recorded_usage", {}).items():
                usage[key] = usage.get(key, 0) + value
        report["aggregates"][arm] = {
            "completed_session_exports": len(sessions),
            "all_three_exported": len(sessions) == len(package["forks"]),
            "added_levels": sum(s["added_levels"] for s in sessions) if sessions else None,
            "continuation_actions": sum(s["continuation_action_count"] for s in sessions) if sessions else None,
            "recorded_usage": usage or None,
            "arm_elapsed_seconds": report["arms"][arm].get("elapsed_seconds"),
            "elapsed_note": "Concurrent per-session elapsed values must not be summed into GPU wall time",
        }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/031-segmentation-forks")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/031-forks-analysis")
    parser.add_argument("--package", type=Path, default=ROOT / "experiments/028-fork-package.json")
    args = parser.parse_args()
    report = analyze(args.root, json.loads(args.package.read_text()))
    if not any(arm["exists"] for arm in report["arms"].values()):
        raise FileNotFoundError(f"No 031 fork output found below {args.root}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    lines = ["# 031 同状态续跑诊断", "", "只汇总实际运行；字段访问仍待人工审阅，不构成采用或提分结论。", "",
        "| 游戏 | A新增关 | B新增关 | A动作 | B动作 | A秒 | B秒 | A生成token | B生成token |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for pair in report["comparisons"]:
        if not pair["complete_pair"]:
            lines.append(f"| {pair['game_id']} | 待完整配对 | | | | | | | |")
            continue
        values = [pair[key] for key in ("added_levels_A", "added_levels_B", "actions_A", "actions_B")]
        values += [round(pair[key], 2) for key in ("elapsed_A", "elapsed_B")]
        values += [(pair.get("recorded_usage_" + arm) or {}).get("completion_tokens", "未返回") for arm in ("A", "B")]
        lines.append("| " + pair["game_id"] + " | " + " | ".join(map(str, values)) + " |")
    lines += ["", "token为返回usage之和；超时请求未知成本不计零。动作包含完整ID及data。", "",
              "人工审阅索引见python-field-candidates.md；完整调用与工具输出见summary.json。"]
    (args.output_dir / "summary.md").write_text("\n".join(lines) + "\n")
    review = ["# 031 Python字段访问候选", "", "以下为静态语法命中。必须阅读真实工具输出、函数调用位置及后续行为；不能据此自动宣称自然采用。"]
    for session in report["sessions"]:
        for call in session["requests"]["new_python_calls"]:
            refs = call["static_field_candidates"]["references"]
            if not refs:
                continue
            review += ["", f"## {session['game_id']} {session['arm']} · {call['call_id']}", "",
                f"请求日志：{session['requests']['path']}:{call['first_snapshot_line']}；工具结果存在：{call['tool_result_present']}；返回码0且无error：{call['successful_tool_result']}。",
                "", "```python", call["code"], "```", "", "静态访问：`" + json.dumps(refs, ensure_ascii=False) + "`", "",
                "```json", json.dumps(call["tool_result"], ensure_ascii=False, indent=2), "```"]
    (args.output_dir / "python-field-candidates.md").write_text("\n".join(review) + "\n")
    print(json.dumps({"sessions": len(report["sessions"]), "comparisons": report["comparisons"],
                      "output_dir": str(args.output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
