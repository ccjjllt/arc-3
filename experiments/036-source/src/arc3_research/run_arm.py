"""Run one public OFFLINE research arm against an already loaded model server.

The notebook owns SGLang and the overall GPU deadline. Each arm gets a fresh
CPU process so its scheduler clocks, imported switches and agent histories do
not leak into the next arm. This module never launches or stops the model.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import pickle
import signal
import sys
import threading
import time
import traceback
from typing import Any

from arc3_research.experiment_config import parse_arm_environment


def _stage(name: str, **fields: Any) -> None:
    print("[ARC3_RESEARCH] " + json.dumps({
        "stage": name,
        "utc": datetime.now(timezone.utc).isoformat(),
        **fields,
    }, ensure_ascii=False, default=str), flush=True)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False,
                                    default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def _source_paths(bundle_dir: Path) -> list[str]:
    return [str(candidate) for repo in sorted((bundle_dir / "src").iterdir(),
                                              reverse=True)
            for candidate in (repo / "src", repo) if candidate.is_dir()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _game_ids(source: str) -> list[str]:
    path = Path(source)
    if "," in source or not path.is_file():
        value = [part.strip() for part in source.split(",")]
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    values = value.get("game_ids") if isinstance(value, dict) else value
    if not isinstance(values, list) or not values:
        raise ValueError("game-list must be a nonempty array or {game_ids: [...]}.")
    if not all(isinstance(item, str) and item.strip() for item in values):
        raise ValueError("game-list entries must be nonempty game ID strings.")
    if len(set(values)) != len(values):
        raise ValueError("game-list contains duplicate IDs.")
    return values


def run_arm(args: argparse.Namespace) -> int:
    started = time.monotonic()
    job_dir = args.working_dir.resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "arm": args.arm,
        "status": "initializing",
        "operation_mode": "OFFLINE",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "budget_seconds": args.budget_seconds,
        "soft_deadline_grace_seconds": 0,
        "cancel_drain_timeout_seconds": 120,
        "active_streams": 10,
        "warmup_action_games": int(getattr(args, "warmup_action_games", 0)),
        "model_server_owned_by_runner": False,
    }
    metadata_path = job_dir / "arm-metadata.json"
    patch = None
    transient_patch = None
    program_patch = None
    animation_patch = None
    current_data_patch = None
    native_patch = None
    grounding_prefix = None
    grounded_patch = None
    checked_patch = None
    stall_patch = None
    repair_patch = None
    admission_patch = None
    executable_repair_patch = None
    persistent_python_patch = None
    segmentation_runs_patch = None
    solved_memory_patch = None
    executable_plan_patch = None
    main_reasoning_patch = None
    community_baselines = None
    timing_patch = None
    deadline_patch = None
    scheduler_patch = None
    bm = None
    exit_code = 0
    _write_json(metadata_path, metadata)
    _stage("arm_initializing", arm=args.arm, working_dir=job_dir,
           budget_seconds=args.budget_seconds)
    try:
        if os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}:
            raise RuntimeError("run_arm only supports public OFFLINE research.")
        if args.budget_seconds <= 0:
            raise ValueError("budget-seconds must be positive.")
        research_family = getattr(args, "research_family", None)
        auxiliary_mode = getattr(args, "auxiliary_reasoning_mode", None)
        model_dir = getattr(args, "model_dir", None)
        if research_family == "035":
            expected_modes = {"executable_plan_A": None, "executable_plan_B": "off",
                              "executable_plan_C": "low"}
            if args.arm not in expected_modes or auxiliary_mode != expected_modes[args.arm]:
                raise ValueError("035 requires A without a branch, B off, and C low.")
            if args.arm == "executable_plan_C":
                recorded_inputs = json.loads((job_dir.parent / "input-paths.json").read_text())
                resolved_model = Path(recorded_inputs["paths"]["model"]).resolve(strict=True)
                if model_dir is None or model_dir.resolve(strict=True) != resolved_model:
                    raise ValueError("035 C must use the model actually resolved in input-paths.json.")
                model_dir = resolved_model
                metadata["mounted_model_dir"] = str(model_dir)
                metadata["mounted_model_path_source"] = str(job_dir.parent / "input-paths.json")
            elif model_dir is not None:
                raise ValueError("Only 035 C performs mounted-template verification.")
            metadata["research_family"] = "035"
            metadata["auxiliary_reasoning_mode"] = auxiliary_mode or "none"
        elif research_family == "036":
            if args.arm not in ("main_medium", "baseline") or auxiliary_mode is not None:
                raise ValueError("036 requires main_medium or baseline, without auxiliary reasoning controls.")
            recorded_inputs = json.loads((job_dir.parent / "input-paths.json").read_text())
            resolved_model = Path(recorded_inputs["paths"]["model"]).resolve(strict=True)
            if model_dir is None or model_dir.resolve(strict=True) != resolved_model:
                raise ValueError("036 must use the model actually resolved in input-paths.json in both arms.")
            model_dir = resolved_model
            metadata["research_family"] = "036"
            metadata["main_reasoning_mode"] = "medium" if args.arm == "main_medium" else "default"
            metadata["mounted_model_dir"] = str(model_dir)
            metadata["mounted_model_path_source"] = str(job_dir.parent / "input-paths.json")
        elif research_family is not None or auxiliary_mode is not None or model_dir is not None or args.arm in ("executable_plan_C", "main_medium"):
            raise ValueError("Explicit reasoning controls require their matching 035 or 036 experiment.")
        overrides = parse_arm_environment(getattr(args, "environment_json", "{}"))
        if args.arm == "tail_80k" and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "1", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError("tail_80k requires its explicit frozen environment.")
        if args.arm == "pace_1x" and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "1",
        }:
            raise ValueError("pace_1x requires its explicit frozen environment.")
        if args.arm in ("native_values", "native") and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError("native_values requires frozen baseline scheduler.")
        if args.arm == "observation_grounding" and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError("observation_grounding requires frozen baseline scheduler.")
        if args.arm == "grounded_state" and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError("grounded_state requires frozen baseline scheduler.")
        if args.arm == "stall_probe" and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError("stall_probe requires frozen baseline scheduler.")
        if args.arm in ("checked_execution", "expect_check") and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError(args.arm + " requires frozen baseline scheduler.")
        if args.arm in ("repair_A", "repair_B") and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError(args.arm + " requires frozen baseline scheduler.")
        if args.arm == "admission_009" and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError("admission_009 requires frozen baseline scheduler.")
        if args.arm in ("executable_plan", "executable_plan_A", "executable_plan_B", "executable_plan_C") and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError(args.arm + " requires frozen baseline scheduler.")
        if args.arm == "baseline" and overrides not in ({
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }, {}):
            raise ValueError("baseline requires frozen scheduler or empty env.")
        if research_family == "036" and overrides != {
            "ARC3_PRIORITY_TAIL_LOOKUP": "remaining", "ARC3_PRIORITY_PACE": "0",
        }:
            raise ValueError("036 requires the explicit frozen scheduler in both arms.")
        os.environ.update(overrides)
        metadata["environment_overrides"] = overrides
        if args.arm == "observation_grounding":
            # This child alone receives the prefix, before any ToolAgent is built.
            from arc3_research.observation_grounding import install_observation_grounding
            grounding_prefix = install_observation_grounding()
            metadata["observation_grounding"] = grounding_prefix.snapshot()
        requested_ids = _game_ids(args.game_list)
        bundle_dir = args.bundle_dir.resolve()
        sys.path[:0] = _source_paths(bundle_dir)
        # The launcher's baseline setup_env must already be in this process.
        os.environ["TAAF_RUN_AS_SUBMISSION"] = "0"
        os.environ["TAAF_MINIMAL_DIAGNOSTICS"] = "0"
        os.environ["ARC3_MAX_ACTIVE_STREAMS"] = "10"
        # Historical research omitted warmup. New comparisons may explicitly
        # retain the formal 009 behavior; never silently change old configs.
        warmup_games = int(getattr(args, "warmup_action_games", 0))
        if warmup_games not in (0, 1):
            raise ValueError("warmup-action-games must be 0 or 1")
        os.environ["ARC3_WARMUP_ACTION_GAMES"] = str(warmup_games)
        os.environ["RECORDINGS_DIR"] = str(job_dir / "server_recording")
        os.environ["ONLY_RESET_LEVELS"] = "true"

        import arc_agi
        import taaf.game_api
        from arc3_research.goal_evidence import install_goal_evidence
        from arc3_research.transient_history import install_transient_history
        from arc3_research.program_state import install_program_state

        if research_family == "036":
            # Verify the mounted server template in both fresh CPU processes.
            # Install before unpickling the benchmark/analyzer, so every main
            # request sees the selected default. The reference never installs.
            from inference.agent import tool_agent
            from arc3_research.main_reasoning import verify_main_reasoning_template
            proof = verify_main_reasoning_template(
                model_dir, job_dir / "main-reasoning-template.json")
            if tool_agent._summary_interval_tokens() != 0:
                raise RuntimeError("036 requires the original disabled summary schedule in both arms.")
            generation_settings = {
                "max_output_tokens": tool_agent._LOCAL_ANALYZER_MAX_OUTPUT,
                "enable_thinking": tool_agent._LOCAL_ANALYZER_ENABLE_THINKING,
                "temperature": tool_agent._LOCAL_ANALYZER_TEMPERATURE,
                "top_p": tool_agent._LOCAL_ANALYZER_TOP_P,
                "top_k": tool_agent._LOCAL_ANALYZER_TOP_K,
            }
            if generation_settings != {"max_output_tokens": 12288,
                                       "enable_thinking": True,
                                       "temperature": 0.7, "top_p": 0.95, "top_k": 20}:
                raise RuntimeError("036 requires unchanged 009 output, thinking and sampling settings in both arms.")
            metadata["main_generation_settings"] = generation_settings
            metadata["main_reasoning_template"] = proof
            metadata["main_reasoning_patch_installed"] = False
            if args.arm == "main_medium":
                from arc3_research.main_reasoning import install_main_reasoning
                main_reasoning_patch = install_main_reasoning(
                    default_effort="medium", template_verification=proof)
                metadata["main_reasoning_patch_installed"] = True
                metadata["main_reasoning"] = main_reasoning_patch.snapshot()

        env_dir = Path(os.environ.get(
            "ARC3_RESEARCH_ENV_DIR",
            "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/environment_files",
        )).resolve()
        if not env_dir.is_dir():
            raise FileNotFoundError(f"Public environment directory not found: {env_dir}")
        arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE,
                                environments_dir=str(env_dir))
        available_ids = [item.game_id for item in arcade.available_environments]
        ids = []
        for requested in requested_ids:
            matches = ([requested] if requested in available_ids else
                       [game_id for game_id in available_ids if game_id.startswith(requested)])
            if len(matches) != 1:
                raise ValueError(f"Expected one public environment for {requested!r}; got {matches}")
            ids.append(matches[0])
        if len(set(ids)) != len(ids):
            raise ValueError("Different requested prefixes resolved to the same game ID.")
        with (bundle_dir / "deploy_target.pkl").open("rb") as file:
            target = pickle.load(file)
        target.actual_run_as_submission = False
        target.is_competition_rerun = False
        target.run_as_submission = False
        with (bundle_dir / "benchmark_initial.pkl").open("rb") as file:
            bm = pickle.load(file)
        bm.label = f"research-{args.arm}"
        bm.job_dir = job_dir
        bm.n_passes = 1
        bm.game_weights = None
        bm.solver.start_local_server = False
        bm.solver.concurrency = len(ids)
        bm.solver.max_runtime_s_per_game = float(args.budget_seconds)
        bm.solver.max_generated_tokens_per_game = None
        bm.solver.analyzer_timeout = 900.0
        bm.solver.max_actions_per_game = None
        bm.solver.save_request_logs = True
        bm.solver.cancel_drain_timeout_s = 120.0
        spec = taaf.game_api.ArcadeSpec(
            operation_mode=arc_agi.OperationMode.OFFLINE,
            environments_dir=str(env_dir),
        )
        bm.games = [taaf.game_api.GameAPI(env_name=game_id, arcade_spec=spec)
                    for game_id in ids]
        patch = install_goal_evidence(enabled=args.arm == "goal_evidence")
        transient_patch = install_transient_history(enabled=args.arm == "transient_history")
        program_patch = install_program_state(enabled=args.arm == "program_state")
        if args.arm == "retrievable_animation":
            # The reference arm never imports or installs this intervention.
            from arc3_research.retrievable_animation import install_retrievable_animation
            animation_patch = install_retrievable_animation()
        if args.arm == "current_data":
            from arc3_research.current_data import install_current_data
            current_data_patch = install_current_data()
        if args.arm in ("native_values", "native"):
            from arc3_research.native_values import install_native_values
            native_patch = install_native_values()
        if args.arm == "grounded_state":
            from arc3_research.grounded_state import install_grounded_state
            grounded_patch = install_grounded_state()
        if args.arm in ("checked_execution", "expect_check"):
            from arc3_research.checked_action import install_checked_execution
            checked_patch = install_checked_execution()
        if args.arm == "stall_probe":
            from arc3_research.stall_probe import install_stall_probe
            stall_patch = install_stall_probe()
        if args.arm in ("repair_A", "repair_B"):
            from arc3_research.failure_repair import install_failure_repair
            repair_patch = install_failure_repair()
        if args.arm == "admission_009":
            # Candidate installs before timing/observer; uninstalls after them.
            from arc3_research.admission_order import install_admission_order
            admission_patch = install_admission_order()
        if args.arm == "program_repair":
            from arc3_research.program_repair import install_program_repair
            executable_repair_patch = install_program_repair()
        if args.arm == "persistent_python":
            from arc3_research.persistent_python import install_persistent_python
            persistent_python_patch = install_persistent_python()
        if args.arm == "segmentation_runs":
            from arc3_research.segmentation_runs import install_segmentation_runs
            segmentation_runs_patch = install_segmentation_runs()
        if args.arm == "solved_level_memory":
            from arc3_research.solved_level_memory import install_solved_level_memory
            solved_memory_patch = install_solved_level_memory()
        if args.arm == "executable_plan":
            from arc3_research.executable_plan import install_executable_plan
            executable_plan_patch = install_executable_plan(min_remaining_seconds=180)
        if os.environ.get("ARC3_COMMUNITY_DEVELOPMENT") == "1":
            from taaf.game_api import GameAPI
            from arc3_research.community import clear_unreliable_baselines
            community_baselines = clear_unreliable_baselines(GameAPI)
        if getattr(args, "request_deadline", False):
            from arc3_research.request_deadline import install_request_deadline
            deadline_patch = install_request_deadline()
        if getattr(args, "inference_timing", False):
            from arc3_research.inference_timing import install_inference_timing
            timing_patch = install_inference_timing()
        if getattr(args, "scheduler_observer", False):
            from arc3_research.scheduler_observer import install_scheduler_observer
            scheduler_patch = install_scheduler_observer()
        git_status = bundle_dir / "git_status.txt"
        if git_status.is_file():
            (job_dir / "git_status.txt").write_bytes(git_status.read_bytes())
        relevant_env = {key: value for key, value in os.environ.items()
                        if key.startswith(("ARC3_", "MULTIMODAL_"))
                        and not any(word in key.upper() for word in ("KEY", "SECRET", "TOKEN"))}
        # Names ending in TOKENS are benign budgets; retain those explicitly.
        for key in ("ARC3_CONTEXT_DRAIN_TOKENS", "LOCAL_ANALYZER_MAX_OUTPUT",
                    "LOCAL_ANALYZER_TEMPERATURE", "LOCAL_ANALYZER_TOP_P",
                    "LOCAL_ANALYZER_TOP_K", "LOCAL_ANALYZER_CONTEXT_WINDOW"):
            if key in os.environ:
                relevant_env[key] = os.environ[key]
        metadata.update({
            "status": "running",
            "game_ids": ids,
            "requested_game_ids": requested_ids,
            "game_count": len(ids),
            "game_order_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            "normalized_budget_seconds": 532 * 60 * len(ids) // 110,
            "concurrency": len(ids),
            "n_passes": 1,
            "analyzer_timeout_seconds": 900.0,
            "source_sha256": {
                "run_arm.py": _sha256(Path(__file__)),
                "goal_evidence.py": _sha256(Path(__file__).with_name("goal_evidence.py")),
                "transient_history.py": _sha256(Path(__file__).with_name("transient_history.py")),
                "program_state.py": _sha256(Path(__file__).with_name("program_state.py")),
                "benchmark_initial.pkl": _sha256(bundle_dir / "benchmark_initial.pkl"),
                "tool_agent.py": _sha256(bundle_dir / "src/ARC3-Inference/inference/agent/tool_agent.py"),
            },
            "environment": relevant_env,
            "public_environment_dir": str(env_dir),
        })
        if animation_patch is not None:
            metadata["source_sha256"]["retrievable_animation.py"] = _sha256(
                Path(__file__).with_name("retrievable_animation.py"))
            metadata["retrievable_animation"] = animation_patch.snapshot()
        if current_data_patch is not None:
            metadata["source_sha256"]["current_data.py"] = _sha256(
                Path(__file__).with_name("current_data.py"))
            metadata["current_data"] = current_data_patch.snapshot()
        if native_patch is not None:
            metadata["source_sha256"]["native_values.py"] = _sha256(
                Path(__file__).with_name("native_values.py"))
            metadata["native_values"] = native_patch.snapshot()
        if grounding_prefix is not None:
            metadata["source_sha256"]["observation_grounding.py"] = _sha256(
                Path(__file__).with_name("observation_grounding.py"))
        if grounded_patch is not None:
            for name in ("grounded_state.py", "observation_representation.py"):
                metadata["source_sha256"][name] = _sha256(Path(__file__).with_name(name))
            metadata["grounded_state"] = grounded_patch.snapshot()
        if checked_patch is not None:
            for name in ("checked_action.py", "checked_execution.py"):
                metadata["source_sha256"][name] = _sha256(Path(__file__).with_name(name))
            metadata["checked_execution"] = checked_patch.snapshot()
        if stall_patch is not None:
            for name in ("stall_probe.py", "bounded_probe.py"):
                metadata["source_sha256"][name] = _sha256(Path(__file__).with_name(name))
            metadata["stall_probe"] = stall_patch.tracker.snapshot()
        if repair_patch is not None:
            for name in ("failure_repair.py", "probe_budget.py"):
                metadata["source_sha256"][name] = _sha256(Path(__file__).with_name(name))
            metadata["failure_repair"] = repair_patch.snapshot()
            for conv in ("experiments/026-fork-inputs.json",
                         "experiments/026-fork-conv.json.gz.b64"):
                candidate = (Path("/kaggle/research") / conv if
                             (Path("/kaggle/research") / conv).is_file() else
                             Path(__file__).resolve().parents[2] / conv)
                metadata["source_sha256"][conv] = _sha256(candidate)
        if admission_patch is not None:
            metadata["source_sha256"]["admission_order.py"] = _sha256(
                Path(__file__).with_name("admission_order.py"))
            metadata["admission_order"] = admission_patch.snapshot()
        if research_family == "036":
            metadata["source_sha256"]["main_reasoning.py"] = _sha256(
                Path(__file__).with_name("main_reasoning.py"))
        if args.arm in ("executable_plan", "executable_plan_A", "executable_plan_B", "executable_plan_C"):
            for name in ("executable_plan.py", "executable_plan_contract.py",
                         "executable_plan_context.py", "program_repair.py"):
                metadata["source_sha256"][name] = _sha256(Path(__file__).with_name(name))
            if executable_plan_patch is not None:
                metadata["executable_plan"] = executable_plan_patch.snapshot()
            else:
                metadata["source_sha256"]["executable_plan_forks.py"] = _sha256(
                    Path(__file__).with_name("executable_plan_forks.py"))
                metadata["diagnostic_forced_trigger"] = args.arm in ("executable_plan_B", "executable_plan_C")
                if research_family == "035":
                    metadata["source_sha256"]["reasoning_mode.py"] = _sha256(
                        Path(__file__).with_name("reasoning_mode.py"))
        metadata["inference_timing_enabled"] = bool(getattr(args, "inference_timing", False))
        if timing_patch is not None:
            metadata["source_sha256"]["inference_timing.py"] = _sha256(
                Path(__file__).with_name("inference_timing.py"))
            metadata["inference_timing"] = timing_patch.snapshot()
        for name, installed in (("request_deadline", deadline_patch),
                                ("scheduler_observer", scheduler_patch)):
            metadata[name + "_enabled"] = installed is not None
            if installed is not None:
                metadata["source_sha256"][name + ".py"] = _sha256(Path(__file__).with_name(name + ".py"))
                metadata[name] = installed.snapshot()

        async def play() -> None:
            loop = asyncio.get_running_loop()

            def request_stop() -> None:
                metadata["external_stop_requested"] = True
                _stage("arm_stop_requested", arm=args.arm)
                bm.request_stop()

            loop.add_signal_handler(signal.SIGUSR1, request_stop)
            soft_end = datetime.now() + timedelta(seconds=args.budget_seconds)
            metadata["benchmark_started_utc"] = datetime.now(timezone.utc).isoformat()
            metadata["soft_end_local"] = soft_end.isoformat()
            _write_json(metadata_path, metadata)
            _stage("arm_benchmark_started", arm=args.arm, games=ids,
                   soft_end_local=soft_end.isoformat())
            benchmark_start = time.monotonic()
            try:
                await bm.run(soft_end_time=soft_end, runtime_environment=target,
                             minimal_diagnostics=False)
            finally:
                metadata["benchmark_wall_seconds"] = time.monotonic() - benchmark_start
                loop.remove_signal_handler(signal.SIGUSR1)

        if args.arm in ("executable_plan_A", "executable_plan_B", "executable_plan_C"):
            from arc3_research.executable_plan_forks import run_forks
            bm.start_time = datetime.now()
            fork_options = {}
            if research_family == "035":
                fork_options = {"arm_label": args.arm.rsplit("_", 1)[-1],
                                "auxiliary_reasoning_mode": auxiliary_mode,
                                "model_dir": model_dir}
            fork_summary = run_forks(
                bm=bm, job_dir=job_dir, budget_seconds=args.budget_seconds,
                use_plan=args.arm in ("executable_plan_B", "executable_plan_C"),
                **fork_options)
            bm.end_time = datetime.now()
            _write_json(job_dir / "executable-plan-forks.json", fork_summary)
            _write_json(job_dir / "benchmark.json", bm.to_json_dict())
        elif args.arm in ("controller_repair_A", "controller_repair_B"):
            from arc3_research.controller_repair_forks import run_forks
            bm.start_time = datetime.now()
            fork_summary = run_forks(
                bm=bm, job_dir=job_dir, budget_seconds=args.budget_seconds,
                use_repair=args.arm == "controller_repair_B")
            bm.end_time = datetime.now()
            _write_json(job_dir / "controller-repair-forks.json", fork_summary)
            _write_json(job_dir / "benchmark.json", bm.to_json_dict())
        elif args.arm in ("segmentation_forks_A", "segmentation_forks_B"):
            from arc3_research.segmentation_forks import run_forks
            bm.start_time = datetime.now()
            fork_summary = run_forks(
                bm=bm, job_dir=job_dir, budget_seconds=args.budget_seconds,
                use_runs=args.arm == "segmentation_forks_B")
            bm.end_time = datetime.now()
            _write_json(job_dir / "segmentation-forks.json", fork_summary)
            _write_json(job_dir / "benchmark.json", bm.to_json_dict())
        elif args.arm == "repair_forks":
            from arc3_research.program_repair_forks import run_forks
            bm.start_time = datetime.now()
            fork_summary = run_forks(bm=bm, job_dir=job_dir,
                                     budget_seconds=args.budget_seconds)
            bm.end_time = datetime.now()
            _write_json(job_dir / "program-repair-forks.json", fork_summary)
            _write_json(job_dir / "benchmark.json", bm.to_json_dict())
        elif args.arm in ("repair_A", "repair_B"):
            from arc3_research.failure_repair import run_fork_arm
            candidates = [
                Path("/kaggle/research/experiments/026-fork-inputs.json"),
                Path(__file__).resolve().parents[2] / "experiments/026-fork-inputs.json",
            ]
            inputs_path = next((p for p in candidates if p.is_file()), None)
            if inputs_path is None:
                raise FileNotFoundError("026 fork inputs not found in payload or repo.")
            fork_inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
            bm.label = f"research-{args.arm}"
            bm.start_time = datetime.now()
            fork_summary = run_fork_arm(
                bm=bm, job_dir=job_dir, arm=args.arm,
                is_b=(args.arm == "repair_B"), budget_seconds=args.budget_seconds,
                prefix_actions=fork_inputs["actions"])
            bm.end_time = datetime.now()
            _write_json(job_dir / "failure-repair.json", fork_summary)
            _write_json(job_dir / "benchmark.json", bm.to_json_dict())
        else:
            asyncio.run(play())
        metadata["status"] = "completed"
    except asyncio.CancelledError:
        metadata["status"] = "stopped"
        exit_code = 130
    except Exception as exc:
        metadata.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        exit_code = 1
    finally:
        if bm is not None:
            metadata["soft_deadline_fired"] = bool(getattr(bm, "_deadline_fired", False))
            runs = getattr(bm, "game_runs", [])
            metadata["game_state_counts"] = dict(Counter(run.state for run in runs))
            metadata["game_results"] = [{
                "game_id": run.game_id,
                "state": run.state,
                "levels_completed": run.levels_completed,
                "number_of_levels": run.number_of_levels,
                "final_score": run.final_score,
                "actions_per_level": run.actions_per_level,
                "solver_note": run.solver_note,
            } for run in runs]
        if patch is not None:
            _write_json(job_dir / "goal-evidence.json", patch.snapshot())
        if transient_patch is not None:
            _write_json(job_dir / "transient-history.json", transient_patch.snapshot())
        if program_patch is not None:
            _write_json(job_dir / "program-state.json", program_patch.snapshot())
        if animation_patch is not None:
            _write_json(job_dir / "retrievable-animation.json", animation_patch.snapshot())
        # TAAF shutdown(wait=False) can return before cancelled workers leave.
        # Briefly allow completed workers to exit, but never wait without a cap.
        join_end = time.monotonic() + 2.0
        for thread in threading.enumerate():
            if thread.name.startswith("harness-game") and thread.is_alive():
                thread.join(max(0.0, join_end - time.monotonic()))
        live = [thread.name for thread in threading.enumerate()
                if thread.name.startswith("harness-game") and thread.is_alive()]
        metadata.update({
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "wall_seconds": time.monotonic() - started,
            "lingering_worker_threads": live,
            "forced_cpu_process_exit": bool(live),
            "exit_code": exit_code,
        })
        if timing_patch is not None:
            try:
                timing = timing_patch.snapshot()
                timing["snapshot_after_worker_join"] = True
                timing["lingering_worker_threads"] = live
                _write_json(job_dir / "inference-timing.json", timing)
            except Exception as exc:
                # A diagnostic export failure must not rewrite solver outcome.
                metadata["inference_timing_export_error"] = f"{type(exc).__name__}: {exc}"
        if current_data_patch is not None:
            try:
                data = current_data_patch.snapshot()
                data["snapshot_after_worker_join"] = True
                data["lingering_worker_threads"] = live
                _write_json(job_dir / "current-data.json", data)
            except Exception as exc:
                metadata["current_data_export_error"] = f"{type(exc).__name__}: {exc}"
        if native_patch is not None:
            try:
                data = native_patch.snapshot()
                data["snapshot_after_worker_join"] = True
                data["lingering_worker_threads"] = live
                _write_json(job_dir / "native-values.json", data)
            except Exception as exc:
                metadata["native_values_export_error"] = f"{type(exc).__name__}: {exc}"
        for name, installed in (("request-deadline", deadline_patch),
                                ("scheduler-observer", scheduler_patch)):
            if installed is not None:
                try:
                    data = installed.snapshot()
                    data["snapshot_after_worker_join"] = True
                    data["lingering_worker_threads"] = live
                    _write_json(job_dir / (name + ".json"), data)
                except Exception as exc:
                    metadata[name + "_export_error"] = f"{type(exc).__name__}: {exc}"
        if grounding_prefix is not None:
            _write_json(job_dir / "observation-grounding.json", grounding_prefix.snapshot())
            if not live:
                grounding_prefix.uninstall()
        if grounded_patch is not None:
            _write_json(job_dir / "grounded-state.json", grounded_patch.snapshot())
            if not live:
                grounded_patch.uninstall()
        if checked_patch is not None:
            _write_json(job_dir / "checked-execution.json", checked_patch.snapshot())
            if not live:
                checked_patch.uninstall()
        if stall_patch is not None:
            _write_json(job_dir / "stall-probe.json", stall_patch.tracker.snapshot())
            if not live:
                stall_patch.uninstall()
        if repair_patch is not None:
            _write_json(job_dir / "failure-repair-summary.json", repair_patch.snapshot())
        if admission_patch is not None:
            _write_json(job_dir / "admission-order.json", admission_patch.snapshot())
            if not live:
                admission_patch.uninstall()
        if executable_repair_patch is not None:
            _write_json(job_dir / "program-repair-summary.json", executable_repair_patch.snapshot())
            if not live:
                executable_repair_patch.uninstall()
        if persistent_python_patch is not None:
            _write_json(job_dir / "persistent-python-summary.json", persistent_python_patch.snapshot())
            if not live:
                persistent_python_patch.uninstall()
        if segmentation_runs_patch is not None:
            _write_json(job_dir / "segmentation-runs-summary.json", segmentation_runs_patch.snapshot())
            if not live:
                segmentation_runs_patch.uninstall()
        if solved_memory_patch is not None:
            _write_json(job_dir / "solved-level-memory-summary.json", solved_memory_patch.snapshot())
            if not live:
                solved_memory_patch.uninstall()
        if executable_plan_patch is not None:
            _write_json(job_dir / "executable-plan-summary.json", executable_plan_patch.snapshot())
            if not live:
                executable_plan_patch.uninstall()
        if main_reasoning_patch is not None:
            _write_json(job_dir / "main-reasoning-summary.json", main_reasoning_patch.snapshot())
            if not live:
                main_reasoning_patch.uninstall()
        if community_baselines is not None:
            _write_json(job_dir / "community-baselines.json", {
                "dropped": community_baselines,
                "reason": "community baseline_actions are not a human action budget",
            })
        _write_json(metadata_path, metadata)
        _stage("arm_finished", arm=args.arm, status=metadata["status"],
               wall_seconds=metadata["wall_seconds"], exit_code=exit_code,
               game_state_counts=metadata.get("game_state_counts", {}),
               lingering_worker_threads=live)
        if live:
            # Only this disposable CPU runner exits. The independent model
            # server remains alive; the parent must drain/flush before B.
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(exit_code)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True,
                        choices=("baseline", "goal_evidence", "transient_history", "program_state",
                                 "retrievable_animation", "current_data", "tail_80k",
                                 "native_values", "native", "pace_1x", "observation_grounding",
                                 "grounded_state", "checked_execution", "expect_check", "stall_probe",
                                 "repair_A", "repair_B", "admission_009", "repair_forks", "program_repair",
                                 "persistent_python", "segmentation_runs",
                                 "segmentation_forks_A", "segmentation_forks_B",
                                 "solved_level_memory", "controller_repair_A", "controller_repair_B",
                                 "executable_plan", "executable_plan_A", "executable_plan_B", "executable_plan_C",
                                 "main_medium"))
    parser.add_argument("--research-family", choices=("035", "036"),
                        help="Explicit reasoning comparison; omitted for frozen legacy runs.")
    parser.add_argument("--auxiliary-reasoning-mode", choices=("off", "low"),
                        help="035 B is off; C is low. A receives no auxiliary mode.")
    parser.add_argument("--model-dir", type=Path,
                        help="Actual resolved model mount for 035 C or both 036 template verifications.")
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--working-dir", required=True, type=Path,
                        help="Output directory for this arm only.")
    parser.add_argument("--game-list", required=True,
                        help="Comma-separated prefixes, or JSON file with an array/game_ids.")
    parser.add_argument("--budget-seconds", required=True, type=int)
    parser.add_argument("--warmup-action-games", type=int, choices=(0, 1), default=0,
                        help="Explicitly match formal 009 warmup when set to 1.")
    parser.add_argument("--inference-timing", action="store_true",
                        help="Record passive request/gate timing in both confirmation arms.")
    parser.add_argument("--environment-json", default="{}",
                        help="Explicit allowed scheduler environment overrides.")
    parser.add_argument("--request-deadline", action="store_true",
                        help="Recheck cancellation after gate wait and before transport.")
    parser.add_argument("--scheduler-observer", action="store_true",
                        help="Record actual bounded queue/snapshot/selection observations.")
    return run_arm(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
