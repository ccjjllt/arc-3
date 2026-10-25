"""Expose the existing frame step as a read-only sandbox history alias.

No prompt, serialization, frame data, action handling, or other view changes.
"""
from __future__ import annotations

from hashlib import sha256


_ORIGINAL_CLASS = '''class HistoryEntryView:
    def __init__(self, *, action, frame, result=None):
        self.action = action
        self.frame = frame
        self.result = dict(result) if isinstance(result, dict) else {}

    def __str__(self):
        return f"AsciiHistoryEntryView(action={self.action!r}, frame={self.frame})"

    __repr__ = __str__
'''
_STEP_PROPERTY = '''    @property
    def step(self):
        return self.frame.step

'''
_PATCHED_CLASS = _ORIGINAL_CLASS.replace("    def __str__(self):\n", _STEP_PROPERTY + "    def __str__(self):\n", 1)
_INSTALLED = None


class HistoryStepCompatPatch:
    def __init__(self):
        from inference.agent import python_tool_sandbox

        self.sandbox = python_tool_sandbox
        self.original_bootstrap = python_tool_sandbox._SANDBOX_BOOTSTRAP
        if self.original_bootstrap.count(_ORIGINAL_CLASS) != 1:
            raise ValueError("Expected the original HistoryEntryView class exactly once")
        self.bootstrap = self.original_bootstrap.replace(_ORIGINAL_CLASS, _PATCHED_CLASS, 1)
        compile(self.bootstrap, "<history-step-compat-bootstrap>", "exec")
        python_tool_sandbox._SANDBOX_BOOTSTRAP = self.bootstrap

    def snapshot(self):
        return {
            "patch": "history-step-compat-v1",
            "scope": "isolated Python HistoryEntryView only",
            "field": "history[*].step",
            "meaning": "existing history entry.frame.step",
            "read_only": True,
            "missing_frame_behavior": "AttributeError, identical to entry.frame.step",
            "new_model_tools": False,
            "new_model_requests": False,
            "prompt_modified": False,
            "action_handling_modified": False,
            "original_bootstrap_sha256": sha256(self.original_bootstrap.encode()).hexdigest(),
            "patched_bootstrap_sha256": sha256(self.bootstrap.encode()).hexdigest(),
            "active": self.sandbox._SANDBOX_BOOTSTRAP is self.bootstrap,
        }

    def uninstall(self):
        global _INSTALLED
        if self.sandbox._SANDBOX_BOOTSTRAP is self.bootstrap:
            self.sandbox._SANDBOX_BOOTSTRAP = self.original_bootstrap
        if _INSTALLED is self:
            _INSTALLED = None


def install_history_step_compat():
    global _INSTALLED
    if _INSTALLED is None:
        _INSTALLED = HistoryStepCompatPatch()
    return _INSTALLED
