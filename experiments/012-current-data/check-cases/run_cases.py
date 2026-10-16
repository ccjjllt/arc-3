#!/usr/bin/env python3
"""Handwritten saved-observation CPU probes through the real harness sandbox.

Run baseline and candidate in separate processes. The session's game carrier is
artificial and contains one saved public observation; no environment is started,
no game action/model/HTTP call is allowed, and no historical tool code executes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
CASES = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def value_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--sdk-path", type=Path, required=True)
    parser.add_argument("--extra-python-path", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    out = args.output_dir or CASES / (datetime.now(timezone.utc).strftime("cpu-%Y%m%dT%H%M%SZ-") + args.arm)
    out.mkdir(parents=True, exist_ok=False)
    sys.path[:0] = [str(args.sdk_path), str(ROOT / "src"),
        str(ROOT / "research/runtime-bundle/src/ARC3-Inference"),
        str(ROOT / "research/runtime-bundle/src/tufa-arc-agi-framework/src")]
    sys.path.extend(str(path) for path in args.extra_python_path)
    os.environ.update(LOCAL_ANALYZER_MODEL_ID="cpu-no-model", ARC3_PERSISTENT_FUNCTIONS="1",
        ARC3_PERSISTENT_FUNCTIONS_SCOPE="game", ARC3_PERSISTENT_FUNCTIONS_IMPORTS="1",
        ARC3_ANIMATION="1", MPLCONFIGDIR="/private/tmp/arc3-012-mpl", MPLBACKEND="Agg")
    import numpy as np
    import requests
    from inference.agent.tool_agent import ToolAgent
    from inference.framework.solver import HarnessSolver, _HarnessGameSession

    blocked = {"http": 0, "actions": 0}

    def no_http(*args, **kwargs):
        blocked["http"] += 1
        raise RuntimeError("CPU data probe forbids HTTP")

    def no_action(*args, **kwargs):
        blocked["actions"] += 1
        raise RuntimeError("CPU data probe forbids game actions")

    requests.sessions.Session.request = no_http
    patch = None
    if args.arm == "candidate":
        from arc3_research.current_data import install_current_data
        patch = install_current_data()
    report = {"arm": args.arm, "cases": [], "python": sys.executable,
              "python_version": sys.version, "sdk_path": str(args.sdk_path),
              "extra_python_paths": [str(path) for path in args.extra_python_path],
              "source_sha256": {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__).read_bytes())},
              "model_called": False, "gpu_started": False, "engine_started": False,
              "logged_code_executed": False,
              "session_scope": "Artificial session carrier, one public saved frame; not a restored historical game or SDK execution."}
    for relative in ("research/runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py",
                     "research/runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py",
                     "research/runtime-bundle/src/ARC3-Inference/inference/framework/solver.py",
                     "experiments/011-evidence-reuse/checks.json"):
        report["source_sha256"][relative] = digest((ROOT / relative).read_bytes())
    if patch:
        report["source_sha256"]["src/arc3_research/current_data.py"] = digest((ROOT / "src/arc3_research/current_data.py").read_bytes())

    def dispatch(session, code, label, directory):
        before = session.state_path.read_bytes()
        result = session.analyzer._run_python_tool(session.state_path, {"code": code})
        payload = json.loads(result.content)
        artifact = {"label": label, "handwritten_code": code, "dispatch": payload,
                    "step_executed": result.step_executed, "made_progress": result.made_progress,
                    "state_file_unchanged": session.state_path.read_bytes() == before}
        write(directory / (label + ".json"), artifact)
        if payload.get("error"):
            raise AssertionError(payload["error"])
        assert not result.step_executed and artifact["state_file_unchanged"]
        lines = [line[7:] for line in payload.get("stdout", "").splitlines() if line.startswith("RESULT=")]
        assert len(lines) == 1, payload
        return json.loads(lines[0])

    suffix = "\nimport json\nprint('RESULT='+json.dumps(output,separators=(',',':')))\n"
    try:
        prior = json.loads((ROOT / "experiments/011-evidence-reuse/checks.json").read_text())
        for name in ("cd82", "ft09"):
            directory = out / name
            directory.mkdir()
            snapshot = json.loads((CASES / name / "source-frame.json").read_text())
            compute = (CASES / name / "compute.py").read_text()
            consume = (CASES / name / "consume.py").read_text()
            for file in ("source-frame.json", "compute.py", "consume.py"):
                path = CASES / name / file
                report["source_sha256"][str(path.relative_to(ROOT))] = digest(path.read_bytes())
            assert digest(Path(snapshot["source_path"]).read_bytes()) == snapshot["source_sha256"]
            assert digest(json.dumps(snapshot["grid"], separators=(",", ":")).encode()) == snapshot["frame_sha256_canonical_grid_json"]
            original_event = json.loads(Path(snapshot["source_path"]).read_text().splitlines()[snapshot["source_line"] - 1])
            assert original_event["board"] == snapshot["grid"]
            assert original_event["action_num"] == snapshot["action_num"]
            assert original_event["level"] == snapshot["level"]
            pixels = np.array(snapshot["grid"], dtype=np.int8)
            state = SimpleNamespace(frame=SimpleNamespace(data=pixels),
                                    raw=SimpleNamespace(frame=[pixels]),
                                    levels_completed=snapshot["level"] - 1, won=False)
            game = SimpleNamespace(game_id="cpu-saved-observation-" + name,
                game_run=SimpleNamespace(game_id="cpu-saved-observation-" + name,
                                         history=[None] * snapshot["action_num"]),
                current_state=state, number_of_levels=snapshot["level"], execute_action=no_action)
            analyzer = ToolAgent(model="cpu-no-model")
            solver = HarnessSolver(model="cpu-no-model", start_local_server=False, kaggle_enable_vllm=False)
            session = _HarnessGameSession(solver=solver, game=game, analyzer=analyzer,
                game_index=0, pass_index=0, state_path=directory / "runtime-state.json",
                transcript_path=directory / "unused-transcript.md", analysis_html_relpath="unused.html",
                stop_event=threading.Event(), viewer_data_path=directory / "unused-viewer.json")
            session.seed_initial_history()
            session.write_runtime_state()
            analyzer._step_env_callback = session.step_env
            if args.arm == "baseline":
                first = dispatch(session, compute + "\noutput={'computed':measurement}" + suffix,
                                 "snippet1-compute", directory)
                second_code = (
                    "try:\n    measurement\n    local_variable_survived=True\n"
                    "except NameError:\n    local_variable_survived=False\n"
                    "recomputed=compute_measurement(current_frame)\n"
                    "output={'local_variable_survived':local_variable_survived,'recomputed':recomputed}")
                second = dispatch(session, second_code + suffix, "snippet2-recompute", directory)
                assert second["local_variable_survived"] is False
                assert first["computed"] == second["recomputed"]
                assert "compute_measurement" in analyzer._kept_functions
                result = {"ordinary_value_survived": False, "retained_pure_function_recompute_equal": True}
            else:
                first_code = "binding_before=current_data.context()['context']\n" + compute
                first_code += "\nack=current_data.put('measurement',measurement,at=binding_before)\noutput={'computed':measurement,'put_ack':ack}"
                first = dispatch(session, first_code + suffix, "snippet1-compute-put", directory)
                assert first["put_ack"]["status"] == "stored"
                second = dispatch(session, consume + "\noutput=consumed" + suffix,
                                  "snippet2-get-consume", directory)
                assert first["computed"] == second["value"]
                hashes = {"computed": value_digest(first["computed"]),
                          "host_ack": first["put_ack"]["value_sha256"],
                          "retrieved": value_digest(second["value"])}
                assert len(set(hashes.values())) == 1
                result = {"put_ack_status": first["put_ack"]["status"], "retrieved_value_equal": True,
                          "value_hashes": hashes, "all_three_value_hashes_equal": True,
                          "consumer": {k: v for k, v in second.items() if k != "value"}}
            value = first["computed"]
            if name == "cd82":
                bb = value["bbox_tlbr_inclusive"]
                observed = [bb[0], bb[2], bb[1], bb[3], value["pixel_count"]]
                assert observed == prior["cd82_gray_value_scan_result_rowmin_rowmax_colmin_colmax_count"]
            else:
                assert value["selected"]["logical_row_col"][1] == prior["ft09_literal_column_index"]
            result.update(case=name, computed=value, agrees_with_prior_independent_pixel_or_literal_check=True,
                          generated_tokens=analyzer.generated_tokens,
                          source_frame_equal_to_original_event=True,
                          value_sha256_canonical_sorted_json=value_digest(value))
            report["cases"].append(result)
        assert blocked == {"http": 0, "actions": 0}
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        report["blocked_calls"] = blocked
        if patch:
            report["current_data_diagnostics"] = patch.snapshot()
        report["trace_sha256"] = {str(path.relative_to(out)): digest(path.read_bytes())
                                  for path in sorted(out.glob("*/*.json"))}
        write(out / "report.json", report)
    print(json.dumps({"status": report["status"], "arm": args.arm, "report": str((out / "report.json").resolve())}))


if __name__ == "__main__":
    main()
