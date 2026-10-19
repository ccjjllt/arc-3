"""Offline 019 protocol checks; never starts a service or runs generated code."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arc3_research.ple_microbench import compare_phase_reports, PHASE_ORDER


def origin(path):
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def assess(comparison, reports):
    groups = {r["group"]: r for r in comparison["groups"]}
    gates = {key: comparison.get(key) is True for key in
             ("same_suite", "provenance_checks_pass", "all_phases_complete", "all_request_payloads_match")}
    quality = groups.get("quality10", {})
    q = quality.get("phases") or {}
    scores = {p: (q.get(p) or {}).get("quality_exact_matches") for p in PHASE_ORDER}
    gates["baseline_quality_floor_8_of_10"] = all(isinstance(scores[p], int) and scores[p] >= 8 for p in ("bf16_a", "bf16_b"))
    gates["candidate_quality_not_lower"] = (all(isinstance(v, int) for v in scores.values())
        and scores["fp8"] >= min(scores["bf16_a"], scores["bf16_b"]))
    failures = {phase: None for phase in PHASE_ORDER}
    case_failures = {phase: {} for phase in PHASE_ORDER}
    duplicate_cases = []
    for report in reports:
        quality_rows = [r for r in report.get("requests", []) if r.get("group") == "quality10"]
        def failure_types(row):
            checks, message = row.get("checks") or {}, row.get("message") or {}
            parsed = checks.get("parsed_tool_arguments") or []
            errors = set()
            valid_call = len(parsed) == 1 and parsed[0].get("name") == "submit_observation"
            if not valid_call:
                errors.add("tool_count_or_name")
            arg = parsed[0].get("arguments") if valid_call else None
            valid = (isinstance(arg, dict) and set(arg) == {"cells", "count"}
                and type(arg["count"]) is int and isinstance(arg["cells"], list)
                and all(isinstance(c, list) and len(c) == 2 and all(type(x) is int for x in c) for c in arg["cells"]))
            if not valid:
                errors.add("argument_schema")
            if checks.get("format_errors"):
                errors.add("tool_argument_parse")
            if str(message.get("content") or "").strip():
                errors.add("extra_content")
            if checks.get("quality_truncated"):
                errors.add("truncation")
            if row.get("stream_errors"):
                errors.add("stream_error")
            return sorted(errors)
        for row in quality_rows:
            case_id = row.get("case_id")
            if case_id in case_failures[report["phase"]]:
                duplicate_cases.append({"phase": report["phase"], "case_id": case_id})
            case_failures[report["phase"]][case_id] = failure_types(row)
        failures[report["phase"]] = sum(bool(failure_types(r)) for r in quality_rows)
    quality_ids = [set(case_failures[phase]) for phase in PHASE_ORDER]
    complete_quality_cases = (not duplicate_cases and len(quality_ids[0]) == 10
                              and None not in quality_ids[0]
                              and quality_ids[0] == quality_ids[1] == quality_ids[2])
    added = []
    for case_id, errors in case_failures["fp8"].items():
        for baseline in ("bf16_a", "bf16_b"):
            new_types = sorted(set(errors) - set(case_failures[baseline].get(case_id, [])))
            if new_types:
                added.append({"case_id": case_id, "relative_to": baseline, "new_failure_types": new_types})
    gates["no_added_quality_format_or_truncation_failures"] = complete_quality_cases and not added
    for name in ("load10_cold", "load10_hot"):
        group = groups.get(name, {})
        gates[name + ":valid"] = group.get("compatible_complete_group") is True
        ratio = group.get("fp8_rate_vs_mean_bf16_ratio")
        gates[name + ":fp8_at_least_10_percent_faster"] = isinstance(ratio, (int, float)) and ratio >= 1.10
        gates[name + ":fp8_above_both_controls"] = group.get("fp8_rate_above_both_bf16_repeats") is True
        drift = group.get("bf16_repeat_rate_ratio")
        gates[name + ":control_drift_at_most_10_percent"] = isinstance(drift, (int, float)) and .90 <= drift <= 1.10
    return {"gates": gates, "all_automatic_gates_pass": all(gates.values()),
            "quality_exact_counts": scores, "quality_format_or_truncation_failures": failures,
            "quality_failure_types_by_case": case_failures,
            "added_quality_failure_types": added, "duplicate_quality_cases": duplicate_cases,
            "resource_review": "required_separately",
            "decision": "review_resources_before_designing_game_ab" if all(gates.values()) else "do_not_advance_this_result",
            "limits": ["Predeclared engineering/quality smoke gates, not a statistical proof or game quality result.",
                       "Manual review of GPU/host memory, startup/steady-state and absence of OOM remains necessary.",
                       "This program never changes weights, submits, or launches another experiment."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Downloaded 019-results directory")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output_dir.resolve()
    if root == out or root in out.parents or out in root.parents:
        parser.error("Keep derived output separate from raw input")
    session_path = root / "session.json"
    session = json.loads(session_path.read_text())
    result = {"kind": "019-offline-analysis", "session_status": session["status"],
              "mode": session["config"]["mode"], "gpu_started": session.get("gpu_started"),
              "sources": [origin(session_path)], "complete": False}
    for name in ["weight-audit.json", "wheel-source-check.json"]:
        path = root / name
        result[name] = json.loads(path.read_text()).get("passed") if path.exists() else None
        if path.exists():
            result["sources"].append(origin(path))
    if session["config"]["mode"] == "weights_only":
        result["complete"] = (session["status"] == "cpu_preflight_complete"
                              and result["weight-audit.json"] is True
                              and result["wheel-source-check.json"] is True
                              and session.get("weight_audit_passed") is True
                              and session.get("gpu_started") is False)
        result["limits"] = ["CPU contract only; no inference speed, numerical logits or answer quality measured."]
    else:
        paths = [root / p / "phase-report.json" for p in PHASE_ORDER]
        if all(p.exists() for p in paths):
            comparison = compare_phase_reports(paths)
            result["comparison"] = comparison
            result["assessment"] = assess(comparison, [json.loads(p.read_text()) for p in paths])
            gates = result["assessment"]["gates"]
            gates.update(mounted_weight_contract=result["weight-audit.json"] is True,
                         runtime_wheel_sources=result["wheel-source-check.json"] is True,
                         session_completed=session["status"] == "complete",
                         owned_processes_stopped=not session.get("cleanup_errors") and all(
                             p.get("driver_stopped") and p.get("server_stopped") for p in session["phases"]))
            result["assessment"]["all_automatic_gates_pass"] = all(gates.values())
            result["assessment"]["decision"] = "review_resources_before_designing_game_ab" if all(gates.values()) else "do_not_advance_this_result"
            result["sources"].extend(origin(p) for p in paths)
            result["complete"] = comparison["all_phases_complete"] and session["status"] == "complete"
        else:
            result["missing_phase_reports"] = [str(p) for p in paths if not p.exists()]
    out.mkdir(parents=True, exist_ok=True)
    result["analyzer"] = origin(Path(__file__))
    (out / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"comparison", "sources", "analyzer"}}, indent=2))


if __name__ == "__main__":
    main()
