"""035: fail-closed, CPU-only proof of the mounted tokenizer's effort modes.

The serving configuration pins ``model_dir/chat_template.jinja``. This check
renders that same file with the mounted tokenizer. It never rewrites a model
file, loads model weights, generates a completion, or downloads a tokenizer.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


_LOW_INSTRUCTION = "Keep your thinking brief"
_OPEN_THINK = "<|im_start|>assistant\n<think>\n"
_CLOSED_THINK = "<|im_start|>assistant\n<think>\n\n</think>\n\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def _render_proof(tokenizer: Any, template: str) -> dict[str, Any]:
    """Render fixed neutral inputs; also usable with a CPU-only test fixture."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Inspect the current state before choosing an action."},
    ]
    tools = [{"type": "function", "function": {
        "name": "inspect_state", "description": "Inspect one visible state.",
        "parameters": {"type": "object", "properties": {
            "detail": {"type": "string"}}, "required": ["detail"]},
    }}]
    options = {
        "off": {"enable_thinking": False, "preserve_thinking": True},
        "low": {"enable_thinking": True, "preserve_thinking": True,
                "reasoning_effort": "low"},
        "medium": {"enable_thinking": True, "preserve_thinking": True,
                   "reasoning_effort": "medium"},
    }
    rendered = {}
    for mode, kwargs in options.items():
        text = tokenizer.apply_chat_template(
            messages, tools=tools, chat_template=template, tokenize=False,
            add_generation_prompt=True, **kwargs)
        if not isinstance(text, str) or not text:
            raise RuntimeError(f"Mounted tokenizer returned no rendered {mode} prompt")
        rendered[mode] = {"chat_template_kwargs": kwargs,
                          "rendered_prompt": text,
                          "rendered_sha256": _sha256(text.encode("utf-8")),
                          "rendered_bytes": len(text.encode("utf-8"))}
    texts = {mode: entry["rendered_prompt"] for mode, entry in rendered.items()}
    checks = {
        "off_closed_think": texts["off"].endswith(_CLOSED_THINK),
        "low_open_think": texts["low"].endswith(_OPEN_THINK),
        "medium_open_think": texts["medium"].endswith(_OPEN_THINK),
        "low_effort_branch_in_template": bool(re.search(
            r"(?:resolved_)?reasoning_effort\s*==\s*['\"]low['\"]", template)),
        "low_instruction_in_template": _LOW_INSTRUCTION in template,
        "low_instruction_in_low": texts["low"].count(_LOW_INSTRUCTION) == 1,
        "low_instruction_absent_off": _LOW_INSTRUCTION not in texts["off"],
        "low_instruction_absent_medium": _LOW_INSTRUCTION not in texts["medium"],
        "all_renderings_distinct": len({entry["rendered_sha256"]
                                         for entry in rendered.values()}) == 3,
    }
    return {"messages": messages, "tools": tools, "renders": rendered,
            "low_specific_instruction": _LOW_INSTRUCTION, "checks": checks,
            "passed": all(checks.values())}


def verify_mounted_reasoning_template(model_dir: str | Path,
                                     report_path: str | Path) -> dict[str, Any]:
    """Write actual local template/render evidence, or raise before C generates.

    The caller must invoke this before the first arm-C generation. A failed
    check writes ``passed: false`` and raises RuntimeError; it must not fall
    back to off/default thinking or download/update a template. The returned
    dictionary is identical to the saved report on a successful check.
    """
    model_dir = Path(model_dir).resolve()
    report_path = Path(report_path)
    report: dict[str, Any] = {
        "check": "035-mounted-reasoning-template-v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_dir": str(model_dir), "passed": False,
        "model_generation_calls": 0, "model_weight_loads": 0, "gpu_calls": 0,
        "local_files_only": True, "network_requested": False,
        "template_updated": False, "source_files": [],
    }
    try:
        # The server explicitly selects this file, rather than a fallback name
        # chosen by AutoTokenizer. Pass its exact text to the local renderer.
        template_path = model_dir / "chat_template.jinja"
        config_path = model_dir / "tokenizer_config.json"
        template_bytes = template_path.read_bytes()
        template = template_bytes.decode("utf-8")
        config_bytes = config_path.read_bytes()
        tokenizer_config = json.loads(config_bytes)
        if not isinstance(tokenizer_config, dict):
            raise ValueError("Mounted tokenizer_config.json is not an object")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        template_archive = report_path.with_name(report_path.stem + "-chat_template.jinja")
        config_archive = report_path.with_name(report_path.stem + "-tokenizer-template-config.json")
        template_archive.write_bytes(template_bytes)
        template_config = {key: tokenizer_config[key] for key in (
            "tokenizer_class", "auto_map", "chat_template", "chat_template_file")
            if key in tokenizer_config}
        config_archive.write_text(json.dumps(template_config, ensure_ascii=False, indent=2) + "\n")
        report["source_files"] = [
            {"path": str(template_path), "bytes": len(template_bytes),
             "sha256": _sha256(template_bytes), "archive": str(template_archive)},
            {"path": str(config_path), "bytes": len(config_bytes),
             "sha256": _sha256(config_bytes),
             "template_fields_archive": str(config_archive),
             "template_fields_sha256": _sha256(json.dumps(
                 template_config, sort_keys=True, ensure_ascii=False).encode("utf-8"))},
        ]
        import transformers
        from transformers import AutoTokenizer
        # Match the existing local server's trusted mounted tokenizer loader.
        # local_files_only forbids fetching tokenizer/config/code artifacts.
        tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir), local_files_only=True, trust_remote_code=True)
        report.update(transformers_version=transformers.__version__,
                      tokenizer_class=type(tokenizer).__name__,
                      active_template_source=str(template_path),
                      active_template_sha256=_sha256(template_bytes))
        report.update(_render_proof(tokenizer, template))
        if not report["passed"]:
            failed = [key for key, passed in report["checks"].items() if not passed]
            raise RuntimeError("Mounted tokenizer does not prove low effort: " + ", ".join(failed))
    except Exception as exc:
        report.update(passed=False, error=f"{type(exc).__name__}: {exc}",
                      decision="abort_C_before_generation")
        _write_report(report_path, report)
        raise RuntimeError("035 mounted reasoning template verification failed; arm C must abort") from exc
    report["decision"] = "allow_C_generation_with_explicit_low"
    _write_report(report_path, report)
    return report
