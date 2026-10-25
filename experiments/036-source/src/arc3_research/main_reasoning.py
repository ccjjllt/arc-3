"""036: change only the main harness's otherwise implicit effort to medium.

The original adaptive effort ladder keeps priority. Neither request construction,
generation limits, game actions nor the mounted model/template is modified.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
from typing import Any


EXPECTED_TEMPLATE_SHA256 = "c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041"
_XHIGH_INSTRUCTION = (
    "Reasoning effort is set to xhigh. Please think carefully through the task, "
    "validate key assumptions, consider plausible alternatives, and prioritize "
    "correctness, consistency, and clarity in the final answer.")
_LOW_INSTRUCTION = "Keep your thinking brief"
_OPEN_THINK = "<|im_start|>assistant\n<think>\n"
_INSTALLED = None


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: str | Path | None, report: dict[str, Any]) -> None:
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def _render_proof(tokenizer: Any, template: str) -> dict[str, Any]:
    messages = [{"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Inspect the current state before choosing an action."}]
    tools = [{"type": "function", "function": {
        "name": "inspect_state", "description": "Inspect one visible state.",
        "parameters": {"type": "object", "properties": {
            "detail": {"type": "string"}}, "required": ["detail"]}}}]
    renders = {}
    for mode in ("default", "medium"):
        kwargs = {"enable_thinking": True, "preserve_thinking": True}
        if mode == "medium":
            kwargs["reasoning_effort"] = "medium"
        text = tokenizer.apply_chat_template(
            messages, tools=tools, chat_template=template, tokenize=False,
            add_generation_prompt=True, **kwargs)
        if not isinstance(text, str) or not text:
            raise RuntimeError("Mounted tokenizer produced no prompt for " + mode)
        renders[mode] = {"chat_template_kwargs": kwargs, "rendered_prompt": text,
                         "rendered_sha256": _sha(text.encode("utf-8")),
                         "rendered_bytes": len(text.encode("utf-8"))}
    default = renders["default"]["rendered_prompt"]
    medium = renders["medium"]["rendered_prompt"]
    checks = {
        "template_default_is_xhigh": bool(re.search(
            r"reasoning_effort\s*\|\s*default\(['\"]xhigh['\"]\)", template)),
        "template_supports_medium": bool(re.search(
            r"resolved_reasoning_effort\s+not\s+in\s*\([^)]*['\"]medium['\"]", template)),
        "default_contains_xhigh_instruction_once": default.count(_XHIGH_INSTRUCTION) == 1,
        "medium_omits_xhigh_instruction": _XHIGH_INSTRUCTION not in medium,
        "both_omit_low_instruction": _LOW_INSTRUCTION not in default and _LOW_INSTRUCTION not in medium,
        "both_keep_thinking_open": default.endswith(_OPEN_THINK) and medium.endswith(_OPEN_THINK),
        "only_rendered_difference_is_xhigh_instruction": default.replace(
            _XHIGH_INSTRUCTION + "\n\n", "", 1) == medium,
        "renderings_distinct": renders["default"]["rendered_sha256"] != renders["medium"]["rendered_sha256"],
    }
    return {"messages": messages, "tools": tools, "renders": renders,
            "checks": checks, "passed": all(checks.values())}


def verify_main_reasoning_template(model_dir: str | Path,
                                   report_path: str | Path | None = None) -> dict[str, Any]:
    """Prove the actual mounted default/medium modes without inference or writes.

    Failure invalidates the whole 036 comparison; callers must not silently
    replace this with a different effort, tokenizer or template.
    """
    model_dir = Path(model_dir).resolve()
    report: dict[str, Any] = {
        "check": "036-mounted-main-reasoning-template-v1", "passed": False,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_dir": str(model_dir), "expected_template_sha256": EXPECTED_TEMPLATE_SHA256,
        "local_files_only": True, "network_requested": False,
        "template_updated": False, "model_generation_calls": 0,
        "model_weight_loads": 0, "gpu_calls": 0,
    }
    try:
        template_path = model_dir / "chat_template.jinja"
        config_path = model_dir / "tokenizer_config.json"
        template_bytes = template_path.read_bytes()
        template = template_bytes.decode("utf-8")
        config_bytes = config_path.read_bytes()
        config = json.loads(config_bytes)
        if not isinstance(config, dict):
            raise ValueError("Mounted tokenizer_config.json is not an object")
        report.update(active_template_source=str(template_path),
                      active_template_sha256=_sha(template_bytes),
                      source_files=[{"path": str(template_path), "sha256": _sha(template_bytes),
                                     "bytes": len(template_bytes)},
                                    {"path": str(config_path), "sha256": _sha(config_bytes),
                                     "bytes": len(config_bytes)}])
        if report["active_template_sha256"] != EXPECTED_TEMPLATE_SHA256:
            raise ValueError("Mounted chat template differs from the frozen 035 template")
        if report_path is not None:
            report_path = Path(report_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            archive = report_path.with_name(report_path.stem + "-chat_template.jinja")
            archive.write_bytes(template_bytes)
            report["template_archive"] = str(archive)
        import transformers
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir), local_files_only=True, trust_remote_code=True)
        report.update(transformers_version=transformers.__version__,
                      tokenizer_class=type(tokenizer).__name__)
        report.update(_render_proof(tokenizer, template))
        if not report["passed"]:
            raise RuntimeError("Default/medium rendering proof failed: " + ", ".join(
                name for name, passed in report["checks"].items() if not passed))
    except Exception as exc:
        report.update(passed=False, error=f"{type(exc).__name__}: {exc}",
                      decision="abort_entire_036_comparison_before_generation")
        _write(report_path, report)
        raise RuntimeError("036 mounted main reasoning template verification failed; comparison must abort") from exc
    report["decision"] = "allow_036_default_versus_medium_comparison"
    _write(report_path, report)
    return report


# The shorter alias is useful to a baseline arm that installs no candidate.
verify_mounted_template = verify_main_reasoning_template


class MainReasoningPatch:
    def __init__(self, agent_class, original, default_effort, proof):
        self.agent_class = agent_class
        self.original = original
        self.default_effort = default_effort
        self.proof = proof
        self.active = True
        self.defaulted_calls = 0
        self.explicit_calls = 0
        self._lock = threading.Lock()
        self.wrapper = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"name": "main_reasoning", "enabled": self.active,
                    "default_effort": self.default_effort,
                    "defaulted_calls": self.defaulted_calls,
                    "explicit_calls": self.explicit_calls,
                    "counter_unit": "template_kwargs_method_calls_including_request_logging",
                    "preserves_explicit_effort_ladder": True,
                    "summary_interval_tokens": 0,
                    "template_verified": self.proof["passed"],
                    "active_template_sha256": self.proof["active_template_sha256"],
                    "model_dir": self.proof["model_dir"],
                    "adds_framework_model_calls": False,
                    "adds_framework_game_actions": False,
                    "changes_max_output_tokens": False,
                    "changes_auxiliary_branch": False}

    def uninstall(self) -> None:
        global _INSTALLED
        if not self.active:
            return
        if self.agent_class._harness_template_kwargs is not self.wrapper:
            raise RuntimeError("Main reasoning wrapper changed while installed")
        self.agent_class._harness_template_kwargs = self.original
        self.active = False
        _INSTALLED = None


def install_main_reasoning(default_effort: str = "medium", *,
                           model_dir: str | Path | None = None,
                           report_path: str | Path | None = None,
                           template_verification: dict[str, Any] | None = None) -> MainReasoningPatch:
    """Install only in the isolated 036 candidate process, after template proof."""
    global _INSTALLED
    if default_effort != "medium":
        raise ValueError("036 varies only the default effort from implicit xhigh to medium")
    if _INSTALLED is not None:
        raise RuntimeError("Main reasoning is already installed")
    from inference.agent import tool_agent
    if tool_agent._summary_interval_tokens() != 0:
        raise ValueError("036 requires the actual summary interval to remain zero")
    if model_dir is not None and template_verification is not None:
        raise ValueError("Supply a model directory or an existing verification, not both")
    if model_dir is not None:
        template_verification = verify_main_reasoning_template(model_dir, report_path)
    elif report_path is not None:
        raise ValueError("report_path requires model_dir; an existing proof is already recorded")
    proof = template_verification
    if (not isinstance(proof, dict) or proof.get("passed") is not True
            or proof.get("check") != "036-mounted-main-reasoning-template-v1"
            or proof.get("active_template_sha256") != EXPECTED_TEMPLATE_SHA256
            or proof.get("decision") != "allow_036_default_versus_medium_comparison"
            or not proof.get("checks") or not all(proof["checks"].values())):
        raise ValueError("036 requires a passed mounted-template proof before installation")
    cls = tool_agent.ToolAgent
    original = cls._harness_template_kwargs
    handle = MainReasoningPatch(cls, original, default_effort, proof)

    def template_kwargs(agent):
        kwargs = dict(original(agent))
        with handle._lock:
            if "reasoning_effort" in kwargs:
                handle.explicit_calls += 1
            else:
                handle.defaulted_calls += 1
        kwargs.setdefault("reasoning_effort", default_effort)
        return kwargs

    handle.wrapper = template_kwargs
    cls._harness_template_kwargs = template_kwargs
    _INSTALLED = handle
    return handle
