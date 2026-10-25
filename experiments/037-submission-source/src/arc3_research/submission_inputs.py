"""Locate 009's attached inputs without requiring public game environments.

Adapted from the input resolver exercised by experiment 007 v2. This module
only resolves files; it does not import the research harness or any patches.
"""
from __future__ import annotations

import json
from pathlib import Path
import time


def resolve_submission_inputs(
    input_root: str | Path = "/kaggle/input", *, timeout_seconds: float = 60,
    report_path: str | Path | None = None,
) -> dict[str, str]:
    root = Path(input_root)
    specs = {
        "bundle": (
            "datasets/dfranzen/taaf-kaggle-source-bundle-copy",
            "taaf-kaggle-bundle.json", "taaf-kaggle-source-bundle-copy",
            ("src/ARC3-Inference", "benchmark_initial.pkl", "deploy_target.pkl"),
        ),
        "wheelhouse": (
            "datasets/dfranzen/pennyroyal-v253", "requirements.lock",
            "pennyroyal-v253", ("wheels", "hot_tokens_64k.pt"),
        ),
        "model": (
            "models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1",
            "config.json", "intel-qwen3.8-flash-next-w4a16-autoround",
            ("model.safetensors.index.json",),
        ),
        "draft": (
            "models/dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1",
            "config.json", "albucino-qwen3-8-flash-next-drafter",
            ("model.safetensors.index.json",),
        ),
        "competition": (
            "competitions/arc-prize-2026-arc-agi-3", "arc_agi_3_wheels",
            "arc-prize-2026-arc-agi-3", (),
        ),
    }
    started = time.monotonic()
    while True:
        found: dict[str, str] = {}
        missing = []
        for name, (preferred, marker, slug, required) in specs.items():
            def matches(path: Path) -> bool:
                return (slug in path.parts
                        and (name not in {"model", "draft"} or path.name == "1")
                        and (path / marker).exists()
                        and all((path / child).exists() for child in required))

            canonical = root / preferred
            candidates = ([canonical] if matches(canonical) else
                          sorted({p.parent for p in root.rglob(marker)
                                  if matches(p.parent)}) if root.exists() else [])
            if len(candidates) > 1:
                raise RuntimeError(f"Ambiguous {name} inputs: {candidates}")
            if candidates:
                found[name] = str(candidates[0])
            else:
                missing.append(name)
        if "competition" in found:
            found["competition_wheels"] = str(Path(found["competition"]) / "arc_agi_3_wheels")
        elapsed = time.monotonic() - started
        report = {
            "paths": found, "missing": missing, "resolution_seconds": elapsed,
            "public_environment_files_required": False,
            "input_root_children": sorted(p.name for p in root.iterdir()) if root.exists() else [],
        }
        if report_path is not None:
            path = Path(report_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2) + "\n")
        if not missing:
            print("Resolved submission inputs: " + json.dumps(found), flush=True)
            return found
        if elapsed >= timeout_seconds:
            raise FileNotFoundError("Attached submission inputs unavailable: " + json.dumps(report))
        print(f"Waiting for attached inputs: {missing} ({elapsed:.0f}s)", flush=True)
        time.sleep(min(3.0, timeout_seconds - elapsed))
