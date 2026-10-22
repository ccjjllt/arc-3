#!/usr/bin/env python3
"""CPU check for action(step, expect=, read=). Not a score and not a model test.

A later sandbox call after a mismatch shows the host can continue. It does not
show that a model will repair the rule.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "experiments/022-expect-check.json"
SANDBOX_FILE = (ROOT / "research/runtime-bundle/src/ARC3-Inference/"
                "inference/agent/python_tool_sandbox.py")
SANDBOX_SHA256 = "3900b7255842df04be9ad08f91b521279a2e63f8226ac4bc77fb6de7a4e36943"


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def traces(stdout: str) -> list[dict]:
    found = []
    for line in stdout.splitlines():
        if line.startswith("checked_trace "):
            found.append(json.loads(line[len("checked_trace "):]))
    return found


class World:
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
        number = len(self.calls)
        if self.mode == "noop":
            return {"action_result": {"executed": False, "stop_reason": "known_noop",
                                       "level": self.level,
                                       "stop_detail": "known no-op action was not executed."},
                    "state": {"current_frame": self.frame(), "history": [], "valid_actions": ["RIGHT"]}}
        for action in actions:
            self.step += 1
            name = action.get("action")
            if self.mode == "wrong_on_second" and number == 2 and name == "RIGHT":
                self.row = "X" + self.row[1:].replace("X", ".")
            elif self.mode == "flip_edge":
                self._move(name)
                if self.row[:1] == "B":
                    self.row = "Q" + self.row[1:]
            elif self.mode != "record":
                self._move(name)
        result = {"executed": True, "level": self.level, "level_completed": False,
                  "game_over": False, "done": False, "run_complete": False,
                  "state": "NOT_FINISHED"}
        if self.mode == "level_completed" and number == 1:
            result["level_completed"] = True
            self.level = 2
        elif self.mode == "game_over" and number == 1:
            result["game_over"] = True
        result["level"] = self.level
        return {"action_result": result,
                "state": {"current_frame": self.frame(), "history": [],
                          "valid_actions": ["RIGHT", "LEFT", "MOUSE"]}}


def main() -> None:
    out = (ROOT / "experiments/022-expect-check-cpu").resolve()
    out.mkdir(parents=True, exist_ok=True)
    if hashlib.sha256(SANDBOX_FILE.read_bytes()).hexdigest() != SANDBOX_SHA256:
        raise RuntimeError("Frozen sandbox file changed")
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "research/runtime-bundle/src/ARC3-Inference")]
    for extra in (Path("/private/tmp/arc3-018-sdk"), Path("/private/tmp/arc3-018-check-deps")):
        if extra.is_dir():
            sys.path.append(str(extra))
    os.environ.pop("ARC3_SYSTEM_PROMPT_PREFIX", None)
    spec = importlib.util.spec_from_file_location("check018", ROOT / "scripts/checks/check_018_grounding.py")
    check018 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check018)
    os.environ.update(check018.baseline_environment())
    from arc3_research.checked_action import CHECKED_EXECUTION_PREFIX, install_checked_execution
    from arc3_research.experiment_config import validate_config
    from inference.agent import python_tool_sandbox as sandbox
    from inference.agent import tool_agent

    config = json.loads(CONFIG.read_text())
    validate_config(config)
    wide = json.loads(CONFIG.read_text())
    wide["games"] = wide["games"] + ["ft09-0d8bbf25"]
    try:
        validate_config(wide)
    except ValueError:
        pass
    else:
        raise RuntimeError("022 accepted more than 3 games")

    original = sandbox._SANDBOX_BOOTSTRAP
    agent_kwargs = dict(model="cpu-no-model", provider="vllm",
                        base_url="http://cpu.invalid/v1", api_key="cpu-not-a-secret")
    baseline = tool_agent.ToolAgent(**agent_kwargs)
    patch = install_checked_execution(sandbox)
    report = {"status": "checking", "scenarios": []}
    try:
        candidate = tool_agent.ToolAgent(**agent_kwargs)
        if candidate._system_prompt != CHECKED_EXECUTION_PREFIX + "\n\n" + baseline._system_prompt:
            raise RuntimeError("Prompt is not the short expect/read prefix plus baseline")
        if "pred=pred, extract=extract" in candidate._system_prompt:
            raise RuntimeError("The long 021 calling form is still in the prompt")

        def run(name, code, world):
            result = tool_agent.run_sandboxed_python(
                code=code, timeout_seconds=15,
                initial_state={"current_frame": world.frame(), "history": [],
                               "valid_actions": ["RIGHT", "LEFT", "MOUSE"],
                               "last_action_call_result": {}},
                action_handler=world.handler)
            record = {"name": name, "calls": world.calls, "error": result.get("error", ""),
                      "traces": traces(result.get("stdout", "")), "stdout": result.get("stdout", "")}
            report["scenarios"].append({k: record[k] for k in ("name", "calls", "error", "traces")})
            save(out / (name + ".json"), record)
            return record

        reader = '''
def read(frame):
    return {"col": frame.ascii.find("X")}
'''
        ordinary = run("ordinary", 'action(["RIGHT", "LEFT"])\n', World("..X..", "move"))
        if ordinary["calls"] != [[{"action": "RIGHT"}, {"action": "LEFT"}]] or ordinary["traces"] or ordinary["error"]:
            raise RuntimeError(f"ordinary action changed: {ordinary['calls']} {ordinary['error']}")

        matched = run("match", reader + '''
r = action("RIGHT", expect={"col": 3}, read=read)
print("FLAG", r.get("level_completed"))
''', World("..X..", "move"))
        if matched["error"] or matched["calls"] != [[{"action": "RIGHT"}]]:
            raise RuntimeError(f"match failed: {matched['error']} {matched['calls']}")
        if matched["traces"] != [{"entered": True, "status": "completed", "comparison": "match",
                                  "stopped": False, "attempted_actions": 1, "unattempted_suffix": 0,
                                  "diffs": [], "error": None, "corrected_in_this_call": False}]:
            raise RuntimeError(f"match trace {matched['traces']}")
        if "FLAG False" not in matched["stdout"]:
            raise RuntimeError("checked match did not return the original action result")

        mismatch = run("mismatch_stops", reader + '''
action(["RIGHT", "RIGHT", "RIGHT"], expect=[{"col": 3}, {"col": 4}, {"col": 5}], read=read)
''', World("..X..", "wrong_on_second"))
        if mismatch["calls"] != [[{"action": "RIGHT"}], [{"action": "RIGHT"}]]:
            raise RuntimeError(f"suffix was not stopped: {mismatch['calls']}")
        if "PredictionMismatch" not in mismatch["error"] or mismatch["traces"][0]["status"] != "mismatch":
            raise RuntimeError(f"mismatch was not reported: {mismatch['error'][:400]}")
        if not mismatch["traces"][0]["stopped"] or mismatch["traces"][0]["unattempted_suffix"] != 1:
            raise RuntimeError(f"stop record missing: {mismatch['traces']}")

        repair = run("repair_next_call", reader + '''
action("LEFT", expect={"col": 0}, read=read)
''', World(".X...", "move"))
        if repair["error"] or repair["traces"][0]["comparison"] != "match":
            raise RuntimeError("a later call could not run a corrected expect")

        level = run("level_not_mismatch", reader + '''
r = action(["RIGHT", "RIGHT"], expect=[{"col": 3}, {"col": 4}], read=read)
print("FLAG", r.get("level_completed"))
''', World("..X..", "level_completed"))
        if level["error"] or level["calls"] != [[{"action": "RIGHT"}]]:
            raise RuntimeError(f"level change compared or continued: {level['error']} {level['calls']}")
        if level["traces"][0]["status"] != "boundary" or level["traces"][0]["comparison"] == "mismatch":
            raise RuntimeError(f"level boundary trace {level['traces']}")
        if "FLAG True" not in level["stdout"]:
            raise RuntimeError("level completion was not returned to the snippet")

        over = run("game_over_not_mismatch", reader + '''
action("RIGHT", expect={"col": 99}, read=read)
''', World("..X..", "game_over"))
        if over["error"] or over["traces"][0]["status"] != "boundary":
            raise RuntimeError("game_over was treated as a prediction miss")

        click = run("click", '''
def read(frame):
    return {"mark": "ready"}
action([{"action": "MOUSE", "row": 4, "col": 7}], expect={"mark": "ready"}, read=read)
''', World("..X..", "record"))
        if click["calls"] != [[{"action": "MOUSE", "row": 4, "col": 7}]] or click["traces"][0]["comparison"] != "match":
            raise RuntimeError(f"click payload changed: {click['calls']}")

        missing = run("no_fallback", '''
action("RIGHT", expect={"col": 3})
''', World("..X..", "move"))
        if missing["calls"] or "refusing unchecked fallback" not in missing["error"]:
            raise RuntimeError(f"missing read fell back or ran: {missing['calls']} {missing['error']}")

        noop = run("noop", reader + '''
action(["RIGHT", "LEFT"], expect=[{"col": 3}, {"col": 2}], read=read)
''', World("..X..", "noop"))
        if noop["calls"] != [[{"action": "RIGHT"}]] or "KnownNoOpActionError" not in noop["error"]:
            raise RuntimeError("known no-op was swallowed")

        quiet = run("undeclared_pixels", '''
def read(frame):
    return 1
action(["RIGHT", "RIGHT"], expect=[1, 1], read=read)
print("ROW", current_frame.ascii)
''', World("..X..", "move"))
        if quiet["error"] or quiet["traces"][0]["comparison"] != "match" or "ROW ....X" not in quiet["stdout"]:
            raise RuntimeError("undeclared pixel change stopped a matching declared value")

        edge = run("declared_edge", '''
def read(frame):
    return frame.ascii[0]
action(["RIGHT", "RIGHT"], expect=["B", "B"], read=read)
''', World("B.X..", "flip_edge"))
        if edge["calls"] != [[{"action": "RIGHT"}]] or edge["traces"][0]["status"] != "mismatch":
            raise RuntimeError(f"declared edge was ignored: {edge['calls']} {edge['traces']}")
    finally:
        if patch.active:
            patch.uninstall()
        if sandbox._SANDBOX_BOOTSTRAP != original or os.environ.get("ARC3_SYSTEM_PROMPT_PREFIX", ""):
            raise RuntimeError("uninstall did not restore the sandbox")

    env = os.environ.copy()
    env.pop("ARC3_SYSTEM_PROMPT_PREFIX", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    env["ARC3_MAX_ACTIVE_STREAMS"] = "10"
    preflight = out / "preflight.json"
    subprocess.run([sys.executable, "-B", "-m", "arc3_research.preflight",
                    "--bundle-dir", str(ROOT / "research/runtime-bundle"),
                    "--config", str(CONFIG), "--report", str(preflight)],
                   cwd=ROOT, env=env, check=True, timeout=120)
    if json.loads(preflight.read_text()).get("status") != "passed":
        raise RuntimeError("preflight failed")
    subprocess.run([sys.executable, str(ROOT / "scripts/build_experiment.py"), "--config", str(CONFIG)],
                   cwd=ROOT, check=True, timeout=120)
    notebook = json.loads((ROOT / "notebooks/022-expect-check/experiment.ipynb").read_text())
    sources = ["".join(c["source"]) if isinstance(c["source"], list) else c["source"] for c in notebook["cells"]]
    embedded = json.loads(ast.literal_eval(next(s for s in sources if s.startswith("CONFIG_JSON = ")).split("\n", 1)[0].split(" = ", 1)[1]))
    if embedded["arm_order"] != ["baseline", "expect_check"] or len(embedded["games"]) != 3:
        raise RuntimeError("notebook does not carry the 3-game probe")
    report["status"] = "passed"
    report["notebook_sha256"] = hashlib.sha256((ROOT / "notebooks/022-expect-check/experiment.ipynb").read_bytes()).hexdigest()
    save(out / "report.json", report)
    print(json.dumps({"status": "passed", "scenarios": len(report["scenarios"]),
                      "notebook_sha256": report["notebook_sha256"]}))


if __name__ == "__main__":
    main()
