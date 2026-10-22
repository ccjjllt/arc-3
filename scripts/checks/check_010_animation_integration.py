#!/usr/bin/env python3
"""Manual CPU delivery checks for 010; not a test suite or benchmark.

Runs original and candidate harnesses in separate processes, using handwritten
public-SDK actions and the actual ToolAgent / solver callback / Python sandbox.
Synthetic storage boundaries are explicitly separate. No model endpoint,
GPU, engine implementation inspection, or historical model-code execution.
All Python/package paths must already exist; this script installs nothing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
GAME = "tn36-ef4dde99"
CLICKS = [(14, 31), (55, 35), (45, 21), (45, 36), (20, 20)]
ENV = {
    "ARC3_ANIMATION": "1", "ARC3_ACTION_ECHO": "1",
    "ARC3_NEW_CHANGED_PROMPTS": "1", "ARC3_BATCH_NOOP_BLOCK": "1",
    "ARC3_GUARDS_FROM_LEVEL": "2", "ARC3_STALE_STATE_BLOCK": "1",
    "ARC3_NOOP_REPEAT_GUARD": "0", "ARC3_DEATH_REPEAT_GUARD": "0",
    "LOCAL_ANALYZER_MODEL_ID": "cpu-no-model", "EXPOSE_RESET": "on",
    "MPLCONFIGDIR": "/private/tmp/arc3-010-mpl", "MPLBACKEND": "Agg",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def source_hashes():
    names = ["scripts/checks/check_010_animation_integration.py",
             "src/arc3_research/retrievable_animation.py",
             "research/runtime-bundle/src/ARC3-Inference/inference/framework/solver.py",
             "research/runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py",
             "research/runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py",
             "research/runtime-bundle/src/tufa-arc-agi-framework/src/taaf/game_api.py"]
    return {name: digest((ROOT / name).read_bytes()) for name in names}


def worker(args):
    out = args.output_dir / args.worker
    out.mkdir(parents=True, exist_ok=False)
    sys.path[:0] = [str(args.sdk_path), str(ROOT / "src"),
                   str(ROOT / "research/runtime-bundle/src/ARC3-Inference"),
                   str(ROOT / "research/runtime-bundle/src/tufa-arc-agi-framework/src")]
    sys.path.extend(str(path) for path in args.extra_python_path)
    os.environ.update(ENV)
    import numpy as np
    import requests
    from inference.agent.tool_agent import ToolAgent
    from inference.agent.runtime_state import Frame, HistoryEntry, write_runtime_state
    from inference.framework.solver import HarnessSolver, _HarnessGameSession
    from inference.utils.animation import build_animation_frames
    from inference.utils.grid_utils import format_grid_ascii
    from taaf.game import RunSession
    from taaf.game_api import ArcadeSpec, GameAPI

    report = {"worker": args.worker, "checks": [], "tool_calls": [],
              "source_sha256": source_hashes(), "environment": ENV,
              "python": sys.executable, "python_version": sys.version,
              "sdk_path": str(args.sdk_path),
              "extra_python_paths": [str(p) for p in args.extra_python_path],
              "versions": {name: importlib.metadata.version(name)
                           for name in ("arc-agi", "arcengine", "numpy", "pydantic", "matplotlib")},
              "http_calls_blocked": 0, "model_called": False, "gpu_started": False,
              "logged_model_code_executed": False, "engine_source_read": False,
              "synthetic": args.worker == "boundaries"}
    patch = None
    runs = []

    def save():
        if patch is not None:
            report["archive_diagnostics"] = patch.snapshot()
        write_json(out / "report.json", report)

    def check(name, condition, **evidence):
        report["checks"].append({"name": name, "passed": bool(condition), **evidence})
        save()
        if not condition:
            raise AssertionError(name)

    def no_http(*unused, **kwargs):
        report["http_calls_blocked"] += 1
        raise RuntimeError("HTTP is prohibited in the CPU delivery check")

    requests.sessions.Session.request = no_http

    def tool(session, code, label):
        before_step = session.action_count
        start = time.perf_counter()
        result = session.analyzer._run_python_tool(session.state_path, {"code": code})
        value = json.loads(result.content)
        item = {"label": label, "code": code, "dispatch": value,
                "step_executed": result.step_executed, "made_progress": result.made_progress,
                "step_before": before_step, "step_after": session.action_count,
                "elapsed_seconds": time.perf_counter() - start,
                "output_chars": len(result.content)}
        trace_name = f"tool-{len(report['tool_calls']):03d}-{label}.json"
        write_json(out / trace_name, item)
        report["tool_calls"].append({k: v for k, v in item.items() if k not in {"code", "dispatch"}} | {"trace": trace_name})
        check(label + "_sandbox_success", "error" not in value, error=value.get("error"))
        lines = [line.removeprefix("RESULT=") for line in value.get("stdout", "").splitlines()
                 if line.startswith("RESULT=")]
        return json.loads(lines[-1]) if lines else value

    def emit(expression):
        return "import json\nprint('RESULT='+json.dumps(" + expression + ",separators=(',',':')))"

    def new_session(name, synthetic=False):
        directory = out / name
        directory.mkdir()
        analyzer = ToolAgent(model="cpu-no-model")
        solver = HarnessSolver(model="cpu-no-model", start_local_server=False, kaggle_enable_vllm=False)
        if synthetic:
            raw = SimpleNamespace(frame=[[[0]]])
            game = SimpleNamespace(game_run=SimpleNamespace(game_id=name, history=[]),
                                   current_state=SimpleNamespace(raw=raw))
        else:
            run = RunSession(record_intermediate_states=False)
            runs.append(run)
            game = GameAPI(env_name=GAME, arcade_spec=ArcadeSpec(
                environments_dir=str(ROOT / "research/data/extracted/environment_files")))
            game.start_game(run)
        session = _HarnessGameSession(
            solver=solver, game=game, analyzer=analyzer, game_index=len(runs), pass_index=0,
            state_path=directory / "state.json", transcript_path=directory / "transcript.md",
            analysis_html_relpath="unused.html", stop_event=threading.Event(),
            viewer_data_path=directory / "viewer.json")
        if synthetic:
            frame = Frame(grid=((0,),), step=0, level=1)
            write_runtime_state(session.state_path, current_frame=frame,
                                history=[HistoryEntry(action="", frame=frame)])
        else:
            session.seed_initial_history()
            session.write_runtime_state()
        analyzer._step_env_callback = session.step_env
        return session

    def callback(session, op, **kw):
        before = session.action_count
        value = session.step_env({"query": "retrievable_animation", "op": op, **kw})
        check("callback_read_did_not_act", session.action_count == before and value.get("executed") is False)
        return value["result"]

    def query_status(session, ref, label, expected):
        got = tool(session, emit("animation_at(" + repr(ref) + ")[\"status\"]"), label)
        check(label, got == expected, status=got, expected=expected)

    try:
        if args.worker != "baseline":
            from arc3_research.retrievable_animation import install_retrievable_animation
            limits = ({"max_records_per_session": 3, "max_bytes_per_session": 400,
                       "max_total_bytes": 600, "max_sessions": 2}
                      if args.worker == "boundaries" else {})
            patch = install_retrievable_animation(**limits)

        if args.worker == "boundaries":
            # These directly supply invented public-frame-shaped inputs at the
            # capture boundary. Retrieval still uses real step_env + sandbox IPC.
            session = new_session("synthetic-a", synthetic=True)
            context = patch._context(session)

            def capture(target, number, frames, before=((0,),), reset=False):
                ctx = patch._context(target)
                target.game.current_state.raw.frame = frames
                payload = {"executed": True, "action_num": number, "level": 1,
                           "action_name": "RESET" if reset else "ACTION1"}
                patch._capture(target, ctx, payload, before, 1, number - 1)
                return {**{key: ctx[key] for key in ("game_id", "session_id", "attempt")},
                        "action_num": number}

            ref1 = capture(session, 1, [[[0]], [[0]]])
            raw = callback(session, "get", ref=ref1)
            check("synthetic_duplicate_frames_preserved", len(raw["frames"]) == 2 and
                  raw["frames"][0]["grid"] == raw["frames"][1]["grid"])
            big = [[1] * 8 for _ in range(8)]
            ref2 = capture(session, 2, [big], before=big)
            ref3 = capture(session, 3, [big], before=big)
            query_status(session, ref2, "synthetic_byte_evicted", "evicted")
            ref4 = capture(session, 4, [])
            query_status(session, ref1, "synthetic_metadata_window_expired", "outside_retained_history")
            query_status(session, ref4, "synthetic_empty_chain", "missing_frames")
            ref5 = capture(session, 5, [big, big, big], before=big)
            query_status(session, ref5, "synthetic_oversize_not_truncated", "too_large")
            ref6 = capture(session, 6, [[[19]]])
            query_status(session, ref6, "synthetic_invalid_color", "invalid_frames")
            ref7 = capture(session, 7, [big], before=big)
            other = new_session("synthetic-b", synthetic=True)
            ref_b = capture(other, 1, [big], before=big)
            query_status(session, ref7, "synthetic_global_byte_evicted", "evicted")
            third = new_session("synthetic-c", synthetic=True)
            capture(third, 1, [[[0]]])
            query_status(session, ref6, "synthetic_session_evicted", "session_evicted")
            query_status(third, ref_b, "synthetic_wrong_live_session", "wrong_scope")
            invalid = tool(third, emit("animation_refs(limit=0)['status']"), "invalid_limit")
            check("synthetic_invalid_limit", invalid == "invalid_limit")
            stats = patch.snapshot()
            check("synthetic_capacity_limits_hold", stats["stored_frame_json_bytes"] <= 600 and
                  stats["retained_sessions"] <= 2 and
                  all(s["stored_frame_json_bytes"] <= 400 and s["metadata_records"] <= 3
                      for s in stats["sessions"]), snapshot=stats)
        else:
            session = new_session("public-tn36")
            oracle = {}
            original_execute = session.game.execute_action

            def observe_public_return(*a, **kw):
                before = np.array(session.game.current_state.raw.frame[-1], dtype=np.uint8, copy=True)
                result = original_execute(*a, **kw)
                frames = [np.array(f, dtype=np.uint8, copy=True) for f in result.raw.frame]
                oracle[session.action_count] = {"before": before, "frames": frames}
                return result

            session.game.execute_action = observe_public_return
            available = tool(session, "try:\n    animation_refs\n    available=True\nexcept NameError:\n    available=False\n" + emit("available"), "helper_visibility")
            check("helper_visibility_matches_arm", available == (args.worker == "candidate"))
            steps = []
            for index, (row, col) in enumerate(CLICKS[:2], 1):
                tool(session, f"action({{'action':'MOUSE','row':{row},'col':{col}}})", f"click-{index}")
                expected = build_animation_frames(session.animation_record)
                got = tool(session, emit("{'count':len(last_animation_frames),'equal':"
                    "[f.ascii for f in last_animation_frames]==" + repr([f["ascii"] for f in expected]) + "}"), f"latest-after-{index}")
                check(f"original_latest_after_{index}", got["equal"] and got["count"] == len(expected), result=got)
                steps.append({"action": index, "raw_frames": len(oracle[index]["frames"]),
                              "latest": expected})
            # Three actions in one actual action() batch; the patch must capture
            # each executor return, rather than only the final batch payload.
            batch = [{"action": "MOUSE", "row": r, "col": c} for r, c in CLICKS[2:]]
            tool(session, "action(" + repr(batch) + ")", "batch-actions-3-5")
            check("all_five_actions_executed", session.action_count == 5)
            expected = build_animation_frames(session.animation_record)
            got = tool(session, emit("{'count':len(last_animation_frames),'equal':"
                "[f.ascii for f in last_animation_frames]==" + repr([f["ascii"] for f in expected]) + "}"), "latest-after-5")
            check("original_latest_after_5", got["equal"] and got["count"] == len(expected), result=got)
            steps.append({"action": 5, "raw_frames": len(oracle[5]["frames"]), "latest": expected})
            report["original_latest_observations"] = steps
            check("old_seven_vs_latest_single_raw", len(oracle[2]["frames"]) == 7 and len(oracle[5]["frames"]) == 1)

            if patch is not None:
                listed = callback(session, "list", limit=16)
                refs = {r["ref"]["action_num"]: r["ref"] for r in listed["records"]}
                check("all_action_refs_captured", set(refs) == {1, 2, 3, 4, 5})
                visible = tool(session, emit("[r['ref'] for r in animation_refs()['records']]"), "list-model-visible")
                check("list_ipc_equals_callback", visible == list(refs.values()))
                old_ref = refs[2]

                def exact_read(label):
                    before = session.state_path.read_bytes()
                    raw = callback(session, "get", ref=old_ref)
                    hashes = [digest(np.array(f["grid"], dtype=np.uint8).tobytes()) for f in raw["frames"]]
                    expected_hashes = [digest(f.tobytes()) for f in oracle[2]["frames"]]
                    check(label + "_callback_exact_pixels", hashes == expected_hashes and raw["nonlatest"], frame_sha256=hashes)
                    json_hashes = [digest(json.dumps(f.tolist(), separators=(",", ":")).encode())
                                   for f in oracle[2]["frames"]]
                    archive_bytes = json.dumps({"before": oracle[2]["before"].tolist(),
                        "frames": [f.tolist() for f in oracle[2]["frames"]]}, separators=(",", ":")).encode()
                    check(label + "_content_hashes", [f["content_sha256"] for f in raw["frames"]] == json_hashes and
                          raw["metadata"]["archive_sha256"] == digest(archive_bytes),
                          content_sha256=json_hashes, archive_sha256=digest(archive_bytes))
                    expected_ascii = [format_grid_ascii(f.tolist()) for f in oracle[2]["frames"]]
                    body = "a=animation_at(" + repr(old_ref) + ")\n" + emit(
                        "{'status':a['status'],'pixels_equal':[f.ascii for f in a['frames']]==" + repr(expected_ascii) +
                        ",'before_equal':a['before_frame'].ascii==" + repr(format_grid_ascii(oracle[2]["before"].tolist())) +
                        ",'indices':[f.raw_frame_index for f in a['frames']],"
                        "'hashes':[f.content_sha256 for f in a['frames']],"
                        "'steps':[f.step for f in a['frames']], 'current_step':current_frame.step,"
                        "'roi':'\\n'.join(row[19:35] for row in a['frames'][2].ascii.splitlines()[13:29]),"
                        "'segmentation_readable':a['frames'][2].segmentation is not None}")
                    got = tool(session, body, label)
                    roi = "\n".join(row[19:35] for row in expected_ascii[2].splitlines()[13:29])
                    check(label + "_sandbox_exact_pixels", got["status"] == "hit" and got["pixels_equal"] and
                          got["before_equal"] and got["indices"] == list(range(7)) and
                          got["steps"] == [2] * 7 and got["hashes"] == json_hashes and
                          got["roi"] == roi and got["segmentation_readable"], result=got)
                    query_event = patch.snapshot()["recent_queries"][-1]
                    report.setdefault("seven_frame_sandbox_queries", []).append({
                        "label": label, "ipc_response_json_bytes": query_event["response_json_bytes"],
                        "sandbox_wall_seconds": report["tool_calls"][-1]["elapsed_seconds"],
                        "model_visible_output_chars": report["tool_calls"][-1]["output_chars"],
                        "timeout_seconds": session.analyzer._python_timeout})
                    check(label + "_current_state_unchanged", session.state_path.read_bytes() == before and
                          got["current_step"] == session.action_count)

                exact_read("old-after-following-actions")
                one = tool(session, "a=animation_at(" + repr(refs[5]) + ")\n" + emit("{'status':a['status'],'count':len(a['frames'])}"), "single-frame")
                check("single_frame_is_stored", one == {"status": "hit", "count": 1})
                query_status(session, {**old_ref, "action_num": 999}, "wrong-action", "missing")
                query_status(session, {**old_ref, "attempt": 1}, "wrong-attempt", "wrong_attempt")
                query_status(session, {**old_ref, "session_id": "foreign"}, "wrong-session", "wrong_scope")
                query_status(session, {**old_ref, "game_id": "foreign"}, "wrong-game", "wrong_scope")
                query_status(session, {"action_num": 2}, "invalid-ref", "invalid_ref")
                tool(session, "action('RESET')", "real-reset")
                after_reset = callback(session, "list", limit=16)
                reset_meta = after_reset["records"][-1]
                check("real_reset_new_attempt", after_reset["attempt"] == 1 and
                      reset_meta["ref"]["attempt"] == 1 and reset_meta["ref"]["action_num"] == 6,
                      metadata=reset_meta)
                exact_read("old-after-reset")
                query_status(session, {**old_ref, "attempt": 1}, "old-action-not-in-new-attempt", "wrong_attempt")
                other = new_session("independent-public-tn36")
                query_status(other, old_ref, "cross-real-session", "wrong_scope")
                no_actions = callback(other, "list", limit=16)
                check("independent_session_empty", no_actions["records"] == [] and other.action_count == 0)
                check("api_note_is_present", "animation_at(ref)" in session.analyzer._system_prompt)
                # Existing baseline function persistence, enabled only for this
                # compatibility probe; no model-generated helper is executed.
                os.environ["ARC3_PERSISTENT_FUNCTIONS"] = "1"
                tool(session, "def archived_frame_count(ref):\n    return len(animation_at(ref)['frames'])",
                     "retain-helper-definition")
                retained = tool(session, emit("archived_frame_count(" + repr(old_ref) + ")"), "retained-helper-next-snippet")
                check("retained_helper_resolves_new_api", retained == 7 and
                      "archived_frame_count" in session.analyzer._kept_functions)
                report["compatibility_probe_environment"] = {"ARC3_PERSISTENT_FUNCTIONS": "1"}
            else:
                check("disabled_no_patch_attribute", not hasattr(ToolAgent, "_research_retrievable_animation_patch"))
                check("disabled_no_api_note", "animation_at(ref)" not in session.analyzer._system_prompt)
            os.environ["ARC3_ANIMATION"] = "0"
            visibility_code = (
                "try:\n    last_animation_frames\n    frames_present=True\nexcept NameError:\n    frames_present=False\n"
                "try:\n    last_animation_timeline\n    timeline_present=True\nexcept NameError:\n    timeline_present=False\n"
                "try:\n    animation_refs\n    archive_present=True\nexcept NameError:\n    archive_present=False\n"
                "archive_status=None\n")
            if patch is not None:
                visibility_code += "archive_status=animation_at(" + repr(old_ref) + ")[\"status\"]\n"
            off = tool(session, visibility_code + emit(
                "{'latest_frames':frames_present,'latest_timeline':timeline_present,"
                "'archive':archive_present,'archive_status':archive_status}"), "legacy-animation-disabled")
            check("legacy_disabled_visibility_preserved", not off["latest_frames"] and not off["latest_timeline"] and
                  off["archive"] == (patch is not None) and
                  off["archive_status"] == ("hit" if patch is not None else None), result=off)
            report["legacy_animation_disabled_probe"] = off
            os.environ["ARC3_ANIMATION"] = "1"
            oracle_data = {f"step_{n}_before": v["before"] for n, v in oracle.items()}
            oracle_data.update({f"step_{n}_frames": np.stack(v["frames"]) for n, v in oracle.items()})
            np.savez_compressed(out / "public-observation-oracle.npz", **oracle_data)
            report["public_observations"] = [{"action_num": n, "frames": len(v["frames"]),
                "frame_sha256_uint8": [digest(f.tobytes()) for f in v["frames"]]} for n, v in oracle.items()]
            report["generated_tokens"] = session.analyzer.generated_tokens
        check("no_http_or_model", report["http_calls_blocked"] == 0)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        for run in runs:
            run.close()
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-path", type=Path, required=True)
    parser.add_argument("--extra-python-path", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--worker", choices=("baseline", "candidate", "boundaries"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.output_dir is None:
        args.output_dir = ROOT / "experiments/010-integration-checks" / datetime.now(timezone.utc).strftime("cpu-%Y%m%dT%H%M%SZ")
    args.output_dir = args.output_dir.resolve()
    if args.worker:
        worker(args)
        return
    args.output_dir.mkdir(parents=True, exist_ok=False)
    statuses = []
    for name in ("baseline", "candidate", "boundaries"):
        command = [sys.executable, str(Path(__file__).resolve()), "--sdk-path", str(args.sdk_path),
                   "--output-dir", str(args.output_dir), "--worker", name]
        for path in args.extra_python_path:
            command.extend(["--extra-python-path", str(path)])
        result = subprocess.run(command, text=True, capture_output=True, timeout=120)
        (args.output_dir / (name + ".stdout.txt")).write_text(result.stdout)
        (args.output_dir / (name + ".stderr.txt")).write_text(result.stderr)
        statuses.append({"worker": name, "exit_code": result.returncode, "command": command})
    reports = {name: json.loads((args.output_dir / name / "report.json").read_text())
               for name in ("baseline", "candidate", "boundaries")}
    latest_equal = reports["baseline"].get("original_latest_observations") == reports["candidate"].get("original_latest_observations")
    final_sources = source_hashes()
    sources_equal = all(r["source_sha256"] == final_sources for r in reports.values())
    summary = {"status": "passed" if all(r["exit_code"] == 0 for r in statuses) and latest_equal and sources_equal else "failed",
               "workers": statuses, "source_sha256": final_sources,
               "worker_source_sha256_equal": sources_equal,
               "baseline_candidate_latest_interface_exact_match": latest_equal,
               "check_count": sum(len(r["checks"]) for r in reports.values()),
               "limitations": ["Handwritten CPU probes verify delivery, not model adoption or score gains.",
                   "One public game and explicit RESET; no real level transition, game-over autoreset, model benchmark or production concurrency.",
                   "Capacity and malformed-frame cases are synthetic; exact stored JSON byte limits are not process RSS limits.",
                   "Disabled means a separate original process that does not install the patch; no in-process uninstall is claimed.",
                   "Sandbox equality probes embed saved oracle ASCII for manual validation; model-selected cropping/interpretation is unmeasured."]}
    write_json(args.output_dir / "summary.json", summary)
    write_json(args.output_dir.parent / "latest.json", {"summary": str((args.output_dir / "summary.json").relative_to(ROOT)),
        "status": summary["status"], "sha256": digest((args.output_dir / "summary.json").read_bytes())})
    print(json.dumps({"status": summary["status"], "summary": str(args.output_dir / "summary.json"), "checks": summary["check_count"]}))
    if summary["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
