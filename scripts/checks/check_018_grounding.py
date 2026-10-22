#!/usr/bin/env python3
"""Manually run 018 CPU contracts and native-cell packaging; never solve games.

Use --build to rebuild the local Notebook first. Imports the real frozen
ToolAgent, constructs agents and reads their tool schemas, but calls no model,
sandbox, environment, or engine action. This is not an automated test suite.
"""
from __future__ import annotations

import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "experiments/018-observation-grounding.json"
NOTEBOOK = ROOT / "notebooks/018-observation-grounding"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def baseline_environment() -> dict[str, str]:
    """Read only literal setup dictionaries; never execute the Notebook cell."""
    path = ROOT / "research/notebooks/cli-baseline/arc-agi-3-milestone-2-solution.ipynb"
    source = "".join(json.loads(path.read_text())["cells"][4]["source"])
    assert "USE_PRIORITY_SCHEDULING = True" in source
    tree = ast.parse(source[source.index("setup_env = {"):])

    def value(node):
        if isinstance(node, ast.Name):
            return {"SERVER_BASE_URL": "http://cpu.invalid/v1", "SERVED_MODEL_NAME": "cpu-no-model"}[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
            left, right = value(node.left), value(node.right)
            return left + right if isinstance(node.op, ast.Add) else left * right
        if isinstance(node, ast.Dict):
            return {value(k): value(v) for k, v in zip(node.keys, node.values)}
        return ast.literal_eval(node)

    settings = value(tree.body[0].value)
    priority = tree.body[1]
    assert isinstance(priority, ast.If) and isinstance(priority.test, ast.Name)
    assert priority.test.id == "USE_PRIORITY_SCHEDULING"
    settings.update(value(priority.body[0].value.args[0]))
    settings["ARC3_WARMUP_ACTION_GAMES"] = "0"
    return {k: str(v) for k, v in settings.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-path", type=Path, required=True)
    parser.add_argument("--extra-python-path", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    out = args.output_dir or ROOT / "experiments/018-grounding-cpu" / datetime.now(timezone.utc).strftime("cpu-%Y%m%dT%H%M%SZ")
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {"status": "checking", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "executable": sys.executable, "checks": [],
              "network_attempts": 0, "http_attempts": 0, "model_calls": 0,
              "sandbox_calls": 0, "game_actions": 0,
              "limits": ["CPU construction and packaging only; no model adoption, score, throughput or remote runtime claim.",
                         "The framework inserts no model calls or actions; the instruction may alter natural requests, tokens, and actions.",
                         "Real ToolAgent is imported and constructed; run_arm game/solver execution is not exercised."]}

    def check(name: str, condition: bool, **details: object) -> None:
        report["checks"].append({"name": name, "passed": bool(condition), **details})
        if not condition:
            raise AssertionError(name)

    def audit(event: str, values: tuple) -> None:
        if event in {"socket.connect", "socket.getaddrinfo"}:
            report["network_attempts"] += 1
            raise RuntimeError("018 CPU checks prohibit network access")

    sys.addaudithook(audit)
    sys.path[:0] = [str(args.sdk_path), str(ROOT / "src"),
                   str(ROOT / "research/runtime-bundle/src/ARC3-Inference"),
                   str(ROOT / "research/runtime-bundle/src/tufa-arc-agi-framework/src")]
    sys.path.extend(str(p) for p in args.extra_python_path)
    os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/arc3-018-mpl")
    os.environ["MPLBACKEND"] = "Agg"
    inherited_prefix = os.environ.get("ARC3_SYSTEM_PROMPT_PREFIX")
    prefix = None
    try:
        check("ambient_prefix_empty", not (inherited_prefix or "").strip())
        settings = baseline_environment()
        os.environ.update(settings)
        report["baseline_environment"] = settings
        report["cpu_environment_substitutions"] = "Only model ID/base URL are CPU placeholders; warmup0 matches the research runner. Setup dictionaries were AST-read, not executed."
        from arc3_research.experiment_config import validate_config
        from arc3_research.observation_grounding import (
            GROUNDING_PREFIX, PREFIX_ENV, install_observation_grounding,
        )
        config = json.loads(CONFIG.read_text())
        validate_config(config)
        check("frozen_screen_pool_and_budget", config["games"] == [
            "ft09-0d8bbf25", "tr87-cd924810", "ar25-0c556536", "sb26-7fbdac44"]
            and config["game_count"] == 4 and config["requested_arm_seconds"] == 1000
            and config["hard_limit_seconds"] == 5400
            and config["kernel_id"] == "jiyujia/arc3-018-observation-grounding")
        rejected = []
        for label, mutate in [
            ("mixed_candidate", lambda c: c["arm_order"].append("native_values")),
            ("changed_schedule", lambda c: c["arm_environment"]["observation_grounding"].update(ARC3_PRIORITY_PACE="1")),
            ("disabled_preflight", lambda c: c.update(preflight_before_serving=False)),
            ("disabled_deadline", lambda c: c.update(request_deadline=False)),
            ("unbounded_environment_prefix", lambda c: c["arm_environment"]["observation_grounding"].update(ARC3_SYSTEM_PROMPT_PREFIX="other")),
        ]:
            invalid = copy.deepcopy(config)
            mutate(invalid)
            try:
                validate_config(invalid)
            except ValueError:
                rejected.append(label)
        check("single_factor_config_rejections", len(rejected) == 5, rejected=rejected)

        import requests
        def no_http(*a, **kw):
            report["http_attempts"] += 1
            raise RuntimeError("018 CPU checks prohibit HTTP")
        requests.sessions.Session.request = no_http
        from inference.agent import tool_agent as ta
        from inference.framework.solver import _HarnessGameSession
        check("frozen_runtime_sources", all(
            sha(ROOT / "research/runtime-bundle" / rel) == expected
            for rel, expected in config["runtime_source_sha256"].items()))
        methods = {name: value for name, value in vars(ta.ToolAgent).items() if callable(value)}
        originals = {"system_builder": ta._build_system_prompt,
                     "play": _HarnessGameSession.play,
                     "python_description": ta._PYTHON_TOOL_DESCRIPTION}
        agent_kwargs = dict(model="cpu-no-model", provider="vllm",
                            base_url="http://cpu.invalid/v1", api_key="cpu-not-a-secret")
        baseline = ta.ToolAgent(**agent_kwargs)
        baseline_tools = baseline._tools(out / "synthetic-baseline/state.json")
        baseline_prompt = baseline._system_prompt
        os.environ[PREFIX_ENV] = "existing-nonempty-prefix"
        try:
            install_observation_grounding()
        except RuntimeError:
            check("nonempty_prefix_rejected_without_overwrite", os.environ[PREFIX_ENV] == "existing-nonempty-prefix")
        else:
            raise AssertionError("nonempty prefix accepted")
        os.environ.pop(PREFIX_ENV)
        prefix = install_observation_grounding()
        candidate = ta.ToolAgent(**agent_kwargs)
        candidate_tools = candidate._tools(out / "synthetic-candidate/state.json")
        check("real_toolagent_prefix_exact", candidate._system_prompt == GROUNDING_PREFIX + "\n\n" + baseline_prompt)
        check("existing_baseline_instance_unchanged", baseline._system_prompt == baseline_prompt)
        check("tools_schema_equal", candidate_tools == baseline_tools and len(candidate_tools) == 1)
        check("toolagent_behavior_objects_unchanged", all(vars(ta.ToolAgent)[k] is v for k, v in methods.items())
              and ta._build_system_prompt is originals["system_builder"]
              and _HarnessGameSession.play is originals["play"]
              and ta._PYTHON_TOOL_DESCRIPTION == originals["python_description"])
        keys = ["_timeout", "_tool_steps", "_python_timeout", "_yield_seconds", "_yield_tokens",
                "_max_output_tokens", "_tool_output_tokens", "_context_budget_tokens", "_history_messages",
                "_step_env_callback", "_last_step_summary", "_last_action_call_result", "_kept_functions"]
        check("agent_controls_and_memory_equal", all(getattr(candidate, k, None) == getattr(baseline, k, None) for k in keys))
        check("zero_agent_usage", baseline.generated_tokens == candidate.generated_tokens == 0)
        try:
            install_observation_grounding()
        except RuntimeError:
            check("duplicate_install_rejected", os.environ[PREFIX_ENV] == GROUNDING_PREFIX)
        else:
            raise AssertionError("duplicate prefix accepted")
        report["candidate"] = prefix.snapshot()
        report["baseline_prompt_sha256"] = hashlib.sha256(baseline_prompt.encode()).hexdigest()
        report["candidate_prompt_sha256"] = hashlib.sha256(candidate._system_prompt.encode()).hexdigest()
        save(out / "toolagent-prompts-and-schema.json", {
            "baseline_prompt": baseline_prompt, "candidate_prompt": candidate._system_prompt,
            "tool_schema": baseline_tools, "synthetic_state_paths_only": True})
        prefix.uninstall()
        prefix.uninstall()
        check("uninstall_restores_baseline", PREFIX_ENV not in os.environ
              and ta.ToolAgent(**agent_kwargs)._system_prompt == baseline_prompt)
        os.environ[PREFIX_ENV] = " \n"
        whitespace = install_observation_grounding()
        whitespace.uninstall()
        check("whitespace_prefix_restored_exactly", os.environ[PREFIX_ENV] == " \n")
        os.environ.pop(PREFIX_ENV)

        # Exercise the real paired preflight in isolated processes; never serving.
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(sys.path)
        env["ARC3_MAX_ACTIVE_STREAMS"] = "10"
        command = [sys.executable, "-B", "-m", "arc3_research.preflight", "--bundle-dir",
                   str(ROOT / "research/runtime-bundle"), "--config", str(CONFIG)]
        for label, extra, expect_success in [("preflight", {}, True),
                                              ("preflight-prefix-conflict", {PREFIX_ENV: "ambient-conflict"}, False)]:
            process = subprocess.run(command + ["--report", str(out / (label + ".json"))],
                                     env={**env, **extra}, text=True, capture_output=True, timeout=120)
            (out / (label + ".stdout.txt")).write_text(process.stdout)
            (out / (label + ".stderr.txt")).write_text(process.stderr)
            result = json.loads((out / (label + ".json")).read_text())
            check(label, (process.returncode == 0) == expect_success
                  and result["status"] == ("passed" if expect_success else "failed"),
                  returncode=process.returncode, error=result.get("error"))
        check("preflight_does_not_set_parent_prefix", PREFIX_ENV not in os.environ)

        if args.build:
            process = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/build_experiment.py"),
                                      "--config", str(CONFIG)], text=True, capture_output=True, timeout=60)
            (out / "build.stdout.txt").write_text(process.stdout)
            (out / "build.stderr.txt").write_text(process.stderr)
            check("notebook_build", process.returncode == 0, returncode=process.returncode)
        report["packaging"] = check_notebook(config, out)
        check("native_notebook_packaging", report["packaging"]["passed"])
        report["dependency_origins"] = {name: str(getattr(importlib.import_module(name), "__file__", None))
                                        for name in ["numpy", "matplotlib", "pydantic", "fastapi", "IPython", "nbformat"]}
        report["source_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in [
            CONFIG, Path(__file__), ROOT / "src/arc3_research/observation_grounding.py",
            ROOT / "src/arc3_research/experiment_config.py", ROOT / "src/arc3_research/run_arm.py",
            ROOT / "src/arc3_research/preflight.py", ROOT / "scripts/build_experiment.py"]}
        check("no_network_or_http", report["network_attempts"] == report["http_attempts"] == 0)
        report["status"] = "passed"
    except BaseException as exc:
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if prefix is not None and prefix.active and os.environ.get("ARC3_SYSTEM_PROMPT_PREFIX") == GROUNDING_PREFIX:
            prefix.uninstall()
        if inherited_prefix is None:
            os.environ.pop("ARC3_SYSTEM_PROMPT_PREFIX", None)
        else:
            os.environ["ARC3_SYSTEM_PROMPT_PREFIX"] = inherited_prefix
        save(out / "report.json", report)
        save(out.parent / "latest.json", {"report": str((out / "report.json").relative_to(ROOT)),
                                          "status": report["status"]})
        print(json.dumps({"status": report["status"], "checks": len(report["checks"]),
                          "report": str(out / "report.json")}, indent=2))


def check_notebook(config: dict, out: Path) -> dict:
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.utils.capture import capture_output
    import nbformat
    notebook_path = NOTEBOOK / "experiment.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)
    manifest = json.loads((NOTEBOOK / "build-manifest.json").read_text())
    metadata = json.loads((NOTEBOOK / "kernel-metadata.json").read_text())
    assert manifest["config"] == config
    assert manifest["notebook_sha256"] == sha(notebook_path)
    for relative, expected in manifest["source_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert metadata["id"] == config["kernel_id"]
    assert metadata["is_private"] and metadata["enable_gpu"] and not metadata["enable_internet"]
    assert metadata["machine_shape"] == "NvidiaRtxPro6000" and "id_no" not in metadata
    preflight = [i for i, c in enumerate(notebook.cells) if "arc3_research.preflight" in c.source
                 and "subprocess.run" in c.source and not c.source.startswith("%%writefile")]
    serving = [i for i, c in enumerate(notebook.cells) if c.source.startswith("# Paste this entire file into the launcher cell.")]
    assert len(preflight) == len(serving) == 1 and preflight[0] < serving[0]
    transformed_count = 0
    transformer = TransformerManager()
    for i, c in enumerate(notebook.cells):
        if c.cell_type != "code":
            continue
        transformed = transformer.transform_cell(c.source)
        compile(transformed, f"018-cell-{i}", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        tree = ast.parse(transformed)
        assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                       and n.func.id in {"exec", "compile", "eval"} for n in ast.walk(tree))
        transformed_count += 1
    helpers = []
    shell = InteractiveShell.instance()
    with tempfile.TemporaryDirectory(prefix="arc3-018-notebook-") as directory:
        temporary = Path(directory)
        for i, c in enumerate(notebook.cells):
            if not c.source.startswith("%%writefile /kaggle/research/"):
                continue
            header, body = c.source.split("\n", 1)
            relative = header.removeprefix("%%writefile /kaggle/research/")
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with capture_output():
                result = shell.run_cell("%%writefile " + str(target) + "\n" + body, store_history=False)
            result.raise_error()
            assert sha(target) == manifest["source_hashes"][relative], relative
            compile(target.read_text(), str(target), "exec")
            helpers.append({"path": relative, "sha256": sha(target), "bytes": target.stat().st_size})
        expected_helpers = {p for p in manifest["source_hashes"] if p.startswith("src/arc3_research/")}
        expected_helpers.add("scripts/summarize_experiment.py")
        assert {h["path"] for h in helpers} == expected_helpers
        source_nb = json.loads((ROOT / "research/notebooks/cli-baseline/arc-agi-3-milestone-2-solution.ipynb").read_text())
        original_patch = "".join(source_nb["cells"][2]["source"])
        patches = [c.source for c in notebook.cells if c.source.startswith("%%writefile /kaggle/harness-changes.patch")]
        assert patches == [original_patch]
        patch_file = temporary / "harness-changes.patch"
        with capture_output():
            result = shell.run_cell(original_patch.replace("/kaggle/harness-changes.patch", str(patch_file), 1), store_history=False)
        result.raise_error()
        assert patch_file.read_bytes().endswith(b"\n")
        process = subprocess.run(["git", "apply", "--stat", str(patch_file)], text=True, capture_output=True, check=True)
        patch_hash = sha(patch_file)
    result = {"passed": True, "notebook_sha256": sha(notebook_path), "cells": len(notebook.cells),
              "compiled_code_cells": transformed_count, "helpers": helpers,
              "inherited_patch_unchanged": True, "written_patch_sha256": patch_hash,
              "git_apply_stat_returncode": process.returncode,
              "preflight_before_serving": True, "executed_cells": "Only native writefile cells redirected to a temporary directory"}
    save(out / "notebook-checks.json", result)
    return result


if __name__ == "__main__":
    main()
