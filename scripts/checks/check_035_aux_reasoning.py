#!/usr/bin/env python3
"""Narrow, offline 035 payload, configuration and template-guard checks.

HTTP is replaced at its transport boundary; no model, ARC environment or GPU
is used. The tokenizer loader below is a marked fixture, never evidence about
the actual Kaggle model mount. Native sandbox cases are run separately with
check_034_executable_plan.py and its branch-only mode selector.
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


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/035-cpu-check/interface")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if (out / "report.json").exists():
        parser.error("Output report exists; use a fresh directory")
    out.mkdir(parents=True, exist_ok=True)
    report = {"status": "running", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "network_attempts": 0, "real_model_calls": 0,
              "gpu_calls": 0, "real_game_actions": 0, "checks": [],
              "limits": ["HTTP responses and tokenizer loader are CPU fixtures.",
                         "No inference quality, latency, throughput or ARC score claim.",
                         "Mounted tokenizer/template validation remains mandatory in arm C before generation."]}

    def deny_network(event, _arguments):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            report["network_attempts"] += 1
            raise RuntimeError("035 CPU check prohibits network access")
    sys.addaudithook(deny_network)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path[:0] = [str(ROOT / "src"), str(RUNTIME),
                    "/private/tmp/arc3-018-sdk", "/private/tmp/arc3-018-check-deps"]
    check018 = load_module("arc3_035_check018", ROOT / "scripts/checks/check_018_grounding.py")
    os.environ.update(check018.baseline_environment())
    os.environ.pop("ARC3_SYSTEM_PROMPT_PREFIX", None)
    from inference.agent import tool_agent
    from arc3_research import program_repair, reasoning_mode
    from arc3_research.executable_plan_context import delivery_tool_schema
    from arc3_research.experiment_config import validate_config
    old_path = ROOT / "experiments/034-v9-source/src/arc3_research/program_repair.py"
    old = load_module("arc3_035_frozen_v9_repair", old_path)
    current = program_repair._completion
    agent = tool_agent.ToolAgent(model="cpu-no-model", provider="vllm",
                                base_url="http://cpu.invalid/v1", api_key="cpu-placeholder")
    messages = [{"role": "system", "content": "Keep facts and hypotheses separate."},
                {"role": "user", "content": "Return a current-frame short program."}]
    tools = [delivery_tool_schema()]
    choice = {"type": "function", "function": {"name": "submit_program"}}
    initial_messages, initial_tools = copy.deepcopy(messages), copy.deepcopy(tools)
    original_post = tool_agent.requests.post
    ordinary_method = tool_agent.ToolAgent._chat_completion
    ordinary_kwargs = copy.deepcopy(agent._harness_template_kwargs())
    captured = []

    class Response:
        status_code = 200
        def __init__(self, body):
            self.body = body
            self.closed = False
        def raise_for_status(self):
            return None
        def json(self):
            return copy.deepcopy(self.body)
        def close(self):
            self.closed = True

    def post(url, *, headers, json, timeout, **kwargs):
        assert url in {"http://cpu.invalid/v1/tokenize", "http://cpu.invalid/v1/chat/completions"}
        assert timeout[0] > 0 and 0 < timeout[1] <= 60
        captured.append({"url": url, "payload": copy.deepcopy(json),
                         "timeout": list(timeout), "transport_kwargs": copy.deepcopy(kwargs)})
        if url.endswith("/tokenize"):
            return Response({"count": 73})
        return Response({"choices": [{"message": {"role": "assistant", "content": "",
            "tool_calls": [{"id": "cpu-delivery", "type": "function", "function": {
                "name": "submit_program", "arguments": "{\"code\":\"def f():\\n    pass\\n\"}"}}]},
            "finish_reason": "tool_calls"}],
            "usage": {"prompt_tokens": 73, "completion_tokens": 12, "total_tokens": 85,
                      "completion_tokens_details": {"reasoning_tokens": 4}}})

    def auxiliary(fn, **options):
        captured.clear()
        record = {}
        result = fn(agent, messages, tools, timeout=60, max_tokens=4096,
                    max_input_tokens=16384, tool_choice_override=choice,
                    request_record=record, **options)
        calls = copy.deepcopy(captured)
        assert len(calls) == 2 and calls[0]["url"].endswith("/tokenize")
        assert calls[1]["url"].endswith("/chat/completions")
        assert calls[0]["payload"] == calls[1]["payload"] == record["request_payload"]
        assert calls[1]["payload"]["max_tokens"] == 4096
        assert record["input_token_cap"] == 16384 and record["timeout_seconds"] == 60
        assert record["input_tokens"] == record["served_prompt_tokens"] == 73
        assert record["tokenize_matches_usage"] is True
        assert result.usage["completion_tokens_details"]["reasoning_tokens"] == 4
        assert messages == initial_messages and tools == initial_tools
        return {"calls": calls, "record": record}

    try:
        tool_agent.requests.post = post
        captured.clear()
        agent._chat_completion(messages, tools=tools, request_timeout_seconds=60, max_tokens=4096)
        ordinary_before = copy.deepcopy(captured)
        frozen_off = auxiliary(old._completion, enable_thinking=False)
        current_off = auxiliary(current, enable_thinking=False)
        low = auxiliary(current, enable_thinking=True, reasoning_effort="low")
        assert frozen_off["record"]["request_payload"] == current_off["record"]["request_payload"]
        off_payload = current_off["record"]["request_payload"]
        low_payload = low["record"]["request_payload"]
        expected_low = copy.deepcopy(off_payload)
        expected_low["chat_template_kwargs"].update(enable_thinking=True, reasoning_effort="low")
        assert expected_low == low_payload, "B/C must differ only in declared template mode fields"
        captured.clear()
        agent._chat_completion(messages, tools=tools, request_timeout_seconds=60, max_tokens=4096)
        ordinary_after = copy.deepcopy(captured)
        assert ordinary_before == ordinary_after
        assert agent._harness_template_kwargs() == ordinary_kwargs
        assert tool_agent.ToolAgent._chat_completion is ordinary_method
        report["checks"].append({"name": "actual_completion_transport_payload_parity", "status": "passed",
            "frozen_v9_source_sha256": sha(old_path), "frozen_off": frozen_off,
            "current_off": current_off, "current_low": low,
            "ordinary_before": ordinary_before, "ordinary_after": ordinary_after,
            "ordinary_template_kwargs": ordinary_kwargs,
            "only_low_payload_changes": ["chat_template_kwargs.enable_thinking",
                                         "chat_template_kwargs.reasoning_effort"]})
        rejected = []
        for options in [{"enable_thinking": False, "reasoning_effort": "low"},
                        {"enable_thinking": True, "reasoning_effort": "high"}]:
            captured.clear()
            try:
                current(agent, messages, tools, timeout=60, max_tokens=4096, **options)
            except ValueError as exc:
                assert not captured
                rejected.append({"options": options, "error": str(exc)})
            else:
                raise AssertionError("Invalid mode reached HTTP transport")
        report["checks"].append({"name": "invalid_effort_fails_before_transport", "status": "passed",
                                 "rejections": rejected})
    finally:
        tool_agent.requests.post = original_post

    # Check the real 035 config, with narrowly corrupted mode/budget copies.
    config_path = ROOT / "experiments/035-aux-reasoning-diagnostic.json"
    config = json.loads(config_path.read_text())
    validate_config(config)
    runtime_hashes = {key: sha(RUNTIME / key.removeprefix("src/ARC3-Inference/"))
                      for key in config["runtime_source_sha256"]}
    assert runtime_hashes == config["runtime_source_sha256"], "Frozen main runtime source changed"
    rejected = []
    mutations = [
        ("C_high", lambda c: c["auxiliary_reasoning_modes"].update(executable_plan_C="high")),
        ("A_branch", lambda c: c["auxiliary_reasoning_modes"].update(executable_plan_A="off")),
        ("wrong_order", lambda c: c["arm_order"].reverse()),
        ("longer_game", lambda c: c.update(continuation_seconds=451)),
        ("more_actions", lambda c: c.update(max_continuation_actions=61)),
        ("longer_arm", lambda c: c.update(requested_arm_seconds=601)),
        ("longer_request", lambda c: c["candidate_delivery"].update(max_request_seconds=61)),
        ("more_output_tokens", lambda c: c["candidate_delivery"].update(max_output_tokens=4097)),
        ("more_extra_time", lambda c: c["candidate_delivery"].update(max_extra_processing_seconds=121)),
        ("silent_template_fallback", lambda c: c["template_preflight"].update(
            unsupported_mode_action="fall_back_off")),
    ]
    for name, change in mutations:
        invalid = copy.deepcopy(config)
        change(invalid)
        try:
            validate_config(invalid)
        except ValueError as exc:
            rejected.append({"name": name, "error": str(exc)})
        else:
            raise AssertionError("035 accepted invalid config: " + name)
    arm_count = len(config["arm_order"])
    reserve = {"startup": config["startup_limit_seconds"],
               "solver": arm_count * config["requested_arm_seconds"],
               "cache": arm_count * config["cache_flush_wait_seconds"],
               "cleanup": arm_count * 150 + 60}
    worst = sum(reserve.values())
    assert worst == 6870 <= config["hard_limit_seconds"] == 7200
    report["checks"].append({"name": "real_035_config_and_budget_guards", "status": "passed",
        "config_path": str(config_path), "config_sha256": sha(config_path),
        "frozen_runtime_source_sha256": runtime_hashes,
        "rejections": rejected, "reserve_seconds": reserve, "worst_reserved_seconds": worst,
        "remaining_slack_seconds": config["hard_limit_seconds"] - worst,
        "limit": "Static reserves only; no actual model startup/cache latency is measured."})

    # A deliberately tiny marked tokenizer fixture tests guard wiring and
    # fail-closed behavior, without pretending to load Kaggle model files.
    valid_template = ("{# CPU fixture only; no mounted template claim #}\n"
                      "{% if reasoning_effort == 'low' %}Keep your thinking brief{% endif %}\n")
    invalid_template = "{# CPU fixture ignores low; no mounted template claim #}\n"
    loader_calls = []

    class FixtureTokenizer:
        def apply_chat_template(self, messages, *, tools, chat_template, tokenize,
                                add_generation_prompt, **kwargs):
            assert tokenize is False and add_generation_prompt is True
            assert messages and tools and kwargs["preserve_thinking"] is True
            prefix = "CPU FIXTURE ONLY\n"
            if kwargs["enable_thinking"] is False:
                return prefix + "<|im_start|>assistant\n<think>\n\n</think>\n\n"
            if kwargs.get("reasoning_effort") == "low" and "reasoning_effort == 'low'" in chat_template:
                prefix += "Keep your thinking brief\n"
            return prefix + "<|im_start|>assistant\n<think>\n"

    class FixtureAutoTokenizer:
        @classmethod
        def from_pretrained(cls, model_dir, **kwargs):
            assert kwargs == {"local_files_only": True, "trust_remote_code": True}
            loader_calls.append({"model_dir": model_dir, "kwargs": copy.deepcopy(kwargs)})
            return FixtureTokenizer()

    fixture_transformers = types.ModuleType("transformers")
    fixture_transformers.__version__ = "035-cpu-fixture-no-real-tokenizer"
    fixture_transformers.AutoTokenizer = FixtureAutoTokenizer
    original_transformers = sys.modules.get("transformers")
    sys.modules["transformers"] = fixture_transformers
    fixture_results = []
    try:
        for name, template, accepted in [("supported_fixture", valid_template, True),
                                          ("unsupported_fixture", invalid_template, False)]:
            fixture_dir = out / name / "fixture-model"
            fixture_dir.mkdir(parents=True)
            template_path = fixture_dir / "chat_template.jinja"
            template_path.write_text(template)
            (fixture_dir / "tokenizer_config.json").write_text(json.dumps({
                "tokenizer_class": "CPUFixtureTokenizer", "chat_template": template}))
            result_path = fixture_dir.parent / "template-check.json"
            try:
                result = reasoning_mode.verify_mounted_reasoning_template(fixture_dir, result_path)
            except RuntimeError:
                assert not accepted
                result = json.loads(result_path.read_text())
                assert result["passed"] is False
                assert result["decision"] == "abort_C_before_generation"
            else:
                assert accepted and result["passed"] is True
                assert result == json.loads(result_path.read_text())
                assert result["active_template_sha256"] == sha(template_path)
                assert all(result["checks"].values())
            assert result["template_updated"] is False and result["local_files_only"] is True
            assert template_path.read_text() == template
            assert result["gpu_calls"] == result["model_generation_calls"] == result["model_weight_loads"] == 0
            fixture_results.append({"name": name, "status": "passed", "accepted": accepted,
                                    "report_path": str(result_path), "template_sha256": sha(template_path)})
    finally:
        if original_transformers is None:
            sys.modules.pop("transformers", None)
        else:
            sys.modules["transformers"] = original_transformers
    report["checks"].append({"name": "template_guard_fixture_only", "status": "passed",
        "not_actual_mounted_template_evidence": True, "fixtures": fixture_results,
        "local_only_loader_calls": loader_calls})
    assert report["network_attempts"] == 0
    report["status"] = "passed"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["source_sha256"] = {str(path.relative_to(ROOT)): sha(path) for path in [
        Path(__file__), ROOT / "src/arc3_research/program_repair.py",
        ROOT / "src/arc3_research/reasoning_mode.py", ROOT / "src/arc3_research/experiment_config.py"]}
    save(out / "report.json", report)
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]),
                      "network_attempts": 0, "report_path": str(out / "report.json")}))


if __name__ == "__main__":
    main()
