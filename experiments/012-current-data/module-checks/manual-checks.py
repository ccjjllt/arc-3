#!/usr/bin/env python3
"""Manual CPU contract diagnosis: real wrappers, synthetic game carriers only.

No SDK environment/action, model, HTTP, GPU, logged code, tests or CI is run.
Real sandbox/SDK lifecycle checks are separately owned by the root integration
script; these probes isolate strict JSON, capacity, identity and failure paths.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PYTHON_PATHS = [
    "/private/tmp/arc3-010-sdk", str(ROOT / "src"),
    str(ROOT / "research/runtime-bundle/src/ARC3-Inference"),
    str(ROOT / "research/runtime-bundle/src/tufa-arc-agi-framework/src"),
]
EXTRA_PATHS = [
    "/Users/zhaohuaxiang/ccjjllt/quant-research-lab/.venv/lib/python3.13/site-packages",
    "/Users/zhaohuaxiang/.cache/uv/archive-v0/0NYjaDD0X1HZ1p_3",
    "/Users/zhaohuaxiang/.cache/uv/archive-v0/GCIcB4ohHyKQ4LxX/lib/python3.13/site-packages",
]


def main():
    sys.path[:0] = PYTHON_PATHS
    sys.path.extend(EXTRA_PATHS)
    os.environ.update(LOCAL_ANALYZER_MODEL_ID="cpu-no-model", MPLCONFIGDIR="/private/tmp/arc3-012-mpl", MPLBACKEND="Agg")
    import requests

    def forbidden_http(*args, **kwargs):
        raise AssertionError("Manual CPU probe forbids HTTP")

    requests.sessions.Session.request = forbidden_http
    import arc3_research.current_data as module
    from inference.framework.solver import _HarnessGameSession
    patch = module.install_current_data()
    source_path = Path(module.__file__)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    results = []
    report = {"scope": __doc__, "module_sha256": source_hash, "checks": results,
              "python": sys.version, "python_executable": sys.executable,
              "python_paths": PYTHON_PATHS, "extra_paths": EXTRA_PATHS,
              "no_model_or_sdk_execution": True, "no_network": True,
              "limits": dict(patch.limits)}

    def check(name, condition, **details):
        results.append({"name": name, "passed": bool(condition), **details})
        if not condition:
            raise AssertionError(name)

    def carrier(game_id="synthetic"):
        obj = _HarnessGameSession.__new__(_HarnessGameSession)
        obj.game = NS(current_state=NS(frame=NS(data=[[1, 2], [3, 4]]), levels_completed=0, won=False),
                      number_of_levels=2, game_run=NS(game_id=game_id, history=[]))
        obj.game_index = 0
        obj.animation_record = {"fixture": "latest untouched"}
        return obj

    def query(obj, **request):
        returned = obj.step_env({"query": "current_data", **request})
        assert returned["executed"] is False
        return returned["result"]

    session = carrier()
    q = lambda **kwargs: query(session, **kwargs)
    action = NS(id=NS(name="ACTION1"))
    sentinel_exception = RuntimeError("original sentinel")
    calls = {"original": 0}

    def executed(obj, action, **kwargs):
        calls["original"] += 1
        obj.game.game_run.history.append(None)
        return {"executed": True, "action_num": obj.action_count}

    def refused(obj, action, **kwargs):
        calls["original"] += 1
        return {"executed": False}

    def after_action_error(obj, action, **kwargs):
        calls["original"] += 1
        obj.game.game_run.history.append(None)
        raise sentinel_exception

    try:
        value = {"utf8": "中文", "nested": [None, False, True, 123, 1.5, -0.0, {"x": 7}]}
        ack = q(op="put", key="main", value=value)
        read = q(op="get", key="main")
        check("exact_json_roundtrip", ack["status"] == "stored" and read["value"] == value)
        expected_hash = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        check("canonical_value_hash", ack["value_sha256"] == read["value_sha256"] == expected_hash)
        check("put_ack_never_contains_value", "value" not in ack)
        read["value"]["nested"].append("mutated local copy")
        check("get_copy_isolation", q(op="get", key="main")["value"] == value)
        value["nested"].append("mutated caller input")
        check("put_copy_isolation", q(op="get", key="main")["value"] != value)
        original_value = q(op="get", key="main")["value"]
        cyclic = []
        cyclic.append(cyclic)
        too_deep = 0
        for _ in range(17):
            too_deep = [too_deep]
        invalids = [
            ("nan", float("nan")), ("positive_inf", float("inf")), ("negative_inf", -float("inf")),
            ("tuple", (1, 2)), ("set", {1, 2}), ("object", object()), ("callable", lambda: None),
            ("numeric_dict_key", {1: "a"}), ("cycle", cyclic), ("depth17", too_deep),
            ("too_large", "x" * 16383), ("invalid_unicode", "\ud800"),
        ]
        for label, item in invalids:
            rejected = q(op="put", key="main", value=item)
            check("strict_reject_" + label, rejected["status"] == "rejected", reason=rejected.get("reason"))
            check("rejected_overwrite_preserves_" + label, q(op="get", key="main")["value"] == original_value)
        for key in (None, 7, "", "k" * 129, "中" * 43):
            check("invalid_key_" + str(type(key).__name__) + "_" + str(len(str(key))),
                  q(op="put", key=key, value=0)["status"] == "rejected")
        depth16 = 0
        for _ in range(16):
            depth16 = [depth16]
        check("depth16_allowed", q(op="put", key="depth", value=depth16)["status"] == "stored")

        identity = q(op="context")["context"]
        patch._original_execute = refused
        session._execute_action(action)
        check("unexecuted_guard_preserves_current", q(op="get", key="main")["status"] == "current")
        check("unexecuted_guard_preserves_binding", q(op="context")["context"] == identity)
        patch._original_execute = executed
        session._execute_action(action)
        after = q(op="context")["context"]
        stale = q(op="get", key="main")
        check("synthetic_identical_grid_executed_action_invalidates", stale["status"] == "stale" and "value" not in stale,
              same_frame_hash=identity["frame_sha256"] == after["frame_sha256"],
              before_action_num=identity["action_num"], after_action_num=after["action_num"])
        check("same_grid_revision_and_action_advance", after["revision"] == identity["revision"] + 1 and after["action_num"] == identity["action_num"] + 1)
        check("stale_pin_rejects_write", q(op="put", key="main", value=1, at=identity)["status"] == "stale_context")
        wrong_type_pin = dict(after, action_num=True)
        check("pin_checks_json_types_not_python_coercion", q(op="put", key="main", value=1, at=wrong_type_pin)["status"] == "stale_context")
        check("current_pin_write_succeeds", q(op="put", key="main", value=1, at=after)["status"] == "stored")
        session.game.current_state.frame.data[0][0] = 9
        check("host_frame_change_without_wrapper_detected", q(op="get", key="main")["status"] == "stale")
        session.game.current_state.frame.data[0][0] = 1
        check("frame_A_B_A_never_revives", q(op="get", key="main")["status"] == "stale")
        q(op="put", key="main", value=2)
        patch._original_execute = after_action_error
        try:
            session._execute_action(action)
        except RuntimeError as exc:
            check("post_execution_error_identity_preserved", exc is sentinel_exception)
        else:
            raise AssertionError("Expected original sentinel")
        check("post_execution_error_invalidates_same_grid", q(op="get", key="main")["status"] == "stale")
        q(op="put", key="main", value=3)
        patch._original_execute = executed
        before_reset = q(op="context")["context"]
        session._execute_action(NS(id=NS(name="RESET")))
        check("synthetic_reset_attempt_increments", q(op="context")["context"]["attempt"] == before_reset["attempt"] + 1)
        check("synthetic_reset_removes_payload", "value" not in q(op="get", key="main"))
        check("old_latest_record_untouched", session.animation_record == {"fixture": "latest untouched"})

        same_game = carrier()
        query(same_game, op="context")
        check("separate_session_same_game_does_not_share", query(same_game, op="get", key="main")["status"] == "missing")
        check("separate_session_uuid", query(same_game, op="context")["context"]["session_id"] != q(op="context")["context"]["session_id"])
        byte_session = carrier("byte-capacity")
        bq = lambda **kwargs: query(byte_session, **kwargs)
        exact_value = "x" * (16384 - 2)
        for index in range(4):
            check("exact_16KiB_value_" + str(index), bq(op="put", key=str(index), value=exact_value)["bytes"] == 16384)
        check("exact_64KiB_session", next(item for item in patch.snapshot()["sessions"] if item["binding"]["game_id"] == "byte-capacity")["stored_value_bytes"] == 65536)
        check("session_capacity_rejects_atomic", bq(op="put", key="extra", value=0) == {"status": "rejected", "reason": "session_byte_capacity"})
        check("capacity_reject_preserves_previous", bq(op="get", key="0")["value"] == exact_value)
        key_session = carrier("key-capacity")
        kq = lambda **kwargs: query(key_session, **kwargs)
        for index in range(32):
            assert kq(op="put", key=str(index), value=None)["status"] == "stored"
        check("32_keys_then_reject", kq(op="put", key="33", value=None)["reason"] == "key_capacity")
        patch._original_execute = executed
        key_session._execute_action(action)
        check("stale_metadata_counts_toward_key_capacity", kq(op="put", key="33", value=None)["reason"] == "key_capacity")
        check("existing_stale_key_can_be_rewritten", kq(op="put", key="0", value=5)["status"] == "stored")

        return_sentinel = object()
        def return_original(*args, **kwargs):
            calls["original"] += 1
            return return_sentinel
        def raise_original(*args, **kwargs):
            calls["original"] += 1
            raise sentinel_exception
        def fail_observer(*args, **kwargs):
            raise RuntimeError("diagnostic failure")
        before_calls = calls["original"]
        original_clock = module.time.thread_time
        original_end = patch._end_action
        try:
            module.time.thread_time = fail_observer
            patch._original_execute = return_original
            check("clock_failure_keeps_return_identity", session._execute_action(action) is return_sentinel)
            patch._original_execute = raise_original
            try:
                session._execute_action(action)
            except RuntimeError as exc:
                check("clock_failure_keeps_exception_identity", exc is sentinel_exception)
            else:
                raise AssertionError("Expected original error")
            module.time.thread_time = original_clock
            patch._end_action = fail_observer
            patch._original_execute = return_original
            check("maintenance_failure_keeps_return_identity", session._execute_action(action) is return_sentinel)
            patch._original_execute = raise_original
            try:
                session._execute_action(action)
            except RuntimeError as exc:
                check("maintenance_failure_keeps_exception_identity", exc is sentinel_exception)
            else:
                raise AssertionError("Expected original error")
        finally:
            module.time.thread_time = original_clock
            patch._end_action = original_end
        check("four_fault_cases_execute_exactly_four_times", calls["original"] - before_calls == 4)
        check("fault_cleanup_releases_inflight", q(op="context")["status"] == "current")
        old_session_id = q(op="context")["context"]["session_id"]
        held_sessions = [carrier("eviction-" + str(index)) for index in range(129)]
        for obj in held_sessions:
            query(obj, op="context")
        check("session_metadata_bounded_128", len(patch.snapshot()["sessions"]) == 128)
        check("old_session_get_is_evicted_without_value", q(op="get", key="main") == {"status": "session_evicted"})
        check("old_session_put_is_evicted", q(op="put", key="main", value=5) == {"status": "session_evicted"})
        check("old_session_not_resurrected", old_session_id not in [item["binding"]["session_id"] for item in patch.snapshot()["sessions"]])
        check("all_evicted_values_freed", patch.snapshot()["stored_value_bytes"] == 0)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        report["final_module_sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        report["source_unchanged"] = report["final_module_sha256"] == source_hash
        report["diagnostics"] = patch.snapshot()
        report["checks_count"] = len(results)
        report["manual_script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        command = {"cwd": str(ROOT), "argv": [sys.executable, "-B", str(Path(__file__).resolve())],
                   "scope": "Explicit manual diagnosis; not a registered test suite or CI command."}
        (OUT / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "checks": len(results), "source_sha256": source_hash,
                      "report": str(OUT / "report.json")}))


if __name__ == "__main__":
    main()
