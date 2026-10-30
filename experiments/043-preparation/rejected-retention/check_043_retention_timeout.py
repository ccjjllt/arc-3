#!/usr/bin/env python3
"""Check 043 with a real local sandbox timeout and the real recorder method.

No model/GPU, network, competition actions or scoring are involved. Only the
recorder's environment-configuration getters are substitutes. The sandbox,
function validator and recorder source come from the existing runtime bundle.
"""
from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "research/runtime-bundle/src/ARC3-Inference"
sys.path.insert(0, str(BUNDLE))
from inference.agent.python_tool_sandbox import run_sandboxed_python
from inference.utils.retained_functions import function_signature

spec = importlib.util.spec_from_file_location(
    "retention_timeout_guard", ROOT / "src/arc3_research/retention_timeout_guard.py"
)
patch = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(patch)


def recorder(source: str, enabled: bool = True, scope: str = "game"):
    module = ast.parse(source)
    cls = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == "ToolAgent")
    method = copy.deepcopy(next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                                and n.name == "_record_retained_functions"))
    module = ast.Module(body=[method], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        "_persistent_functions": lambda: enabled,
        "_persistent_functions_scope": lambda: scope,
        "_get_env_bool": lambda name, default: default,
        "function_signature": function_signature,
    }
    exec(compile(module, "<actual-retention-recorder>", "exec"), namespace)
    return namespace["_record_retained_functions"]


def call_record(fn, report, kept):
    obj = SimpleNamespace(_kept_functions=copy.deepcopy(kept))
    payload = {}
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        fn(obj, report, payload)
    return obj._kept_functions, payload, output.getvalue()


def main():
    original = (BUNDLE / patch.RELATIVE_TARGET).read_text()
    checks = {}
    with tempfile.TemporaryDirectory(prefix="arc043-check-") as temporary:
        target = Path(temporary) / patch.RELATIVE_TARGET
        target.parent.mkdir(parents=True)
        target.write_text(original)
        install = patch.install_retention_timeout_guard(Path(temporary))
        modified = target.read_text()
        checks["exactly_one_source_replacement"] = modified == original.replace(
            patch.ORIGINAL, patch.REPLACEMENT, 1
        ) and install["matched"] == 1
        for name, content in [("already_installed", modified),
                              ("missing_anchor", original.replace(patch.ORIGINAL, "", 1)),
                              ("duplicated_anchor", original + patch.ORIGINAL)]:
            target.write_text(content)
            try:
                patch.install_retention_timeout_guard(Path(temporary))
            except RuntimeError:
                checks[name + "_fails_before_write"] = target.read_text() == content
            else:
                checks[name + "_fails_before_write"] = False

    old_fn, new_fn = recorder(original), recorder(modified)
    helpers = {"helper": "def helper(x):\n    return x + 1\n"}
    state = {"current_frame": {"grid": [[0, 0], [0, 0]], "level": 1, "step": 1},
             "history": [], "transitions": [], "valid_actions": []}

    def sandbox(code, kept, timeout=3):
        return run_sandboxed_python(
            code=code, timeout_seconds=timeout, initial_state=state,
            action_handler=lambda *args, **kwargs: {}, kept_functions=list(kept.values()),
            retain_imports=True,
        )

    timeout = sandbox("while True:\n    pass", helpers, timeout=1)
    checks["real_timeout_report_has_no_retention_field"] = (
        "timed out" in timeout["error"] and "keepable_functions" not in timeout
        and timeout["action_results"] == []
    )
    old, old_payload, _ = call_record(old_fn, timeout, helpers)
    new, new_payload, log = call_record(new_fn, timeout, helpers)
    checks["old_timeout_discards_known_helper"] = old == {}
    checks["new_timeout_preserves_known_helper"] = new == helpers
    checks["count_only_log"] = log == "[043-retention] preserved_functions=1\n"
    lost = sandbox("print(helper(2))", old)
    recovered = sandbox("print(helper(2))", new)
    checks["real_reuse_baseline_nameerror_candidate_success"] = (
        "NameError" in lost["error"] and recovered["stdout"].strip() == "3"
        and not recovered["error"]
    )
    rows = []
    cases = [
        ("transport_failure_missing", {"error": "Sandbox process returned invalid response."}, helpers),
        # Protocol-unreachable in the current sandbox, but documents missing-field semantics.
        ("missing_without_error", {"stdout": "", "action_results": []}, helpers),
        ("explicit_empty", {"keepable_functions": []}, {}),
        ("explicit_none", {"keepable_functions": None}, {}),
        ("invalid_metadata", {"keepable_functions": [{"name": "helper", "source": "bad"}]}, {}),
        ("completed_new", {"keepable_functions": [{"name": "new", "source": "def new(x):\n return x * 2\n"}]},
         {"new": "def new(x):\n return x * 2\n"}),
        ("malformed_non_dictionary", None, {}),
    ]
    for name, data, expected in cases:
        kept, payload, output = call_record(new_fn, data, helpers)
        checks[name] = kept == expected
        if "keepable_functions" in (data or {}) or data is None:
            checks[name + "_unchanged_from_original"] = (
                (kept, payload, output) == call_record(old_fn, data, helpers)
            )
        rows.append({"name": name, "kept_names": sorted(kept), "payload": payload, "log": output})
    checks["missing_and_no_previous_functions_unchanged"] = (
        call_record(old_fn, timeout, {}) == call_record(new_fn, timeout, {})
    )
    checks["disabled_is_unchanged"] = (
        call_record(recorder(original, False), timeout, helpers)
        == call_record(recorder(modified, False), timeout, helpers)
    )
    for scope in ("game", "levelup", "turn"):
        kept, _, _ = call_record(recorder(modified, scope=scope), timeout, helpers)
        checks["existing_scope_" + scope + "_keeps_last_complete_report"] = kept == helpers
    # The single exact replacement leaves session, level and turn reset methods byte-identical.
    checks["scope_reset_methods_unchanged"] = modified.replace(patch.REPLACEMENT, patch.ORIGINAL, 1) == original

    result = {
        "passed": all(checks.values()), "checks_passed": sum(checks.values()),
        "checks": checks, "install_report": install,
        "runtime_source_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "patch_sha256": hashlib.sha256(Path(patch.__file__).read_bytes()).hexdigest(),
        "real_timeout_result": timeout,
        "old_after_timeout": {"kept_names": sorted(old), "payload": old_payload, "reuse": lost},
        "new_after_timeout": {"kept_names": sorted(new), "payload": new_payload, "reuse": recovered},
        "boundary_cases": rows,
        "limitations": [
            "CPU only; no model/GPU/game actions or score measurement.",
            "Uses actual sandbox, function validator and extracted recorder method; environment getters are substitutes.",
            "One-second timeout fixture exercises the real timeout branch; production timeout remains30 seconds.",
            "Scope reset methods verified unchanged; this is not an end-to-end game lifecycle replay.",
            "Missing-without-error fixture is unreachable under the present final/error protocol, included as a contract boundary.",
        ],
    }
    out = ROOT / "experiments/043-preparation/retention-cpu-check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "checks_passed": result["checks_passed"],
                      "report": str(out), "failed": [k for k, v in checks.items() if not v]}, indent=2))
    assert result["passed"]


if __name__ == "__main__":
    main()
