"""019 fixed-request PLE microbenchmark; imports and preparation are offline.

Only run_phase() / CLI ``run --allow-local-network`` contact an existing loopback
service. No service startup, model code execution, game access or judge model.
Pinned API inspected 2026-10-18:
https://github.com/jpezzulli/sglang-rtxpro6000/blob/d00d88efc8d6281b12be4f4073126aec95038c55/python/sglang/srt/entrypoints/openai/protocol.py
https://github.com/jpezzulli/sglang-rtxpro6000/blob/d00d88efc8d6281b12be4f4073126aec95038c55/python/sglang/srt/entrypoints/openai/serving_chat.py

SSE chunks are not tokens. Streaming token IDs/meta_info are unsupported by this
pinned chat endpoint. Usage and sglext are separate final chunks and are retained.
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import http.client
import ipaddress
import json
import math
from pathlib import Path
import re
import socket
import statistics
import threading
import time
from urllib.parse import urlsplit

PHASE_ORDER = ["bf16_a", "fp8", "bf16_b"]
SOURCE_COMMIT = "d00d88efc8d6281b12be4f4073126aec95038c55"
PAYLOAD_KEYS = ("messages", "tools", "tool_choice", "chat_template_kwargs")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def value_hash(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def finite_json(value):
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite_json(v) for v in value.values())
    if isinstance(value, list):
        return all(finite_json(v) for v in value)
    return True


def strict_json(text):
    def bad(value):
        raise ValueError("Nonfinite JSON constant: " + value)
    return json.loads(text, parse_constant=bad)


def sample_public_requests(paths, count=10):
    """First/middle requests per ordered log, then 3/4, 1/4, 1/8, etc.

    For four logs this selects first+middle from each, then 3/4 from the first
    two. Exact path/line/hash and the source request object are retained. The
    diagnostic log does not contain original sampling fields; benchmark fields
    are explicitly added later. System/messages/tools are never truncated.
    """
    pools = []
    for path in paths:
        path = Path(path)
        requests = []
        with path.open() as f:
            for line_no, line in enumerate(f, 1):
                obj = strict_json(line)
                if obj.get("event") == "request":
                    requests.append((line_no, obj))
        if not requests:
            raise ValueError(f"No requests in {path}")
        pools.append((path, file_hash(path), requests))
    if not pools:
        return []
    selected, used = [], set()
    fractions = (0, .5, .75, .25, .125, .875, .375, .625)
    for fraction in fractions:
        for path, sha, requests in pools:
            index = min(len(requests) - 1, int(len(requests) * fraction))
            line_no, original = requests[index]
            key = (str(path.resolve()), line_no)
            if key in used:
                continue
            used.add(key)
            selected.append({"payload": {k: deepcopy(original[k]) for k in PAYLOAD_KEYS if k in original},
                             "source": {"path": str(path.resolve()), "sha256": sha, "line": line_no,
                                        "request_ordinal_1based": index + 1, "request_count_in_log": len(requests),
                                        "source_request_sha256": value_hash(original)},
                             "original_request": original})
            if len(selected) == count:
                return selected
    raise ValueError(f"Only {len(selected)} distinct requests available; {count} required")


def _quality_cases():
    cases = []
    tool = {"type": "function", "function": {"name": "submit_observation",
        "description": "Return the requested observed cells, without executing any actions.",
        "parameters": {"type": "object", "properties": {"cells": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}},
                        "count": {"type": "integer"}}, "required": ["cells", "count"], "additionalProperties": False}}}
    for i in range(10):
        # Public synthetic characters and independent exact answers. Holes and
        # disconnected cells matter; no ARC hidden/environment data are used.
        rows = [["." for _ in range(8)] for _ in range(6)]
        for r in range(1, 5):
            for c in range(1, 7):
                if (r in (1, 4) or c in (1, 6)) and (r + 2 * c + i) % 5:
                    rows[r][c] = "B"
        rows[i % 6][(i * 3) % 8] = "Y"
        r0, c0 = 10 + i, 20 + 2 * i
        expected_cells = [[r0 + r, c0 + c] for r in range(6) for c in range(8) if rows[r][c] == "B"]
        grid = "\n".join("".join(row) for row in rows)
        prompt = (f"Observe this 6 by 8 character crop with global origin row={r0}, col={c0}.\n{grid}\n"
                  "Return every cell whose literal character is B, as global [row,col] pairs sorted by row then col. "
                  "Preserve holes; Y and . are not B. Use submit_observation exactly once with cells and count. "
                  "Do not call Python, move anything, fill the bounding box, or provide prose.")
        cases.append({"id": f"quality_{i:02d}", "kind": "synthetic_exact_tool", "source": {"kind": "deterministic_public_synthetic", "version": 1},
                      "payload": {"messages": [{"role": "system", "content": "Read literal observations carefully and return the requested tool arguments."},
                                               {"role": "user", "content": prompt}], "tools": [tool], "tool_choice": "auto",
                                  "chat_template_kwargs": {"enable_thinking": False, "preserve_thinking": True}},
                      "expected": {"cells": expected_cells, "count": len(expected_cells)}})
    return cases


def make_suite(public_request_logs=None, *, output_tokens=256, seed=190018, model="flashnext"):
    """Pure offline suite. Pass four ordered baseline *_requests.jsonl paths.

    Ten immutable public snapshots are used when supplied; otherwise synthetic
    long-prefix requests provide an offline smoke suite (explicitly different).
    Every phase uses the same suite; never regenerate it after viewing outputs.
    """
    if not isinstance(output_tokens, int) or not 32 <= output_tokens <= 2048:
        raise ValueError("output_tokens must be a frozen integer in [32,2048]")
    public = sample_public_requests(public_request_logs or [], 10)
    tasks = []
    for i in range(10):
        if public:
            payload, source = deepcopy(public[i]["payload"]), public[i]["source"]
        else:
            prefix = "\n".join(f"Cell {n:04d}: row={n // 31}, column={n % 31}, code={(n * 7 + i) % 16}." for n in range(350 + 50 * (i % 3)))
            payload = {"messages": [{"role": "system", "content": "Reason using only the supplied public synthetic table."},
                                    {"role": "user", "content": prefix + "\nExplain the coordinate and code pattern and give worked examples."}],
                       "chat_template_kwargs": {"enable_thinking": True, "preserve_thinking": True}}
            source = {"kind": "public_synthetic_long_prefix", "case": i}
        tasks.append({"id": f"load_{i:02d}", "kind": "public_snapshot_fixed_length" if public else "synthetic_fixed_length",
                      "payload": payload, "source": source})
    latency = []
    for i in range(2):
        case = deepcopy(tasks[i]); case["id"] = f"latency_{i:02d}"
        latency.append(case)
    all_cases = latency + tasks + _quality_cases()
    for i, case in enumerate(all_cases):
        quality = case["kind"] == "synthetic_exact_tool"
        p = case["payload"]
        limit = 512 if quality else min(128, output_tokens) if case["id"].startswith("latency_") else output_tokens
        p.update(model=model, temperature=0.0, top_p=1.0, top_k=-1, seed=seed + i, n=1,
                 max_tokens=limit, min_tokens=0 if quality else limit, ignore_eos=not quality,
                 stream=True, stream_options={"include_usage": True, "continuous_usage_stats": True},
                 return_spec_tokens_details=True, return_cached_tokens_details=True,
                 cache_salt="arc3-019-v1-" + case["id"])
        case["payload_sha256"] = value_hash(p)
        case["fixed_output_tokens"] = None if quality else limit
    groups = [
        {"id": "latency_cold", "concurrency": 1, "cache": "cold", "flush_before": True, "task_ids": [c["id"] for c in latency]},
        {"id": "latency_hot", "concurrency": 1, "cache": "hot", "flush_before": False, "task_ids": [c["id"] for c in latency]},
        {"id": "load10_cold", "concurrency": 10, "cache": "cold", "flush_before": True, "task_ids": [c["id"] for c in tasks]},
        {"id": "load10_hot", "concurrency": 10, "cache": "hot", "flush_before": False, "task_ids": [c["id"] for c in tasks]},
        {"id": "quality10", "concurrency": 10, "cache": "isolated_salt_unprimed", "flush_before": False, "task_ids": [f"quality_{i:02d}" for i in range(10)]},
    ]
    suite = {"schema_version": 1, "id": "019-ple-fixed-requests-v1", "phase_order": PHASE_ORDER,
             "server_random_seed": seed, "source_api_commit": SOURCE_COMMIT, "cases": all_cases, "groups": groups,
             "public_sources": [{"source": p["source"], "original_request": p["original_request"]} for p in public],
             "controls": {"sampling": "temperature0/top_p1/top_k-1; fixed per-case seed in all phases",
                 "cache": "Unique per-case cache_salt; cold batch after backend-confirmed flush; hot repeats byte-identical payload after all cold requests finish.",
                 "public_snapshot_changes": "Preserve full messages/tools/tool_choice/template kwargs; add fixed benchmark generation/stream/cache fields. Original logs omit original sampling fields.",
                 "output_length": "Forced fixed-length throughput is not a quality task. Quality uses natural EOS, thinking off, a frozen 512-token cap.",
                 "quality_scope": "Ten deterministic synthetic literal-reading/tool tasks only; no full-game quality, hidden performance, judge model or generated-code execution.",
                 "streaming": "No return_token_ids or return_meta_info: pinned streaming endpoint rejects them. Chunks are not tokens."}}
    suite["suite_sha256"] = value_hash(suite)
    validate_suite(suite)
    return suite


def validate_suite(suite):
    content = {k: v for k, v in suite.items() if k != "suite_sha256"}
    if value_hash(content) != suite.get("suite_sha256"):
        raise ValueError("Suite hash mismatch")
    if suite["phase_order"] != PHASE_ORDER:
        raise ValueError("Frozen BF16/FP8/BF16 order required")
    cases = {c["id"]: c for c in suite["cases"]}
    if len(cases) != len(suite["cases"]):
        raise ValueError("Duplicate task IDs")
    for case in cases.values():
        p = case["payload"]
        if value_hash(p) != case["payload_sha256"] or not finite_json(p):
            raise ValueError("Corrupt/nonfinite payload")
        if not p.get("stream") or p.get("n") != 1 or p.get("return_token_ids") or p.get("return_meta_info") or p.get("return_prompt_token_ids"):
            raise ValueError("Unsupported streaming configuration")
        for message in p["messages"]:
            parts = message.get("content")
            if isinstance(parts, list):
                for part in parts:
                    for key in ("image_url", "audio_url", "video_url"):
                        if key in part:
                            value = part[key]
                            url = value.get("url", "") if isinstance(value, dict) else value
                            if not isinstance(url, str) or not url.startswith("data:"):
                                raise ValueError("Replay media must be inline data, never remote URLs")
    for group in suite["groups"]:
        if group["concurrency"] not in (1, 10) or not all(t in cases for t in group["task_ids"]):
            raise ValueError("Invalid frozen group")
    return {"valid": True, "suite_sha256": suite["suite_sha256"], "cases": len(cases),
            "total_requests_per_phase": sum(len(g["task_ids"]) for g in suite["groups"]),
            "public_request_count": len(suite["public_sources"])}


def _endpoint(base_url):
    p = urlsplit(base_url)
    host = "127.0.0.1" if p.hostname == "localhost" else p.hostname
    try:
        local = ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        local = False
    if p.scheme != "http" or not local or p.username or p.password or p.query or p.fragment or p.path.rstrip("/") not in ("", "/v1"):
        raise ValueError("Only plain HTTP loopback service roots or /v1 are supported")
    return host, p.port or 80


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.sequence = 0

    def append(self, row):
        with self.lock:
            self.sequence += 1
            value = {"ledger_seq": self.sequence, **row}
            with self.path.open("a") as stream:
                stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
            return self.sequence


def _local_request(base_url, endpoint, *, method="GET", payload=None, timeout=5):
    host, port = _endpoint(base_url)
    connection = http.client.HTTPConnection(host, port, timeout=max(.1, timeout))
    captured_socket = [None]
    timer = _connection_deadline(connection, captured_socket, max(.1, timeout))
    try:
        body = canonical(payload).encode() if payload is not None else b"" if method == "POST" else None
        connection.request(method, endpoint, body=body, headers={"Content-Type": "application/json"})
        captured_socket[0] = connection.sock
        response = connection.getresponse()
        raw = response.read().decode("utf-8", errors="replace")
        return {"http_status": response.status, "body": raw}
    finally:
        timer.cancel()
        connection.close()


def _connection_deadline(connection, captured_socket, seconds):
    # Socket read timeouts reset when bytes trickle in; shutdown at an absolute
    # wall duration also interrupts a partial SSE line or slow response body.
    # Retain the socket because HTTPConnection clears .sock on Connection:close
    # while HTTPResponse can still own its file object.
    def terminate():
        sock = connection.sock or captured_socket[0]
        if sock is not None:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
        connection.close()
    timer = threading.Timer(seconds, terminate)
    timer.daemon = True
    timer.start()
    return timer


def _sanitize_info(raw):
    # Public benchmark has no auth, but do not serialize server credentials if
    # an operator happens to configure them. The redacted response is labeled.
    try:
        value = strict_json(raw)
    except ValueError:
        return raw
    def clean(obj):
        if isinstance(obj, dict):
            return {k: "[REDACTED]" if any(t in k.lower() for t in ("api_key", "password", "secret")) and v else clean(v) for k, v in obj.items()}
        return [clean(v) for v in obj] if isinstance(obj, list) else obj
    return clean(value)


def _snapshot(base_url, endpoint, ledger, label, deadline):
    start = time.monotonic()
    try:
        if start >= deadline:
            raise TimeoutError("Phase deadline reached before diagnostics")
        result = _local_request(base_url, endpoint, timeout=min(3, deadline - start))
        if endpoint in ("/get_server_info", "/server_info"):
            result["body"] = _sanitize_info(result["body"])
            result["credentials_redacted"] = True
    except Exception as exc:
        result = {"error": type(exc).__name__, "detail": str(exc)}
    row = {"event": "server_snapshot", "label": label, "endpoint": endpoint,
           "epoch": time.time(), "duration_seconds": time.monotonic() - start, **result}
    ledger.append(row)
    return row


def _flush(base_url, serve_log, ledger, deadline, label):
    path = Path(serve_log) if serve_log is not None else None
    offset = path.stat().st_size if path and path.is_file() else None
    row = {"event": "cache_flush", "label": label, "epoch": time.time(), "serve_log_offset_before": offset}
    try:
        row.update(_local_request(base_url, "/flush_cache", method="POST", timeout=min(10, max(.1, deadline - time.monotonic()))))
        confirmed = False
        until = min(deadline, time.monotonic() + 10)
        while offset is not None and time.monotonic() < until:
            with path.open("rb") as f:
                f.seek(offset); recent = f.read()
            if b"Cache flushed successfully!" in recent:
                confirmed = True
                row["backend_confirmation_text"] = recent.decode(errors="replace")
                break
            time.sleep(.1)
        row["backend_confirmed"] = confirmed
    except Exception as exc:
        row.update(error=type(exc).__name__, detail=str(exc), backend_confirmed=False)
    ledger.append(row)
    if row.get("http_status") != 200 or not row["backend_confirmed"]:
        raise RuntimeError("Cold-cache group lacks new backend flush confirmation")
    return row


class StreamAccumulator:
    """Pure SSE decoder; callable on retained CPU fixtures without a server."""
    def __init__(self):
        self.content = ""
        self.reasoning = ""
        self.tools = {}
        self.usage = None
        self.sglext = {}
        self.finish_reason = None
        self.done = False
        self.errors = []
        self.first_any = self.first_visible = self.first_arguments = self.last_any = None
        self.first_payload_usage = None
        self.payload_events = 0

    def feed(self, data, elapsed):
        if data == "[DONE]":
            self.done = True
            return
        try:
            obj = strict_json(data)
        except ValueError as exc:
            self.errors.append("invalid_sse_json: " + str(exc)); return
        if not finite_json(obj):
            self.errors.append("nonfinite_sse_json"); return
        if obj.get("error"):
            self.errors.append(obj["error"])
        if obj.get("usage") is not None:
            self.usage = obj["usage"]
        if obj.get("sglext"):
            self.sglext.update(obj["sglext"])
        for choice in obj.get("choices", []):
            if choice.get("index", 0) != 0:
                self.errors.append("unexpected_choice_index"); continue
            self.finish_reason = choice.get("finish_reason") or self.finish_reason
            delta = choice.get("delta") or {}
            content = delta.get("content") or ""
            reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
            if not isinstance(content, str) or not isinstance(reasoning, str):
                self.errors.append("nonstring_text_delta"); continue
            self.content += content; self.reasoning += reasoning
            arguments = False
            tool_payload = False
            for item in delta.get("tool_calls") or []:
                index = item.get("index", 0)
                target = self.tools.setdefault(index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                if item.get("id"):
                    target["id"] = item["id"]
                fn = item.get("function") or {}
                for key in ("name", "arguments"):
                    fragment = fn.get(key) or ""
                    if not isinstance(fragment, str):
                        self.errors.append("nonstring_tool_delta"); continue
                    target["function"][key] += fragment
                    tool_payload |= bool(fragment)
                    if key == "arguments": arguments |= bool(fragment)
            if content and self.first_visible is None: self.first_visible = elapsed
            if arguments and self.first_arguments is None: self.first_arguments = elapsed
            if content or reasoning or tool_payload:
                if self.first_any is None:
                    self.first_any = elapsed
                    self.first_payload_usage = (obj.get("usage") or {}).get("completion_tokens")
                self.last_any = elapsed
                self.payload_events += 1

    def result(self):
        return {"message": {"content": self.content, "reasoning_content": self.reasoning,
                            "tool_calls": [self.tools[k] for k in sorted(self.tools)]},
                "usage": self.usage, "sglext": self.sglext, "finish_reason": self.finish_reason,
                "sse_done": self.done, "stream_errors": self.errors,
                "first_semantic_payload_seconds": self.first_any, "first_visible_content_seconds": self.first_visible,
                "first_tool_arguments_seconds": self.first_arguments, "last_semantic_payload_seconds": self.last_any,
                "first_payload_completion_tokens_if_reported": self.first_payload_usage,
                "semantic_payload_events_not_tokens": self.payload_events}


def response_checks(case, result):
    message = result["message"]
    parsed, format_errors = [], []
    for tool in message["tool_calls"]:
        try:
            args = strict_json(tool["function"]["arguments"])
            if not finite_json(args): raise ValueError("nonfinite arguments")
            if tool["function"]["name"] == "python":
                if not isinstance(args, dict) or not isinstance(args.get("code"), str):
                    raise ValueError("python tool has no string code")
                ast.parse(args["code"])  # Syntax only. Never executes code.
            parsed.append({"name": tool["function"]["name"], "arguments": args})
        except (ValueError, SyntaxError, TypeError) as exc:
            format_errors.append(str(exc))
    quality = case["kind"] == "synthetic_exact_tool"
    arg = parsed[0]["arguments"] if len(parsed) == 1 else None
    integer_cells = (isinstance(arg, dict) and type(arg.get("count")) is int
                     and isinstance(arg.get("cells"), list) and all(isinstance(cell, list) and len(cell) == 2
                     and all(type(coord) is int for coord in cell) for cell in arg["cells"]))
    exact = (len(parsed) == 1 and parsed[0]["name"] == "submit_observation" and integer_cells
             and arg == case.get("expected") and not format_errors and not message["content"].strip())
    return {"tool_calls": len(message["tool_calls"]), "parsed_tool_arguments": parsed,
            "format_errors": format_errors, "content_contains_replacement_character": "\ufffd" in canonical(message),
            "quality_exact_match": bool(exact) if quality else None,
            "quality_truncated": result.get("finish_reason") == "length" if quality else None,
            "public_format_observation_only": not quality,
            "note": "Fixed-length replay may cut a tool call intentionally. Format observations there are not quality failures. No generated Python is executed; AST parse checks syntax only."}


def _stream_request(base_url, case, group, phase, ledger, deadline, request_timeout=120):
    start, epoch = time.monotonic(), time.time()
    end = min(deadline, start + request_timeout)
    identity = {"phase": phase, "group": group, "case_id": case["id"], "payload_sha256": case["payload_sha256"]}
    ledger.append({"event": "request", **identity, "epoch": epoch, "payload": case["payload"]})
    accumulator, error, status = StreamAccumulator(), None, None
    connection = None
    timer = None
    captured_socket = [None]
    headers_time = None
    try:
        if start >= end: raise TimeoutError("No request budget remains")
        host, port = _endpoint(base_url)
        connection = http.client.HTTPConnection(host, port, timeout=max(.1, end - start))
        timer = _connection_deadline(connection, captured_socket, max(.1, end - time.monotonic()))
        connection.request("POST", "/v1/chat/completions", body=canonical(case["payload"]).encode(), headers={"Content-Type": "application/json"})
        captured_socket[0] = connection.sock
        response = connection.getresponse()
        status, headers_time = response.status, time.monotonic() - start
        ledger.append({"event": "response_headers", **identity, "elapsed_seconds": headers_time,
                       "http_status": status, "headers": dict(response.getheaders())})
        if status != 200:
            body = response.read().decode(errors="replace")
            ledger.append({"event": "http_error_body", **identity, "body": body})
            raise RuntimeError(f"HTTP {status}")
        data_lines = []
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0: raise TimeoutError("Absolute request/phase deadline")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            line = response.readline()
            if not line: break
            elapsed = time.monotonic() - start
            raw = line.decode("utf-8", errors="replace").rstrip("\r\n")
            ledger.append({"event": "sse_line", **identity, "elapsed_seconds": elapsed, "data": raw})
            if raw.startswith("data:"):
                data_lines.append(raw[5:].lstrip(" "))
            elif raw == "" and data_lines:
                accumulator.feed("\n".join(data_lines), elapsed)
                data_lines = []
                if accumulator.done: break
        if data_lines: accumulator.feed("\n".join(data_lines), time.monotonic() - start)
        if not accumulator.done: raise RuntimeError("SSE ended without [DONE]")
        if time.monotonic() > end: raise TimeoutError("Completion observed after absolute request/phase deadline")
    except Exception as exc:
        error = {"type": type(exc).__name__, "detail": str(exc)}
    finally:
        if timer: timer.cancel()
        if connection: connection.close()
    duration = time.monotonic() - start
    result = {**identity, "started_epoch": epoch, "elapsed_seconds": duration, "headers_seconds": headers_time,
              "http_status": status, "error": error, **accumulator.result()}
    usage = result.get("usage") or {}
    count = usage.get("completion_tokens")
    interval = (result["last_semantic_payload_seconds"] - result["first_semantic_payload_seconds"]
                if result["first_semantic_payload_seconds"] is not None and result["last_semantic_payload_seconds"] is not None else None)
    first_count = result["first_payload_completion_tokens_if_reported"]
    result["post_first_payload_usage_tokens_per_second_proxy"] = ((count - first_count) / interval
        if isinstance(count, int) and isinstance(first_count, int) and interval and interval > 0 and count >= first_count else None)
    result["usage_output_tokens_per_end_to_end_second"] = count / duration if isinstance(count, int) and duration > 0 else None
    result["fixed_output_length_matches"] = count == case["fixed_output_tokens"] if case["fixed_output_tokens"] is not None else None
    result["checks"] = response_checks(case, result)
    result["complete"] = error is None and result["sse_done"] and not result["stream_errors"] and isinstance(count, int)
    ledger.append({"event": "response_complete", **result})
    return result


def _stats(values):
    values = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    if not values: return {"n": 0, "mean": None, "median": None}
    return {"n": len(values), "mean": statistics.fmean(values), "median": statistics.median(values),
            "min": min(values), "max": max(values)}


def _group_summary(group, rows, elapsed, flush):
    tokens = sum((r.get("usage") or {}).get("completion_tokens", 0) or 0 for r in rows)
    cached = [((r.get("usage") or {}).get("prompt_tokens_details") or {}).get("cached_tokens") for r in rows]
    proposed = correct = 0
    spec_records = 0
    for r in rows:
        d = (r.get("sglext") or {}).get("spec_tokens_details")
        if isinstance(d, dict):
            spec_records += 1
            proposed += d.get("spec_num_proposed_drafts", 0)
            correct += d.get("spec_num_correct_drafts", 0)
    return {**group, "requests_expected": len(group["task_ids"]), "requests_completed": sum(r["complete"] for r in rows),
            "batch_wall_seconds": elapsed, "completion_tokens": tokens,
            "aggregate_output_tokens_per_batch_wall_second": tokens / elapsed if elapsed else None,
            "first_semantic_payload_seconds": _stats([r["first_semantic_payload_seconds"] for r in rows]),
            "first_visible_content_seconds": _stats([r["first_visible_content_seconds"] for r in rows]),
            "first_tool_arguments_seconds": _stats([r["first_tool_arguments_seconds"] for r in rows]),
            "post_first_payload_token_rate_proxy": _stats([r["post_first_payload_usage_tokens_per_second_proxy"] for r in rows]),
            "end_to_end_seconds": _stats([r["elapsed_seconds"] for r in rows]),
            "fixed_lengths_all_match": all(r["fixed_output_length_matches"] is True for r in rows) if group["id"] != "quality10" else None,
            "cached_tokens": cached, "cache_usage_all_known": all(isinstance(n, int) for n in cached),
            "cache_condition_observed": all(n == 0 for n in cached) if group["cache"] == "cold" else all(isinstance(n, int) and n > 0 for n in cached) if group["cache"] == "hot" else None,
            "flush": flush, "quality_exact_matches": sum(r["checks"]["quality_exact_match"] is True for r in rows) if group["id"] == "quality10" else None,
            "quality_truncations": sum(r["checks"]["quality_truncated"] is True for r in rows) if group["id"] == "quality10" else None,
            "spec_details_requests": spec_records, "spec_proposed_drafts": proposed if spec_records else None,
            "spec_correct_drafts": correct if spec_records else None,
            "spec_accept_rate_weighted": correct / proposed if proposed else None,
            "all_requests_complete": len(rows) == len(group["task_ids"]) and all(r["complete"] for r in rows)}


def run_phase(base_url, outdir, suite, deadline, *, phase, serve_log=None, metadata=None, request_timeout=120, metrics_interval=5):
    """Explicit network operation against an already-ready loopback server.

    deadline is an ABSOLUTE time.monotonic() deadline; caller owns service
    lifecycle/GPU/RSS measurement and should reserve shutdown time separately.
    This function refuses reuse of its own output files and never shortens the
    frozen suite. The caller's serve.log/launcher-state may already be present.
    """
    validate_suite(suite); _endpoint(base_url)
    if phase not in PHASE_ORDER: raise ValueError("Unknown BF16/FP8 phase")
    if deadline <= time.monotonic(): raise ValueError("Expired monotonic deadline")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    owned = ("suite.json", "manifest.json", "phase-report.json", "responses.jsonl", "server-metrics.jsonl")
    collisions = [name for name in owned if (outdir / name).exists()]
    if collisions: raise FileExistsError("Refusing to overwrite microbenchmark outputs: " + ", ".join(collisions))
    ledger, diagnostics = Ledger(outdir / "responses.jsonl"), Ledger(outdir / "server-metrics.jsonl")
    dump(outdir / "suite.json", suite)
    manifest = {"schema_version": 1, "phase": phase, "suite_sha256": suite["suite_sha256"],
                "module_sha256": file_hash(__file__), "started_utc": datetime.now(timezone.utc).isoformat(),
                "started_epoch": time.time(), "base_url": base_url, "deadline_monotonic": deadline,
                "metadata": metadata or {}, "status": "running", "groups": [], "requests": [],
                "semantics": {"ttft": "First semantic SSE payload, including reasoning/tool payload. Parser buffering can delay it beyond actual first generated token.",
                    "decode": "Continuous usage delta divided by first-to-last payload interval is a proxy, not a GPU kernel rate. Null if usage is missing at first payload.",
                    "batch_rate": "Successful-return completion tokens divided by actual group wall duration; retain failures and incomplete groups.",
                    "quality": "Exact synthetic answers only. Fixed-length public replays are deliberately truncated and cannot establish full-game quality.",
                    "numerics": "JSON/usage/output structural checks cannot prove hidden logits or model weights are finite; no hidden-state instrumentation."}}
    dump(outdir / "manifest.json", manifest)
    stop, current_group = threading.Event(), ["initial"]
    def sample():
        while not stop.wait(metrics_interval) and time.monotonic() < deadline:
            _snapshot(base_url, "/metrics", diagnostics, current_group[0], deadline)
    sampler = threading.Thread(target=sample, daemon=True)
    start = time.monotonic()
    try:
        info = _snapshot(base_url, "/get_server_info", diagnostics, "start", deadline)
        manifest["server_info_start"] = info
        sampler.start()
        cases = {c["id"]: c for c in suite["cases"]}
        for group in suite["groups"]:
            if time.monotonic() >= deadline: raise TimeoutError("Phase deadline before next frozen group")
            current_group[0] = group["id"]
            flush = _flush(base_url, serve_log, diagnostics, deadline, group["id"]) if group["flush_before"] else None
            _snapshot(base_url, "/metrics", diagnostics, group["id"] + ":before", deadline)
            group_start = time.monotonic()
            with ThreadPoolExecutor(max_workers=group["concurrency"]) as pool:
                futures = [pool.submit(_stream_request, base_url, cases[tid], group["id"], phase, ledger, deadline, request_timeout) for tid in group["task_ids"]]
                rows = [f.result() for f in futures]
            summary = _group_summary(group, rows, time.monotonic() - group_start, flush)
            manifest["requests"].extend(rows); manifest["groups"].append(summary)
            _snapshot(base_url, "/metrics", diagnostics, group["id"] + ":after", deadline)
            dump(outdir / "manifest.json", manifest)
            if not summary["all_requests_complete"]:
                raise RuntimeError("Frozen group incomplete; aborting instead of comparing a subset")
        manifest["status"] = "complete"
    except Exception as exc:
        manifest["status"] = "incomplete"
        manifest["error"] = {"type": type(exc).__name__, "detail": str(exc)}
    finally:
        stop.set()
        if sampler.is_alive(): sampler.join(timeout=4)
        manifest["metrics_sampler_stopped"] = not sampler.is_alive()
        manifest["finished_epoch"] = time.time()
        manifest["elapsed_seconds"] = time.monotonic() - start
        manifest["raw_response_sha256"] = file_hash(ledger.path) if ledger.path.exists() else None
        manifest["server_metrics_sha256"] = file_hash(diagnostics.path) if diagnostics.path.exists() else None
        dump(outdir / "manifest.json", manifest)
        dump(outdir / "phase-report.json", manifest)
    return manifest


def compare_phase_reports(paths):
    """Pure offline comparison; incomplete groups cannot produce speed claims."""
    reports = [json.loads(Path(p).read_text()) for p in paths]
    by_phase = {r["phase"]: r for r in reports}
    if len(reports) != 3 or set(by_phase) != set(PHASE_ORDER):
        raise ValueError("Exactly bf16_a, fp8, bf16_b reports required")
    ordered = [by_phase[p] for p in PHASE_ORDER]
    suite_same = len({r["suite_sha256"] for r in ordered}) == 1
    configs = [(r.get("server_info_start") or {}).get("body") for r in ordered]
    config_fields = ("dtype", "quantization", "kv_cache_dtype", "context_length", "max_running_requests",
                     "chunked_prefill_size", "max_prefill_tokens", "page_size", "mem_fraction_static",
                     "schedule_policy", "random_seed", "speculative_algorithm", "speculative_num_steps",
                     "speculative_num_draft_tokens", "speculative_accept_threshold_single",
                     "speculative_accept_threshold_acc", "mamba_ssm_dtype", "mamba_radix_cache_strategy",
                     "gdn_mtp_cache_mode", "reasoning_parser", "tool_call_parser", "default_chat_template_kwargs")
    configs_present = all(isinstance(c, dict) for c in configs)
    config_checks = {key: configs_present and all(key in c for c in configs)
                    and configs[0][key] == configs[1][key] == configs[2][key] for key in config_fields}
    chronological = all(a["finished_epoch"] <= b["started_epoch"] for a, b in zip(ordered, ordered[1:]))
    raw_checks = []
    for path in paths:
        r = json.loads(Path(path).read_text())
        raw = Path(path).parent / "responses.jsonl"
        raw_checks.append({"phase": r["phase"], "path": str(raw.resolve()),
                           "exists": raw.is_file(), "hash_matches": raw.is_file() and file_hash(raw) == r.get("raw_response_sha256")})
    provenance_valid = all(config_checks.values()) and chronological and all(r["hash_matches"] for r in raw_checks)
    maps = [{g["id"]: g for g in r["groups"]} for r in ordered]
    rows = []
    for group in sorted(set().union(*(set(m) for m in maps))):
        gs = [m.get(group) for m in maps]
        compatible = suite_same and provenance_valid and all(g and g["all_requests_complete"] for g in gs)
        if group != "quality10":
            compatible = compatible and all(g["fixed_lengths_all_match"] and g["cache_condition_observed"] is True for g in gs if g)
        row = {"group": group, "compatible_complete_group": bool(compatible),
               "phases": {phase: g for phase, g in zip(PHASE_ORDER, gs)}}
        if compatible and group != "quality10":
            aa, bb, cc = [g["aggregate_output_tokens_per_batch_wall_second"] for g in gs]
            baseline = (aa + cc) / 2
            row["fp8_rate_vs_mean_bf16_ratio"] = bb / baseline if baseline else None
            row["bf16_repeat_rate_ratio"] = cc / aa if aa else None
            row["fp8_rate_above_both_bf16_repeats"] = bb > max(aa, cc)
        rows.append(row)
    request_maps = [{(r["group"], r["case_id"]): r for r in report["requests"]} for report in ordered]
    paired = []
    for key in sorted(set().union(*(set(m) for m in request_maps))):
        rs = [m.get(key) for m in request_maps]
        same = all(rs) and len({r["payload_sha256"] for r in rs}) == 1
        def semantic(r):
            if r is None: return None
            msg = r["message"]
            return {"content": msg["content"], "reasoning_content": msg["reasoning_content"],
                    "tool_functions": [t["function"] for t in msg["tool_calls"]]}
        paired.append({"group": key[0], "case_id": key[1], "same_request_payload": bool(same),
                       "bf16_repeat_exact_output": semantic(rs[0]) == semantic(rs[2]) if all(rs) else None,
                       "fp8_equals_bf16_a": semantic(rs[1]) == semantic(rs[0]) if all(rs) else None,
                       "quality_exact_matches": {p: r["checks"]["quality_exact_match"] if r else None for p, r in zip(PHASE_ORDER, rs)}})
    return {"schema_version": 1, "phase_order": PHASE_ORDER, "same_suite": suite_same,
            "server_config_checks": config_checks, "phase_execution_order_verified": chronological,
            "raw_response_checks": raw_checks, "provenance_checks_pass": provenance_valid,
            "all_phases_complete": all(r["status"] == "complete" for r in ordered),
            "all_request_payloads_match": all(p["same_request_payload"] for p in paired),
            "sources": [{"path": str(Path(p).resolve()), "sha256": file_hash(p)} for p in paths],
            "groups": rows, "paired_requests": paired,
            "limits": ["Same seeds do not guarantee deterministic concurrent generation; BF16 repeat is a drift diagnostic, not a confidence interval.",
                       "Synthetic exact-answer quality is limited. Public forced-length outputs have no semantic judge and are never executed.",
                       "Client TTFT/decode proxies and aggregate throughput do not identify PLE kernel causality. Combine with independent weight/config/GPU/RSS audits.",
                       "Selected server controls and raw response hashes are checked here. Different model/tokenizer/draft paths require the runner's content/weight audit, not path-string equality.",
                       "No automatic acceptance, serving change, game run or submission follows this analysis."]}


def cpu_check():
    """No-network in-memory checks; no new tests/CI entry point."""
    suite = make_suite()
    check = validate_suite(suite)
    acc = StreamAccumulator()
    acc.feed('{"choices":[{"index":0,"delta":{"role":"assistant"}}]}', .1)
    assert acc.first_any is None
    chunks = [('{"choices":[{"index":0,"delta":{"reasoning_content":"r"}}],"usage":{"completion_tokens":1}}', .2),
              ('{"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"x","function":{"name":"submit_observation","arguments":"{\\"cells\\":"}}]}}],"usage":{"completion_tokens":2}}', .3),
              ('{"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"[],\\"count\\":0}"}}]},"finish_reason":"tool_calls"}]}', .4),
              ('{"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":7,"total_tokens":17}}', .5),
              ('{"choices":[],"sglext":{"spec_tokens_details":{"spec_num_proposed_drafts":8,"spec_num_correct_drafts":6}}}', .6)]
    for data, t in chunks: acc.feed(data, t)
    acc.feed('[DONE]', .7)
    result = acc.result()
    assert result["usage"]["completion_tokens"] == 7 and result["first_semantic_payload_seconds"] == .2
    assert result["first_tool_arguments_seconds"] == .3 and result["first_visible_content_seconds"] is None
    assert strict_json(result["message"]["tool_calls"][0]["function"]["arguments"]) == {"cells": [], "count": 0}
    checks = response_checks({"kind": "synthetic_exact_tool", "expected": {"cells": [], "count": 0}}, result)
    assert checks["quality_exact_match"]
    bad = StreamAccumulator(); bad.feed('{"usage":{"completion_tokens":NaN}}', 0)
    assert bad.errors and not bad.done
    for url in ("https://127.0.0.1:8001", "http://example.com", "http://127.0.0.1.evil.test", "http://127.0.0.1:8001/anything"):
        try: _endpoint(url)
        except ValueError: pass
        else: raise AssertionError("Unsafe endpoint accepted")
    return {"passed": True, "suite": check, "checks": ["offline_suite_hash", "role_chunk_not_token", "split_tool_arguments", "separate_final_usage_and_sglext", "reasoning_vs_visible_vs_tool_latency", "strict_nonfinite_rejection", "loopback_only"],
            "network_used": False, "models_or_logged_code_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--request-log", action="append", default=[], type=Path)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--output-tokens", type=int, default=256)
    prep.add_argument("--seed", type=int, default=190018)
    prep.add_argument("--model", default="flashnext")
    valid = sub.add_parser("validate"); valid.add_argument("suite", type=Path)
    sub.add_parser("cpu-check")
    run = sub.add_parser("run")
    run.add_argument("--allow-local-network", action="store_true")
    run.add_argument("--suite", type=Path, required=True); run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--phase", choices=PHASE_ORDER, required=True); run.add_argument("--base-url", default="http://127.0.0.1:8001")
    run.add_argument("--budget-seconds", type=float, default=360); run.add_argument("--serve-log", type=Path, required=True)
    analyze = sub.add_parser("analyze"); analyze.add_argument("reports", nargs=3, type=Path); analyze.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = make_suite(args.request_log, output_tokens=args.output_tokens, seed=args.seed, model=args.model)
        if args.output.exists(): raise FileExistsError("Refusing to overwrite a frozen suite")
        dump(args.output, result); print(json.dumps(validate_suite(result), indent=2))
    elif args.command == "validate": print(json.dumps(validate_suite(json.loads(args.suite.read_text())), indent=2))
    elif args.command == "cpu-check": print(json.dumps(cpu_check(), indent=2))
    elif args.command == "run":
        if not args.allow_local_network: parser.error("run requires explicit --allow-local-network")
        result = run_phase(args.base_url, args.output_dir, json.loads(args.suite.read_text()), time.monotonic() + args.budget_seconds,
                           phase=args.phase, serve_log=args.serve_log)
        print(json.dumps({k: result[k] for k in ("phase", "status", "elapsed_seconds")}, indent=2))
        if result["status"] != "complete": raise SystemExit(1)
    elif args.command == "analyze":
        result = compare_phase_reports(args.reports); dump(args.output, result)
        print(json.dumps({k: result[k] for k in ("same_suite", "all_phases_complete", "all_request_payloads_match")}, indent=2))


if __name__ == "__main__":
    main()
