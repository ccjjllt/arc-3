"""Narrow, explicit research-arm environment overrides (never credentials)."""
from __future__ import annotations

import json
from typing import Any


ALLOWED_ARM_ENVIRONMENT = {
    "ARC3_PRIORITY_TAIL_LOOKUP": frozenset({"remaining", "1"}),
    "ARC3_PRIORITY_PACE": frozenset({"0", "1"}),
}


def arm_environment(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("Arm environment must be a JSON object.")
    result = {}
    for key, setting in value.items():
        if key not in ALLOWED_ARM_ENVIRONMENT or not isinstance(setting, str):
            raise ValueError(f"Unsupported research environment key/type: {key!r}")
        if setting not in ALLOWED_ARM_ENVIRONMENT[key]:
            raise ValueError(f"Unsupported setting for {key}: {setting!r}")
        result[key] = setting
    return result


def parse_arm_environment(value: str) -> dict[str, str]:
    return arm_environment(json.loads(value))


def validate_config(config: dict[str, Any]) -> None:
    arms = config["arm_order"]
    if not arms or len(arms) != len(set(arms)):
        raise ValueError("arm_order must contain distinct arms.")
    environments = config.get("arm_environment", {})
    if not isinstance(environments, dict) or set(environments) - set(arms):
        raise ValueError("arm_environment must name only configured arms.")
    for value in environments.values():
        arm_environment(value)
    if "tail_80k" in arms:
        expected = {
            "baseline": {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"},
            "tail_80k": {"ARC3_PRIORITY_TAIL_LOOKUP": "1", "ARC3_PRIORITY_PACE": "0"},
        }
        if set(arms) != set(expected) or environments != expected:
            raise ValueError("tail_80k requires the frozen baseline/tail-only environment pair.")
        if config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1:
            raise ValueError("The tail comparison must retain 10 streams and one pass.")
        if not all(config.get(key) is True for key in (
            "inference_timing", "scheduler_observer", "request_deadline",
            "strict_arm_budget", "require_cache_flush", "preflight_before_serving",
        )):
            raise ValueError("The tail comparison requires paired diagnostics, deadline checks and strict startup contracts.")
    if "pace_1x" in arms:
        expected = {
            "baseline": {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"},
            "pace_1x": {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "1"},
        }
        if set(arms) != set(expected) or environments != expected:
            raise ValueError("pace_1x requires the frozen baseline/pace-only environment pair.")
        if config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1:
            raise ValueError("The pace comparison must retain 10 streams and one pass.")
        if not all(config.get(key) is True for key in (
            "inference_timing", "scheduler_observer", "request_deadline",
            "strict_arm_budget", "require_cache_flush", "preflight_before_serving",
        )):
            raise ValueError("The pace comparison requires paired diagnostics, deadline checks and strict startup contracts.")
    if any(a in ("native_values", "native") for a in arms):
        # Scheduler frozen to baseline; single-factor is native handoff only.
        for arm in arms:
            if environments.get(arm, {}) != {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"}:
                raise ValueError("native_values arms require frozen baseline scheduler.")
        if config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1:
            raise ValueError("Native comparison must retain 10 streams and one pass.")
    if "observation_grounding" in arms:
        expected = {arm: {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"}
                    for arm in ("baseline", "observation_grounding")}
        if arms != ["baseline", "observation_grounding"] or environments != expected:
            raise ValueError("018 requires baseline then observation_grounding with unchanged scheduling.")
        if (config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1
                or config.get("warmup_action_games") != 0
                or config.get("reference_arm") != "baseline"):
            raise ValueError("018 requires 10 stream capacity, one pass, no warmup and baseline reference.")
        if not all(config.get(key) is True for key in (
            "inference_timing", "scheduler_observer", "request_deadline",
            "strict_arm_budget", "require_cache_flush", "require_cache_flush_log",
            "require_drained_workers", "require_complete_pool", "preflight_before_serving",
            "native_payload_cells",
        )):
            raise ValueError("018 requires the shared strict budget, diagnostics and startup contracts.")
    if "grounded_state" in arms:
        expected = {arm: {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"}
                    for arm in ("baseline", "grounded_state")}
        if arms != ["baseline", "grounded_state"] or environments != expected:
            raise ValueError("020 requires baseline then grounded_state with unchanged scheduling.")
        if (config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1
                or config.get("warmup_action_games") != 0
                or config.get("reference_arm") != "baseline"):
            raise ValueError("020 requires 10 stream capacity, one pass, no warmup and baseline reference.")
        if not all(config.get(key) is True for key in (
            "inference_timing", "scheduler_observer", "request_deadline",
            "strict_arm_budget", "require_cache_flush", "require_cache_flush_log",
            "require_drained_workers", "require_complete_pool", "preflight_before_serving",
            "native_payload_cells",
        )):
            raise ValueError("020 retains the shared budget, diagnostics and startup contracts.")
