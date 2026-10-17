"""CPU-only compatibility check before allocating time to model startup.

Runs in a disposable subprocess. It does not construct games, start serving,
make network requests, or call a language model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from arc3_research.experiment_config import validate_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    config = json.loads(args.config.read_text())
    validate_config(config)
    for repo in sorted((args.bundle_dir / "src").iterdir(), reverse=True):
        for directory in (repo / "src", repo):
            if directory.is_dir():
                sys.path.insert(0, str(directory))
    report = {"status": "checking", "network_calls": 0, "model_calls": 0,
              "game_actions": 0, "arms": config["arm_order"], "checks": []}
    patches = []
    try:
        import requests

        def no_network(*args, **kwargs):
            report["network_calls"] += 1
            raise RuntimeError("Preflight must not call the network.")

        requests.sessions.Session.request = no_network
        from inference.agent.tool_agent import ToolAgent
        from inference.framework.solver import _HarnessGameSession
        from inference.agent import tool_agent
        originals = {"play": _HarnessGameSession.play, "chat": ToolAgent._chat_completion,
                     "handover": ToolAgent._maybe_handover, "requests": tool_agent.requests,
                     "enqueue": tool_agent._PriorityGate._enqueue_and_wait,
                     "pump": tool_agent._PriorityGate._pump,
                     **{f"gate_{name}": getattr(tool_agent._PriorityGate, name)
                        for name in ("acquire", "handover", "release")}}
        markers = ("_research_request_deadline_patch", "_research_inference_timing_patch",
                   "_research_scheduler_observer_patch")
        if any(hasattr(ToolAgent, name) for name in markers):
            raise RuntimeError("CPU preflight must start from an unpatched process.")
        original_codes = {key: value.__code__ for key, value in originals.items()
                          if hasattr(value, "__code__")}
        for relative, expected in config.get("runtime_source_sha256", {}).items():
            actual = hashlib.sha256((args.bundle_dir / relative).read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError(f"Runtime source changed: {relative}")
        report["checks"].append("runtime_source_hashes")
        original_environment = os.environ.copy()
        report["arm_policy_checks"] = {}
        try:
            for arm in config["arm_order"]:
                os.environ.update(config.get("arm_environment", {}).get(arm, {}))
                options = tool_agent._priority_level_options()
                expected = True if arm == "tail_80k" else "remaining"
                if (options["tail_lookup"] != expected or options["normalize_score"] is not True
                        or os.environ.get("ARC3_PRIORITY_PACE") != "0"
                        or os.environ.get("ARC3_MAX_ACTIVE_STREAMS") != "10"):
                    raise RuntimeError(f"Frozen scheduler policy did not take effect: {arm}")
                report["arm_policy_checks"][arm] = options
        finally:
            os.environ.clear()
            os.environ.update(original_environment)
        report["checks"].append("both_dynamic_scheduler_policies")
        if config.get("request_deadline"):
            from arc3_research.request_deadline import install_request_deadline
            patches.append(install_request_deadline())
        if config.get("inference_timing"):
            from arc3_research.inference_timing import install_inference_timing
            patches.append(install_inference_timing())
        if config.get("scheduler_observer"):
            from arc3_research.scheduler_observer import install_scheduler_observer
            patches.append(install_scheduler_observer())
        report["patches"] = [patch.snapshot() for patch in patches]
        report["checks"].append("all_hooks_install_and_snapshot")
        for patch in reversed(patches):
            patch.uninstall()
        patches.clear()
        restored = {"play": _HarnessGameSession.play, "chat": ToolAgent._chat_completion,
                    "handover": ToolAgent._maybe_handover, "requests": tool_agent.requests,
                    "enqueue": tool_agent._PriorityGate._enqueue_and_wait,
                    "pump": tool_agent._PriorityGate._pump,
                    **{f"gate_{name}": getattr(tool_agent._PriorityGate, name)
                       for name in ("acquire", "handover", "release")}}
        for key, original in originals.items():
            if restored[key] is not original:
                raise RuntimeError(f"Preflight did not restore {key}")
            if key in original_codes and original.__code__ is not original_codes[key]:
                raise RuntimeError(f"Preflight did not restore code: {key}")
        if any(hasattr(ToolAgent, name) for name in markers):
            raise RuntimeError("Preflight left an installed patch marker.")
        report["checks"].append("reverse_uninstall_restores_originals")
        report["environment_before_overrides"] = {
            key: os.environ.get(key) for key in
            ("ARC3_PRIORITY_TAIL_LOOKUP", "ARC3_PRIORITY_PACE", "ARC3_MAX_ACTIVE_STREAMS")}
        report["status"] = "passed"
    except BaseException as exc:
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        cleanup_errors = []
        for patch in reversed(patches):
            try:
                patch.uninstall()
            except BaseException as exc:
                cleanup_errors.append(f"{type(exc).__name__}: {exc}")
        if cleanup_errors:
            report.update(status="failed", cleanup_errors=cleanup_errors)
        report["elapsed_seconds"] = time.monotonic() - started
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: report[key] for key in
                          ("status", "elapsed_seconds", "network_calls", "model_calls", "game_actions")}))


if __name__ == "__main__":
    main()
