#!/usr/bin/env python3
"""Export the three real 028 fork checkpoints without future observations.

CPU only: recover accepted source-only functions from tool retention records,
replay the recorded actions, compare with the original request image/events,
and write a self-contained package for the GPU continuation driver.
"""
from __future__ import annotations

import ast
import base64
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", "/tmp/arc3-028-mpl")
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "research/runtime-bundle/src/ARC3-Inference"),
                "/private/tmp/arc3-018-sdk", "/private/tmp/arc3-018-check-deps"]

from PIL import Image
from arcengine import GameAction
from arc_agi import Arcade, OperationMode
from inference.agent.vision_context import ARC_COLOR_MAP
from inference.agent.python_tool_sandbox import run_sandboxed_python
from inference.utils.retained_functions import _function_record, _import_statements

ENV_DIR = ROOT / "research/data/extracted/environment_files"
SPECS = {
    "ft09-0d8bbf25": {"base": "runs/015-native-adoption/baseline", "cut": 27,
                       "record": 30, "analysis_step": 7, "kind": "failure"},
    "tu93-0768757b": {"base": "runs/027-tail-confirm/baseline", "cut": 276,
                       "record": 262, "analysis_step": 46, "kind": "failure"},
    "r11l-495a7899": {"base": "runs/016-pace-allocation-jiyujia/baseline", "cut": 40,
                       "record": 110, "analysis_step": 25, "kind": "control"},
}
STATE_RE = re.compile(r"Current state:\s*step\s+(\d+),\s*level\s+(\d+)", re.I)
RETAIN_RE = re.compile(r"Retained your function\s+([A-Za-z_]\w*)\(")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_content(content) -> str:
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content
                       if isinstance(p, dict) and p.get("type") == "text")
    return str(content or "")


def definitions(code: str) -> tuple[dict[str, str], dict[str, str]]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, TypeError):
        return {}, {}
    imports = {}
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            try:
                imports.update(_import_statements([node]))
            except ValueError:
                pass
    return ({n.name: ast.get_source_segment(code, n) for n in tree.body
             if isinstance(n, ast.FunctionDef) and not n.decorator_list}, imports)


def original_grid(messages, shape):
    """The first image on the final user turn is the actual current frame."""
    last = next(m for m in reversed(messages) if m.get("role") == "user")
    content = last.get("content", [])
    if not isinstance(content, list):
        return None
    part = next((p for p in content if p.get("type") == "image_url"), None)
    if part is None:
        return None
    url = part["image_url"]["url"]
    if not url.startswith("data:image/png;base64,"):
        raise ValueError("Original checkpoint image is not an inline PNG")
    image = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB")
    rows, cols = shape
    inverse = {v: k for k, v in ARC_COLOR_MAP.items()}
    # Existing requests use exact nearest-neighbor board images. Sampling the
    # center avoids changing their palette or interpolating new colors.
    result = []
    for r in range(rows):
        line = []
        for c in range(cols):
            rgb = image.getpixel((int((c + .5) * image.width / cols),
                                  int((r + .5) * image.height / rows)))
            if rgb not in inverse:
                raise ValueError(f"Original frame has nonpalette sample {rgb}")
            line.append(inverse[rgb])
        result.append(line)
    return result


def load_checkpoint(path: Path, cut_record: int):
    calls, accepted, seen, imports = {}, {}, set(), {}
    target = None
    for index, line in enumerate(path.open()):
        if index > cut_record:
            break
        record = json.loads(line)
        for message in record.get("messages", []):
            if message.get("role") == "assistant":
                for call in message.get("tool_calls", []):
                    function = call.get("function", {})
                    if function.get("name") != "python":
                        continue
                    try:
                        code = json.loads(function.get("arguments", "{}"))["code"]
                    except (ValueError, KeyError, TypeError):
                        continue
                    calls[call["id"]] = definitions(code)
            if message.get("role") != "tool":
                continue
            call_id = message.get("tool_call_id")
            if call_id in seen:
                continue
            seen.add(call_id)
            try:
                payload = json.loads(text_content(message.get("content")))
            except ValueError:
                continue
            notes = str(payload.get("function_retention", ""))
            fresh, declared_imports = calls.get(call_id, ({}, {}))
            imports.update(declared_imports)
            for name in RETAIN_RE.findall(notes):
                source = fresh.get(name)
                if source is None:
                    source = accepted.get(name)
                if source is None:
                    raise ValueError(f"No source for accepted retained function {name}")
                # 009 enables explicit import retention. Rebuild the source-only
                # bundle from the imports used by this accepted definition.
                _, _, reads = _function_record(source, retain_imports=True)
                source = "\n".join([*(imports[n] for n in sorted(reads & imports.keys())), source])
                accepted[name] = source
        if index == cut_record:
            target = record
    if not target or target.get("event") != "request":
        raise ValueError(f"Cut {cut_record} is not a model request boundary")
    last_user = next(m for m in reversed(target["messages"]) if m.get("role") == "user")
    text = text_content(last_user.get("content"))
    marker = "Your retained functions from earlier Python calls "
    if marker in text:
        tail = text.rsplit(marker, 1)[1].split(": ", 1)[1]
        tail = tail.split(". These are your previous definitions", 1)[0]
        names = list(dict.fromkeys(re.findall(r"\b([A-Za-z_]\w*)\(", tail)))
    else:
        names = []
    missing = set(names) - accepted.keys()
    if missing:
        raise ValueError(f"Missing accepted definitions at checkpoint: {sorted(missing)}")
    kept = {name: accepted[name] for name in names}
    messages = copy.deepcopy(target["messages"])
    removed_images = 0
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            removed_images += sum(p.get("type") != "text" for p in content)
            m["content"] = [p for p in content if p.get("type") == "text"]
    match = STATE_RE.search(text)
    if not match:
        raise ValueError("Checkpoint has no step/level metadata")
    return target, messages, kept, int(match.group(1)), int(match.group(2)), removed_images


def replay(game_id: str, actions: list[dict]):
    arcade = Arcade(environments_dir=str(ENV_DIR), operation_mode=OperationMode.OFFLINE,
                    recordings_dir=f"/tmp/arc3-028-package-{game_id}")
    env = arcade.make(game_id, seed=0, render_mode=None, save_recording=False)
    if env is None or env.reset() is None:
        raise RuntimeError(f"Failed to reset {game_id}")
    for action in actions:
        obs = env.step(GameAction.from_name(action["id"]), data=action["data"] or None)
        if obs is None:
            raise RuntimeError(f"Missing replay frame in {game_id}")
    game = env._game
    raw = game.camera.render(game.current_level.get_sprites())
    grid = [[int(c) for c in row] for row in raw.tolist()]
    return grid, int(game.level_index) + 1


def main():
    package = {"schema_version": 1, "forks": {}}
    report = {"gpu_seconds": 0, "repair_calls": 0, "forks": {}}
    for game_id, spec in SPECS.items():
        base = ROOT / spec["base"]
        req_path = base / f"{game_id}_p0_requests.jsonl"
        bench_path = base / "benchmark.json"
        benchmark = json.loads(bench_path.read_text())
        run = next(g for g in benchmark["game_runs"] if g["game_id"] == game_id)
        actions = [{"id": h["action"]["id"], "data": dict(h["action"].get("data") or {})}
                   for h in run["history"][:spec["cut"]]]
        target, messages, kept, step, level, removed_images = load_checkpoint(req_path, spec["record"])
        grid, replay_level = replay(game_id, actions)
        image_grid = original_grid(target["messages"], (len(grid), len(grid[0])))
        if image_grid is None or image_grid != grid or replay_level != level:
            raise ValueError(f"Original checkpoint frame differs from replay for {game_id}")
        current = {"grid": grid, "step": step, "level": level}
        sandbox = run_sandboxed_python(
            code="print('checkpoint retained functions restored')", timeout_seconds=10,
            initial_state={"current_frame": current, "history": []},
            action_handler=lambda _: (_ for _ in ()).throw(RuntimeError("no env actions during preparation")),
            kept_functions=list(kept.values()), retain_imports=True)
        restored = {item["name"] for item in sandbox.get("keepable_functions", [])}
        if sandbox.get("error") or restored != set(kept):
            raise ValueError(f"Retained definitions failed restoration: missing={sorted(set(kept)-restored)}, "
                             f"error={sandbox.get('error')}, rejected={sandbox.get('retention_rejected')}")
        env_sources = {str(p.relative_to(ROOT)): digest(p.read_bytes())
                       for p in sorted((ENV_DIR / game_id.split("-", 1)[0]).rglob("*.py"))}
        entry = {"cut": spec["cut"], "cut_record": spec["record"],
                 "analysis_step": spec["analysis_step"], "kind": spec["kind"],
                 "max_extra_actions": 30, "max_extra_seconds": 250, "seed": 0,
                 "actions": actions, "messages": messages, "kept_functions": kept,
                 "retain_imports": True,
                 "current_frame": current, "environment_sources": env_sources,
                 "source": {"benchmark": str(bench_path.relative_to(ROOT)),
                            "request_log": str(req_path.relative_to(ROOT)),
                            "request_sha256": digest(req_path.read_bytes())}}
        package["forks"][game_id] = entry
        report["forks"][game_id] = {
            "cut": spec["cut"], "cut_record": spec["record"], "step": step, "level": level,
            "actions": len(actions), "messages": len(messages), "removed_images": removed_images,
            "kept_function_names": list(kept), "retained_sandbox_restore_passed": True,
            "replay_matches_original_request_image": True,
            "grid_sha256": digest(json.dumps(grid).encode()),
            "environment_sources": env_sources,
        }
        print(game_id, "frame matched", "messages", len(messages), "retained", len(kept), flush=True)
    out = ROOT / "experiments/028-fork-package.json"
    raw = json.dumps(package, separators=(",", ":"), ensure_ascii=False).encode()
    out.write_bytes(raw + b"\n")
    packed = base64.b64encode(gzip.compress(raw, mtime=0)).decode()
    out.with_suffix(".json.gz.b64").write_text(packed + "\n")
    report.update(package=str(out.relative_to(ROOT)), package_sha256=digest(raw + b"\n"),
                  package_bytes=len(raw) + 1, packed_bytes=len(packed) + 1)
    report_path = ROOT / "experiments/028-minimal-repair/package-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "forks"}, indent=2))


if __name__ == "__main__":
    main()
