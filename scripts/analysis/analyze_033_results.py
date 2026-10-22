#!/usr/bin/env python3
"""Read the candidate-only 033 extraction-repair diagnostic; never infer A/B gain."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from analyze_031_forks import analyze_requests, seeded_call_ids

ROOT = Path(__file__).resolve().parents[2]
GAME = "ft09-0d8bbf25"


def read(path):
    return json.loads(path.read_text()) if path.is_file() else None


def source(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size} if path.is_file() else {"path": str(path), "exists": False}


def usage_sum(values):
    result = {}
    for usage in values:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = (usage or {}).get(key)
            if isinstance(value, (int, float)):
                result[key] = result.get(key, 0) + value
    return result or None


def task_references(code):
    """Static review navigation only, including definitions and nested code."""
    names = {"extract", "rebuild", "pieces", "patterns", "pats", "leg", "target_for", "satisfaction"}
    try:
        tree = ast.parse(code)
    except (SyntaxError, TypeError):
        return {"parse_error": True}
    return {"names": sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in names}),
            "calls": [{"name": n.func.id, "code_line": n.lineno} for n in ast.walk(tree)
                      if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in names],
            "definitions": [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names],
            "claim": "Static candidate; execution, consumption and semantic correction require manual review"}


def analyze(root):
    arm = root / "controller_repair_B"
    if not arm.is_dir() and (root / "controller-repair-forks.json").is_file():
        arm = root
    summary_path = arm / "controller-repair-forks.json"
    summary = read(summary_path)
    result_path = arm / f"{GAME}-B.json"
    result = read(result_path)
    if result is None and summary:
        result = next((f for f in summary.get("forks", []) if f.get("game_id") == GAME), None)
    repair_paths = sorted((arm / "artifacts").glob("*_controller-repair.json"))
    if len(repair_paths) > 1:
        raise ValueError("Multiple repair event files; provide a single candidate arm directory")
    repair = read(repair_paths[0]) if repair_paths else (result or {}).get("controller_repair")
    if summary is None and result is None and repair is None:
        raise FileNotFoundError(f"No 033 candidate result found in {arm}")
    request_path = arm / "requests.jsonl"
    if not request_path.is_file():
        alternative = arm / f"{GAME}_B_requests.jsonl"
        if alternative.is_file():
            request_path = alternative
    package = json.loads((ROOT / "experiments/028-fork-package.json").read_text())
    requests = analyze_requests(request_path, seeded_call_ids(package["forks"][GAME]))
    calls = (repair or {}).get("calls", [])
    repair_usage = usage_sum(call.get("usage") for call in calls)
    main_usage = requests.get("recorded_usage") or None
    known_total = usage_sum([repair_usage, main_usage])
    note = re.fullmatch(r"tokens=(\d+)", str((result or {}).get("solver_note", "")))
    analyzer_tokens = int(note.group(1)) if note else None
    passed = any(call.get("validation", {}).get("passed")
                 and call.get("retained_extract_validation", {}).get("passed") for call in calls)
    for call in requests["new_python_calls"]:
        call["task_references"] = task_references(call["code"])
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Candidate-only forced checkpoint diagnostic; no fresh paired baseline and no A/B score estimate",
        "sources": {"fork_summary": source(summary_path), "game_result": source(result_path),
                    "repair_event": source(repair_paths[0]) if repair_paths else None,
                    "request_log": source(request_path)},
        "session_manifest": read(root / "experiment-manifest.json"),
        "arm_metadata": read(arm / "arm-metadata.json"), "fork_summary": summary,
        "result": result, "repair": repair, "main_requests": requests,
        "observed_stages": {
            "repair_responses_with_code": sum(bool(c.get("code")) for c in calls),
            "repair_calls_with_actual_tool_output": sum(c.get("actual_tool_output") is not None for c in calls),
            "full_frame_pixel_contract_passed_twice": passed,
            "task_rebuild_supplied": (repair or {}).get("task_rebuild_supplied"),
            "task_rebuild_output": (repair or {}).get("task_rebuild_output"),
            "exact_result_delivered_in_history": bool((repair or {}).get("delivery_message_sha256")) if repair else None,
            "verified_delivery_seen_in_actual_main_request": (result or {}).get("verified_delivery_seen_in_main_request"),
            "controller_first_action": (repair or {}).get("controller_action"),
            "actual_subsequent_main_actions": (result or {}).get("subsequent_main_actions"),
            "added_levels_after_checkpoint": (result or {}).get("added_levels"),
            "validation_environment_actions": (repair or {}).get("validation_environment_actions"),
            "blocked_action_calls": (repair or {}).get("blocked_action_calls"),
            "failed_functions_rolled_back": (repair or {}).get("failed_functions_rolled_back"),
            "original_history_prefix_preserved": (repair or {}).get("original_history_prefix_preserved"),
        },
        "costs": {"arm_allowance_seconds": (summary or {}).get("arm_allowance_seconds"),
            "continuation_budget_seconds": (summary or {}).get("continuation_budget_seconds"),
            "continuation_elapsed_seconds": (result or {}).get("elapsed_seconds"),
            "repair_elapsed_seconds_included": (repair or {}).get("elapsed_seconds"),
            "repair_returned_usage": repair_usage, "main_returned_usage": main_usage,
            "known_disjoint_response_usage_total": known_total,
            "analyzer_reported_generated_tokens": analyzer_tokens,
            "analyzer_minus_known_returned_completion_tokens": (
                analyzer_tokens - known_total["completion_tokens"] if analyzer_tokens is not None
                and known_total and "completion_tokens" in known_total else None),
            "note": "Repair completion usage and native main-request response usage are disjoint sources. Timeouts may have unknown unreturned cost. Repair time is inside continuation time, not additional."},
        "semantic_review": {"status": "not_reviewed", "P4_or_pieces_corrected": None,
            "verified_extraction_consumed_by_later_computation": None,
            "action_improvement": None,
            "required_evidence": "Read rebuild output and later pieces/pattern/target code and actual tool returns against the contemporaneous visible frame; inspect actions and new levels. Copying all frame.ascii pixels alone is not semantic repair."},
        "limitations": [
            "No fresh A arm: historical028/031 controls cannot be substituted as a matched score-gain estimate.",
            "Full-frame pixel validation is deliberately separate from P4/pieces/target semantics and successful gameplay.",
            "Static references, function retention, result delivery and subsequent actions are different evidence stages; none alone proves causal benefit.",
            "The exported final_score includes the restored prefix; it is not an added-score claim.",
            "An unreturned final generation may be absent from request snapshots; consult transcript before claiming no further code.",
            "Offline pixel checks are not proof of correctness in hidden environments."]}
    if result and result.get("continuation_actions") is not None:
        if len(result["continuation_actions"]) != result.get("continuation_action_count"):
            raise ValueError("Actual continuation action list/count mismatch")
    return report


def write(report, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    stages, costs = report["observed_stages"], report["costs"]
    repair = report["repair"] or {}
    result = report["result"] or {}
    lines = ["# 033 控制器纠错实际诊断", "", "候选单臂，无新配对基线；不计算A/B涨分。", "",
        f"修复状态：`{repair.get('status', '尚无事件结果')}`。全帧像素合同两次通过：**{stages['full_frame_pixel_contract_passed_twice']}**；这不代表P4/pieces/target语义修好。", "",
        f"真实新增关：{result.get('added_levels', '未知')}；续跑动作：{result.get('continuation_action_count', '未知')}；下一真实主请求含准确结果：{stages['verified_delivery_seen_in_actual_main_request']}。", "",
        f"续跑耗时：{costs['continuation_elapsed_seconds']}秒，其中修复：{costs['repair_elapsed_seconds_included']}秒；二者不可相加。", "",
        "| token口径 | 记录usage |", "|---|---|",
        "| 修复请求 | " + json.dumps(costs["repair_returned_usage"]) + " |",
        "| 随后主请求 | " + json.dumps(costs["main_returned_usage"]) + " |", "",
        "超时未返回usage成本未知。完整响应、实际执行输出、验收拒因、函数回滚、计划/预测、真实动作与来源hash见summary.json。", "",
        "语义纠错和行动改善尚待人工审阅review.md；不能用完整frame.ascii复制通过代替真正修复。"]
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n")
    review = ["# 033 修复与后续消费人工审阅", "", "代码均为已保存产物，本文不执行它们。全帧像素合同通过与任务语义修复分别判断。"]
    for call in repair.get("calls", []):
        review += ["", f"## 修复请求 {call['index']}", "", "```python", call.get("code", "未返回可接受代码"), "```", "",
            "验收/执行错误：", "```json", json.dumps({key: call.get(key) for key in (
                "error", "validation", "retained_extract_validation", "usage")}, ensure_ascii=False, indent=2), "```"]
    review += ["", "## rebuild实际语义输出（未自动验收）", "", "```json",
        json.dumps(repair.get("task_rebuild_output"), ensure_ascii=False, indent=2), "```"]
    for call in report["main_requests"]["new_python_calls"]:
        review += ["", f"## 后续 {call['call_id']}", "",
            f"来源 {report['main_requests']['path']}:{call['first_snapshot_line']}；工具返回存在={call['tool_result_present']}。", "",
            "```python", call["code"], "```", "", "```json",
            json.dumps(call["tool_result"], ensure_ascii=False, indent=2), "```"]
    review += ["", "## 实际动作", "", "```json", json.dumps({
        "controller": stages["controller_first_action"], "subsequent_main": stages["actual_subsequent_main_actions"],
        "added_levels": stages["added_levels_after_checkpoint"]}, ensure_ascii=False, indent=2), "```"]
    (output_dir / "review.md").write_text("\n".join(review) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/033-controller-candidate")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/033-controller-analysis")
    args = parser.parse_args()
    report = analyze(args.root)
    write(report, args.output_dir)
    print(json.dumps({"output_dir": str(args.output_dir), "repair_status": (report["repair"] or {}).get("status"),
        "full_frame_contract_passed": report["observed_stages"]["full_frame_pixel_contract_passed_twice"],
        "added_levels": (report["result"] or {}).get("added_levels"),
        "semantic_status": "manual_review_required_no_paired_gain_claim"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
