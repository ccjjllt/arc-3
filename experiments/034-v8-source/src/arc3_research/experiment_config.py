"""Narrow, explicit research-arm environment overrides (never credentials)."""
from __future__ import annotations

import json
from pathlib import Path
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
    if any(a in ("executable_plan", "executable_plan_A", "executable_plan_B") for a in arms):
        expected = {arm: {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"}
                    for arm in arms}
        if environments != expected or config.get("n_passes_per_arm") != 1:
            raise ValueError("034 requires explicit unchanged scheduling and one pass.")
        if config.get("active_streams") != 10 or not config.get("require_rtx_pro6000"):
            raise ValueError("034 keeps the 10-stream RTX PRO 6000 serving contract.")
        if any(a in ("executable_plan_A", "executable_plan_B") for a in arms):
            delivery_v3 = config.get("research_revision") in (3, 4, 5, 6, 7, 8)
            transport = config.get("fork_transport", "separate_gzip_base64")
            if (transport not in ("separate_gzip_base64", "combined_xz_base64")
                    or (not delivery_v3 and transport != "separate_gzip_base64")):
                raise ValueError("Combined checkpoint transport is only supported by delivery diagnostics.")
            expected_order = (["executable_plan_B", "executable_plan_A"] if delivery_v3
                              else ["executable_plan_A", "executable_plan_B"])
            if (arms != expected_order
                    or config.get("reference_arm") != "executable_plan_A"
                    or config.get("games") != ["ft09-0d8bbf25", "su15-1944f8ab"]):
                raise ValueError("034 diagnostic order must match its revision on frozen ft09/su15 only.")
            if (config.get("requested_arm_seconds") != 600
                    or config.get("continuation_seconds") != 450
                    or config.get("max_continuation_actions") != 60
                    or config.get("hard_limit_seconds") != (6300 if config.get("research_revision") == 5 else 7200)
                    or config.get("startup_limit_seconds") != 4200
                    or config.get("warmup_action_games") != 0
                    or config.get("request_deadline") is not False
                    or config.get("skip_blanket_model_precache") is not False):
                raise ValueError("034 diagnostic budget/startup contract differs from its frozen design.")
            if not all(config.get(key) is True for key in (
                "strict_arm_budget", "require_cache_flush", "require_cache_flush_log",
                "require_drained_workers", "require_complete_pool", "native_payload_cells",
            )):
                raise ValueError("034 diagnostic retains isolated, complete and drained arm contracts.")
            if delivery_v3:
                expected_delivery = {
                    "compact_context": True, "thinking": False,
                    "max_prompt_tokens": 16384, "max_output_tokens": 4096,
                    "max_request_seconds": 60, "max_extra_processing_seconds": 120,
                    "max_actions_per_contract": 3, "contract_lifetime": "current_short_plan",
                    "token_count_source": "served_model_tokenize_endpoint"}
                if config.get("research_revision") in (4, 5, 6, 7, 8):
                    expected_delivery["submission_tool"] = "submit_program"
                if config.get("candidate_delivery") != expected_delivery:
                    raise ValueError("034 delivery revision differs from its frozen contract.")
                if config.get("research_revision") in (5, 6, 7, 8) and config.get("hypothesis_context") != {
                    "source": "latest_prior_assistant_natural_language",
                    "max_messages": 2, "max_text_characters": 12000,
                    "per_message_text_characters": 8000,
                    "copy": "verbatim_provenance_segments", "status": "unverified_may_be_stale",
                }:
                    raise ValueError("034 v5-v8 require bounded provenance-labelled prior hypotheses.")
                if config.get("research_revision") in (6, 7, 8) and config.get("object_evidence") != {
                    "geometry": "same_color_4_connected_components",
                    "source": "current_ascii_and_two_recent_real_transitions",
                    "roles": "model_hypotheses_only",
                    "runtime_attribute": "frame.object_evidence",
                }:
                    raise ValueError("034 v6-v8 require observed component geometry, never host-assigned roles.")
                if config.get("research_revision") == 7 and config.get("short_program_feedback") != {
                    "max_nonempty_lines": 120, "max_code_bytes": 12000,
                    "max_followup_requests": 1,
                    "quota_shared_with_real_mismatch_repair": True,
                    "zero_action_failure_stages": ["extract", "plan_validation", "initial_prediction"],
                    "validation_feedback_prior_text": "provenance_only_no_old_natural_language",
                }:
                    raise ValueError("034 v7 requires short programs and one shared bounded validation/mismatch follow-up.")
                if config.get("research_revision") == 8 and config.get("short_program_feedback") != {
                    "max_nonempty_lines": None, "max_code_bytes": 12000,
                    "allow_literal_helper_defaults": True,
                    "static_diagnostics": "bounded_aggregate",
                    "max_followup_requests": 1,
                    "quota_shared_with_real_mismatch_repair": True,
                    "zero_action_failure_stages": ["extract", "plan_validation", "initial_prediction"],
                    "validation_feedback_prior_text": "provenance_only_no_old_natural_language",
                }:
                    raise ValueError("034 v8 requires byte/AST-bounded delivery, literal helper defaults and aggregated static feedback.")
        elif arms not in (["baseline", "executable_plan"], ["executable_plan"]):
            raise ValueError("034 natural runs require the isolated executable_plan arm, optionally after baseline.")
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
    if "checked_execution" in arms:
        expected = {arm: {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"}
                    for arm in ("baseline", "checked_execution")}
        if arms != ["baseline", "checked_execution"] or environments != expected:
            raise ValueError("021 requires baseline then checked_execution with unchanged scheduling.")
        if (config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1
                or config.get("warmup_action_games") != 0
                or config.get("reference_arm") != "baseline"):
            raise ValueError("021 requires 10 stream capacity, one pass, no warmup and baseline reference.")
        if not all(config.get(key) is True for key in (
            "inference_timing", "scheduler_observer", "request_deadline",
            "strict_arm_budget", "require_cache_flush", "require_cache_flush_log",
            "require_drained_workers", "require_complete_pool", "preflight_before_serving",
            "native_payload_cells",
        )):
            raise ValueError("021 retains the shared budget, diagnostics and startup contracts.")
    if "expect_check" in arms:
        expected = {arm: {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"}
                    for arm in ("baseline", "expect_check")}
        if arms != ["baseline", "expect_check"] or environments != expected:
            raise ValueError("022 requires baseline then expect_check with unchanged scheduling.")
        if len(config.get("games") or []) != 3 or config.get("requested_arm_seconds") != 600:
            raise ValueError("022 is a 3-game, 600-second probe, not another full pool.")
        if (config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1
                or config.get("warmup_action_games") != 0
                or config.get("reference_arm") != "baseline"
                or config.get("hard_limit_seconds") != 3600):
            raise ValueError("022 keeps the scheduler contract and a 3600-second session cap.")
        if not all(config.get(key) is True for key in (
            "inference_timing", "scheduler_observer", "request_deadline",
            "strict_arm_budget", "require_cache_flush", "require_cache_flush_log",
            "require_drained_workers", "require_complete_pool", "preflight_before_serving",
            "native_payload_cells",
        )):
            raise ValueError("022 retains the shared budget, diagnostics and startup contracts.")
    if "stall_probe" in arms:
        expected = {arm: {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"}
                    for arm in ("baseline", "stall_probe")}
        if arms != ["baseline", "stall_probe"] or environments != expected:
            raise ValueError("Stall probe requires baseline then stall_probe with unchanged scheduling.")
        games = list(config.get("games") or [])
        historical = games == ["m0r0-492f87ba", "r11l-495a7899", "sb26-7fbdac44"]
        failure_pair = games == ["tt03-63be02fb", "ih01-v1"] and config.get("community_development") is True
        if historical:
            if config.get("requested_arm_seconds") != 600 or config.get("hard_limit_seconds") != 3600:
                raise ValueError("023 stays a 3-game, 600-second probe inside a 3600-second cap.")
        elif failure_pair:
            if config.get("requested_arm_seconds") != 1800 or config.get("hard_limit_seconds") != 5400:
                raise ValueError("024 is the two recorded failures at 1800 seconds, session cap 5400.")
        else:
            raise ValueError("Stall probe only runs the recorded 023 trio or the 024 failure pair.")
        if (config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1
                or config.get("warmup_action_games") != 0 or config.get("reference_arm") != "baseline"):
            raise ValueError("Stall probe keeps one pass, no warmup, and the baseline reference.")
        if not config.get("require_rtx_pro6000"):
            raise ValueError("Stall probe must refuse a non-RTX session before loading the model.")
    if "admission_009" in arms:
        expected = {arm: {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"}
                    for arm in ("baseline", "admission_009")}
        if arms != ["baseline", "admission_009"] or environments != expected:
            raise ValueError("025 requires baseline then admission_009 with unchanged scheduling.")
        if (config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1
                or config.get("warmup_action_games") != 0
                or config.get("reference_arm") != "baseline"):
            raise ValueError("025 keeps one pass, no warmup, and the baseline reference.")
        if len(config.get("games") or []) != 25:
            raise ValueError("025 is the official 25-game pool, not a subset.")
        if config.get("requested_arm_seconds") != 7254 or config.get("hard_limit_seconds") != 18000:
            raise ValueError("025 keeps the 014/016 arm budget (7254s) and session cap (18000s).")
        if not all(config.get(key) is True for key in (
            "inference_timing", "scheduler_observer", "request_deadline",
            "strict_arm_budget", "require_cache_flush", "require_cache_flush_log",
            "require_drained_workers", "require_complete_pool", "preflight_before_serving",
            "native_payload_cells",
        )):
            raise ValueError("025 retains the shared budget, diagnostics and startup contracts.")
        if not config.get("require_rtx_pro6000"):
            raise ValueError("025 must refuse a non-RTX session before loading the model.")
    if "repair_A" in arms or "repair_B" in arms:
        expected = {arm: {"ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0"}
                    for arm in ("repair_A", "repair_B")}
        if arms != ["repair_A", "repair_B"] or environments != expected:
            raise ValueError("026 requires repair_A then repair_B with unchanged scheduling.")
        if (config.get("active_streams") != 10 or config.get("n_passes_per_arm") != 1
                or config.get("warmup_action_games") != 0
                or config.get("reference_arm") != "repair_A"):
            raise ValueError("026 keeps one pass, no warmup, and the repair_A reference.")
        if (sorted(config.get("games") or []) != sorted(
                ["ft09-0d8bbf25", "tr87-cd924810", "r11l-495a7899"])):
            raise ValueError("026 runs the four recorded failure prefixes only.")
        if config.get("requested_arm_seconds") != 1800 or config.get("hard_limit_seconds") != 5400:
            raise ValueError("026 is two 1800-second fork arms inside a 5400-second cap.")
        if not all(config.get(key) is True for key in (
            "inference_timing", "scheduler_observer", "request_deadline",
            "strict_arm_budget", "require_cache_flush", "require_cache_flush_log",
            "require_drained_workers", "require_complete_pool", "preflight_before_serving",
            "native_payload_cells",
        )):
            raise ValueError("026 retains the shared budget, diagnostics and startup contracts.")
        if not config.get("require_rtx_pro6000"):
            raise ValueError("026 must refuse a non-RTX session before loading the model.")
    if config.get("community_development"):
        allow = config.get("community_allowlist")
        games = list(config.get("games") or [])
        failure_pair = games == ["tt03-63be02fb", "ih01-v1"] and "stall_probe" in arms
        if failure_pair:
            if not isinstance(allow, list) or any(game_id not in allow for game_id in games):
                raise ValueError("The failure pair must stay inside the embedded development allowlist.")
        elif arms != ["baseline"] or allow != games:
            raise ValueError("Community development runs the existing agent on its embedded allowlist only.")
        # The Kaggle payload has no experiments/ tree. When the local split file
        # is present, it must agree with that embedded list.
        split = Path(__file__).resolve().parents[2] / "experiments/020-community/solver-allowlists.json"
        if split.is_file():
            data = json.loads(split.read_text())
            if any(game_id not in data["development"] for game_id in games):
                raise ValueError("Community games must come from the frozen development list.")
            if set(games) & (set(data["frozen"]) | set(data["reserve"])):
                raise ValueError("Community development run includes a reserve or frozen id.")
            if not failure_pair and games != data["development"]:
                raise ValueError("Community development games must stay the frozen 12-id list.")
        if not failure_pair and (
                config.get("requested_arm_seconds") != 1800 or config.get("hard_limit_seconds") != 3600
                or config.get("n_passes_per_arm") != 1 or config.get("warmup_action_games") != 0):
            raise ValueError("Community development uses one 1800-second pass inside a 3600-second cap.")
