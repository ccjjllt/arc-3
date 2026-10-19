"""Read-only 020 score/resource summary; no automatic promotion or adoption gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_018_results import compare, gpu_resources, origin, save


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/020-overview")
    parser.add_argument("--frozen", type=Path, default=ROOT / "experiments/020-source/kernel")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/020-analysis")
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output_dir.resolve()
    if root == out or root in out.parents or out in root.parents:
        parser.error("Keep raw and derived outputs separate")
    manifest = read(root / "experiment-manifest.json")
    build = read(args.frozen / "build-manifest.json")
    arms = manifest["experiment"]["arm_order"]
    if arms != ["baseline", "grounded_state"]:
        parser.error("This analysis is for the frozen 020 arm pair")
    raw = {a: read(root / a / "benchmark.json") for a in arms}
    meta = {a: read(root / a / "arm-metadata.json") for a in arms}
    comparison = compare(manifest, raw, meta)
    gpu = gpu_resources(root, manifest, meta)
    common = meta[arms[0]]["source_sha256"].keys() & meta[arms[1]]["source_sha256"].keys()
    checks = {
        "config_matches_frozen": manifest["experiment"] == build["config"],
        "source_manifest_matches_frozen": manifest["source_hashes"] == build["source_hashes"],
        "common_runtime_sources_equal": all(meta[arms[0]]["source_sha256"][k] ==
                                            meta[arms[1]]["source_sha256"][k] for k in common),
        "both_arms_clean_and_complete": len(manifest["arms"]) == 2 and all(
            e.get("exit_code") == 0 and e.get("complete_pool") is True for e in manifest["arms"]),
        "same_order_and_requested_budget": all(
            meta[a]["game_ids"] == manifest["experiment"]["games"] and
            meta[a]["budget_seconds"] == manifest["experiment"]["requested_arm_seconds"] for a in arms),
        "cache_flush_confirmed": all(e.get("cache_flush_backend_confirmed") is True for e in manifest["arms"]),
        "workers_drained": all(meta[a].get("lingering_worker_threads") == [] for a in arms),
        "server_stopped": manifest.get("gpu_server_stopped") is True,
        "no_recorded_actions_or_levels_after_deadline": all(
            not r["post_deadline_action_count"] and not r["post_deadline_completed_levels"]
            for a in arms for r in comparison["timing"][a]["runs"].values()),
    }
    report = {
        "kind": "020-descriptive-results", "experiment": manifest["experiment"]["id"],
        "primary_result": comparison["delta"], "runtime_checks": checks,
        "runtime_checks_pass": all(checks.values()),
        "session_minutes": manifest["elapsed_seconds"] / 60,
        "startup_minutes": manifest["model_ready_seconds"] / 60,
        "gpu_strict_windows": [r for r in gpu["groups"] if r["phase"].endswith(":strict_budget")],
        "trajectory_review": "See separately attributed adoption notes; this script does not infer adoption from API strings.",
        "selection_policy": "docs/handoff/020-research-sprint.md; primary score and actual risk, no joint auxiliary-metric veto",
        "limits": ["Single fixed-order comparison on familiar public development games, not hidden score or causal proof.",
                   "No logged model code, game implementation, pickle, network or GPU is executed.",
                   "GPU arithmetic sample means are not exact billing or busy-time integrals."],
        "sources": [origin(root / "experiment-manifest.json"), origin(args.frozen / "build-manifest.json"),
                    *[origin(root / a / name) for a in arms for name in ("benchmark.json", "arm-metadata.json")]],
    }
    save(out / "comparison.json", comparison)
    save(out / "gpu-phases.json", gpu)
    save(out / "report.json", report)
    print(json.dumps({k: report[k] for k in ("primary_result", "runtime_checks_pass", "session_minutes", "startup_minutes")}, indent=2))


if __name__ == "__main__":
    main()
