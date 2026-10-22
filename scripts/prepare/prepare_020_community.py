"""Inventory and bounded CPU interface screening of a pinned community checkout.

No solver, game-source inspection, solution extraction, GPU, or network calls.
The source tree must have been acquired separately at the fixed revision.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
REVISION = "02152bc4806869ace6ef167468970ca84bac0c5a"
SEED = "arc3-community-020-family-split-v1"
EXCLUDED = {"ft09": "official familiar game", "ls20": "official familiar game",
            "vc33": "official familiar game", **{f"ez{i:02}": "onboarding tutorial" for i in range(1, 5)}}
# Conservative metadata/registry groupings, not implementation genealogy.
# Every same-prefix variant is tied; broad cross-prefix groups reduce leakage.
MERGES = [
    "ci mb op pb pw rz sk tk wp", "bd cf cq ep gl hm in va vp wk tr",
    "cy eb nw tc wa wg wr rv dn", "es fc hs sc st tg",
    "df fb fi fw gc hd hz lf ox rh vi zq bl", "gp sf sy", "lo eg cz cw",
    "fl lw lp", "ck rp pd pu bp kv", "ab sp sb", "mc ob sw dp qt",
    "jw pt qr sl", "co kb ul or tw dt fs vt", "dl em mo ec rr",
    "tb cr wl", "bi rk kn ju pm", "pj rb sg tf wb ex bt tm au",
    "mm rc", "dm pk", "cs ct cu cv", "as dd nu sq",
    "dg dr mx", "bn fg", "av gr", "ff zm",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _rank(value, salt=""):
    return digest((SEED + "|" + salt + "|" + value).encode())


def _bucket(category):
    value = category.lower()
    if any(s in value for s in ["memory", "hidden", "exploration", "deduction"]):
        return "hidden_or_exploration"
    if any(s in value for s in ["timing", "survival", "hazard", "stealth"]):
        return "time_or_hazard"
    if any(s in value for s in ["pattern", "precision", "geometry", "tiling"]):
        return "visual_or_spatial"
    if any(s in value for s in ["graph", "logic", "math", "field"]):
        return "logic_or_field"
    if any(s in value for s in ["simulation", "territory", "growth"]):
        return "simulation"
    if any(s in value for s in ["collection", "sequenc", "order", "logistic", "coordination", "multi-agent"]):
        return "order_or_coordination"
    return "movement_or_planning"


def _round_robin(rows, count, salt):
    buckets = defaultdict(list)
    for row in rows:
        buckets[row["bucket"]].append(row)
    for bucket in buckets:
        buckets[bucket].sort(key=lambda r: _rank(r["family"], salt))
    chosen = []
    order = sorted(buckets, key=lambda b: _rank(b, salt))
    while len(chosen) < count:
        added = False
        for bucket in order:
            if buckets[bucket] and len(chosen) < count:
                chosen.append(buckets[bucket].pop(0))
                added = True
        if not added:
            break
    return chosen


def inventory(source, tree_path, output):
    tree_bytes = tree_path.read_bytes()
    tree = json.loads(tree_bytes)
    if tree.get("truncated") or tree.get("sha") != REVISION:
        raise ValueError("Expected complete pinned GitHub tree")
    blobs = {r["path"]: r for r in tree["tree"] if r["type"] == "blob"}
    # Verify opaque bytes against the commit tree, without decoding game source.
    for rel, row in blobs.items():
        if row.get("mode") == "120000":
            continue  # Archive symlinks are deliberately not materialized.
        data = (source / rel).read_bytes()
        if hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != row["sha"]:
            raise ValueError("Checkout content differs from frozen tree: " + rel)
    categories = {}
    registry_stems = []
    for line in (source / "GAMES.md").read_text().splitlines():
        cells = [s.strip() for s in line.split("|")]
        if len(cells) >= 8 and re.fullmatch(r"[a-z]{2}\d{2}", cells[1]):
            registry_stems.append(cells[1])
            categories[cells[1]] = cells[2]
    prefix_map = {}
    for words in MERGES:
        prefixes = words.split()
        family = "family_" + "_".join(sorted(prefixes))
        for prefix in prefixes:
            if prefix in prefix_map:
                raise ValueError("Cross-family alias repeated")
            prefix_map[prefix] = family
    packages = []
    paths = sorted(p for p in blobs if re.fullmatch(r"environment_files/[^/]+/[^/]+/metadata.json", p))
    for relative in paths:
        raw = (source / relative).read_bytes()
        metadata = json.loads(raw)
        _, stem, version, _ = relative.split("/")
        if metadata.get("game_id") != f"{stem}-{version}":
            raise ValueError("Metadata package ID mismatch: " + relative)
        directory = relative.rsplit("/", 1)[0]
        package_files = {p: v["sha"] for p, v in blobs.items() if p.startswith(directory + "/")}
        row = {"stem": stem, "game_id": metadata["game_id"], "version": version,
               "metadata_path": relative, "metadata_sha256": digest(raw),
               "prefix_family": stem[:2], "family": prefix_map.get(stem[:2], "family_" + stem[:2]),
               "category": categories.get(stem, "unregistered"),
               "bucket": _bucket(categories.get(stem, "unregistered")),
               "package_blob_sha1": package_files, "registry_present": stem in categories,
               "excluded": EXCLUDED.get(stem),
               "baseline_actions_metadata": metadata.get("baseline_actions"),
               "metadata_keys": sorted(metadata)}
        # Do not export descriptions, physics_rules, titles, level data or hints.
        packages.append(row)
    ids = [r["game_id"] for r in packages]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate installable game IDs")
    families = defaultdict(list)
    for row in packages:
        if not row["excluded"]:
            families[row["family"]].append(row)
    representatives = [min(rows, key=lambda r: _rank(r["game_id"], "representative"))
                       for rows in families.values()]
    selected = _round_robin(representatives, 40, "screen")
    if len(selected) != 40:
        raise ValueError("Fewer than 40 eligible independent metadata groups")
    heldout = {r["family"] for r in _round_robin(selected, 16, "holdout")}
    development = {r["family"] for r in _round_robin(
        [r for r in selected if r["family"] not in heldout], 12, "development")}
    family_assignment = {f: "unscreened_reserve" for f in families}
    for row in selected:
        family_assignment[row["family"]] = ("frozen" if row["family"] in heldout
                                            else "development" if row["family"] in development
                                            else "reserve")
    manifest = {"schema_version": 1, "source_revision": REVISION, "selection_seed": SEED,
                "frozen_before_smoke": True, "selection_uses_gameplay_outcomes": False,
                "selection_uses_implementation_or_solutions": False,
                "selection_policy": "one hash-selected representative per conservative metadata family; category round-robin; 40 screened; 12 development, 12 reserve, 16 frozen",
                "smoke_seed": 200019, "smoke_max_actions": 3,
                "failure_policy": "Retain failures and split; no favorable replacement. Usable subset requires explicit compatibility filtering with reasons.",
                "heldout_policy": "All variants and cross-prefix aliases of a heldout family stay out of development. No tuning on heldout results.",
                "selected": [{"game_id": r["game_id"], "stem": r["stem"], "family": r["family"],
                              "bucket": r["bucket"], "split": family_assignment[r["family"]],
                              "metadata_sha256": r["metadata_sha256"],
                              "package_blob_sha1": r["package_blob_sha1"]} for r in selected],
                "family_members": {f: sorted(r["game_id"] for r in rs) for f, rs in sorted(families.items())},
                "family_assignment": family_assignment,
                "limitations": ["Metadata semantic families are conservative grouping, not proven implementation genealogy.",
                                "The human registry and author metadata are collector-only; never solver prompts.",
                                "Community metadata baseline_actions is not an available-actions schema or certified optimal policy."]}
    for row in packages:
        row["split"] = "excluded" if row["excluded"] else family_assignment[row["family"]]
    result = {"source_revision": REVISION, "source_tree_sha256": digest(tree_bytes),
              "license": "MIT (copyright ARC Interactive 2026); preserved LICENSE file",
              "package_count": len(packages), "metadata_count": len(paths),
              "base_directory_count": len({r["stem"] for r in packages}),
              "prefix_family_count": len({r["prefix_family"] for r in packages}),
              "registry_row_count": len(registry_stems), "registry_unique_stem_count": len(set(registry_stems)),
              "registry_only": sorted(set(registry_stems) - {r["stem"] for r in packages}),
              "package_only": sorted({r["stem"] for r in packages} - set(registry_stems)),
              "exclusions": {r["game_id"]: r["excluded"] for r in packages if r["excluded"]},
              "eligible_package_count": sum(not r["excluded"] for r in packages),
              "conservative_family_count": len(families), "cross_prefix_group_definitions": MERGES,
              "opaque_package_hashes_verified": True, "implementation_read_as_text": False,
              "packages": packages}
    save(output / "inventory.json", result)
    save(output / "split-frozen.json", manifest)
    # A future solver should receive only this separate allowlist, never inventory/GAMES.
    save(output / "solver-allowlists.json", {
        "source_revision": REVISION,
        "development": [r["game_id"] for r in manifest["selected"] if r["split"] == "development"],
        "reserve": [r["game_id"] for r in manifest["selected"] if r["split"] == "reserve"],
        "frozen": [r["game_id"] for r in manifest["selected"] if r["split"] == "frozen"]})
    return {k: result[k] for k in ["package_count", "prefix_family_count", "registry_row_count", "eligible_package_count", "conservative_family_count"]}


def smoke(source, output, python, dependency_paths, extra_paths, workers):
    manifest_path = output / "split-frozen.json"
    before = manifest_path.read_bytes()
    manifest = json.loads(before)
    if manifest["source_revision"] != REVISION or not manifest["frozen_before_smoke"]:
        raise ValueError("Need frozen inventory/split first")
    inventory_report = json.loads((output / "inventory.json").read_text())
    tree_raw = (output / "source-tree.json").read_bytes()
    if digest(tree_raw) != inventory_report["source_tree_sha256"]:
        raise ValueError("Pinned source tree manifest changed")
    tree = json.loads(tree_raw)
    if tree.get("truncated") or tree.get("sha") != REVISION:
        raise ValueError("Invalid source commit tree")
    for item in tree["tree"]:
        if item["type"] == "blob" and item.get("mode") != "120000":
            raw = (source / item["path"]).read_bytes()
            if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != item["sha"]:
                raise ValueError("Source/support file changed: " + item["path"])
    started = time.monotonic()
    target = output / "smoke"
    target.mkdir(parents=True, exist_ok=True)

    def run(row):
        path = target / (row["game_id"] + ".json")
        if path.exists():
            raise FileExistsError("Never overwrite existing smoke outcome: " + str(path))
        boot = ("import sys; sys.path[:0]=" + repr([str(ROOT / "src"), *dependency_paths]) +
                "; sys.path.extend(" + repr(extra_paths) + "); "
                "from arc3_research.community import main; raise SystemExit(main())")
        cmd = [python, "-c", boot, "--source-root", str(source), "--game-id", row["game_id"],
               "--seed", str(manifest["smoke_seed"]), "--output", str(path)]
        # No account/API credentials are passed to community runtime code.
        env = {k: os.environ[k] for k in ["PATH", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT"] if k in os.environ}
        env.update(PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg")
        t0 = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="arc3-community-api-") as cwd:
            proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            timeout = False
            try:
                logs, _ = proc.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                timeout = True
                os.killpg(proc.pid, signal.SIGKILL)
                logs, _ = proc.communicate()
        report = json.loads(path.read_text()) if path.exists() else {
            "passed": False, "error": {"type": "Timeout" if timeout else "WorkerFailure",
                                       "message": "No structured API result; raw output withheld to avoid implementation leakage."}}
        # Tracebacks may contain source lines; preserve hash/count, not the text.
        report.update(game_id=row["game_id"], split=row["split"], family=row["family"],
                      subprocess_returncode=proc.returncode, timeout=timeout,
                      subprocess_seconds=time.monotonic() - t0,
                      opaque_log_sha256=digest(logs), opaque_log_bytes=len(logs))
        report["passed"] = bool(report.get("passed") and proc.returncode == 0 and not timeout)
        save(path, report)
        return report

    with ThreadPoolExecutor(max_workers=workers) as pool:
        reports = list(pool.map(run, manifest["selected"]))
    if manifest_path.read_bytes() != before:
        raise RuntimeError("Frozen split changed during smoke")
    summary = {"schema_version": 1, "source_revision": REVISION,
               "split_sha256": digest(before), "elapsed_seconds": time.monotonic() - started,
               "all_regular_source_blob_hashes_verified_before_execution": True,
               "symlinks_not_materialized": [r["path"] for r in tree["tree"] if r.get("mode") == "120000"],
               "screened": len(reports), "passed": sum(r["passed"] for r in reports),
               "by_split": {s: {"screened": sum(r["split"] == s for r in reports),
                                    "passed": sum(r["split"] == s and r["passed"] for r in reports)}
                            for s in ["development", "reserve", "frozen"]},
               "failures": [{"game_id": r["game_id"], "error": r.get("error")} for r in reports if not r["passed"]],
               "policy": "No replacement, solver, semantic frame review or implementation inspection; API legality is not strategy correctness.",
               "dependency_paths": dependency_paths, "extra_paths": extra_paths,
               "python": python,
               "reports_sha256": {r["game_id"]: digest((target / (r["game_id"] + ".json")).read_bytes()) for r in reports}}
    save(output / "smoke-summary.json", summary)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["inventory", "smoke"])
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--output", type=Path, default=ROOT / "experiments/020-community")
    p.add_argument("--tree", type=Path)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--dependency-path", action="append", default=[])
    p.add_argument("--extra-path", action="append", default=[])
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    if not 1 <= args.workers <= 4:
        raise ValueError("Use one to four bounded CPU workers")
    source, output = args.source_root.resolve(), args.output.resolve()
    if args.mode == "inventory":
        if (output / "split-frozen.json").exists():
            raise FileExistsError("Frozen split exists; do not silently recreate it")
        report = inventory(source, args.tree or output / "source-tree.json", output)
    else:
        report = smoke(source, output, args.python, args.dependency_path, args.extra_path, args.workers)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
