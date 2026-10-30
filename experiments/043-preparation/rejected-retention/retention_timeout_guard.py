"""Preserve the last complete function report after an incomplete tool call.

Adapted from the HF function-retention fix in ondrewsha's ARC-AGI-3 Stack S9
(https://www.kaggle.com/code/ondrewsha/arc-agi-3-stack-s9), distributed there
under Apache-2.0. Original ARC3 harness by Daniel Franzen, Jeroen Cottaar and
Tufa Labs. This file isolates that fix; it does not install S9's other edits.

The sandbox's completed final/error messages always include
``keepable_functions``. Its timeout, failed-start, EOF and invalid-response
paths do not. Missing metadata is therefore not an authoritative empty report.
Explicit empty or invalid reports retain the harness's existing clear behavior.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


RELATIVE_TARGET = Path("inference/agent/tool_agent.py")
MARKER = "[043-retention]"
ORIGINAL = (
    "    def _record_retained_functions(self, sandbox_result, payload) -> None:\n"
    "        if not _persistent_functions():\n"
    "            return\n"
    "        try:\n"
)
REPLACEMENT = (
    "    def _record_retained_functions(self, sandbox_result, payload) -> None:\n"
    "        if not _persistent_functions():\n"
    "            return\n"
    '        if isinstance(sandbox_result, dict) and "keepable_functions" not in sandbox_result and self._kept_functions:\n'
    '            payload["function_retention"] = (\n'
    '                "The snippet did not finish, so nothing new was retained; "\n'
    '                "your retained functions from earlier calls are unchanged."\n'
    "            )\n"
    '            print(f"[043-retention] preserved_functions={len(self._kept_functions)}", flush=True)\n'
    "            return\n"
    "        try:\n"
)


def install_retention_timeout_guard(bundle_root: Path | str) -> dict:
    """Patch the ARC3-Inference directory exactly once, before importing it.

    Raises before writing if the unique expected anchor is absent or the fix
    was already installed. Instrumentation prints only the retained count.
    """
    target = Path(bundle_root) / RELATIVE_TARGET
    before = target.read_text(encoding="utf-8")
    if MARKER in before:
        raise RuntimeError("043 retention guard already installed")
    matched = before.count(ORIGINAL)
    if matched != 1:
        raise RuntimeError(f"043 retention guard expected one anchor, found {matched}")
    after = before.replace(ORIGINAL, REPLACEMENT, 1)
    compile(after, str(target), "exec")
    target.write_text(after, encoding="utf-8")
    return {
        "experiment": "043",
        "active": True,
        "matched": matched,
        "target": str(target),
        "relative_target": RELATIVE_TARGET.as_posix(),
        "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
        "sole_behavior_change": "preserve previous functions when retention report is absent",
        "explicit_empty_report_clears": True,
        "explicit_invalid_report_keeps_original_behavior": True,
        "scope_reset_logic_unchanged": True,
        "log_marker": MARKER,
    }
