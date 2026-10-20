"""Recover 028 diagnostics from saved traces after post-run export failed."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ACTION_IDS = {"UP": "ACTION1", "DOWN": "ACTION2", "LEFT": "ACTION3",
              "RIGHT": "ACTION4", "SPACE": "ACTION5", "MOUSE": "ACTION6",
              "UNDO": "ACTION7", "RESET": "RESET"}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def action_from_display(display):
    match = re.fullmatch(r"MOUSE\(row=(-?\d+), col=(-?\d+)\)", display)
    if match:
        row, col = map(int, match.groups())
        return {"id": "ACTION6", "data": {"x": col, "y": row}}
    if display in ACTION_IDS:
        return {"id": ACTION_IDS[display], "data": {}}
    raise ValueError(f"Unrecognized actual action display: {display}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/028-program-repair")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/028-analysis")
    args = parser.parse_args()
    arm = args.root / "repair_forks"
    package = json.loads((ROOT / "experiments/028-fork-package.json").read_text())
    result = {"scope": "Existing GPU 028 v1 evidence only; no model calls or rerun",
              "arm_status": json.loads((arm / "arm-metadata.json").read_text())["status"],
              "export_error": "ActionRecord.get failed only after six sessions finished",
              "sessions": [], "comparisons": [], "limitations": [
                  "Single concurrent six-session diagnostic; not an official score or full-pool comparison.",
                  "Request timeout may have generated unreported server tokens; no zero-cost assumption."]}
    finished = []
    for line in (arm / "run.log").read_text().splitlines():
        match = re.match(r'\[finished\] (\S+) state=(\S+) level=(\d+)/(\d+) score=([\d.]+) actions=(\d+) .*note="tokens=(\d+)"', line)
        if match:
            game, state, levels, total, score, actions, tokens = match.groups()
            finished.append({"game_id": game, "state": state, "levels_completed": int(levels),
                             "levels_available": int(total), "score_display": float(score),
                             "total_actions": int(actions), "analyzer_reported_tokens": int(tokens)})
    for game, fork in package["forks"].items():
        for label in ("A", "B"):
            stem = f"{game}_{label}"
            transcript_path = arm / "transcripts" / (stem + ".txt")
            text = transcript_path.read_text()
            request_path = arm / (stem + "_requests.jsonl")
            requests = read_jsonl(request_path)
            normal_tokens = sum((r.get("usage") or {}).get("completion_tokens", 0)
                                for r in requests if r.get("event") == "response")
            echo = re.findall(r"^\[action\] (.*?) ->", text, re.M)
            actions = [action_from_display(display) for display in echo]
            events_path = arm / "artifacts" / (stem + "_events.jsonl")
            if events_path.is_file():
                events = read_jsonl(events_path)
                post = [e for e in events if e.get("type") == "action"
                        and int(e.get("action_num", 0)) > int(fork["cut"])]
                actions = [action_from_display(e["action_display"]) for e in post]
                source = str(events_path.relative_to(ROOT))
            else:
                # Echoes are actual execution output, rather than requested code.
                # These short sessions have no automatic RESETs (final levels
                # and total action counts are independently cross-checked).
                source = str(transcript_path.relative_to(ROOT)) + ": actual [action] echoes"
            repair_path = arm / "artifacts" / (stem + "_tool_runtime_state_program-repair.jsonl")
            repair = read_jsonl(repair_path)[0] if repair_path.is_file() else None
            repair_tokens = sum((c.get("usage") or {}).get("completion_tokens", 0)
                                for c in (repair or {}).get("calls", []))
            total_actions = int(fork["cut"]) + len(actions)
            matches = [item for item in finished if item["game_id"] == game
                       and item["total_actions"] == total_actions]
            exact = [item for item in matches if item["analyzer_reported_tokens"] == normal_tokens + repair_tokens]
            completion = exact[0] if exact else matches[0] if len(matches) == 1 else None
            if completion is None:
                raise RuntimeError(f"Could not uniquely align {stem} with finished log")
            viewer_path = arm / "artifacts" / (stem + "_viewer_data.json")
            if viewer_path.is_file():
                viewer = json.loads(viewer_path.read_text())
                assert viewer["levels_completed"] == completion["levels_completed"]
                completion = {**completion, "final_score": viewer.get("final_score")}
            initial_levels = int(fork["current_frame"]["level"]) - 1
            entry = {"game_id": game, "arm": label, "cut": fork["cut"],
                     "initial_levels_completed": initial_levels,
                     **{key: value for key, value in completion.items() if key != "game_id"},
                     "added_levels": completion["levels_completed"] - initial_levels,
                     "continuation_actions": actions, "continuation_action_count": len(actions),
                     "action_source": source, "recorded_normal_completion_tokens": normal_tokens,
                     "reported_repair_completion_tokens": repair_tokens,
                     "token_accounting_residual": completion["analyzer_reported_tokens"] - normal_tokens - repair_tokens,
                     "repair": repair,
                     "request_log": str(request_path.relative_to(ROOT)),
                     "transcript": str(transcript_path.relative_to(ROOT)),
                     "request_log_sha256": hashlib.sha256(request_path.read_bytes()).hexdigest()}
            result["sessions"].append(entry)
    for game in package["forks"]:
        a, b = [next(s for s in result["sessions"] if s["game_id"] == game and s["arm"] == label)
                for label in ("A", "B")]
        pairs = list(zip(a["continuation_actions"], b["continuation_actions"]))
        first = next((i + 1 for i, (x, y) in enumerate(pairs) if x != y), None)
        result["comparisons"].append({"game_id": game, "added_levels_A": a["added_levels"],
            "added_levels_B": b["added_levels"], "delta_added_levels": b["added_levels"] - a["added_levels"],
            "actions_A": a["continuation_action_count"], "actions_B": b["continuation_action_count"],
            "actions_id_and_data_equal": a["continuation_actions"] == b["continuation_actions"],
            "first_differing_paired_action_1based": first,
            "sequence_length_differs": len(a["continuation_actions"]) != len(b["continuation_actions"]),
            "reported_total_tokens_A": a["analyzer_reported_tokens"],
            "reported_total_tokens_B": b["analyzer_reported_tokens"]})
    result["verdict"] = "No paired case gained a level. ft09 repair executed and was used but retained its key pixel error; tu93 repair timed out. Do not expand this implementation on these results."
    result["mechanism_findings"] = {
        "ft09": {"repair_executed": True, "retained_functions": ["analyze", "satisfaction"],
            "used_by_main_model": "Main continuation derived and executed analyze2/analyze3/polar variants from the returned extractor, retaining the same bbox-fill logic.",
            "pixel_audit": "experiments/028-analysis/ft09-repair-pixel-audit.json",
            "key_error_persists": "pattern(5,2) middle row actual WOg was still extracted as WOW; frame coordinate row46,col32 is g but returned extractor gives W.",
            "recovery": "No level gain; A and B each clicked ACTION6(x22,y30), an actual no-op."},
        "tu93": {"repair_executed": False, "failure": "HTTP ReadTimeout at 60s; no returned code or usage",
            "continuation": "Main model continued and executed nine actions in B, but no level gain; this cannot be attributed to a repaired program."}}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    lines = ["# 028 真实修复结果", "", result["verdict"], "",
             "| 游戏 | A新增关 | B新增关 | A续跑动作 | B续跑动作 | A总token | B总token |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for x in result["comparisons"]:
        lines.append(f"| {x['game_id']} | {x['added_levels_A']} | {x['added_levels_B']} | {x['actions_A']} | {x['actions_B']} | {x['reported_total_tokens_A']} | {x['reported_total_tokens_B']} |")
    lines += ["", "ft09 B：真实修复调用50.19秒，1116生成token、58470输入token；代码执行并被后续模型采用，但关键WOg→WOW误编码仍存在。",
              "", "tu93 B：修复调用60.32秒后ReadTimeout，无返回代码；超时调用的实际生成token未知。",
              "", "六路续跑均实际执行至退出；arm ERROR来自结束后ActionRecord.get导出错误。该工程故障不能抹去已有修复与续跑证据，也不需要重跑GPU恢复结果。",
              "", "这是六路并发单次诊断，不是正式榜分；token为分析器记录，非计费。动作比较包含ID和完整坐标参数。"]
    (args.output_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"verdict": result["verdict"], "comparisons": result["comparisons"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
