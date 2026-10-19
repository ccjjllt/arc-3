#!/usr/bin/env python3
"""CPU check for the 021 checked-action path. Not a test suite and not a score.

Runs the real sandbox child. The host action handler is a fake public frame,
so this does not play a game, call a model, or use the network. A scripted
repair after mismatch shows the suffix stopped and a later action can still run.
It does not show that the model will choose to repair.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/021-checked-execution.json"
SANDBOX_FILE = (ROOT / "research/runtime-bundle/src/ARC3-Inference/"
                "inference/agent/python_tool_sandbox.py")
SANDBOX_SHA256 = "3900b7255842df04be9ad08f91b521279a2e63f8226ac4bc77fb6de7a4e36943"
COLUMN = '''
def extract(frame):
    return {"col": frame.ascii.find("X")}
def pred(values, action):
    name = action["action"]
    step = 1 if name == "RIGHT" else -1 if name == "LEFT" else 0
    return {"col": values["col"] + step}
'''


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def briefs(stdout: str) -> list[dict]:
    found = []
    for line in stdout.splitlines():
        if line.startswith("checked_execution "):
            found.append(json.loads(line[len("checked_execution "):]))
    return found


class World:
    """Public frames only. Modes name the host reply, not a game rule."""

    def __init__(self, row: str, mode: str):
        self.row = row
        self.mode = mode
        self.level = 1
        self.step = 0
        self.calls = []

    def frame(self) -> dict:
        return {"ascii": self.row, "step": self.step, "level": self.level,
                "shape": [1, len(self.row)], "grid": [[0] * len(self.row)]}

    def _move(self, name: str) -> None:
        index = self.row.find("X")
        if index < 0:
            return
        chars = list(self.row)
        if name == "RIGHT" and index + 1 < len(chars):
            chars[index], chars[index + 1] = chars[index + 1], chars[index]
        elif name == "LEFT" and index > 0:
            chars[index], chars[index - 1] = chars[index - 1], chars[index]
        self.row = "".join(chars)

    def handler(self, actions, stale_after=None):
        self.calls.append([dict(item) for item in actions])
        call_number = len(self.calls)
        if self.mode == "noop":
            return {"action_result": {
                "executed": False, "stop_reason": "known_noop", "level": self.level,
                "stop_detail": "known no-op action was not executed."},
                "state": {"current_frame": self.frame(), "history": [],
                          "valid_actions": ["RIGHT"]}}
        for action in actions:
            self.step += 1
            name = action.get("action")
            if self.mode == "wrong_on_second" and call_number == 2 and name == "RIGHT":
                self.row = "X" + self.row[1:].replace("X", ".")
            elif self.mode == "flip_edge":
                self._move(name)
                if self.row[:1] == "B":
                    self.row = "Q" + self.row[1:]
            elif self.mode != "record":
                self._move(name)
        result = {"executed": True, "level": self.level, "level_completed": False,
                  "game_over": False, "done": False, "run_complete": False,
                  "state": "NOT_FINISHED",
                  "action_echo": "[action] " + ",".join(str(item.get("action")) for item in actions)}
        if self.mode == "level_completed" and call_number == 1:
            result["level_completed"] = True
            self.level = 2
            self.row = "X...."
        elif self.mode == "game_over" and call_number == 1:
            result["game_over"] = True
            self.row = "X...."
        elif self.mode == "done" and call_number == 1:
            result["done"] = True
        elif self.mode == "silent_level" and call_number == 1:
            self.level = 2
            self.row = "X...."
        result["level"] = self.level
        return {"action_result": result,
                "state": {"current_frame": self.frame(), "history": [],
                          "valid_actions": ["RIGHT", "LEFT", "MOUSE"]}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "experiments/021-checked-execution-cpu")
    parser.add_argument("--sdk-path", type=Path, default=Path("/private/tmp/arc3-018-sdk"))
    parser.add_argument("--dependency-path", type=Path, default=Path("/private/tmp/arc3-018-check-deps"))
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {"status": "checking", "python": sys.version, "executable": sys.executable,
              "network_attempts": 0, "model_calls": 0, "game_actions": 0,
              "sandbox_calls": 0, "scenarios": [],
              "limits": [
                  "Fake public frames, not an ARC game and not a score.",
                  "The repair step is scripted in the snippet. It shows a later action can run after a stopped suffix.",
                  "No claim that a model will call pred/extract or repair.",
              ]}

    def deny_network(event, arguments):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            report["network_attempts"] += 1
            raise RuntimeError("021 CPU check prohibits network")
    sys.addaudithook(deny_network)

    sandbox_hash = hashlib.sha256(SANDBOX_FILE.read_bytes()).hexdigest()
    if sandbox_hash != SANDBOX_SHA256:
        raise RuntimeError("Frozen python_tool_sandbox.py changed; 021 must patch a copy in memory")
    report["frozen_sandbox_sha256"] = sandbox_hash

    sys.path[:0] = [str(ROOT / "src"),
                    str(ROOT / "research/runtime-bundle/src/ARC3-Inference")]
    for extra in (args.sdk_path, args.dependency_path):
        if extra.is_dir():
            sys.path.append(str(extra))
    os.environ.pop("ARC3_SYSTEM_PROMPT_PREFIX", None)
    spec = importlib.util.spec_from_file_location(
        "check018", ROOT / "scripts/check_018_grounding.py")
    check018 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check018)
    os.environ.update(check018.baseline_environment())
    if os.environ.get("ARC3_SYSTEM_PROMPT_PREFIX", "").strip():
        raise RuntimeError("Start from an empty system prefix")

    from arc3_research.checked_action import (
        CHECKED_EXECUTION_PREFIX, install_checked_execution,
    )
    from arc3_research.experiment_config import validate_config
    from inference.agent import python_tool_sandbox as sandbox
    from inference.agent import tool_agent as tool_agent

    config = json.loads(CONFIG.read_text())
    validate_config(config)
    mixed = json.loads(CONFIG.read_text())
    mixed["arm_order"] = ["baseline", "checked_execution", "grounded_state"]
    try:
        validate_config(mixed)
    except ValueError:
        report["rejects_mixed_arms"] = True
    else:
        raise RuntimeError("021 config accepted a mixed arm list")
    paced = json.loads(CONFIG.read_text())
    paced["arm_environment"]["checked_execution"]["ARC3_PRIORITY_PACE"] = "1"
    try:
        validate_config(paced)
    except ValueError:
        report["rejects_scheduler_change"] = True
    else:
        raise RuntimeError("021 config accepted a scheduler change")

    original_bootstrap = sandbox._SANDBOX_BOOTSTRAP
    agent_kwargs = dict(model="cpu-no-model", provider="vllm",
                        base_url="http://cpu.invalid/v1", api_key="cpu-not-a-secret")
    baseline_agent = tool_agent.ToolAgent(**agent_kwargs)
    patch = install_checked_execution(sandbox)
    try:
        if sandbox._SANDBOX_BOOTSTRAP == original_bootstrap:
            raise RuntimeError("Install did not change the child bootstrap")
        if hashlib.sha256(SANDBOX_FILE.read_bytes()).hexdigest() != SANDBOX_SHA256:
            raise RuntimeError("Install wrote the frozen sandbox file")
        candidate = tool_agent.ToolAgent(**agent_kwargs)
        prompt_ok = candidate._system_prompt == CHECKED_EXECUTION_PREFIX + "\n\n" + baseline_agent._system_prompt
        schema_ok = candidate._tools(out / "unused/state.json") == baseline_agent._tools(out / "unused/state.json")
        report["prompt_is_prefix_plus_baseline"] = prompt_ok
        report["tool_schema_unchanged"] = schema_ok
        report["baseline_agent_prompt_unchanged"] = baseline_agent._system_prompt != candidate._system_prompt
        if not (prompt_ok and schema_ok and report["baseline_agent_prompt_unchanged"]):
            raise RuntimeError("Prompt or tool schema changed beyond the checked-execution prefix")
        try:
            install_checked_execution(sandbox)
        except RuntimeError:
            report["rejects_double_install"] = True
        else:
            raise RuntimeError("A second install was accepted")

        def run(name, code, world):
            result = tool_agent.run_sandboxed_python(
                code=code, timeout_seconds=15,
                initial_state={"current_frame": world.frame(), "history": [],
                               "valid_actions": ["RIGHT", "LEFT", "MOUSE"],
                               "last_action_call_result": {}},
                action_handler=world.handler)
            report["sandbox_calls"] += 1
            record = {"name": name, "calls": world.calls, "error": result.get("error", ""),
                      "briefs": briefs(result.get("stdout", "")),
                      "action_result_count": len(result.get("action_results") or []),
                      "stdout": result.get("stdout", "")}
            report["scenarios"].append({key: record[key] for key in
                                        ("name", "calls", "error", "briefs", "action_result_count")})
            save(out / (name + ".json"), record)
            if report["network_attempts"]:
                raise RuntimeError("Network attempt during sandbox check")
            return record

        def expect(name, record, *, calls, brief=None, error_has=None, absent_text=None):
            if record["calls"] != calls:
                raise RuntimeError(f"{name}: calls {record['calls']!r} != {calls!r}")
            if error_has is not None and error_has not in record["error"]:
                raise RuntimeError(f"{name}: error {record['error']!r} lacks {error_has!r}")
            if error_has is None and record["error"]:
                raise RuntimeError(f"{name}: unexpected error {record['error']!r}")
            if brief is not None:
                if record["briefs"] != [brief] and not _brief_matches(record["briefs"], brief):
                    raise RuntimeError(f"{name}: brief {record['briefs']!r} != {brief!r}")
            if absent_text is not None and absent_text in record["stdout"]:
                raise RuntimeError(f"{name}: stdout unexpectedly contains {absent_text!r}")

        ordinary = run("ordinary_batch", 'action(["RIGHT", "LEFT"])\n', World("..X..", "move"))
        expect("ordinary_batch", ordinary,
               calls=[[{"action": "RIGHT"}, {"action": "LEFT"}]],
               absent_text="checked_execution")

        single = run("ordinary_string", 'action("RIGHT")\n', World("..X..", "move"))
        expect("ordinary_string", single, calls=[[{"action": "RIGHT"}]],
               absent_text="checked_execution")

        matched = run("matched_suffix", COLUMN + '''
summary = action(["RIGHT", "RIGHT"], pred=pred, extract=extract, scope="marker-col")
print("STATUS", summary["status"], summary["unattempted_suffix"])
''', World("..X..", "move"))
        expect("matched_suffix", matched,
               calls=[[{"action": "RIGHT"}], [{"action": "RIGHT"}]],
               brief={"status": "completed", "reason": "all_executed_actions_match_selected_projection",
                      "planned_actions": 2, "attempted_actions": 2, "observed_actions": 2,
                      "unattempted_suffix": 0, "comparison": "match", "diffs": [], "error": None})
        if "STATUS completed 0" not in matched["stdout"]:
            raise RuntimeError("matched suffix did not report completion to the snippet")

        repair = run("mismatch_then_repair", COLUMN + '''
summary = action(["RIGHT", "RIGHT", "RIGHT"], pred=pred, extract=extract, scope="marker-col")
print("STATUS", summary["status"], summary["attempted_actions"], summary["unattempted_suffix"])
if summary["status"] == "mismatch":
    action(["LEFT"])
''', World("..X..", "wrong_on_second"))
        expect("mismatch_then_repair", repair,
               calls=[[{"action": "RIGHT"}], [{"action": "RIGHT"}], [{"action": "LEFT"}]])
        got = repair["briefs"][0]
        if (got["status"] != "mismatch" or got["attempted_actions"] != 2
                or got["unattempted_suffix"] != 1 or got["comparison"] != "mismatch"):
            raise RuntimeError(f"mismatch brief was {got!r}")
        if not any(item.get("field") == "col" for item in got["diffs"]):
            raise RuntimeError(f"mismatch did not report the col field: {got['diffs']!r}")
        if "STATUS mismatch 2 1" not in repair["stdout"]:
            raise RuntimeError("snippet did not observe the stopped suffix before the repair action")

        def boundary(name, mode, reason, same_level):
            record = run(name, COLUMN + '''
summary = action(["RIGHT", "RIGHT"], pred=pred, extract=extract, scope="marker-col")
last = summary["events"][-1]
print("LEVEL", last["before"]["level_id"], last["after"]["level_id"], last["comparison"])
''', World("..X..", mode))
            expect(name, record, calls=[[{"action": "RIGHT"}]])
            got_brief = record["briefs"][0]
            if got_brief["status"] != "boundary" or got_brief["reason"] != reason:
                raise RuntimeError(f"{name}: {got_brief!r}")
            if got_brief["comparison"] != "skipped_boundary" or got_brief["unattempted_suffix"] != 1:
                raise RuntimeError(f"{name}: suffix was not skipped before compare: {got_brief!r}")
            text = record["stdout"]
            if same_level and "LEVEL public-level:1 public-level:1" not in text:
                raise RuntimeError(f"{name}: level id changed:\n{text}")
            if not same_level and "LEVEL public-level:1 public-level:2" not in text:
                raise RuntimeError(f"{name}: new level was not public:\n{text}")
            if "mismatch" == got_brief["status"]:
                raise RuntimeError(f"{name}: boundary reported as mismatch")

        boundary("level_completed", "level_completed", "level_completed", False)
        boundary("game_over", "game_over", "game_over", True)
        boundary("run_complete", "done", "run_complete", True)
        boundary("silent_level_change", "silent_level", "level_changed", False)

        refused = run("known_noop_not_swallowed", COLUMN + '''
action(["RIGHT", "LEFT"], pred=pred, extract=extract, scope="marker-col")
''', World("..X..", "noop"))
        expect("known_noop_not_swallowed", refused, calls=[[{"action": "RIGHT"}]],
               error_has="KnownNoOpActionError")
        if refused["briefs"]:
            raise RuntimeError("known no-op was converted into a checked summary")

        undeclared = run("undeclared_pixels_do_not_stop", '''
def extract(frame):
    return {"ok": 1}
def pred(values, action):
    return {"ok": 1}
summary = action(["RIGHT", "RIGHT"], pred=pred, extract=extract, scope="declared-ok-only")
print("ROW", current_frame.ascii)
print("STATUS", summary["status"])
''', World("..X..", "move"))
        expect("undeclared_pixels_do_not_stop", undeclared,
               calls=[[{"action": "RIGHT"}], [{"action": "RIGHT"}]],
               brief={"status": "completed", "reason": "all_executed_actions_match_selected_projection",
                      "planned_actions": 2, "attempted_actions": 2, "observed_actions": 2,
                      "unattempted_suffix": 0, "comparison": "match", "diffs": [], "error": None})
        if "ROW ....X" not in undeclared["stdout"]:
            raise RuntimeError("the frame changed, so this check no longer shows an undeclared difference")

        border = run("border_field_is_compared", '''
def extract(frame):
    return {"edge": frame.ascii[0], "col": frame.ascii.find("X")}
def pred(values, action):
    step = 1 if action["action"] == "RIGHT" else 0
    return {"edge": values["edge"], "col": values["col"] + step}
action(["RIGHT", "RIGHT"], pred=pred, extract=extract, scope="edge-and-col")
''', World("B.X..", "flip_edge"))
        expect("border_field_is_compared", border, calls=[[{"action": "RIGHT"}]])
        border_brief = border["briefs"][0]
        if border_brief["status"] != "mismatch" or not any(
                item.get("field") == "edge" for item in border_brief["diffs"]):
            raise RuntimeError(f"border field was not compared: {border_brief!r}")

        click = run("click_row_col_preserved", '''
import json
seen = []
def extract(frame):
    return {"mark": "ready"}
def pred(values, action):
    seen.append({"action": action["action"], "row": action["row"], "col": action["col"]})
    return {"mark": "ready"}
action([{"action": "MOUSE", "row": 4, "col": 7}], pred=pred, extract=extract, scope="click-payload")
print("SEEN " + json.dumps(seen))
''', World("..X..", "record"))
        expect("click_row_col_preserved", click,
               calls=[[{"action": "MOUSE", "row": 4, "col": 7}]],
               brief={"status": "completed", "reason": "all_executed_actions_match_selected_projection",
                      "planned_actions": 1, "attempted_actions": 1, "observed_actions": 1,
                      "unattempted_suffix": 0, "comparison": "match", "diffs": [], "error": None})
        if 'SEEN [{"action": "MOUSE", "row": 4, "col": 7}]' not in click["stdout"]:
            raise RuntimeError("pred did not receive the click payload:\n" + click["stdout"])

        legacy = run("legacy_mouse_xy_rejected", '''
def extract(frame):
    return {"mark": "ready"}
def pred(values, action):
    return {"mark": "ready"}
action([{"action": "MOUSE", "x": 1, "y": 2}], pred=pred, extract=extract, scope="click-payload")
''', World("..X..", "record"))
        expect("legacy_mouse_xy_rejected", legacy, calls=[], error_has="row and col")

        missing = run("missing_extract_no_fallback", '''
def pred(values, action):
    return {"col": 0}
action(["RIGHT", "LEFT"], pred=pred, scope="marker-col")
''', World("..X..", "move"))
        expect("missing_extract_no_fallback", missing, calls=[], error_has="refusing unchecked fallback")

        ambiguous = run("extract_error_stops_before_action", '''
def extract(frame):
    raise RuntimeError("ambiguous marker")
def pred(values, action):
    return {"col": 0}
action(["RIGHT", "LEFT"], pred=pred, extract=extract, scope="marker-col")
''', World("..X..", "move"))
        expect("extract_error_stops_before_action", ambiguous, calls=[])
        if ambiguous["briefs"][0]["status"] != "unverifiable" or ambiguous["briefs"][0]["attempted_actions"] != 0:
            raise RuntimeError(f"extract failure was not unverifiable: {ambiguous['briefs']!r}")

        extra = run("schema_change_before_action", '''
def extract(frame):
    return {"col": 1}
def pred(values, action):
    return {"col": 1, "extra": True}
action(["RIGHT"], pred=pred, extract=extract, scope="marker-col")
''', World("..X..", "move"))
        expect("schema_change_before_action", extra, calls=[])
        if extra["briefs"][0]["status"] != "unverifiable":
            raise RuntimeError(f"schema change ran or fell back: {extra['briefs']!r}")

        too_long = run("plan_over_32_not_executed", COLUMN + '''
action(["RIGHT"] * 33, pred=pred, extract=extract, scope="marker-col")
''', World("..X..", "move"))
        expect("plan_over_32_not_executed", too_long, calls=[], error_has="bounded")

        named = run("string_action_normalized", COLUMN + '''
action("RIGHT", pred=pred, extract=extract, scope="marker-col")
''', World("..X..", "move"))
        expect("string_action_normalized", named, calls=[[{"action": "RIGHT"}]],
               brief={"status": "completed", "reason": "all_executed_actions_match_selected_projection",
                      "planned_actions": 1, "attempted_actions": 1, "observed_actions": 1,
                      "unattempted_suffix": 0, "comparison": "match", "diffs": [], "error": None})
    finally:
        if patch.active:
            patch.uninstall()
        restored = (sandbox._SANDBOX_BOOTSTRAP == original_bootstrap
                    and not hasattr(sandbox, "_research_checked_execution_patch")
                    and os.environ.get("ARC3_SYSTEM_PROMPT_PREFIX", "") == "")
        report["uninstalled"] = restored
        if not restored:
            report["status"] = "failed"
            save(out / "report.json", report)
            raise RuntimeError("Uninstall did not restore the sandbox and prefix")
        save(out / "report.json", report)

    restored_run_world = World("..X..", "move")
    restored_run = tool_agent.run_sandboxed_python(
        code='action(["UP"])\n', timeout_seconds=15,
        initial_state={"current_frame": restored_run_world.frame(), "history": [],
                       "valid_actions": ["UP"], "last_action_call_result": {}},
        action_handler=restored_run_world.handler)
    report["sandbox_calls"] += 1
    if restored_run_world.calls != [[{"action": "UP"}]] or restored_run.get("error"):
        raise RuntimeError(f"restored ordinary action failed: {restored_run_world.calls} {restored_run.get('error')}")
    if "checked_execution" in restored_run.get("stdout", ""):
        raise RuntimeError("restored sandbox still printed a checked summary")
    report["restored_ordinary_action"] = True

    preflight_report = out / "preflight.json"
    env = os.environ.copy()
    env.pop("ARC3_SYSTEM_PROMPT_PREFIX", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    env["ARC3_MAX_ACTIVE_STREAMS"] = "10"
    subprocess.run([sys.executable, "-B", "-m", "arc3_research.preflight",
                    "--bundle-dir", str(ROOT / "research/runtime-bundle"),
                    "--config", str(CONFIG), "--report", str(preflight_report)],
                   cwd=ROOT, env=env, check=True, timeout=120)
    preflight = json.loads(preflight_report.read_text())
    if preflight.get("status") != "passed" or preflight.get("network_calls") or preflight.get("game_actions"):
        raise RuntimeError(f"preflight did not pass cleanly: {preflight}")
    report["preflight"] = {key: preflight.get(key) for key in
                           ("status", "network_calls", "model_calls", "game_actions", "checks")}

    subprocess.run([sys.executable, str(ROOT / "scripts/build_experiment.py"),
                    "--config", str(CONFIG)], cwd=ROOT, check=True, timeout=120)
    notebook_path = ROOT / "notebooks/021-checked-execution/experiment.ipynb"
    notebook = json.loads(notebook_path.read_text())
    meta = json.loads((notebook_path.parent / "kernel-metadata.json").read_text())
    if meta.get("id") != "jiyujia/arc3-021-checked-execution":
        raise RuntimeError(f"kernel id is {meta.get('id')}")
    sources = []
    for cell in notebook["cells"]:
        source = cell["source"]
        sources.append("".join(source) if isinstance(source, list) else source)
    joined = "\n".join(sources)
    for name in ("checked_action.py", "checked_execution.py"):
        marker = f"%%writefile /kaggle/research/src/arc3_research/{name}\n"
        body = (ROOT / "src/arc3_research" / name).read_text()
        if marker + body not in sources:
            raise RuntimeError(f"notebook is missing the native cell for {name}")
    if "%%writefile /kaggle/research/src/arc3_research/grounded_state.py\n" in joined:
        raise RuntimeError("021 notebook bundles the 020 region patch")
    if '"checked_execution"' not in joined or "grounded_state" not in joined:
        # run_arm.py still names the older arm. The experiment config must select only 021.
        raise RuntimeError("notebook lost either the new arm name or the shared runner")
    if 'ARC3_EXPERIMENT = json.loads(' not in joined:
        raise RuntimeError("notebook has no embedded experiment config")
    import ast
    config_literal = next(source for source in sources if source.startswith("CONFIG_JSON = "))
    embedded = json.loads(ast.literal_eval(config_literal.split("\n", 1)[0].split(" = ", 1)[1]))
    if embedded["arm_order"] != ["baseline", "checked_execution"]:
        raise RuntimeError(f"embedded arms are {embedded['arm_order']}")
    if embedded["kernel_id"] != "jiyujia/arc3-021-checked-execution":
        raise RuntimeError("embedded kernel id changed")
    report["notebook"] = {"cells": len(notebook["cells"]), "kernel_id": meta["id"],
                          "sha256": hashlib.sha256(notebook_path.read_bytes()).hexdigest()}
    report["status"] = "passed"
    save(out / "report.json", report)
    print(json.dumps({"status": report["status"], "sandbox_calls": report["sandbox_calls"],
                      "scenarios": len(report["scenarios"]), "preflight": report["preflight"]["status"],
                      "notebook_sha256": report["notebook"]["sha256"]}))


def _brief_matches(found, expected) -> bool:
    if len(found) != 1:
        return False
    actual = found[0]
    for key, value in expected.items():
        if actual.get(key) != value:
            return False
    return True


if __name__ == "__main__":
    main()
