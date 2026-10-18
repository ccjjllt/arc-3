"""Bounded, CPU-only checkpoint audit for experiment 019.

Reads JSON, safetensors headers and selected byte ranges. Never imports torch,
unpickles data, loads a complete weight tensor, or contacts a network service.
The result is a sampling contract, not a full checkpoint integrity proof.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import time


PLE_PREFIX = "model.language_model.layers.1.ple.ple_embedding.ngram_embedding."
SCALE_KEY = PLE_PREFIX + "weight_scale"
PLE_RE = re.compile(re.escape(PLE_PREFIX) + r"shard_(\d+)\.weight$")
DTYPE_BITS = {"BOOL": 8, "U8": 8, "I8": 8, "F8_E4M3": 8,
              "F8_E5M2": 8, "I16": 16, "U16": 16, "F16": 16,
              "BF16": 16, "I32": 32, "U32": 32, "F32": 32,
              "I64": 64, "U64": 64, "F64": 64}


class AuditStop(RuntimeError):
    pass


def _require(condition, message):
    if not condition:
        raise AuditStop(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bf16-dir", required=True)
    parser.add_argument("--fp8-dir", required=True)
    parser.add_argument("--draft-dir", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run_weight_audit(args.bf16_dir, args.fp8_dir, args.draft_dir,
                              args.contract, args.output)
    print(json.dumps({"passed": report["passed"], "stage": report["stage"],
                      "elapsed_seconds": report["elapsed_seconds"],
                      "error": report.get("error"), "output": args.output}))
    return 0 if report["passed"] else 1


def _json(raw):
    return json.loads(raw, object_pairs_hook=_unique)


class _Reader:
    def __init__(self, root, deadline, budget):
        self.root = Path(root).resolve()
        self.deadline = deadline
        self.budget = int(budget)
        self.bytes_read = 0
        self.read_calls = 0
        self.fds = {}

    def check(self):
        _require(time.monotonic() < self.deadline, "Audit wall-clock deadline exceeded")

    def path(self, name):
        rel = Path(name)
        _require(not rel.is_absolute() and ".." not in rel.parts,
                 f"Unsafe input-relative path: {name}")
        path = (self.root / rel).resolve()
        _require(path.is_relative_to(self.root), f"Input path escapes root: {name}")
        _require(path.is_file(), f"Missing input: {path}")
        return path

    def read(self, name, start, count):
        self.check()
        _require(start >= 0 and count >= 0, "Negative range")
        _require(self.bytes_read + count <= self.budget,
                 f"Read budget exceeded for {self.root}")
        path = self.path(name)
        _require(start + count <= path.stat().st_size, f"Range beyond file: {name}")
        if name not in self.fds:
            self.fds[name] = os.open(path, os.O_RDONLY)
        data = os.pread(self.fds[name], count, start)
        self.bytes_read += len(data)
        self.read_calls += 1
        _require(len(data) == count, f"Short read: {name}")
        self.check()
        return data

    def document(self, name, limit=32 * 1024 * 1024):
        size = self.path(name).stat().st_size
        _require(size <= limit, f"Metadata file too large: {name}")
        raw = self.read(name, 0, size)
        return _json(raw), _sha(raw)

    def close(self):
        for fd in self.fds.values():
            os.close(fd)


def _catalog(reader, max_header):
    index, index_sha = reader.document("model.safetensors.index.json")
    wm = index.get("weight_map")
    _require(isinstance(wm, dict) and wm, "Missing/empty weight_map")
    _require(all(isinstance(k, str) and isinstance(v, str) for k, v in wm.items()),
             "Invalid index keys/files")
    descriptors, files = {}, {}
    for name in sorted(set(wm.values())):
        reader.check()
        n = struct.unpack("<Q", reader.read(name, 0, 8))[0]
        _require(0 < n <= max_header, f"Invalid header length: {name}: {n}")
        raw = reader.read(name, 8, n)
        header = _json(raw)
        size = reader.path(name).stat().st_size
        spans = []
        count = 0
        for key, d in header.items():
            if key == "__metadata__":
                continue
            _require(isinstance(d, dict), f"Invalid descriptor: {key}")
            dtype, shape, offsets = d.get("dtype"), d.get("shape"), d.get("data_offsets")
            _require(dtype in DTYPE_BITS, f"Unsupported dtype {dtype}: {key}")
            _require(isinstance(shape, list) and all(type(v) is int and v >= 0 for v in shape),
                     f"Invalid shape: {key}")
            _require(isinstance(offsets, list) and len(offsets) == 2
                     and all(type(v) is int for v in offsets), f"Invalid offsets: {key}")
            start, end = offsets
            expected = math.prod(shape) * DTYPE_BITS[dtype] // 8
            _require(0 <= start <= end and end - start == expected
                     and 8 + n + end <= size, f"Bad tensor bounds/size: {key}")
            _require(key not in descriptors, f"Tensor occurs in multiple files: {key}")
            _require(wm.get(key) == name, f"Header/index mapping mismatch: {key}")
            descriptors[key] = {"file": name, "dtype": dtype, "shape": shape,
                                "offset": 8 + n + start, "nbytes": expected}
            spans.append((start, end))
            count += 1
        cursor = 0
        for start, end in sorted(spans):
            _require(start == cursor, f"Overlapping/non-contiguous tensor data: {name}")
            cursor = end
        _require(8 + n + cursor == size, f"Trailing/unindexed tensor bytes: {name}")
        files[name] = {"file_size": size, "header_size": n,
                       "header_sha256": _sha(raw), "tensor_count": count}
    _require(set(descriptors) == set(wm), "Index refers to missing tensor keys")
    return {"index_sha256": index_sha, "index_tensor_count": len(wm),
            "files": files, "tensors": descriptors}


def decode_e4m3fn(byte):
    """IEEE-like E4M3FN: exponent 15 is finite except mantissa 7 (NaN)."""
    sign = -1.0 if byte & 128 else 1.0
    exponent, mantissa = (byte >> 3) & 15, byte & 7
    if exponent == 15 and mantissa == 7:
        return math.nan
    if exponent == 0:
        return sign * math.ldexp(mantissa, -9)
    return sign * math.ldexp(1.0 + mantissa / 8.0, exponent - 7)


def decode_bf16(raw):
    _require(len(raw) % 2 == 0, "Odd BF16 byte count")
    return [struct.unpack("<f", struct.pack("<I", v[0] << 16))[0]
            for v in struct.iter_unpack("<H", raw)]


def _round_bf16(value):
    bits = struct.unpack("<I", struct.pack("<f", value))[0]
    if bits & 0x7f800000 != 0x7f800000:
        bits = (bits + 0x7fff + ((bits >> 16) & 1)) & 0xffffffff
    return struct.unpack("<f", struct.pack("<I", bits & 0xffff0000))[0]


def _sample_rows(key, rows, random_count, seed):
    chosen = {0, rows - 1, rows // 2}
    index = 0
    count = min(rows, 3 + random_count)
    while len(chosen) < count:
        digest = hashlib.sha256(f"{seed}|{key}|{index}".encode()).digest()
        chosen.add(int.from_bytes(digest[:8], "little") % rows)
        index += 1
    return sorted(chosen)


def _sample_keys(keys, tensors, maximum, seed):
    """Fixed strata: key roles, each physical shard, model layers, then hash fill."""
    priority = lambda k: (_sha((seed + "|" + k).encode()), k)
    selected = []

    def add(key):
        if key not in selected and len(selected) < maximum:
            selected.append(key)

    special = [k for k in keys if any(s in k for s in
               ("embed_tokens.weight", "lm_head.weight", ".ple.", "hyper_connection_mixer"))]
    for key in sorted(special, key=priority)[:24]:
        add(key)
    groups = {}
    for key in keys:
        groups.setdefault(tensors[key]["file"], []).append(key)
    for filename in sorted(groups):
        for key in sorted(groups[filename], key=priority)[:2]:
            add(key)
    layers = {}
    for key in keys:
        match = re.search(r"\.layers\.(\d+)\.", key)
        if match:
            layers.setdefault(int(match[1]), []).append(key)
    for layer in sorted(layers):
        add(min(layers[layer], key=priority))
    for key in sorted(keys, key=priority):
        if len(selected) >= maximum:
            break
        add(key)
    return selected


def _tensor_sample(reader, desc, span_bytes):
    size = desc["nbytes"]
    width = min(span_bytes, size)
    starts = sorted({0, max(0, (size - width) // 2), max(0, size - width)})
    h = hashlib.sha256()
    spans = []
    for start in starts:
        raw = reader.read(desc["file"], desc["offset"] + start, width)
        h.update(struct.pack("<QQ", start, width))
        h.update(raw)
        spans.append([start, width])
    return {"sha256": h.hexdigest(), "spans": spans}


def run_weight_audit(bf16_dir, fp8_dir, draft_dir, contract, out):
    """Return and write a fail-closed report; callers must require passed=True.

    `contract` is a dict or path to 019-weight-contract.json. `out` is a JSON
    filename. The elapsed-time deadline is checked before/after every bounded
    read; a parent process timeout is still needed for a hung filesystem read.
    """
    started = time.monotonic()
    cfg = _json(Path(contract).read_bytes()) if isinstance(contract, (str, Path)) else contract
    limits = cfg["audit_limits"]
    deadline = started + limits["max_seconds"]
    readers = {name: _Reader(root, deadline, limits["max_bytes_per_source"])
               for name, root in [("bf16", bf16_dir), ("fp8", fp8_dir), ("draft", draft_dir)]}
    result = {"schema_version": 1, "passed": False, "stage": "metadata",
              "contract_sha256": _sha(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()),
              "limits": limits, "sources": {}, "checks": {},
              "limitations": ["Selected payload ranges do not prove full tensor/file identity.",
                              "No model loading, inference, GPU execution or game data was used.",
                              "PLE error limits are engineering smoke gates, not quality guarantees.",
                              "Audit touches file cache; later startup is not an untouched cold-I/O measurement."]}
    try:
        configs = {}
        cats = {}
        for arm, reader in readers.items():
            config, sha = reader.document("config.json")
            configs[arm] = config
            result["sources"][arm] = {"path": str(reader.root), "config_sha256": sha}
        a = json.loads(json.dumps(configs["bf16"]))
        b = json.loads(json.dumps(configs["fp8"]))
        _require(b["text_config"].pop("ple_embedding_dtype", None) == "float8_e4m3fn",
                 "Candidate must explicitly declare float8_e4m3fn PLE")
        _require(a["text_config"].get("ple_embedding_dtype") in (None, "bfloat16"),
                 "Baseline PLE dtype is not BF16")
        a["text_config"].pop("ple_embedding_dtype", None)
        _require(a == b, "Target configs differ beyond PLE storage dtype")
        config_sha = _sha(json.dumps(a, sort_keys=True, separators=(",", ":")).encode())
        _require(config_sha == cfg["expected_normalized_config_sha256"],
                 "Target config differs from pinned upstream contract")
        for key, expected in cfg["expected_text_config"].items():
            _require(a["text_config"].get(key) == expected, f"Unexpected text_config.{key}")
        q = a.get("quantization_config", {})
        _require(q.get("quant_method") == "auto-round" and q.get("bits") == 4
                 and q.get("group_size") == 128 and q.get("sym") is True,
                 "Target must remain AutoRound symmetric W4A16/group128")
        result["checks"]["config_only_ple_dtype_diff"] = True
        for name in cfg["identical_target_metadata"]:
            hashes = {}
            for arm in ("bf16", "fp8"):
                r = readers[arm]
                size = r.path(name).stat().st_size
                _require(size <= limits["max_metadata_file_bytes"], f"Metadata too large: {name}")
                hashes[arm] = _sha(r.read(name, 0, size))
            _require(hashes["bf16"] == hashes["fp8"], f"Target metadata differs: {name}")
            if name == "tokenizer.json" and cfg.get("expected_tokenizer_sha256"):
                _require(hashes["bf16"] == cfg["expected_tokenizer_sha256"], "Wrong tokenizer for frozen FR-Spec map")
            result["checks"][name] = hashes["bf16"]
        dq = configs["draft"].get("quantization_config", {})
        _require(dq.get("quant_method") == "compressed-tensors"
                 and "mtp_routed_experts" in dq.get("config_groups", {}),
                 "Independent draft is not expected compressed-tensors MTP")
        group = dq["config_groups"]["mtp_routed_experts"]
        weights = group.get("weights", {})
        _require(weights.get("num_bits") == 4 and weights.get("group_size") == 32
                 and weights.get("symmetric") is True,
                 "Draft must remain symmetric INT4 group32")
        for arm, reader in readers.items():
            cats[arm] = _catalog(reader, limits["max_header_bytes"])
            result["sources"][arm].update({k: v for k, v in cats[arm].items() if k != "tensors"})
        tensors = {arm: cat["tensors"] for arm, cat in cats.items()}
        _require(any(k.startswith("mtp.layers.0.mlp.experts.") for k in tensors["draft"]),
                 "Independent draft has no expected MTP expert keys")
        result["stage"] = "tensor_contract"
        ple = cfg["ple"]
        expected_keys = [PLE_PREFIX + f"shard_{i}.weight" for i in range(ple["shard_count"])]
        for arm in ("bf16", "fp8"):
            actual = {k for k in tensors[arm] if PLE_RE.fullmatch(k)}
            _require(actual == set(expected_keys), f"Missing/extra PLE shards: {arm}")
            wanted_prefix = set(expected_keys) | ({SCALE_KEY} if arm == "fp8" else set())
            _require({k for k in tensors[arm] if k.startswith(PLE_PREFIX)} == wanted_prefix,
                     f"Unexpected PLE scale/storage keys: {arm}")
            for key in expected_keys:
                d = tensors[arm][key]
                _require(d["shape"] == ple["shard_shape"]
                         and d["dtype"] == ple[f"{arm}_dtype"], f"PLE shape/dtype mismatch: {arm}: {key}")
        nonple = {arm: {k for k in tensors[arm] if not k.startswith(PLE_PREFIX)
                       and not k.startswith("mtp.")} for arm in ("bf16", "fp8")}
        _require(nonple["bf16"] == nonple["fp8"], "Non-PLE/non-MTP key sets differ")
        keys_sha = _sha(json.dumps(sorted(nonple["bf16"]), separators=(",", ":")).encode())
        _require(len(nonple["bf16"]) == cfg["expected_nonple_tensor_count"]
                 and keys_sha == cfg["expected_nonple_keys_sha256"],
                 "Non-PLE key set differs from pinned upstream contract")
        for key in nonple["bf16"]:
            da, db = tensors["bf16"][key], tensors["fp8"][key]
            _require((da["dtype"], da["shape"], da["nbytes"]) ==
                     (db["dtype"], db["shape"], db["nbytes"]), f"Non-PLE header mismatch: {key}")
        result["checks"]["nonple_all_headers_equal"] = len(nonple["bf16"])
        result["checks"]["nonple_keys_sha256"] = keys_sha
        result["checks"]["excluded_mtp_counts"] = {
            arm: sum(k.startswith("mtp.") for k in tensors[arm]) for arm in ("bf16", "fp8")}
        scale_d = tensors["fp8"].get(SCALE_KEY)
        _require(scale_d and scale_d["shape"] == [1] and scale_d["dtype"] == ple["scale_dtype"],
                 "Missing/invalid global scale")
        raw = readers["fp8"].read(scale_d["file"], scale_d["offset"], scale_d["nbytes"])
        scale = decode_bf16(raw)[0] if scale_d["dtype"] == "BF16" else struct.unpack("<f", raw)[0]
        _require(math.isfinite(scale) and scale > 0, "Scale must be positive finite")
        _require(raw.hex() == ple["scale_raw_hex"], "Scale differs from pinned upstream value")
        result["scale"] = {"value": scale, "dtype": scale_d["dtype"], "shape": [1],
                           "raw_hex": raw.hex(), "formula": "BF16(FP8_value * BF16_scale)"}
        result["stage"] = "nonple_samples"
        sample = cfg["sampling"]
        selected = _sample_keys(nonple["bf16"], tensors["bf16"], sample["nonple_max_tensors"], sample["seed"])
        result["nonple_samples"] = []
        for key in selected:
            row = {"key": key}
            for arm in ("bf16", "fp8"):
                row[arm] = _tensor_sample(readers[arm], tensors[arm][key], sample["tensor_span_bytes"])
            result["nonple_samples"].append(row)
            _require(row["bf16"] == row["fp8"], f"Sampled non-PLE payload differs: {key}")
        result["draft_samples"] = []
        for key in _sample_keys(set(tensors["draft"]), tensors["draft"], sample["draft_max_tensors"], sample["seed"]):
            result["draft_samples"].append({"key": key, **_tensor_sample(
                readers["draft"], tensors["draft"][key], sample["tensor_span_bytes"])})
        result["stage"] = "ple_samples"
        result["ple_samples"] = []
        total_n = 0
        sumsq_ref = sumsq_err = sumsq_unscaled = sumsq_inverse = max_abs_error = 0.0
        max_bound_excess = 0.0
        violations = nonfinite = saturated = zeros = 0
        for key in expected_keys:
            rows, width = ple["shard_shape"]
            chosen = _sample_rows(key, rows, sample["random_rows_per_shard"], sample["seed"])
            ha, hb = hashlib.sha256(), hashlib.sha256()
            shard_sse = shard_ref = 0.0
            for row in chosen:
                da, db = tensors["bf16"][key], tensors["fp8"][key]
                ba = readers["bf16"].read(da["file"], da["offset"] + row * width * 2, width * 2)
                bb = readers["fp8"].read(db["file"], db["offset"] + row * width, width)
                ha.update(struct.pack("<Q", row) + ba)
                hb.update(struct.pack("<Q", row) + bb)
                for ref, code in zip(decode_bf16(ba), bb):
                    qvalue = decode_e4m3fn(code)
                    if not math.isfinite(ref) or not math.isfinite(qvalue):
                        nonfinite += 1
                        continue
                    reconstructed = _round_bf16(qvalue * scale)
                    error = abs(reconstructed - ref)
                    bound = sample["relative_error_bound"] * abs(ref) + scale * sample["absolute_error_scale_factor"]
                    violations += error > bound
                    max_bound_excess = max(max_bound_excess, error - bound)
                    saturated += abs(qvalue) == 448.0
                    zeros += qvalue == 0.0
                    max_abs_error = max(max_abs_error, error)
                    total_n += 1
                    sumsq_ref += ref * ref
                    sumsq_err += error * error
                    sumsq_unscaled += (qvalue - ref) ** 2
                    sumsq_inverse += (qvalue / scale - ref) ** 2
                    shard_sse += error * error
                    shard_ref += ref * ref
            result["ple_samples"].append({"key": key, "rows": chosen,
                "bf16_sample_sha256": ha.hexdigest(), "fp8_sample_sha256": hb.hexdigest(),
                "nrmse": math.sqrt(shard_sse / shard_ref) if shard_ref else None})
        nrmse = math.sqrt(sumsq_err / sumsq_ref) if sumsq_ref else None
        result["ple_numeric"] = {"elements": total_n, "nonfinite_elements": nonfinite,
            "scale_times_q_nrmse": nrmse, "max_abs_error": max_abs_error,
            "error_bound_violations": violations, "max_error_bound_excess": max_bound_excess,
            "saturated_fp8_elements": saturated, "zero_fp8_elements": zeros,
            "unscaled_nrmse": math.sqrt(sumsq_unscaled / sumsq_ref) if sumsq_ref else None,
            "inverse_scale_nrmse": math.sqrt(sumsq_inverse / sumsq_ref) if sumsq_ref else None}
        _require(nonfinite == 0, "Nonfinite PLE sample")
        _require(nrmse is not None and nrmse <= sample["max_nrmse"], "PLE sample NRMSE gate failed")
        _require(violations == 0, "PLE sample error exceeds frozen conservative FP8 bound")
        result["stage"] = "complete"
        result["passed"] = True
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        result["elapsed_seconds"] = time.monotonic() - started
        result["io"] = {arm: {"bytes_read": r.bytes_read, "read_calls": r.read_calls}
                        for arm, r in readers.items()}
        for reader in readers.values():
            reader.close()
        destination = Path(out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
