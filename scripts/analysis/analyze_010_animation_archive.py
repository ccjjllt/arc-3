#!/usr/bin/env python3
"""Manual public-SDK CPU observation/archive study; no solver or model execution.

Five fixed MOUSE actions are independently repeated, followed by one RESET.
The action list is an observed historical case, not a game-solving policy. No
model-authored code, engine implementation or hidden state is inspected.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import statistics
import sys
import time
import tracemalloc
import uuid


ROOT = Path(__file__).resolve().parents[2]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def deep_size(value, seen=None):
    """Python index-object size; excludes SDK, ndarray buffers and allocator slack."""
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(deep_size(k, seen) + deep_size(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple)):
        size += sum(deep_size(item, seen) for item in value)
    return size


class ObservationArchive:
    """Small research-only append-per-action archive, not a production integration."""

    def __init__(self, directory, np):
        self.directory = Path(directory)
        self.np = np
        self.index_path = self.directory / "index.jsonl"
        self.index = {}
        if self.index_path.exists():
            for line in self.index_path.read_text().splitlines():
                entry = json.loads(line)
                self.index[self.key(entry)] = entry

    @staticmethod
    def key(entry):
        return (entry["session_id"], entry["attempt"], entry["step"])

    def append(self, entry, frames):
        if self.key(entry) in self.index:
            raise ValueError("Archive action keys are append-only")
        np = self.np
        stack = np.stack(frames).astype(np.uint8, copy=False)
        if not all(np.array_equal(a, b) for a, b in zip(stack, frames)):
            raise ValueError("uint8 conversion changed visible pixel values")
        payload_name = f"attempt-{entry['attempt']:03d}-step-{entry['step']:06d}.npz"
        payload_path = self.directory / payload_name
        started = time.perf_counter_ns()
        np.savez_compressed(payload_path, frames=stack)
        entry = dict(entry, payload=payload_name, frame_count=len(stack),
                     shape=list(stack.shape[1:]), canonical_dtype=str(stack.dtype),
                     original_dtypes=[str(frame.dtype) for frame in frames],
                     raw_array_bytes=stack.nbytes, payload_bytes=payload_path.stat().st_size,
                     frame_sha256=[sha256(frame.tobytes(order="C")) for frame in stack],
                     frame_indices=list(range(len(stack))))
        with self.index_path.open("a") as handle:
            handle.write(json_text(entry) + "\n")
        elapsed_ms = (time.perf_counter_ns()-started)/1e6
        self.index[self.key(entry)] = entry
        return entry, elapsed_ms

    def read(self, session_id, attempt, step, frame_index):
        entry = self.index[(session_id, attempt, step)]
        if type(frame_index) is not int or not 0 <= frame_index < entry["frame_count"]:
            raise IndexError("Unknown frame index")
        with self.np.load(self.directory / entry["payload"], allow_pickle=False) as payload:
            # The compressed per-action file decompresses its whole stack.
            frame = payload["frames"][frame_index].copy()
        if sha256(frame.tobytes(order="C")) != entry["frame_sha256"][frame_index]:
            raise ValueError("Stored frame hash mismatch")
        return frame, entry

    def query(self, session_id, attempt, step, frame_index, bbox=None):
        frame, entry = self.read(session_id, attempt, step, frame_index)
        h, w = frame.shape
        bounds = list(bbox) if bbox is not None else [0, 0, h-1, w-1]
        if len(bounds) != 4 or any(type(v) is not int for v in bounds):
            raise ValueError("Expected inclusive integer top,left,bottom,right")
        t, l, b, r = bounds
        if not 0 <= t <= b < h or not 0 <= l <= r < w:
            raise ValueError("Invalid region; never silently clipped")
        crop = frame[t:b+1, l:r+1]
        chars = "WwgGcBMPRbSYOrNp"
        return {"session_id": session_id, "attempt": attempt, "step": step,
                "frame_index": frame_index, "level_after": entry["level_after"],
                "bbox_order": "top,left,bottom,right; zero_based; inclusive", "bbox": bounds,
                "frame_shape": [h, w], "frame_sha256": entry["frame_sha256"][frame_index],
                "roi_sha256": sha256(crop.tobytes(order="C")),
                "ascii_rows": ["".join(chars[int(value)] for value in row) for row in crop]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-path", type=Path,
                        help="Optional existing/offline-extracted package directory; no installs are performed")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/010-animation-archive")
    args = parser.parse_args()
    if args.sdk_path:
        sys.path.insert(0, str(args.sdk_path.resolve()))
    # Same default full-reset mode as the valid 005 independent observation run.
    reset_env_before = os.environ.pop("ONLY_RESET_LEVELS", None)
    import arc_agi
    from arcengine import GameAction
    import numpy as np

    now = datetime.now(timezone.utc)
    session = "tn36-cpu-" + now.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = args.output_dir / session
    archive_dir = run_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=False)
    source_paths = [Path(__file__), ROOT / "experiments/005-animation-replay.json",
                    ROOT / "research/notes/005/005-animation-replay.md",
                    ROOT / "runs/005-full-baseline/baseline/artifacts/tn36-ef4dde99_p0_events.jsonl"]
    sources = [{"path": str(path.relative_to(ROOT)), "sha256": sha256(path.read_bytes())}
               for path in source_paths]
    wheel_record = args.sdk_path / "arc3-offline-wheel-sources.json" if args.sdk_path else None
    wheel_sources = []
    if wheel_record is not None and wheel_record.exists():
        wheel_sources = [{"path": str(Path(path).relative_to(ROOT)), "sha256": sha256(Path(path).read_bytes())}
                         for path in json.loads(wheel_record.read_text())]
    logger = logging.getLogger("arc3-010-observation")
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.ERROR)
    tracemalloc.start()
    arc = arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=str(ROOT / "research/data/extracted/environment_files"),
        recordings_dir=str(run_dir / "sdk-recordings"), logger=logger)
    env = arc.make("tn36-ef4dde99", seed=0)
    if env is None or env.observation_space is None:
        raise RuntimeError("Public SDK provided no initial observation")
    archive = ObservationArchive(archive_dir, np)
    # Oracle copies exist only in this manual study to compare against original returns.
    original_returns, records, write_ms, checks = {}, [], [], []
    attempt = 0
    previous = None
    action_seconds = 0.0
    max_canonical_action_bytes = 0

    def capture(obs, step, action, data, attempt_before, attempt_after):
        nonlocal previous, max_canonical_action_bytes
        frames = [np.asarray(frame).copy() for frame in obs.frame]
        if not frames or any(frame.ndim != 2 or np.any(frame < 0) or np.any(frame > 15) for frame in frames):
            raise ValueError("Missing/unsupported visible ARC frame")
        original_returns[(session, attempt_after, step)] = frames
        level_after = int(obs.levels_completed)+1
        entry = {"schema_version": 1, "session_id": session, "game_id": "tn36-ef4dde99",
                 "attempt": attempt_after, "attempt_before": attempt_before, "step": step,
                 "step_semantics": "explicit SDK action ordinal including RESET; initial observation is 0",
                 "frame_index_semantics": "zero-based index in the uncollapsed observation.frame array",
                 "action": action, "data": data, "level_after": level_after,
                 "levels_completed": int(obs.levels_completed), "state": obs.state.value,
                 "previous_result": None if previous is None else previous}
        saved, elapsed = archive.append(entry, frames)
        records.append(saved)
        write_ms.append(elapsed)
        max_canonical_action_bytes = max(max_canonical_action_bytes, saved["raw_array_bytes"])
        previous = {"session_id": session, "attempt": attempt_after, "step": step,
                    "frame_index": saved["frame_count"]-1}
        return frames

    obs = env.observation_space
    capture(obs, 0, "INITIAL_OBSERVATION_FROM_MAKE", {}, 0, 0)
    coordinates = [(14, 31), (55, 35), (45, 21), (45, 36), (20, 20)]
    for step, (row, col) in enumerate(coordinates, 1):
        started = time.perf_counter()
        obs = env.step(GameAction.ACTION6, data={"x": col, "y": row})
        action_seconds += time.perf_counter()-started
        if obs is None:
            raise RuntimeError(f"No public observation after action {step}")
        capture(obs, step, "ACTION6", {"x": col, "y": row}, attempt, attempt)
        if step >= 3:
            expected = original_returns[(session, 0, 2)]
            comparisons = []
            for index, frame in enumerate(expected):
                loaded, _ = archive.read(session, 0, 2, index)
                comparisons.append(np.array_equal(loaded, frame))
            checks.append({"after_step": step, "old_action": 2,
                           "frame_comparisons": comparisons, "all_match": all(comparisons)})
    latest_before_reset = len(obs.frame)
    started = time.perf_counter()
    obs = env.step(GameAction.RESET)
    action_seconds += time.perf_counter()-started
    if obs is None:
        raise RuntimeError("No public observation after explicit RESET")
    capture(obs, 6, "RESET", {}, 0, 1)

    # Re-open only the persisted index/files; do not rely on writer state after RESET.
    restored = ObservationArchive(archive_dir, np)
    all_frames = []
    for key, frames in original_returns.items():
        for index, frame in enumerate(frames):
            loaded, entry = restored.read(*key, index)
            original_hash = sha256(np.asarray(frame, dtype=np.uint8).tobytes(order="C"))
            all_frames.append({"attempt": key[1], "step": key[2], "frame_index": index,
                               "original_sha256": original_hash,
                               "stored_sha256": entry["frame_sha256"][index],
                               "numeric_equal": bool(np.array_equal(frame, loaded)),
                               "hash_equal": original_hash == entry["frame_sha256"][index]})
    wrong_keys_rejected = {}
    for name, key in [("wrong_attempt", (session, 1, 2, 0)),
                      ("wrong_session", (session+"-different", 0, 2, 0))]:
        try:
            restored.read(*key)
            wrong_keys_rejected[name] = False
        except KeyError:
            wrong_keys_rejected[name] = True

    target_frames = original_returns[(session, 0, 2)]
    before = original_returns[(session, 0, 1)][-1]
    chain = np.stack([before, *target_frames]).astype(np.uint8)
    change_count = np.count_nonzero(chain[1:] != chain[:-1], axis=0)
    transient = change_count >= 2
    locations = np.argwhere(transient)
    transient_bbox = None if not len(locations) else [int(locations[:, 0].min()), int(locations[:, 1].min()),
                                                     int(locations[:, 0].max()), int(locations[:, 1].max())]
    # A fixed local crop inside the visible historical transient bbox; no semantic label.
    roi_bbox = (13, 19, 28, 34)
    sample_roi = restored.query(session, 0, 2, 0, roi_bbox)
    sample_full = restored.query(session, 0, 2, 0)
    roi_query_ns, full_query_ns = [], []
    for index in range(100):
        started = time.perf_counter_ns()
        restored.query(session, 0, 2, index % len(target_frames), roi_bbox)
        roi_query_ns.append(time.perf_counter_ns()-started)
        started = time.perf_counter_ns()
        restored.query(session, 0, 2, index % len(target_frames))
        full_query_ns.append(time.perf_counter_ns()-started)
    traced_current, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    def latency(values):
        ordered = sorted(values)
        return {"n": len(values), "median_ms": statistics.median(values)/1e6,
                "p95_ms": ordered[int(.95*(len(ordered)-1))]/1e6, "max_ms": max(values)/1e6}
    roi_all = [restored.query(session, 0, 2, i, roi_bbox) for i in range(len(target_frames))]
    (run_dir / "roi-action2.json").write_text(json.dumps(roi_all, indent=2)+"\n")
    visible_matches_005 = []
    with source_paths[-1].open() as handle:
        for line_number, line in enumerate(handle, 1):
            event = json.loads(line)
            step = event.get("action_num")
            if event.get("type") == "action" and step in range(1, 6):
                visible_matches_005.append({"step": step, "source_line": line_number,
                                           "endpoint_equal": bool(np.array_equal(
                                               event["board"], original_returns[(session, 0, step)][-1]))})
    report = {
        "schema_version": 1, "created_at_utc": now.isoformat(), "session_id": session,
        "scope": "Independent seed-0 public SDK CPU observation, not recovery of 005 missing frames",
        "mode": "OFFLINE", "game_id": "tn36-ef4dde99", "environment_seed": 0,
        "explicit_mouse_actions": 5, "explicit_reset_actions": 1,
        "ONLY_RESET_LEVELS_before": reset_env_before, "ONLY_RESET_LEVELS_during": None,
        "python": sys.version, "python_executable": sys.executable,
        "packages": {name: importlib.metadata.version(name) for name in
                     ["arc-agi", "arcengine", "numpy", "pydantic", "flask"]},
        "sdk_import_paths": {"arc_agi": arc_agi.__file__}, "offline_wheel_sources": wheel_sources,
        "sources": sources, "records": records, "after_later_action_checks": checks,
        "after_reset_disk_reopen_frame_checks": all_frames,
        "wrong_key_rejections": wrong_keys_rejected,
        "observation_difference": {"action2_returned_frames": len(target_frames),
                                   "last_mouse_action5_returned_frames": latest_before_reset,
                                   "after_reset_returned_frames": len(obs.frame),
                                   "action2_transient_pixels": int(np.count_nonzero(transient)),
                                   "action2_transient_bbox": transient_bbox,
                                   "action2_final_fullframe_changed_pixels": int(np.count_nonzero(before != target_frames[-1])),
                                   "action2_final_inner_changed_pixels": int(np.count_nonzero(before[4:-4,4:-4] != target_frames[-1][4:-4,4:-4]))},
        "visible_endpoints_vs005": visible_matches_005,
        "storage": {"archive_payload_bytes": sum(r["payload_bytes"] for r in records),
                    "index_jsonl_bytes": restored.index_path.stat().st_size,
                    "canonical_visible_arrays_bytes": sum(r["raw_array_bytes"] for r in records),
                    "frame_count": sum(r["frame_count"] for r in records),
                    "action2_payload_bytes": records[2]["payload_bytes"]},
        "memory": {"python_reader_index_deep_bytes": deep_size(restored.index),
                   "max_one_action_uint8_stack_bytes": max_canonical_action_bytes,
                   "study_oracle_original_array_bytes": sum(f.nbytes for fs in original_returns.values() for f in fs),
                   "whole_study_tracemalloc_current_bytes": traced_current,
                   "whole_study_tracemalloc_peak_bytes": traced_peak,
                   "note": "Whole-study trace includes SDK, study oracle, compression and queries; not production archive overhead or RSS."},
        "latency": {"sdk_six_actions_seconds": action_seconds,
                    "archive_write_ms": write_ms,
                    "roi_read_hash_decode_serialize_ready": latency(roi_query_ns),
                    "full_frame_read_hash_decode_serialize_ready": latency(full_query_ns),
                    "note": "100 warm-local filesystem reads per mode; query timings include decompression, hash and ASCII construction, exclude json.dumps, model, IPC and cold storage."},
        "output": {"roi_bbox": list(roi_bbox), "single_roi_json_chars": len(json_text(sample_roi)),
                   "single_fullframe_json_chars": len(json_text(sample_full)),
                   "seven_roi_json_chars": len(json_text(roi_all)),
                   "sample_roi": sample_roi},
        "all_frames_match_original_returns": all(f["numeric_equal"] and f["hash_equal"] for f in all_frames),
        "sources_unchanged": all(sha256((ROOT / s["path"]).read_bytes()) == s["sha256"] for s in sources),
        "boundaries": ["No model, GPU, network install, solver patch or Notebook changes.",
                       "No game-specific engine implementation or hidden state was inspected.",
                       "Only five fixed MOUSE calls and one RESET; no transcript code executed.",
                       "Index step is this script's explicit action ordinal, not an inferred engine state counter.",
                       "RESET result is stored under attempt 1 / global step 6; prior attempt 0 remains queryable.",
                       "Matching endpoints with 005 does not recover 005 intermediate frames or prove equal hidden state.",
                       "This tiny local sample cannot estimate 110-game Kaggle archive cost, model adoption, or score gains."],
    }
    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    (args.output_dir / "latest.json").write_text(json.dumps({"session_id": session,
        "report": str(report_path.relative_to(ROOT)), "report_sha256": sha256(report_path.read_bytes())}, indent=2)+"\n")
    print(json.dumps({"report": str(report_path), "all_frames_match": report["all_frames_match_original_returns"],
                      "difference": report["observation_difference"], "storage": report["storage"],
                      "memory": report["memory"], "latency": report["latency"],
                      "output_chars": {k:v for k,v in report["output"].items() if k.endswith("chars")}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
