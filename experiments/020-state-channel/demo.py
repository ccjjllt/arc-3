#!/usr/bin/env python3
"""Two saved-public-frame -> generic program consumers, in the real CPU sandbox.

No transcript code is executed. All snippets below are newly authored examples.
The frame files are observations, never game source or internal game objects.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-path", type=Path, default=Path("/private/tmp/arc3-018-sdk"))
    parser.add_argument("--extra-python-path", type=Path, action="append", default=[])
    args = parser.parse_args()
    out = Path(__file__).resolve().parent
    sys.path[:0] = [str(ROOT / "src"), str(args.sdk_path),
                   str(ROOT / "research/runtime-bundle/src/ARC3-Inference"),
                   str(ROOT / "research/runtime-bundle/src/tufa-arc-agi-framework/src")]
    sys.path.extend(str(p) for p in args.extra_python_path)
    os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/arc3-020-mpl")
    os.environ["MPLBACKEND"] = "Agg"
    report = {"kind": "saved-public-frame-program-consumption", "status": "running",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "network_attempts": 0, "model_calls": 0,
              "game_actions": 0, "sandbox_calls": 0, "demonstrations": []}

    def deny_network(event, arguments):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            report["network_attempts"] += 1
            raise RuntimeError("020 CPU demonstration prohibits network")
    sys.addaudithook(deny_network)

    # Read the original literal setup_env through the existing CPU helper; no
    # Notebook cell or model code is executed by this helper.
    spec = importlib.util.spec_from_file_location("setup018", ROOT / "scripts/check_018_grounding.py")
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    os.environ.update(setup.baseline_environment())
    if os.environ.get("ARC3_SYSTEM_PROMPT_PREFIX", "").strip():
        raise RuntimeError("Start the demonstration with an empty system prefix")
    from arc3_research.grounded_state import (
        GROUND_STATE_PREFIX, GroundedStateError, install_grounded_state, read_region,
    )
    from arc3_research.observation_representation import ARC_SYMBOLS
    from inference.agent import tool_agent as ta, python_tool_sandbox as sandbox
    agent_kwargs = dict(model="cpu-no-model", provider="vllm",
                        base_url="http://cpu.invalid/v1", api_key="cpu-not-a-secret")
    baseline = ta.ToolAgent(**agent_kwargs)
    originals = {"runner": ta.run_sandboxed_python, "tool": ta.ToolAgent._run_python_tool,
                 "bootstrap": sandbox._SANDBOX_BOOTSTRAP}
    patch = install_grounded_state()
    try:
        candidate = ta.ToolAgent(**agent_kwargs)
        report["integration"] = {
            "actual_toolagent_constructor": True,
            "prefix_exact": candidate._system_prompt == GROUND_STATE_PREFIX + "\n\n" + baseline._system_prompt,
            "tool_schema_unchanged": candidate._tools(out / "unused/state.json") == baseline._tools(out / "unused/state.json"),
            "python_runner_identity_unchanged": ta.run_sandboxed_python is originals["runner"],
            "python_tool_identity_unchanged": ta.ToolAgent._run_python_tool is originals["tool"],
        }
        assert all(report["integration"].values())
        report["patch"] = patch.snapshot()
        save(out / "prompts-and-tool-schema.json", {
            "baseline_prompt": baseline._system_prompt, "candidate_prompt": candidate._system_prompt,
            "tool_schema": candidate._tools(out / "unused/state.json")})

        def load_frame(relative, line_number):
            path = ROOT / relative
            event = json.loads(next(line for i, line in enumerate(path.open(), 1) if i == line_number))
            rows = event["board_ascii"].splitlines()
            assert rows == ["".join(ARC_SYMBOLS[v] for v in row) for row in event["board"]]
            frame = {"ascii": "\n".join(rows), "step": event["action_num"], "level": event["level"],
                     "shape": [len(rows), len(rows[0])], "grid": event["board"]}
            source = {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "line": line_number, "event_type": event["type"],
                      "action_num": event["action_num"], "analysis_step": event["analysis_step"]}
            return frame, source

        def no_action(*args, **kwargs):
            report["game_actions"] += 1
            raise AssertionError("No demonstration may request an action")

        def consume(label, frame, source, code):
            save(out / (label + "-frame.json"), {"source": source, "frame": frame})
            (out / (label + "-consumer.py")).write_text(code)
            result = ta.run_sandboxed_python(code=code, timeout_seconds=10,
                                             initial_state={"current_frame": frame, "history": [],
                                                            "valid_actions": [], "last_action_call_result": {}},
                                             action_handler=no_action)
            report["sandbox_calls"] += 1
            save(out / (label + "-result.json"), result)
            if result.get("error"):
                raise AssertionError(result["error"])
            report["demonstrations"].append({"label": label, "source": source,
                                            "consumer": label + "-consumer.py",
                                            "result": result["result"]})
            return result["result"]

        ar25, ar25_source = load_frame(
            "runs/018-observation-grounding/observation_grounding/artifacts/ar25-0c556536_p0_events.jsonl", 177)
        ar25_code = '''def occupied_blocks(cells, origin, block_size, minimum_pixels, color):
    # Generic projection into an explicitly chosen block lattice, not a game solver.
    counts = {}
    for row, values in enumerate(cells):
        for col, value in enumerate(values):
            if value == color:
                block = ((origin[0] + row) // block_size, (origin[1] + col) // block_size)
                counts[block] = counts.get(block, 0) + 1
    return sorted(block for block, count in counts.items() if count >= minimum_pixels)

region = current_frame.region((9, 42, 29, 62), foreground="B")
observed_blocks = occupied_blocks(region.cells, region.origin, 3, 7, "B")
probe = current_frame.region((24, 51, 26, 56), foreground="B")
result = {"observed_blocks": observed_blocks, "source": region.source,
          "probe_source": probe.source, "probe_rows": probe.raw_rows,
          "probe_mask": probe.mask, "probe_positions": probe.positions(),
          "consumer_input": "region.cells and region.origin passed directly; no copied block table"}
'''
        result = consume("ar25", ar25, ar25_source, ar25_code)
        assert len(result["observed_blocks"]) == 13
        assert [8, 18] in result["observed_blocks"] and [8, 17] not in result["observed_blocks"]
        assert result["probe_rows"] == ["bbbBBB", "bbbBbB", "bbbBBB"]
        assert len(result["probe_positions"]) == 8

        tr87, tr87_source = load_frame(
            "runs/007-program-state/program_state/artifacts/tr87-cd924810_p0_events.jsonl", 34)
        tr87_code = '''def equal_color_masks(left, right):
    # Exact comparison. Rotation, reflection and semantic identity are not assumed.
    return left == right

region = current_frame.region((23, 6, 27, 10), foreground="B")
other = current_frame.region((41, 26, 45, 30), foreground="B")
same = equal_color_masks(region.mask, other.mask)
# Select a node derived from current segmentation without transcribing its rectangle.
node = next(node for node in current_frame.segmentation["nodes"]
               if node["color"] == "B" and node["boundary"]
               and max(p[0] for p in node["boundary"]) - min(p[0] for p in node["boundary"]) < 10
               and max(p[1] for p in node["boundary"]) - min(p[1] for p in node["boundary"]) < 10)
node_region = current_frame.region_from_node(node, foreground="B")
result = {"equal": same, "rows": region.raw_rows, "mask": region.mask,
          "sources": [region.source, other.source], "node_source": node_region.source,
          "node_observed_pixel_count": len(node_region.positions()),
          "consumer_input": "two current_frame mask tuples passed directly to comparison"}
'''
        result = consume("tr87", tr87, tr87_source, tr87_code)
        assert result["equal"] is True
        assert result["rows"] == ["PPBBB", "PPBPB", "BBBBB", "BPBPP", "BBBPP"]

        # A small manual contract check, separate from the real subprocess demos.
        # Swapping an observation object here is not an engine action.
        first = SimpleNamespace(ascii="Bb\nbB", shape=(2, 2), step=1, level=1)
        current = [first]
        region = read_region(first, lambda: current[0], (0, 0, 1, 1), foreground="B")
        historical_cells, historical_source = region.cells, region.source
        current[0] = SimpleNamespace(ascii="BB\nbB", shape=(2, 2), step=2, level=1)
        failures = []
        for label, operation in [
            ("stale_region", lambda: region.cells),
            ("stale_frame", lambda: read_region(first, lambda: current[0], (0, 0, 1, 1))),
            ("unknown_symbol", lambda: read_region(current[0], lambda: current[0], (0, 0, 1, 1), foreground="?")),
            ("out_of_bounds", lambda: read_region(current[0], lambda: current[0], (0, 0, 2, 1))),
        ]:
            try:
                operation()
            except GroundedStateError as exc:
                failures.append({"case": label, "explicit_error": str(exc)})
        assert len(failures) == 4 and historical_cells == (("B", "b"), ("b", "B"))
        report["manual_contract"] = {"explicit_failures": failures,
                                     "detached_history_still_available": historical_cells,
                                     "detached_history_source": historical_source}
        report["status"] = "completed"
    finally:
        patch.uninstall()
        report["baseline_restored"] = sandbox._SANDBOX_BOOTSTRAP == originals["bootstrap"]
        report["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
            "src/arc3_research/grounded_state.py", "src/arc3_research/observation_representation.py",
            "src/arc3_research/run_arm.py", "src/arc3_research/experiment_config.py",
            "src/arc3_research/preflight.py", "experiments/020-state-channel/demo.py")}
        save(out / "cpu-demo-report.json", report)
    print(json.dumps({k: report[k] for k in ("status", "sandbox_calls", "network_attempts", "model_calls", "game_actions")}))


if __name__ == "__main__":
    main()
