#!/usr/bin/env python3
"""Static AST/JSON audit of selected 014 request logs; never executes model code."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_turn_records(path: Path) -> dict[str, Any]:
    """Extract unique python calls, tool outputs, context trims, and NameError chains."""
    calls: dict[str, dict[str, Any]] = {}
    call_order: list[str] = []
    outputs: dict[str, dict[str, Any]] = {}
    trims: list[dict[str, Any]] = []
    prev_msg_count = 0
    count: Counter[str] = Counter()
    req_lines = 0
    resp_lines = 0
    usage_totals: Counter[str] = Counter()

    with path.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            obj = json.loads(raw)
            event = obj.get("event")
            messages = obj.get("messages") or []
            if event == "request":
                req_lines += 1
                if len(messages) < prev_msg_count:
                    trims.append({
                        "line": line_no,
                        "analysis_step": obj.get("analysis_step"),
                        "action": obj.get("action"),
                        "previous_messages": prev_msg_count,
                        "current_messages": len(messages),
                    })
                prev_msg_count = len(messages)
            elif event == "response":
                resp_lines += 1
                for key, val in (obj.get("usage") or {}).items():
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        usage_totals[key] += val
            for msg in messages:
                for tc in msg.get("tool_calls") or []:
                    tc_id = tc.get("id")
                    if not tc_id or tc_id in calls:
                        continue
                    fn = tc.get("function") or {}
                    if fn.get("name") != "python":
                        continue
                    try:
                        args = (
                            json.loads(fn["arguments"])
                            if isinstance(fn.get("arguments"), str)
                            else fn["arguments"]
                        )
                        code = args.get("code", "")
                    except (KeyError, ValueError, TypeError):
                        continue
                    calls[tc_id] = {
                        "id": tc_id,
                        "seq": len(call_order) + 1,
                        "first_line": line_no,
                        "analysis_step": obj.get("analysis_step"),
                        "request_action": obj.get("action"),
                        "code": code,
                        "reasoning_excerpt": str(
                            msg.get("reasoning_content") or msg.get("reasoning") or ""
                        )[:600],
                    }
                    call_order.append(tc_id)
                if msg.get("role") == "tool":
                    tc_id = msg.get("tool_call_id")
                    if tc_id and tc_id not in outputs:
                        outputs[tc_id] = {
                            "first_line": line_no,
                            "analysis_step": obj.get("analysis_step"),
                            "request_action": obj.get("action"),
                            "content": msg.get("content", ""),
                        }

    previous_stores: dict[str, list[dict[str, Any]]] = defaultdict(list)
    definition_history: dict[tuple[str, str], int] = {}
    evidence: list[dict[str, Any]] = []
    ordered_snippets: list[dict[str, Any]] = []

    for tc_id in call_order:
        call = calls[tc_id]
        count["unique_python_calls"] += 1
        code = call["code"]
        output = outputs.get(tc_id)
        stdout = ""
        error = None
        has_action_echo = False
        names: list[str] = []
        if output:
            count["unique_python_results"] += 1
            content = output["content"]
            try:
                body = json.loads(content)
            except (ValueError, TypeError):
                body = {}
            stdout = str(body.get("stdout") or "")
            error = body.get("error")
            has_action_echo = "[action]" in stdout
            if has_action_echo:
                count["calls_with_action_echo"] += 1
            else:
                count["calls_without_action_echo"] += 1
            if error:
                count["calls_with_error"] += 1
            names = sorted(
                set(
                    re.findall(
                        r"(?:NameError: )?name ['\"]([^'\"]+)['\"] is not defined",
                        content,
                    )
                )
            )
            if names:
                count["results_with_nameerror"] += 1
                for name in names:
                    earlier = previous_stores.get(name, [])
                    same_action = [
                        p
                        for p in earlier
                        if p["request_action"] == call["request_action"]
                    ]
                    same_action_no_echo = [
                        p for p in same_action if not p["has_action_echo"] and not p["had_error"]
                    ]
                    evidence.append({
                        "kind": "undefined_name",
                        "name": name,
                        "call_id": tc_id,
                        "seq": call["seq"],
                        "code_first_line": call["first_line"],
                        "result_first_line": output["first_line"],
                        "analysis_step": call["analysis_step"],
                        "request_action": call["request_action"],
                        "earlier_assignments": earlier[-3:],
                        "same_request_action_earlier_assignment": bool(same_action),
                        "same_action_successful_no_action_prior": bool(same_action_no_echo),
                        "code_excerpt": code[:900],
                        "error_excerpt": str(error or content)[:600],
                    })
                    count["nameerror_names"] += 1
                    count["nameerror_with_prior_assignment"] += bool(earlier)
                    count["nameerror_prior_assignment_same_action_proxy"] += bool(
                        same_action
                    )
                    count["nameerror_prior_successful_no_action_snippet"] += bool(
                        same_action_no_echo
                    )
            if "was not retained:" in content:
                count["results_with_retention_rejection"] += 1
                count["results_with_unavailable_dependencies"] += (
                    "unavailable dependencies:" in content
                )

        assigned_names: list[str] = []
        defined_funcs: list[str] = []
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defined_funcs.append(node.name)
                    normalized = ast.dump(node, include_attributes=False)
                    if (node.name, normalized) in definition_history:
                        count["exact_function_redefinitions"] += 1
                    definition_history[node.name, normalized] = call["first_line"]
                if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    targets = (
                        node.targets
                        if isinstance(node, ast.Assign)
                        else [node.target]
                    )
                    for target in targets:
                        for n in ast.walk(target):
                            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                                assigned_names.append(n.id)
                                previous_stores[n.id].append({
                                    "seq": call["seq"],
                                    "first_line": call["first_line"],
                                    "call_id": tc_id,
                                    "request_action": call["request_action"],
                                    "has_action_echo": has_action_echo,
                                    "had_error": bool(error),
                                    "code_excerpt": code[:400],
                                })
        except (SyntaxError, TypeError):
            count["ast_parse_failures"] += 1

        ordered_snippets.append({
            "seq": call["seq"],
            "call_id": tc_id,
            "first_line": call["first_line"],
            "analysis_step": call["analysis_step"],
            "request_action": call["request_action"],
            "has_action_echo": has_action_echo,
            "had_error": bool(error),
            "nameerrors": names,
            "assigned_names": sorted(set(assigned_names)),
            "defined_funcs": defined_funcs,
            "code_excerpt": code[:500],
            "stdout_excerpt": stdout[:500],
            "error_excerpt": str(error)[:400] if error else None,
        })

    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha(path),
        "bytes": path.stat().st_size,
        "request_events": req_lines,
        "response_events": resp_lines,
        "context_trims": trims,
        "usage_totals": dict(usage_totals),
        "counts": dict(count),
        "nameerror_evidence": evidence,
        "snippet_count": len(ordered_snippets),
        "first_snippets": ordered_snippets[:5],
        "last_snippets": ordered_snippets[-8:],
        "trim_window_snippets": _snippets_around_trims(ordered_snippets, trims),
    }


def _snippets_around_trims(
    snippets: list[dict[str, Any]], trims: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    windows = []
    for trim in trims:
        line = trim["line"]
        before = [s for s in snippets if s["first_line"] <= line][-3:]
        after = [s for s in snippets if s["first_line"] > line][:4]
        windows.append({
            "trim": trim,
            "before_trim": before,
            "after_trim": after,
        })
    return windows


def main() -> None:
    files = sorted((ROOT / "runs/014-tail-allocation").glob("*/*_requests.jsonl"))
    reports = []
    totals: Counter[str] = Counter()
    by_arm: dict[str, Counter[str]] = defaultdict(Counter)
    for path in files:
        arm = path.parent.name
        rep = extract_turn_records(path)
        reports.append(rep)
        totals.update(rep["counts"])
        by_arm[arm].update(rep["counts"])
        print(
            rep["path"],
            "calls=",
            rep["counts"].get("unique_python_calls", 0),
            "trims=",
            len(rep["context_trims"]),
            "nameerrors=",
            rep["counts"].get("results_with_nameerror", 0),
            "same_action_no_echo_prior=",
            rep["counts"].get("nameerror_prior_successful_no_action_snippet", 0),
        )
    out_path = ROOT / "experiments/014-analysis/selected-requests-audit.json"
    out_path.write_text(
        json.dumps(
            {
                "scope": "16 selected 014 request logs (8 games x 2 arms); static JSON/AST audit only, zero model code executed.",
                "script_sha256": sha(Path(__file__)),
                "file_count": len(reports),
                "totals": dict(totals),
                "by_arm": {k: dict(v) for k, v in by_arm.items()},
                "files": reports,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print("WROTE", out_path)
    print("TOTALS", dict(totals))


if __name__ == "__main__":
    main()
