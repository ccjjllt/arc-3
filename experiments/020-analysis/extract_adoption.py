"""020 code-only retrieval index. Never executes logged code or assigns adoption pass.

Only explicitly confirmed complete per-game logs are read. The 018 extractor
deduplicates repeated history snapshots by tool call ID. Repeated identical code
under different IDs remains distinct calls; a separate code-hash count is kept.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_018_results import extract_log, fallback_response_evidence

APIS = {"region", "region_from_node"}
PROPERTIES = {"cells", "mask", "origin", "shape", "bbox", "source", "raw_rows", "positions"}
MANUAL_ALIAS_NOTES = {
    "ft09-0d8bbf25": "Inspected retrieved seq32: 'group by region' is a comment; reg is a Counter, not a GroundedRegion. No API invocation in this retrieved call.",
    "ar25-0c556536": "No API names or within-call API alias bindings found in the 94 visible code calls. No positive alias evidence; this is not a proof against dynamic string construction or absent final calls.",
    "cd82-fb555c5d": "Inspected seq74 call_a782478e23a142c7a7d529e0: reg binds current_frame.region; reg.raw_rows is printed. This is retrieval/display evidence, not demonstrated solver/planner consumption.",
    "bp35-0a0ad940": "Inspected seq19/20/21 and comment-only seq42. reg/reg0/reg2 are region-result aliases, not callable-method aliases. seq21 f0=history[0].frame raises not_live_current_frame on its first region call; the later current_frame.region syntax in that same code is not evidence of execution. seq19/20 print reg.cells; no adoption verdict assigned.",
    "ls20-9607627b": "Inspected retrieved seq20: region occurs only in a comment; no region method or method alias found by this index.",
    "m0r0-492f87ba": "No API names/within-call API aliases in visible code; dynamic construction or absent final calls are not excluded.",
    "re86-8af5384d": "Inspected seq26 and46: region is descriptive print text; r is an action result, not a region or callable-method alias.",
    "r11l-495a7899": "Inspected direct API calls and retained blocked_mask helper. seq13 positions -> candidates -> t -> MOUSE(54,30) actually executes but is NO-OP. seq18 defines/calls blocked_mask, records retention; seq36 calls it after an effect action and uses its cells in a segment check. seq12 has argument-format error; seq20 historical-frame call is rejected before later expressions. These are real uses plus interface-boundary errors, not proof of benefit or incorrect region extraction. See r11l-adoption-note.md.",
    "tr87-cd924810": "Inspected retrieved seq2: region is a comment about a handwritten ASCII crop; crop/norm are ordinary helper functions, not aliases of the new APIs.",
    "sb26-7fbdac44": "No API names/within-call API aliases in visible code; dynamic construction or absent final calls are not excluded.",
    "vc33-5430563c": "Inspected retrieved seq1/10/15/19/47: f/fr alias current_frame, but accesses are segmentation/ascii/shape/level. No region method invocation in these alias calls.",
    "wa30-ee6fef47": "No API names/within-call API aliases in visible code; dynamic construction or absent final calls are not excluded.",
}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def code_index(code):
    """Path-insensitive, within-call navigation hints, not execution/dataflow proof."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"ast_error": str(exc), "code_mentions": sorted(set(re.findall(r"\b(region_from_node|region)\b", code))),
                "api_calls": [], "aliases": [], "region_object_uses": []}
    aliases = {}
    frame_names = {"current_frame": "current_frame", "previous_frame": "previous_frame"}
    region_objects = set()
    bindings, calls, uses, references = [], [], [], []
    assignment_call_resolution = {}

    def receiver(node):
        if isinstance(node, ast.Name):
            return frame_names.get(node.id, node.id)
        return ast.unparse(node)

    def resolve(expr):
        if isinstance(expr, ast.Attribute) and expr.attr in APIS:
            return {"api": expr.attr, "receiver": receiver(expr.value), "resolution": "attribute_name"}
        if isinstance(expr, ast.Name) and expr.id in aliases:
            return {**aliases[expr.id], "resolution": "within_call_alias", "via": expr.id}
        if (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "getattr"
                and len(expr.args) >= 2 and isinstance(expr.args[1], ast.Constant)
                and expr.args[1].value in APIS):
            return {"api": expr.args[1].value, "receiver": receiver(expr.args[0]),
                    "resolution": "literal_getattr"}
        return None

    # This lexical ordering intentionally does not claim branch/scope execution.
    nodes = sorted(ast.walk(tree), key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0)))
    for node in nodes:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            names = [n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)]
            resolved = resolve(value) if value is not None else None
            returned = resolve(value.func) if isinstance(value, ast.Call) else None
            if returned:
                assignment_call_resolution[id(value)] = returned
            for name in names:
                aliases.pop(name, None)
                frame_names.pop(name, None)
                region_objects.discard(name)
                if resolved:
                    aliases[name] = resolved
                    bindings.append({"name": name, "line": node.lineno, **resolved})
                if isinstance(value, ast.Name) and value.id in frame_names:
                    frame_names[name] = frame_names[value.id]
                    bindings.append({"name": name, "line": node.lineno,
                                     "kind": "frame_alias", "receiver": frame_names[name]})
                if returned:
                    region_objects.add(name)
                    bindings.append({"name": name, "line": node.lineno,
                                     "kind": "region_result_binding", **returned})
        if isinstance(node, ast.Attribute) and node.attr in APIS:
            references.append({"line": node.lineno, "text": ast.unparse(node)})
        if isinstance(node, ast.Call):
            found = assignment_call_resolution.get(id(node)) or resolve(node.func)
            if found:
                calls.append({"line": node.lineno, "column": node.col_offset,
                              "expression": ast.unparse(node), **found})
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id in region_objects and node.attr in PROPERTIES):
            uses.append({"line": node.lineno, "object_alias": node.value.id,
                         "property": node.attr, "text": ast.unparse(node)})
    return {"ast_error": None, "code_mentions": sorted(set(re.findall(r"\b(region_from_node|region)\b", code))),
            "api_calls": calls, "aliases": bindings, "region_object_uses": uses,
            "attribute_references": references,
            "alias_limit": "Static within-call lexical hints; function/branch scopes and inter-call persistence require semantic review."}


def helper_index(code, known, call):
    """Find later references to visibly defined region helpers; retention is separate evidence."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [], []
    defined = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_api = any(isinstance(n, ast.Attribute) and n.attr in APIS for n in ast.walk(node))
            has_helper = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                             and n.func.id in known for n in ast.walk(node))
            if has_api or has_helper:
                binding = {"name": node.name, "definition_call_id": call["call_id"],
                           "definition_seq": call["seq"], "definition_source_line": call["first_seen"]["source_line"]}
                known[node.name] = binding
                defined.append(binding)
            else:
                known.pop(node.name, None)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    invocations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in known:
            parent, scopes = parents.get(node), []
            while parent:
                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    scopes.append(getattr(parent, "name", "lambda"))
                parent = parents.get(parent)
            invocations.append({**known[node.func.id], "code_line": node.lineno,
                                "expression": ast.unparse(node), "enclosing_function_definitions": scopes,
                                "note": "Named-helper syntax only; retention, actual execution and inputs require returned-log review."})
    return defined, invocations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/020-candidate-logs/grounded_state")
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/020-analysis/adoption-index.json")
    parser.add_argument("--complete-game", action="append", required=True,
                        help="Exact full ID confirmed by downloader; never infer completion from stable size")
    parser.add_argument("--fallback-complete", action="store_true",
                        help="Downloader separately confirmed root requests.jsonl complete")
    args = parser.parse_args()
    expected = json.loads((ROOT / "experiments/020-grounded-state.json").read_text())["games"]
    confirmed = set(args.complete_game)
    if not confirmed <= set(expected):
        raise ValueError("Unexpected game ID")
    game_paths = {game: args.root / f"{game}_p0_requests.jsonl" for game in expected if game in confirmed}
    snapshots = {}
    for path in [*game_paths.values(), *([args.root / "requests.jsonl"] if args.fallback_complete else [])]:
        st = path.stat()
        if st.st_size <= 0:
            raise ValueError("Confirmed file empty: " + str(path))
        with path.open("rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                raise ValueError("Confirmed file lacks final newline: " + str(path))
        snapshots[str(path)] = (st.st_size, st.st_mtime_ns)
    supplemental = {game: [] for game in game_paths}
    fallback_evidence = {"status": "not_read_unconfirmed", "matches": [], "issues": []}
    if args.fallback_complete:
        supplemental, fallback_evidence = fallback_response_evidence(args.root, game_paths)
        fallback_evidence["coverage_note"] = "Unmatched records remain unresolved while some per-game logs are pending; no ownership is guessed."
    reports = {}
    global_ids, cross_game_ids = {}, []
    for game in expected:
        if game not in confirmed:
            continue
        path = args.root / f"{game}_p0_requests.jsonl"
        before = path.stat()
        if before.st_size <= 0:
            raise ValueError("Confirmed file empty: " + game)
        with path.open("rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                raise ValueError("Confirmed file lacks final newline: " + game)
        extracted = extract_log(path, prefix=None, fallback_responses=supplemental[game])
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError("File changed while reading: " + game)
        if any(i["issue"] == "invalid_json" for i in extracted["issues"]):
            raise ValueError("Invalid JSON in confirmed complete file: " + game)
        indexed, code_counts, parsed_count = [], Counter(), 0
        known_helpers = {}
        aliases_for_review = []
        for call in extracted["snippets"]:
            tid = call["call_id"]
            if tid in global_ids and global_ids[tid] != game:
                cross_game_ids.append({"call_id": tid, "games": [global_ids[tid], game]})
            global_ids[tid] = game
            code = call.get("code")
            if not isinstance(code, str):
                continue
            parsed_count += 1
            code_counts[sha(code)] += 1
            scan = code_index(code)
            helper_definitions, helper_invocations = helper_index(code, known_helpers, call)
            if scan["aliases"]:
                aliases_for_review.append({"call_id": call["call_id"], "seq": call["seq"],
                                           "source_line": call["first_seen"]["source_line"],
                                           "aliases": scan["aliases"]})
            if scan["code_mentions"] or scan["api_calls"] or scan["aliases"] or helper_invocations:
                indexed.append({"call_id": call["call_id"], "seq": call["seq"],
                    "source_line": call["first_seen"]["source_line"], "code_sha256": sha(code),
                    "snapshot_appearances": call["snapshot_appearances"], "code": code,
                    "has_tool_result": call["result"] is not None,
                    "execution_evidence": "tool_result_recorded_in_later_history" if call["result"] is not None else "not_confirmed",
                    "observed_result_error": call["observed_result_error"],
                    "helper_definitions": helper_definitions, "helper_invocations": helper_invocations, **scan})
        reports[game] = {"source": extracted["source"], "download_completion": "explicitly_confirmed_by_root",
            "request_records": extracted["summary"]["request_records"],
            "response_records": extracted["summary"]["response_records"],
            "fallback_response_matches": extracted["fallback_response_matches"],
            "unique_call_ids": extracted["summary"]["unique_tool_call_ids"],
            "code_call_ids": parsed_count, "unique_code_hashes": len(code_counts),
            "repeated_code_different_call_ids": {k: v for k, v in code_counts.items() if v > 1},
            "calls_with_api_syntax": sum(bool(r["api_calls"]) for r in indexed),
            "calls_with_helper_invocation_syntax": sum(bool(r["helper_invocations"]) for r in indexed),
            "api_syntactic_expression_counts": dict(Counter(c["api"] for r in indexed for c in r["api_calls"])),
            "ast_errors_in_retrieved_calls": sum(r["ast_error"] is not None for r in indexed),
            "calls": indexed, "alias_candidates": aliases_for_review,
            "manual_alias_review": {"status": "retrieved_calls_reviewed" if game in MANUAL_ALIAS_NOTES else "pending",
                                    "reviewer": "Codex static review, not human annotation",
                                    "scope": "Retrieved API/code references and within-call alias candidates only; no logged code execution.",
                                    "note": MANUAL_ALIAS_NOTES.get(game, "AST index is not manual adoption review.")},
            "extractor_issues": extracted["issues"], "orphan_result_ids": extracted["orphan_result_ids"],
            "scope": "Retrieval only; property references or successful tool return do not prove planning/action consumption."}
    result = {"schema_version": 1, "experiment": "020-grounded-state",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "coverage": {"expected_games": expected, "confirmed_complete_and_read": [g for g in expected if g in reports],
                     "not_read_pending_or_missing": [g for g in expected if g not in reports],
                     "read_count": len(reports), "expected_count": len(expected)},
        "method": {"extractor": "scripts/analyze_018_results.py:extract_log(prefix=None)",
                   "deduplication": "tool call ID across history snapshots; code hashes counted separately, not collapsed across distinct IDs",
                   "search_scope": "parsed tool-call code only; never system prompt/reasoning/result text",
                   "code_executed": False, "adoption_classification": "not_assigned",
                   "limitations": ["Only calls retained in later message-history snapshots are visible; final unrecorded calls cannot be reconstructed.",
                                   "Dynamic aliases, exec strings, function scope, cross-call retention and actual consumption need manual review.",
                                   "No adoption pass/fail or causal conclusion is generated."]},
        "games": reports, "fallback_response_evidence": fallback_evidence,
        "source_hashes": {"extractor": hashlib.sha256((ROOT / "scripts/analyze_018_results.py").read_bytes()).hexdigest(),
                          "indexer": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    result["retrieval_totals"] = {
        "unique_call_ids_summed_per_game": sum(r["unique_call_ids"] for r in reports.values()),
        "unique_call_ids_global": len(global_ids),
        "cross_game_call_id_duplicates": cross_game_ids,
        "code_call_ids": sum(r["code_call_ids"] for r in reports.values()),
        "games_with_direct_api_syntax": [g for g, r in reports.items() if r["calls_with_api_syntax"]],
        "calls_with_direct_api_syntax": sum(r["calls_with_api_syntax"] for r in reports.values()),
        "syntactic_expression_counts_not_dynamic_execution_counts": dict(Counter(
            c["api"] for r in reports.values() for item in r["calls"] for c in item["api_calls"])),
        "helper_only_additional_call_refs": [{"game_id": g, "call_id": c["call_id"],
                                               "seq": c["seq"], "source_line": c["source_line"]}
                                              for g, r in reports.items() for c in r["calls"]
                                              if c["helper_invocations"] and not c["api_calls"]],
        "manual_evidence_note": "r11l has returned region data consumed in an executed click and retained-helper diagnostics. Other references, errors and absent API syntax do not support a blanket all-adopted/all-not-adopted conclusion.",
        "adoption_pass_assigned": False,
    }
    for filename, snapshot in snapshots.items():
        st = Path(filename).stat()
        if (st.st_size, st.st_mtime_ns) != snapshot:
            raise RuntimeError("Confirmed input changed during indexing: " + filename)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"coverage": result["coverage"], "counts": {
        g: {k: r[k] for k in ["unique_call_ids", "calls_with_api_syntax", "api_syntactic_expression_counts"]}
        for g, r in reports.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
