#!/usr/bin/env python3
"""030 score comparison and conservative cross-call Python-state evidence.

Read completed outputs with:
  python3 scripts/analyze_030_results.py --root runs/030-capability-comparison

The AST scan produces candidates for reading code/stdout, not automatic proof
of semantic reuse or causally improved scores. It excludes ordinary retained
function definitions and imported modules from direct variable-reuse counts.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics
import symtable

from summarize_experiment import summarize_benchmark, compare, fmt

ROOT = Path(__file__).resolve().parents[1]
STATE_RE = re.compile(r"Current state:\s*step\s+(\d+),\s*level\s+(\d+)", re.I)
QUEUE_RE = re.compile(r"(?:queue|frontier|heap|seen|visited|parent|cache|plan|path|states|dist|^q$)", re.I)
RUNTIME_NAMES = set("current_frame previous_frame history transitions last_transition valid_actions last_action_call_result last_animation_frames last_animation_timeline action frame_diff animation".split())


def text(content):
    return "".join(p.get("text", "") for p in content if isinstance(p, dict)
                   and p.get("type") == "text") if isinstance(content, list) else str(content or "")


def parse_payload(content):
    try:
        value = json.loads(text(content))
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def exception_signature(error):
    lines = [l.strip() for l in str(error).splitlines()
             if re.match(r"^[A-Za-z_]\w*(?:Error|Exception):", l.strip())]
    return lines[-1] if lines else str(error).splitlines()[-1] if error else ""


def binding_kind(value):
    if isinstance(value, (ast.List, ast.ListComp)):
        return "list"
    if isinstance(value, (ast.Dict, ast.DictComp)):
        return "dict"
    if isinstance(value, (ast.Set, ast.SetComp)):
        return "set"
    if isinstance(value, ast.Call):
        name = ast.unparse(value.func)
        return "queue" if name.endswith(("deque", "PriorityQueue", "Queue")) else "computed_value"
    return "ordinary_value"


class CallFacts(ast.NodeVisitor):
    """Reads before any assignment in the current snippet; nested defs skipped.

    Conditional execution is retained as a review caveat. This scan never
    executes a model program or imports an environment.
    """
    def __init__(self, code):
        self.code = code
        self.defined = set()
        self.bindings = {}
        self.external_reads = set()
        self.called_names = set()
        self.control_depth = 0
        self.conditional_reads = set()
        self.function_globals = {}

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id not in self.defined:
            self.external_reads.add(node.id)
            if self.control_depth:
                self.conditional_reads.add(node.id)

    def bind(self, target, kind):
        for name in [n.id for n in ast.walk(target) if isinstance(n, ast.Name)
                     and isinstance(n.ctx, (ast.Store, ast.Del))]:
            self.defined.add(name)
            self.bindings[name] = {"kind": kind, "conditional": bool(self.control_depth)}

    def visit_Assign(self, node):
        self.visit(node.value)
        for target in node.targets:
            # Attribute/subscript assignment can read a previous container.
            if isinstance(target, (ast.Subscript, ast.Attribute)):
                self.visit(target.value)
            else:
                self.bind(target, binding_kind(node.value))

    def visit_AnnAssign(self, node):
        if node.value is not None:
            self.visit(node.value)
        self.bind(node.target, binding_kind(node.value))

    def visit_AugAssign(self, node):
        if isinstance(node.target, ast.Name):
            if node.target.id not in self.defined:
                self.external_reads.add(node.target.id)
        else:
            self.visit(node.target)
        self.visit(node.value)
        self.bind(node.target, "ordinary_value")

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.defined.add(name)
            self.bindings[name] = {"kind": "import", "conditional": bool(self.control_depth)}

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            self.defined.add(name)
            self.bindings[name] = {"kind": "import", "conditional": bool(self.control_depth)}

    def visit_FunctionDef(self, node):
        for value in [*node.decorator_list, *node.args.defaults,
                      *(v for v in node.args.kw_defaults if v is not None)]:
            self.visit(value)
        source = ast.get_source_segment(self.code, node)
        try:
            child = symtable.symtable(source, "<model-function>", "exec").get_children()[0]
            self.function_globals[node.name] = sorted(s.get_name() for s in child.get_symbols()
                                                       if s.is_global() and s.is_referenced())
        except (SyntaxError, IndexError):
            self.function_globals[node.name] = []
        self.defined.add(node.name)
        self.bindings[node.name] = {"kind": "function", "conditional": bool(self.control_depth)}

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.defined.add(node.name)
        self.bindings[node.name] = {"kind": "class", "conditional": bool(self.control_depth)}

    def visit_Lambda(self, node):
        for value in [*node.args.defaults, *(v for v in node.args.kw_defaults if v is not None)]:
            self.visit(value)

    def comprehension(self, node):
        saved = set(self.defined)
        self.control_depth += 1
        for generator in node.generators:
            self.visit(generator.iter)
            self.defined.update(n.id for n in ast.walk(generator.target)
                                if isinstance(n, ast.Name))
            for condition in generator.ifs:
                self.visit(condition)
        for part in ([node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]):
            self.visit(part)
        self.defined = saved
        self.control_depth -= 1

    visit_ListComp = comprehension
    visit_SetComp = comprehension
    visit_DictComp = comprehension
    visit_GeneratorExp = comprehension

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.called_names.add(node.func.id)
        self.generic_visit(node)

    def visit_For(self, node):
        self.visit(node.iter)
        self.control_depth += 1
        self.bind(node.target, "loop_target")
        for part in [*node.body, *node.orelse]:
            self.visit(part)
        self.control_depth -= 1

    visit_AsyncFor = visit_For

    def visit_If(self, node):
        self.visit(node.test)
        self.control_depth += 1
        for part in [*node.body, *node.orelse]:
            self.visit(part)
        self.control_depth -= 1

    def visit_While(self, node):
        self.visit_If(node)

    def visit_Delete(self, node):
        for target in node.targets:
            self.bind(target, "deleted")


def code_facts(code):
    facts = CallFacts(code)
    try:
        facts.visit(ast.parse(code))
        return facts, None
    except SyntaxError as exc:
        return facts, f"{exc.msg} at line {exc.lineno}"


def completed_python_calls(path):
    """Yield actual tool outputs once, with their matching submitted code."""
    calls, seen = {}, set()
    digest = hashlib.sha256()
    costs = Counter()
    malformed_lines = []
    outputs = []
    with path.open() as handle:
        for line_index, line in enumerate(handle, 1):
            digest.update(line.encode())
            try:
                record = json.loads(line)
            except ValueError:
                malformed_lines.append(line_index)
                continue
            if record.get("event") == "response":
                usage = record.get("usage") or {}
                for field in ("completion_tokens", "prompt_tokens", "total_tokens"):
                    costs[field] += usage.get(field) or 0
                costs["cached_prompt_tokens"] += (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
                costs["responses"] += 1
            level, step, visible_names = None, None, []
            for message in record.get("messages", []):
                if message.get("role") == "user":
                    user_text = text(message.get("content"))
                    match = STATE_RE.search(user_text)
                    if match:
                        step, level = map(int, match.groups())
                    marker = "Python names retained on this level: "
                    if marker in user_text:
                        names = user_text.rsplit(marker, 1)[1].split(". Re-read", 1)[0]
                        visible_names = [n.strip() for n in names.split(",") if n.strip()]
                elif message.get("role") == "assistant":
                    for call in message.get("tool_calls", []):
                        function = call.get("function", {})
                        if function.get("name") != "python":
                            continue
                        try:
                            code = json.loads(function.get("arguments", "{}"))["code"]
                        except (ValueError, KeyError, TypeError):
                            code = ""
                        calls.setdefault(call["id"], {"code": code, "level": level,
                            "step_before_call": step, "request_line_1based": line_index,
                            "analysis_step": record.get("analysis_step"),
                            "visible_persistent_names_before": list(visible_names)})
                elif message.get("role") == "tool":
                    call_id = message.get("tool_call_id")
                    if not call_id or call_id in seen:
                        continue
                    seen.add(call_id)
                    payload = parse_payload(message.get("content"))
                    if payload.get("tool") != "python":
                        continue
                    outputs.append({**calls.get(call_id, {"code": "", "level": None}),
                                    "tool_call_id": call_id, "result_line_1based": line_index,
                                    "payload": payload})
    return outputs, {"path": str(path), "sha256": digest.hexdigest(),
                     "costs": dict(costs), "malformed_lines": malformed_lines}


def call_excerpt(call):
    payload = call["payload"]
    return {"tool_call_id": call["tool_call_id"], "request_line_1based": call.get("request_line_1based"),
            "result_line_1based": call["result_line_1based"], "level": call.get("level"),
            "analysis_step": call.get("analysis_step"), "code": call["code"],
            "stdout": str(payload.get("stdout") or "")[:4000],
            "result": payload.get("result"), "error": payload.get("error"),
            "python_state": payload.get("python_state"),
            "function_retention": payload.get("function_retention")}


def analyze_requests(path, max_evidence):
    calls, source = completed_python_calls(path)
    bindings, functions, evidence, errors = {}, {}, [], []
    stats = Counter()
    current_level = object()
    for index, call in enumerate(calls):
        payload = call["payload"]
        state = payload.get("python_state") or {}
        level = call.get("level")
        if level != current_level or state.get("lost"):
            bindings.clear()
            functions.clear()
        current_level = level
        stats["python_calls"] += 1
        stats["calls_with_state_metadata"] += int(bool(state))
        stats["state_loss_notifications"] += int(bool(state.get("lost")))
        stats["name_count_positive_calls"] += int((state.get("name_count") or 0) > 0)
        error = str(payload.get("error") or "")
        stats["errors"] += bool(error)
        stats["timeouts"] += int("timed out" in error.lower())
        stats["state_loss_error_messages"] += int("variables for this level were cleared" in error)
        facts, parse_error = code_facts(call["code"])
        stats["ast_parse_errors"] += int(parse_error is not None)
        direct = {name for name in facts.external_reads if name in bindings
                  and bindings[name]["kind"] not in {"function", "class", "import", "deleted"}
                  and name not in RUNTIME_NAMES}
        indirect = set()
        for name in facts.called_names:
            indirect.update(n for n in {**functions, **facts.function_globals}.get(name, []) if n in bindings
                            and bindings[n]["kind"] not in {"function", "class", "import", "deleted"}
                            and n not in RUNTIME_NAMES and n not in facts.defined)
        if error:
            errors.append({"line_1based": call["result_line_1based"], "level": level,
                           "analysis_step": call.get("analysis_step"),
                           "error": exception_signature(error), "python_state": state})
        # Both a preceding definition and a later successful tool are required.
        # Still only a candidate: AST/control-flow and semantic use need review.
        if (direct or indirect) and not error and payload.get("returncode") == 0:
            stats["successful_cross_call_read_candidate_calls"] += 1
            names = sorted(direct | indirect)
            chosen = sorted(names, key=lambda n: (not bool(QUEUE_RE.search(n)), n))
            for name in chosen:
                origin = bindings[name]
                is_direct = name in direct
                item = {"name": name, "kind": origin["kind"], "same_recorded_level": level is not None,
                        "read_mode": "direct_before_definition" if is_direct else "called_function_global_candidate",
                        "conditional_read": name in facts.conditional_reads,
                        "definition_conditional": origin["conditional"],
                        "queue_or_search_name": bool(QUEUE_RE.search(name)),
                        "definition_had_error": origin["had_error"],
                        "python_state_metadata_present": bool(state),
                        "name_listed_in_persistent_context": name in call.get("visible_persistent_names_before", []),
                        "definition": call_excerpt(calls[origin["call_index"]]),
                        "reuse": call_excerpt(call),
                        "review_status": "unreviewed_static_candidate_not_proven_semantic_reuse"}
                evidence.append(item)
        for name, value in facts.bindings.items():
            bindings[name] = {**value, "call_index": index, "had_error": bool(error)}
        functions.update(facts.function_globals)
    evidence.sort(key=lambda e: (not e["queue_or_search_name"], e["read_mode"] != "direct_before_definition",
                                 e["definition_had_error"], e["conditional_read"]))
    return {"source": source, "stats": dict(stats), "error_types": dict(Counter(e["error"].split(":", 1)[0] for e in errors)),
            "errors": errors, "evidence_candidate_count": len(evidence),
            "evidence": evidence[:max_evidence]}


def level_rows(benchmark):
    rows = {}
    occurrence = Counter()
    for run in json.loads(benchmark.read_text())["game_runs"]:
        game = run["game_id"]
        repeat = occurrence[game]
        occurrence[game] += 1
        n, k = run["number_of_levels"], run["levels_completed"]
        actions, human = run.get("actions_per_level") or [], run.get("base_actions_per_level") or []
        for i in range(n):
            a = actions[i] if i < len(actions) else 0
            h = human[i] if i < len(human) else None
            efficiency = (None if h is None else min(115.0, (h / a) ** 2 * 100) if a > 0 else 0.0) if i < k else 0.0
            rows[(game, repeat, i + 1)] = {"game_id": game, "occurrence": repeat, "level": i + 1,
                "completed": i < k, "actions": a, "human_actions": h,
                "uncapped_weighted_efficiency_contribution": ((i + 1) * efficiency / (n * (n + 1) / 2)) if efficiency is not None and n else None}
    return rows


def write_markdown(report, out):
    lines = ["# 030 持久 Python 结果分析", "", "自动提取的跨调用读取仅供人工复核；定义存在、函数保留和工具不报错均不等于实际解题收益。", ""]
    if "benchmarks" in report:
        lines += ["| 臂 | 平均分 | 完成关卡 | 全通 | 动作 | 记录token | 分析器token |", "|---|---:|---:|---:|---:|---:|---:|"]
        for arm in report["benchmarks"]:
            s = arm["summary"]
            lines.append(f"| {arm['label']} | {fmt(s['mean_score'],4)} | {s['levels_completed']}/{s['levels_available']} | {s['wins']} | {s['actions']} | {s['generated_tokens']} | {fmt(s['analyzer_reported_generated_tokens'],0)} |")
        lines += ["", f"候选减基线平均分：{fmt(report['comparison']['mean_game_score_delta'],4)}。", "", "| 游戏 | 基线 | 候选 | 分差 | 关数差 |", "|---|---:|---:|---:|---:|"]
        for row in sorted(report["comparison"]["games"], key=lambda r: r["delta_mean_score"] or 0, reverse=True):
            lines.append(f"| {row['game_id']} | {fmt(row['reference_mean_score'],3)} | {fmt(row['candidate_mean_score'],3)} | {fmt(row['delta_mean_score'],3)} | {fmt(row['delta_mean_levels_completed'],0)} |")
    lines += ["", "## 实际 Python 调用与读取候选", "", "| 文件 | 去重调用 | 异常 | 超时 | 状态丢失通知 | 成功读取候选调用 |", "|---|---:|---:|---:|---:|---:|"]
    for result in report.get("request_logs", []):
        s = result["stats"]
        lines.append(f"| {Path(result['source']['path']).name} | {s.get('python_calls',0)} | {s.get('errors',0)} | {s.get('timeouts',0)} | {s.get('state_loss_notifications',0)} | {s.get('successful_cross_call_read_candidate_calls',0)} |")
    lines += ["", "状态丢失通知可能同时出现在超时调用和随后重启调用，不是独立丢失次数。调用token来自完整response日志；benchmark与日志记账分别保留，不能相加冒充新增成本。", "", "## 待人工确认的代码和输出", ""]
    for evidence in report.get("selected_evidence", []):
        before, after = evidence["definition"], evidence["reuse"]
        lines += [f"### {evidence['game_log']} 变量 {evidence['name']}", "",
                  f"读取方式：{evidence['read_mode']}；类型：{evidence['kind']}；定义输出行{before['result_line_1based']}，读取输出行{after['result_line_1based']}；关卡{after.get('level')}。", "",
                  "定义代码：", "```python", before["code"], "```", "", "随后代码：", "```python", after["code"], "```", "", "实际随后输出：", "```text", after["stdout"], "```", "",
                  "人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。", ""]
    out.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/030-capability-comparison")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--requests", type=Path, help="Override candidate request-log file or directory")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/030-analysis")
    parser.add_argument("--max-evidence", type=int, default=15)
    parser.add_argument("--requests-only", action="store_true", help="Inspect downloaded candidate logs while benchmarks are pending")
    parser.add_argument("--sandbox-demo", type=Path, help="Read an existing CPU demo JSON only; no score or reuse conclusion")
    args = parser.parse_args()
    if args.sandbox_demo:
        demo = json.loads(args.sandbox_demo.read_text())
        payloads = [c.get("payload", {}) for c in demo.get("calls", [])]
        print(json.dumps({"mode": "existing_demo_json_read_only", "calls": len(payloads),
            "errors": sum(bool(p.get("error")) for p in payloads),
            "state_loss_notifications": sum(bool((p.get("python_state") or {}).get("lost")) for p in payloads),
            "scope": "Parser smoke only; no model, GPU, game result or real cross-call adoption conclusion"}, indent=2))
        return
    baseline = args.baseline or args.root / "baseline/benchmark.json"
    candidate = args.candidate or args.root / "persistent_python/benchmark.json"
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "schema_version": 1,
              "scope": "Public development trajectories; official per-game scoring formula, not hidden leaderboard",
              "evidence_status": "unreviewed_static_candidates", "request_logs": []}
    if not args.requests_only:
        a = summarize_benchmark("baseline", baseline, "local-experiment")
        b = summarize_benchmark("persistent_python", candidate, "local-experiment")
        report.update(benchmarks=[a, b], comparison=compare(a, b))
        la, lb = level_rows(baseline), level_rows(candidate)
        report["per_level"] = [{"key": list(key), "baseline": la.get(key), "candidate": lb.get(key),
            "actions_delta": lb[key]["actions"] - la[key]["actions"] if key in la and key in lb else None,
            "completion_delta": int(lb[key]["completed"]) - int(la[key]["completed"]) if key in la and key in lb else None}
            for key in sorted(la.keys() | lb.keys())]
        report["aggregate_deltas"] = {field: b["summary"][field] - a["summary"][field]
            for field in ("mean_score", "levels_completed", "wins", "actions", "generated_tokens")}
    request_root = args.requests or candidate.parent
    paths = [request_root] if request_root.is_file() else sorted(request_root.rglob("*_requests.jsonl"))
    for path in paths:
        result = analyze_requests(path, args.max_evidence)
        report["request_logs"].append(result)
    report["missing_request_logs"] = not paths
    selected = [{**e, "game_log": Path(log["source"]["path"]).name}
                for log in report["request_logs"] for e in log["evidence"]]
    selected.sort(key=lambda e: (not e["queue_or_search_name"], e["read_mode"] != "direct_before_definition",
                                e["definition_had_error"], e["conditional_read"]))
    report["selected_evidence"] = selected[:args.max_evidence]
    report["limitations"] = ["Static reads may be on an unexecuted branch; inspect complete submitted code and actual stdout/actions.",
        "Bindings in an erroring or conditional snippet may never have executed; these are explicitly flagged.",
        "Level is inferred from the preceding user observation; unknown level cannot prove within-level continuity.",
        "Definition/function existence is excluded from direct ordinary-variable reuse candidates.",
        "No automatic causal attribution, score gain or statistical significance is inferred from variable reads."]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    write_markdown(report, args.output_dir / "report.md")
    print(json.dumps({"output": str(args.output_dir.resolve()), "request_logs": len(paths),
        "evidence_candidates_shown": len(report["selected_evidence"]),
        "mean_game_score_delta": report.get("comparison", {}).get("mean_game_score_delta")}, indent=2))


if __name__ == "__main__":
    main()
