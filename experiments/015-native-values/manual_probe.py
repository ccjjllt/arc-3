"""Hand-authored CPU contracts; no model/engine/history-code execution."""
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import types

from codec import NativeValueError, capture_namespace, decode_values, encode_values
from prototype import NativeStore, Observation, copied_runner, SyntheticSession


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
REPORT = {"scope": __doc__, "checks": [], "sandbox_calls": [],
          "model_requests": 0, "gpu_started": False, "game_engine_executed": False,
          "historical_model_code_executed": False, "python": sys.version,
          "python_executable": sys.executable}


def write():
    (OUT / "cpu-report.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n")


def check(name, condition, **detail):
    REPORT["checks"].append({"name": name, "passed": bool(condition), **detail})
    write()
    if not condition:
        raise AssertionError(name)


def rejected(name, function):
    try:
        function()
    except NativeValueError as exc:
        check(name, True, reason=str(exc))
    else:
        check(name, False)


def run(session, label, code, **kwargs):
    before = time.perf_counter()
    result = session.run(code, **kwargs)
    elapsed = time.perf_counter() - before
    REPORT["sandbox_calls"].append({"label": label, "code": code, "elapsed_seconds": elapsed,
                                     **result})
    write()
    return result


def main():
    started = time.perf_counter()
    REPORT["source_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (OUT / "codec.py", OUT / "prototype.py", Path(__file__))}
    values = {"none": None, "truth": True, "integer": 1, "negative": -999,
              "float_value": -0.0, "text": "中文", "list_value": [1, (2, 3)],
              "tuple_value": (1, 2), "dict_value": {(1, 2): {3, 4}, 8: frozenset((5, 6))}}
    got = decode_values(encode_values(values))
    check("all_supported_types", got == values and all(type(got[k]) is type(v) for k, v in values.items()))
    check("negative_zero", math.copysign(1, got["float_value"]) == -1)
    check("tuple_dict_keys_and_frozenset", type(next(iter(got["dict_value"]))) is tuple
          and type(got["dict_value"][8]) is frozenset)
    a = [1, 2]
    source = {"a": a, "b": a, "nested": {"c": a}}
    got = decode_values(encode_values(source))
    check("shared_container_alias_preserved", got["a"] is got["b"] is got["nested"]["c"])
    got["a"].append(3)
    check("snapshot_copy_isolated_from_source", a == [1, 2] and got["b"] == [1, 2, 3])
    cyc = []; cyc.append(cyc)
    invalid = {"cycle": cyc, "callable": lambda: 1, "module": types,
               "object": object(), "bytes": b"no", "complex": 1j,
               "nan": float("nan"), "inf": float("inf"), "surrogate": "\ud800",
               "int_limit": 1 << 4097, "string_limit": "x" * 16385,
               "node_limit": [0] * 4097}
    for label, value in invalid.items():
        rejected("reject_" + label, lambda value=value: encode_values({"x": value}))
    protocols = []
    class HostileList(list):
        def __iter__(self): protocols.append("iter"); raise RuntimeError()
        def __len__(self): protocols.append("len"); raise RuntimeError()
        def __reduce__(self): protocols.append("reduce"); raise RuntimeError()
        def __repr__(self): protocols.append("repr"); raise RuntimeError()
    rejected("exact_builtin_only", lambda: encode_values({"x": HostileList([1])}))
    check("custom_protocols_never_called", not protocols)
    deep = 1
    for _ in range(17): deep = [deep]
    rejected("depth_limit", lambda: encode_values({"x": deep}))
    shared = [1]
    deep = shared
    for _ in range(16): deep = [deep]
    rejected("alias_cannot_hide_depth", lambda: encode_values({"short": shared, "long": deep}))
    rejected("name_limit", lambda: encode_values({"v" + str(i): i for i in range(33)}))
    rejected("aggregate_byte_limit", lambda: encode_values({"v" + str(i): "x" * 15000 for i in range(5)}))
    rejected("reserved_dunder_name", lambda: encode_values({"__builtins__": 7}))
    rejected("nonfinite_wire", lambda: decode_values(b'{"version":1,"roots":[["x",["f","nan"]]],"nodes":[]}'))
    rejected("cycle_wire", lambda: decode_values(b'{"version":1,"roots":[["x",["r",0]]],"nodes":[["list",[["r",0]]]]}'))
    rejected("unknown_wire_tag", lambda: decode_values(b'{"version":1,"roots":[["x",["pickle","abc"]]],"nodes":[]}'))
    rejected("duplicate_wire_key", lambda: decode_values(b'{"version":1,"roots":[["x",["r",0]]],"nodes":[["dict",[[["i","1"],["n"]],[["b",true],["n"]]]]]}'))
    blob, excluded = capture_namespace({"current_frame": [1], "x": 4, "f": lambda: 1}, {"current_frame"})
    check("reserved_and_callable_excluded", decode_values(blob) == {"x": 4}
          and excluded == [{"name": "f", "reason": "unsupported_type"}])

    observation = Observation("s1", 0, 1, 1, "0" * 64)
    for field, value in (("session", "s2"), ("attempt", 1), ("action", 2),
                         ("level", 2), ("frame_sha256", "1" * 64), ("revision", 1)):
        store = NativeStore(); ticket, _ = store.begin(observation)
        store.finish(ticket, observation, successful=True, blob=encode_values({"x": 1}))
        _, restored = store.begin(replace(observation, **{field: value}))
        check("identity_change_clears_" + field, decode_values(restored) == {})
    store = NativeStore(); ticket, _ = store.begin(observation)
    ack = store.finish(ticket, observation, successful=True, blob=encode_values({"x": 1}))
    check("host_commit", ack["committed"])
    check("old_ticket_cannot_commit", store.finish(ticket, observation, successful=True,
          blob=encode_values({"x": 9}))["reason"] == "stale_ticket")
    ticket, _ = store.begin(observation)
    rejected_ack = store.finish(ticket, observation, successful=False, blob=encode_values({"x": 9}))
    check("error_rolls_back_prior_committed_snapshot", not rejected_ack["committed"]
          and decode_values(store.blob) == {"x": 1})
    ticket, _ = store.begin(observation)
    ack = store.finish(ticket, observation, successful=True, blob=None)
    check("successful_capture_failure_clears_prior_names", ack["reason"] == "invalid_snapshot_cleared"
          and decode_values(store.blob) == {})

    runner, metadata = copied_runner(ROOT)
    REPORT["runner"] = metadata
    s = SyntheticSession(runner)
    out = run(s, "create-values", "xs=[1,2]\nalias=xs\nclicks=[(3,4),(5,6)]\nlookup={(1,2):{3,4}}\nfrozen=frozenset([8,9])")
    check("real_sandbox_commit", out["commit"]["committed"], error=out["result"].get("error"))
    out = run(s, "consume-natural-names", "xs.append(7)\nprint(alias is xs,clicks[0],lookup[(1,2)],type(frozen).__name__)\ndel clicks\nxs=11")
    check("natural_names_alias_and_types", not out["result"].get("error") and "True (3, 4)" in out["result"]["stdout"])
    values = decode_values(s.store.blob)
    check("delete_and_rebind_replace_snapshot", "clicks" not in values and values["xs"] == 11 and values["alias"] == [1, 2, 7])
    out = run(s, "error-after-mutation", "alias.append(99)\nnew_value=6\nraise RuntimeError('expected')")
    check("real_error_no_partial_commit", out["commit"]["reason"] == "snippet_failed"
          and decode_values(s.store.blob)["alias"] == [1, 2, 7] and "new_value" not in decode_values(s.store.blob))
    out = run(s, "timeout-after-mutation", "alias.append(99)\nwhile True: pass", timeout=1)
    check("real_timeout_no_partial_commit", not out["commit"]["committed"] and "timed out" in out["result"].get("error", "")
          and decode_values(s.store.blob)["alias"] == [1, 2, 7])
    out = run(s, "unsupported-rebind-removes-old", "xs=lambda:4\nsaved_frame=current_frame\nimport math")
    check("unsupported_rebind_does_not_resurrect", "xs" not in decode_values(s.store.blob))
    check("frames_modules_callables_absent", not ({"saved_frame", "math", "xs"} & set(decode_values(s.store.blob))))
    out = run(s, "pure-function-and-data-dependent-function", "offset=5\ndef pure(x):\n    return x+1\ndef dependent(x):\n    return x+offset")
    check("original_retention_contract", [v["name"] for v in out["result"]["keepable_functions"]] == ["pure"]
          and any(r["name"] == "dependent" and "offset" in r["reason"] for r in out["result"]["retention_rejected"]))
    out = run(s, "restored-functions-and-values", "print(pure(offset))")
    check("pure_function_can_consume_explicit_restored_argument", out["result"]["stdout"].strip() == "6")
    previous = s.store.blob
    out = run(s, "refused-action-no-commit", "offset=99\naction('ACTION1')", action_mode="refuse")
    check("refusal_preserves_previous_but_no_commit", out["commit"]["reason"] == "action_requested" and s.store.blob == previous)
    out = run(s, "executed-noop-invalidates", "action('ACTION1')\nafter_action=123")
    check("executed_noop_clears_snapshot_and_skips_commit", out["executed_actions"] == 1
          and decode_values(s.store.blob) == {} and not out["commit"]["committed"])
    out = run(s, "old-value-not-restored-after-action", "print(offset)")
    check("post_action_nameerror_expected", "NameError" in out["result"].get("error", ""))
    run(s, "create-before-reset", "before_reset=42")
    before = s.current.attempt
    out = run(s, "reset-invalidates", "action('RESET')")
    check("reset_increments_attempt_and_clears", s.current.attempt == before + 1 and decode_values(s.store.blob) == {})
    run(s, "create-before-uncertain-action", "before_uncertain=42")
    out = run(s, "uncertain-action-invalidates", "action('ACTION1')", action_mode="uncertain")
    check("uncertain_action_clears", decode_values(s.store.blob) == {} and not out["commit"]["committed"])
    run(s, "create-before-action-timeout", "before_timeout=42")
    out = run(s, "action-then-timeout", "action('ACTION1')\nwhile True: pass", timeout=1)
    check("action_then_timeout_stays_cleared", out["executed_actions"] == 1
          and "timed out" in out["result"].get("error", "") and decode_values(s.store.blob) == {})
    check("no_action_replay", s.action_calls == 5)
    original = sys.modules["_native015_original_sandbox"]
    baseline = original.run_sandboxed_python(code="ephemeral=123", timeout_seconds=2,
        initial_state={"history": [], "valid_actions": []}, action_handler=lambda *a, **k: {})
    check("original_runner_not_mutated", "native_values" not in baseline)
    REPORT["elapsed_seconds"] = time.perf_counter() - started
    REPORT["passed"] = sum(c["passed"] for c in REPORT["checks"])
    REPORT["total"] = len(REPORT["checks"])
    write()
    print(json.dumps({"passed": REPORT["passed"], "total": REPORT["total"],
                      "sandbox_calls": len(REPORT["sandbox_calls"]), "elapsed_seconds": REPORT["elapsed_seconds"]}))


if __name__ == "__main__":
    try:
        main()
    finally:
        write()
