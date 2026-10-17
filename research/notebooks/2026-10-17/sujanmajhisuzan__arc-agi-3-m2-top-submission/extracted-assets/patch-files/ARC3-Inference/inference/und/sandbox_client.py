"""CONTRACT: Pure-Python client for World Model tools in the sandbox (Rules 04, 05).

Self-contained stdlib-only module. Embedded into python_tool_sandbox runtime.
Provides WorldModelClient (`wm`) exposing:
- wm.digest(): mechanics digest without goal leakage
- wm.card(): knowledge card with confirmed laws and hypotheses
- wm.status(): session telemetry and active rules summary
- wm.claim(): register empirical law or working hypothesis
- wm.goal(): declare current goal focus
- wm.plan(): query forward plan search
- wm.begin_step() / wm.end_step(): step prediction and verification loop
- wm.probe(): query exploratory probe budget and allowance
- wm.undo(): query ACTION7 availability
- wm.budget(): query action budget and timer pressure
- wm.hook_register(): register model hooks
- wm.run(): safe execution of actions with step prediction and verification
"""
from __future__ import annotations

import inspect
from typing import Any, Callable


class WorldModelClient:
    """Thin client proxying world model requests to host-resident UndSession."""

    def __init__(
        self,
        send_fn: Callable[[dict[str, Any]], None] | None = None,
        recv_fn: Callable[[], dict[str, Any]] | None = None,
        action_fn: Callable[..., Any] | None = None,
    ) -> None:
        self._send = send_fn
        self._recv = recv_fn
        self._action = action_fn

    def _call(self, op: str, **args: Any) -> Any:
        """Issue an RPC request to the host and return the unwrapped result."""
        if self._send is None or self._recv is None:
            raise RuntimeError("WorldModelClient is not connected to sandbox host.")
        clean_args = {k: v for k, v in args.items() if v is not None}
        self._send({"type": "und", "op": op, "args": clean_args})
        reply = self._recv()
        if not isinstance(reply, dict):
            raise RuntimeError(f"Invalid reply from host for op {op!r}: {reply!r}")
        if not reply.get("ok"):
            err_msg = str(reply.get("error") or "RPC call failed")
            raise RuntimeError(f"wm.{op}() failed: {err_msg}")
        return reply.get("result")

    def digest(self, max_tokens: int | None = None) -> str:
        """Return deterministic mechanics digest without goal leakage."""
        res = self._call("digest", max_tokens=max_tokens)
        return str(res or "")

    def card(self, format: str = "text", max_tokens: int | None = None) -> str | dict[str, Any]:
        """Return current knowledge card with confirmed laws and hypotheses."""
        res = self._call("card", format=format, max_tokens=max_tokens)
        return res if isinstance(res, (str, dict)) else str(res or "")

    def status(self) -> dict[str, Any]:
        """Return session status including timer, claims, and overlay count."""
        res = self._call("status")
        return dict(res) if isinstance(res, dict) else {}

    def claim(
        self,
        law: str,
        subject: Any = None,
        predicate: Any = None,
        kind: str | None = None,
        expected: Any = None,
    ) -> dict[str, Any]:
        """Register or propose an empirical law / hypothesis."""
        res = self._call("claim", law=law, subject=subject, predicate=predicate, kind=kind, expected=expected)
        return dict(res) if isinstance(res, dict) else {}

    def goal(
        self,
        kind: str = "",
        color: int | None = None,
        target: Any = None,
        criteria: Any = None,
        goal_type: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Declare active goal focus."""
        gt = kind or goal_type or "custom"
        res = self._call("goal", goal_type=gt, kind=gt, color=color, target=target, criteria=criteria, **kwargs)
        return dict(res) if isinstance(res, dict) else {}

    def plan(
        self,
        target: Any = None,
        color: int | None = None,
        max_depth: int = 20,
        strategy: str = "astar",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search for a candidate plan towards target."""
        res = self._call("plan", target=target, color=color, max_depth=max_depth, strategy=strategy, **kwargs)
        return dict(res) if isinstance(res, dict) else {}

    def begin_step(self, action: Any, category: str = "planned") -> dict[str, Any]:
        """Notify world model of upcoming action execution to record prediction."""
        res = self._call("begin_step", action=action, category=category)
        return dict(res) if isinstance(res, dict) else {}

    def end_step(self) -> dict[str, Any]:
        """Verify post-step outcome against prediction (MATCH / MISMATCH)."""
        res = self._call("end_step")
        return dict(res) if isinstance(res, dict) else {}

    def probe(self, action: Any, hypothesis: str = "") -> dict[str, Any]:
        """Check exploratory probe allowance and remaining probe budget."""
        res = self._call("probe", action=action, hypothesis=hypothesis)
        return dict(res) if isinstance(res, dict) else {}

    def undo(self) -> dict[str, Any]:
        """Check whether ACTION7 (undo) is supported and available."""
        res = self._call("undo")
        return dict(res) if isinstance(res, dict) else {}

    def budget(self) -> dict[str, Any]:
        """Query action budget, timer presence, and probe limits."""
        res = self._call("budget")
        return dict(res) if isinstance(res, dict) else {}

    def hook_register(self, hook_name: str, code: str) -> dict[str, Any]:
        """Register model hook function on host."""
        res = self._call("hook_register", hook_name=hook_name, code=code)
        return dict(res) if isinstance(res, dict) else {}

    def hook(self, hook_name: str, code: str) -> dict[str, Any]:
        """Alias for hook_register (Rule 05 В§4)."""
        return self.hook_register(hook_name=hook_name, code=code)

    def test_law(self, law_fn: Callable[..., Any], before: Any = None, action: Any = None, after: Any = None) -> dict[str, Any]:
        """Evaluate a law predicate law_*(before, action, after) -> bool | None (Plan v8)."""
        try:
            val = law_fn(before, action, after)
            v_name = "FOLLOW" if val is True else ("NULL" if val is False else "OMIT")
            return {"ok": True, "verdict": v_name, "holds": val is True, "is_null": val is False, "is_unobserved": val is None}
        except Exception as exc:
            return {"ok": False, "verdict": "NULL", "error": str(exc), "holds": False, "is_null": True, "is_unobserved": False}

    def run(self, actions: Any, category: str = "planned") -> Any:
        """Execute action(s) wrapped in begin_step / end_step prediction verification (Rule 05 В§4, В§5)."""
        if isinstance(actions, dict) and "actions" in actions and isinstance(actions["actions"], (list, tuple)):
            items = list(actions["actions"])
        elif isinstance(actions, (str, dict, int)):
            items = [actions]
        elif isinstance(actions, (list, tuple)):
            items = list(actions)
        else:
            raise TypeError("wm.run expects an action, plan dict, or list of actions")

        results: list[Any] = []
        for item in items:
            self.begin_step(action=item, category=category)
            action_res = None
            try:
                if self._action is not None:
                    action_res = self._action([item])
            except BaseException as exc:
                if type(exc).__name__ in ("KnownNoOpActionError", "KnownDeathActionError"):
                    end_verdict = self.end_step()
                    results.append({
                        "action_result": {"blocked": True, "reason": str(exc), "error_type": type(exc).__name__},
                        "verification": end_verdict,
                    })
                    break
                raise

            end_verdict = self.end_step()
            combined = {
                "action_result": action_res,
                "verification": end_verdict,
            }
            results.append(combined)

            # Plan v8 В§1.1: Halt immediately on NULL / MISMATCH in current state (no reset)
            is_mismatch = (
                end_verdict.get("verdict") in ("MISMATCH", "NULL")
                or end_verdict.get("brusentsov_verdict") == "NULL"
                or end_verdict.get("is_null") is True
            )
            if is_mismatch:
                break

            if isinstance(action_res, dict):
                for flag in ("game_over", "level_completed", "run_complete", "done", "stopped_early"):
                    if action_res.get(flag):
                        return results[-1] if len(items) == 1 else results

        return results[-1] if len(items) == 1 else results


def get_sandbox_client_source() -> str:
    """Return self-contained source code of WorldModelClient for bootstrap injection."""
    return inspect.getsource(WorldModelClient)
