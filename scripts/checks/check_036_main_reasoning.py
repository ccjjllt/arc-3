#!/usr/bin/env python3
"""Manual CPU request-boundary checks for the single-field 036 candidate.

Real ToolAgent request construction is used with HTTP replaced at the transport
boundary. The marked tokenizer fixture tests guard wiring, not a fresh mounted
tokenizer. It never loads weights, calls a model, touches ARC or uses a GPU.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "research/runtime-bundle/src/ARC3-Inference"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path,
                        default=ROOT / "experiments/036-preparation/main-mode-cpu.json")
    parser.add_argument("--archived-template", type=Path, default=ROOT / (
        "runs/035-aux-reasoning-diagnostic/executable_plan_C/"
        "reasoning-template-verification-chat_template.jinja"))
    args = parser.parse_args()
    report_path = args.report.resolve()
    if report_path.exists():
        parser.error("Output report exists; use a fresh path")
    fixture_dir = report_path.parent / (report_path.stem + "-fixture")
    fixture_dir.mkdir(parents=True, exist_ok=True)
    report = {"status": "checking", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "network_attempts": 0, "real_model_calls": 0,
              "gpu_calls": 0, "real_game_actions": 0,
              "runtime_mounted_guard_pending": True, "checks": [],
              "limits": ["HTTP and tokenizer loader are explicitly marked CPU fixtures.",
                         "Actual mounted tokenizer proof is mandatory in both arms before generation.",
                         "No score, generation quality, latency or throughput claim.",
                         "12288 is an explicit CPU request argument, not proof of an online environment setting."]}

    def audit(event, _arguments):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            report["network_attempts"] += 1
            raise RuntimeError("036 CPU check prohibits network access")
    sys.addaudithook(audit)
    sys.path[:0] = [str(ROOT / "src"), str(RUNTIME),
                    "/private/tmp/arc3-018-sdk", "/private/tmp/arc3-018-check-deps"]
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    setup = load_module("arc3_036_setup", ROOT / "scripts/checks/check_018_grounding.py")
    os.environ.update(setup.baseline_environment())
    for key in ("ARC3_SYSTEM_PROMPT_PREFIX", "ARC3_SUMMARY_INTERVAL_TOKENS",
                "ARC3_REASONING_EFFORT_LADDER"):
        os.environ.pop(key, None)
    from inference.agent import tool_agent
    from arc3_research import main_reasoning
    assert tool_agent._summary_interval_tokens() == 0
    runtime_before = sha(RUNTIME / "inference/agent/tool_agent.py")

    archived = args.archived_template.read_bytes()
    assert hashlib.sha256(archived).hexdigest() == main_reasoning.EXPECTED_TEMPLATE_SHA256
    model_dir = fixture_dir / "fixture-model"
    model_dir.mkdir(exist_ok=True)
    (model_dir / "chat_template.jinja").write_bytes(archived)
    (model_dir / "tokenizer_config.json").write_text(json.dumps({
        "tokenizer_class": "ExplicitCPUFixtureTokenizer"}))
    loader_calls = []

    class FixtureTokenizer:
        def apply_chat_template(self, messages, *, tools, chat_template, tokenize,
                                add_generation_prompt, **kwargs):
            assert messages and tools and tokenize is False and add_generation_prompt is True
            assert kwargs["enable_thinking"] is True and kwargs["preserve_thinking"] is True
            assert hashlib.sha256(chat_template.encode()).hexdigest() == main_reasoning.EXPECTED_TEMPLATE_SHA256
            prefix = "CPU FIXTURE ONLY\n"
            if kwargs.get("reasoning_effort", "xhigh") == "xhigh":
                prefix += main_reasoning._XHIGH_INSTRUCTION + "\n\n"
            return prefix + "tools and neutral message\n" + main_reasoning._OPEN_THINK

    class FixtureAutoTokenizer:
        @classmethod
        def from_pretrained(cls, path, **kwargs):
            assert kwargs == {"local_files_only": True, "trust_remote_code": True}
            loader_calls.append({"path": path, "kwargs": copy.deepcopy(kwargs)})
            return FixtureTokenizer()

    fixture_module = types.ModuleType("transformers")
    fixture_module.__version__ = "036-cpu-fixture-no-real-tokenizer"
    fixture_module.AutoTokenizer = FixtureAutoTokenizer
    old_transformers = sys.modules.get("transformers")
    sys.modules["transformers"] = fixture_module
    try:
        proof = main_reasoning.verify_main_reasoning_template(model_dir, fixture_dir / "guard.json")
        assert proof["passed"] is True and all(proof["checks"].values())
        assert json.loads((fixture_dir / "guard.json").read_text()) == proof
        assert len(loader_calls) == 1
        before_loads = len(loader_calls)
        (model_dir / "chat_template.jinja").write_bytes(archived + b"\n")
        try:
            main_reasoning.verify_main_reasoning_template(model_dir, fixture_dir / "rejected-template.json")
        except RuntimeError:
            rejected = json.loads((fixture_dir / "rejected-template.json").read_text())
            assert rejected["passed"] is False
            assert rejected["decision"] == "abort_entire_036_comparison_before_generation"
            assert len(loader_calls) == before_loads
        else:
            raise AssertionError("Changed template was accepted")
        (model_dir / "chat_template.jinja").write_bytes(archived)
        report["checks"].append({"name": "mounted_guard_wiring_with_marked_fixture", "passed": True,
            "archived_035_template_sha256": sha(args.archived_template),
            "fixture_tokenizer": True, "proof_path": str(fixture_dir / "guard.json"),
            "changed_template_rejection": rejected, "loader_calls": loader_calls})
    finally:
        if old_transformers is None:
            sys.modules.pop("transformers", None)
        else:
            sys.modules["transformers"] = old_transformers

    agent = tool_agent.ToolAgent(model="cpu-no-model", provider="vllm",
                                base_url="http://cpu.invalid/v1", api_key="cpu-placeholder")
    tools = agent._tools(fixture_dir / "unused-state.pkl")
    messages = [{"role": "system", "content": "Use observed facts."},
                {"role": "user", "content": "Inspect this current state."}]
    original_messages, original_tools = copy.deepcopy(messages), copy.deepcopy(tools)
    captured = []

    class Response:
        status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return {"choices": [{"message": {"role": "assistant", "content": "CPU fixture response"},
                                 "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 73, "completion_tokens": 12, "total_tokens": 85}}
        def close(self):
            pass

    def post(url, *, headers, json, timeout, **kwargs):
        assert url == "http://cpu.invalid/v1/chat/completions"
        captured.append({"url": url, "payload": copy.deepcopy(json),
                         "timeout": list(timeout), "transport_kwargs": copy.deepcopy(kwargs)})
        return Response()

    original_post = tool_agent.requests.post
    original_method = tool_agent.ToolAgent._harness_template_kwargs
    original_chat = tool_agent.ToolAgent._chat_completion

    def request(*, explicit_max=True):
        captured.clear()
        options = {"max_tokens": 12288} if explicit_max else {}
        agent._chat_completion(messages, tools=tools, request_timeout_seconds=60, **options)
        assert len(captured) == 1
        assert messages == original_messages and tools == original_tools
        return copy.deepcopy(captured[0])

    patch = None
    try:
        tool_agent.requests.post = post
        before = request()
        before_server_default = request(explicit_max=False)
        patch = main_reasoning.install_main_reasoning(template_verification=proof)
        assert tool_agent.ToolAgent._chat_completion is original_chat
        medium = request()
        medium_server_default = request(explicit_max=False)
        expected = copy.deepcopy(before)
        expected["payload"]["chat_template_kwargs"]["reasoning_effort"] = "medium"
        assert medium == expected, "Candidate changed more than one default template field"
        expected_default = copy.deepcopy(before_server_default)
        expected_default["payload"]["chat_template_kwargs"]["reasoning_effort"] = "medium"
        assert medium_server_default == expected_default
        assert before["payload"]["max_tokens"] == medium["payload"]["max_tokens"] == 12288
        assert medium["payload"]["chat_template_kwargs"]["enable_thinking"] is True
        duplicate_rejected = False
        try:
            main_reasoning.install_main_reasoning(template_verification=proof)
        except RuntimeError:
            duplicate_rejected = True
        assert duplicate_rejected
        os.environ["ARC3_REASONING_EFFORT_LADDER"] = "medium,low"
        agent._reasoning_effort_rung = 1
        explicit_low = request()
        assert explicit_low["payload"]["chat_template_kwargs"]["reasoning_effort"] == "low"
        expected_low = copy.deepcopy(before)
        expected_low["payload"]["chat_template_kwargs"]["reasoning_effort"] = "low"
        assert explicit_low == expected_low
        agent._reasoning_effort_rung = -1
        os.environ.pop("ARC3_REASONING_EFFORT_LADDER", None)
        # A different already-created agent sees this process's candidate only.
        second = tool_agent.ToolAgent(model="cpu-no-model", provider="vllm",
                                     base_url="http://cpu.invalid/v1", api_key="cpu-placeholder")
        assert second._harness_template_kwargs()["reasoning_effort"] == "medium"
        snapshot = patch.snapshot()
        assert snapshot["defaulted_calls"] == 3 and snapshot["explicit_calls"] == 1
        assert snapshot["summary_interval_tokens"] == 0
        assert "arc3_research.executable_plan" not in sys.modules
        assert "arc3_research.program_repair" not in sys.modules
        patch.uninstall()
        assert tool_agent.ToolAgent._harness_template_kwargs is original_method
        assert main_reasoning._INSTALLED is None
        assert patch.snapshot()["enabled"] is False
        patch.uninstall()
        restored = request()
        assert restored == before
        assert second._harness_template_kwargs() == original_method(second)
        report["checks"].append({"name": "real_main_http_payload_single_field_difference", "passed": True,
            "baseline": before, "medium": medium, "explicit_low": explicit_low,
            "server_default_baseline": before_server_default,
            "server_default_medium": medium_server_default,
            "candidate_snapshot": snapshot, "restored": restored,
            "duplicate_install_rejected": duplicate_rejected,
            "auxiliary_branch_imported_or_installed": False,
            "only_changed_field": "chat_template_kwargs.reasoning_effort"})
    finally:
        if patch is not None and patch.active:
            patch.uninstall()
        tool_agent.requests.post = original_post
        os.environ.pop("ARC3_REASONING_EFFORT_LADDER", None)

    rejections = []
    for label, options in [("missing_template_proof", {}),
                           ("unpassed_template_proof", {"template_verification": {"passed": False}}),
                           ("different_default_effort", {"default_effort": "low", "template_verification": proof})]:
        try:
            main_reasoning.install_main_reasoning(**options)
        except ValueError as exc:
            rejections.append({"name": label, "error": str(exc)})
        else:
            raise AssertionError("Accepted invalid installation: " + label)
    os.environ["ARC3_SUMMARY_INTERVAL_TOKENS"] = "100"
    try:
        main_reasoning.install_main_reasoning(template_verification=proof)
    except ValueError as exc:
        assert tool_agent._summary_interval_tokens() == 100
        rejections.append({"name": "nonzero_actual_summary_interval", "error": str(exc)})
    else:
        raise AssertionError("Accepted enabled summaries")
    finally:
        os.environ.pop("ARC3_SUMMARY_INTERVAL_TOKENS", None)
    assert tool_agent._summary_interval_tokens() == 0
    assert main_reasoning._INSTALLED is None
    assert tool_agent.ToolAgent._harness_template_kwargs is original_method
    assert sha(RUNTIME / "inference/agent/tool_agent.py") == runtime_before
    report["checks"].append({"name": "invalid_installations_fail_closed_and_restore", "passed": True,
                             "rejections": rejections, "runtime_source_unchanged_sha256": runtime_before})
    report.update(status="passed", checks_passed=len(report["checks"]),
                  helper_sha256=sha(ROOT / "src/arc3_research/main_reasoning.py"),
                  checker_sha256=sha(Path(__file__)))
    save(report_path, report)
    print(json.dumps({"status": report["status"], "checks_passed": report["checks_passed"],
                      "report": str(report_path), "runtime_mounted_guard_pending": True}))


if __name__ == "__main__":
    main()
