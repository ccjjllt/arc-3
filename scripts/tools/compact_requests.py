#!/usr/bin/env python3
"""Compact repeated request snapshots without dropping context-trim boundaries.

Writes next to the source or to --output-dir; refuses to overwrite an existing
compact unless --overwrite is explicit. Never executes tool code. All JSONL
events retain metadata, including response usage. Text-message sequence
alignment handles history deletion/replacement; stable tool-call IDs prevent
counting replayed assistant/tool messages as new executions. User images are
omitted, with source locations and hashes retained. API-name references are
syntactic evidence, not proof of successful execution or causal use.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re


ANIMATION_HINT = re.compile(
    r"animation|transient|last_animation|changed and changed back|"
    r"last_animation_timeline|last_animation_frames",
    re.I,
)
CODE_HINT = re.compile(
    r"last_animation_timeline|last_animation_frames",
    re.I,
)
TRANSIENT_CUE = re.compile(r"animated over\s+\d+\s+frames", re.I)


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content
                         if isinstance(part, dict) and isinstance(part.get("text"), str))
    return "" if content is None else json.dumps(content, ensure_ascii=False)


def _signature(message: dict) -> str:
    # Image pruning must not count a replayed user cue as a new text message.
    if message.get("role") == "user":
        return _digest({"role": "user", "text": _text(message.get("content"))})
    return _digest(message)


def _stable_id(message: dict):
    if message.get("role") == "tool" and message.get("tool_call_id"):
        return "tool:" + message["tool_call_id"]
    calls = message.get("tool_calls") or []
    if message.get("role") == "assistant" and calls and all(c.get("id") for c in calls):
        return "assistant:" + ",".join(c["id"] for c in calls)
    return None


def _user_excerpt(content) -> dict:
    text = _text(content)
    lines = [line for line in text.splitlines() if ANIMATION_HINT.search(line)]
    return {
        "chars": len(text),
        "prefix": text[:500],
        "animation_lines": lines,
        "transient_cue_lines": [line for line in text.splitlines() if TRANSIENT_CUE.search(line)],
        "nontext_parts_omitted": sum(isinstance(p, dict) and p.get("type") != "text"
                                     for p in content) if isinstance(content, list) else 0,
        "excerpt_only": True,
    }


def _tool_content(content) -> dict:
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    payload = None
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        payload = None
    stdout = payload.get("stdout") if isinstance(payload, dict) else None
    error = payload.get("error") if isinstance(payload, dict) else None
    animation = None
    if isinstance(payload, dict):
        animation = payload.get("animation")
        result = payload.get("action_result")
        if animation is None and isinstance(result, dict):
            animation = result.get("animation")
    out = {
        "chars": len(text),
        "stdout": stdout if isinstance(stdout, str) else text[:80000],
        "error": error,
        "animation": animation,
        "mentions_animation": bool(ANIMATION_HINT.search(text)),
    }
    if isinstance(payload, dict):
        out["payload_metadata"] = {k: v for k, v in payload.items() if k != "stdout"}
    elif len(text) > 80000:
        out["stdout_truncated"] = True
    if isinstance(stdout, str) and len(stdout) > 80000:
        out["stdout"] = stdout[:40000] + "\n...<truncated>...\n" + stdout[-20000:]
        out["stdout_truncated"] = True
    return out


def _assistant(message: dict) -> dict:
    tool_calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        arguments = function.get("arguments")
        code = None
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                code = parsed.get("code")
                arguments = parsed
        elif isinstance(arguments, dict):
            code = arguments.get("code")
        loads = Counter()
        parse_error = None
        if isinstance(code, str):
            try:
                loads = Counter(node.id for node in ast.walk(ast.parse(code))
                                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                                and node.id in {"last_animation_timeline", "last_animation_frames", "frame_diff"})
            except SyntaxError as exc:
                parse_error = str(exc)
        tool_calls.append({
            "id": call.get("id"),
            "name": function.get("name"),
            "code": code,
            "arguments": arguments if code is None else {k: v for k, v in arguments.items() if k != "code"},
            "mentions_animation_api": bool(isinstance(code, str) and CODE_HINT.search(code)),
            "reads_animation_api": bool(loads["last_animation_timeline"] or loads["last_animation_frames"]),
            "direct_name_loads": dict(loads),
            "code_parse_error": parse_error,
            "execution_status": "not_inferred_from_code_reference",
        })
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    return {
        "reasoning": reasoning,
        "content": message.get("content"),
        "tool_calls": tool_calls,
        "reasoning_mentions_animation": bool(ANIMATION_HINT.search(str(reasoning))),
    }


def compact_file(path: Path) -> dict:
    records = []
    previous_signatures = []
    previous_hashes = []
    previous_ids = []
    known_stable_ids = set()
    request_count = 0
    response_count = 0
    trim_count = 0
    stats = Counter()
    api_counts = Counter()
    content_reference_counts = Counter()
    usage_totals = Counter()
    source_digest = hashlib.sha256()
    for source_line, raw in enumerate(path.open(encoding="utf-8"), 1):
        source_digest.update(raw.encode())
        if not raw.strip():
            continue
        obj = json.loads(raw)
        event = obj.get("event")
        if event == "request":
            request_count += 1
        elif event == "response":
            response_count += 1
            for key, value in (obj.get("usage") or {}).items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    usage_totals[key] += value
        messages = obj.get("messages") or []
        signatures = [_signature(message) for message in messages]
        hashes = [_digest(message) for message in messages]
        # Equal text can survive middle truncation, coalescing or image removal.
        # Positional slicing by the previous length silently loses new tail items.
        opcodes = SequenceMatcher(a=previous_signatures, b=signatures, autojunk=False).get_opcodes()
        current_ids = [None] * len(messages)
        new_indices = []
        context_changes = []
        image_only_revisions = []
        for tag, a0, a1, b0, b1 in opcodes:
            if tag == "equal":
                for old, new in zip(range(a0, a1), range(b0, b1)):
                    current_ids[new] = previous_ids[old]
                    if previous_hashes[old] != hashes[new]:
                        image_only_revisions.append({"message_id": current_ids[new], "message_index": new,
                                                     "raw_message_sha256": hashes[new]})
                continue
            context_changes.append({"operation": tag, "previous_range": [a0, a1],
                                    "current_range": [b0, b1]})
            new_indices.extend(range(b0, b1))
        dropped = len(messages) < len(previous_signatures)
        trim_count += int(dropped)
        compact_messages = []
        for index in new_indices:
            message = messages[index]
            role = message.get("role")
            stable_id = _stable_id(message)
            first_observation = stable_id not in known_stable_ids if stable_id else True
            message_id = stable_id or f"line:{source_line}:message:{index}"
            current_ids[index] = message_id
            if stable_id:
                known_stable_ids.add(stable_id)
            item = {
                "role": role,
                "message_id": message_id,
                "first_observation": first_observation,
                "source_line": source_line,
                "source_message_index": index,
                "raw_message_sha256": hashes[index],
                "analysis_step": obj.get("analysis_step"),
                "action": obj.get("action"),
                "event": event,
            }
            if role == "assistant":
                item.update(_assistant(message))
                if first_observation:
                    for call in item["tool_calls"]:
                        loads = call["direct_name_loads"]
                        stats["unique_tool_calls"] += 1
                        stats["animation_reference_tool_calls"] += int(call["reads_animation_api"])
                        content_reference_counts["either_animation_api_tool_calls"] += int(call["mentions_animation_api"])
                        for name in ("last_animation_timeline", "last_animation_frames", "frame_diff"):
                            content_reference_counts[name + "_tool_calls"] += int(name in (call.get("code") or ""))
                            api_counts[name + "_tool_calls"] += int(loads.get(name, 0) > 0)
                            api_counts[name + "_name_loads"] += loads.get(name, 0)
            elif role == "tool":
                item["tool_call_id"] = message.get("tool_call_id")
                item.update(_tool_content(message.get("content")))
            elif role == "user":
                item.update(_user_excerpt(message.get("content")))
                stats["user_text_messages"] += 1
                stats["user_animation_mention_messages"] += int(bool(item["animation_lines"]))
                stats["user_transient_cue_messages"] += int(bool(item["transient_cue_lines"]))
            else:
                item["content_prefix"] = str(message.get("content"))[:400]
            compact_messages.append(item)
            if first_observation:
                stats[role + "_first_observations"] += 1
        records.append({
            "source_line": source_line,
            "event": event,
            "analysis_step": obj.get("analysis_step"),
            "action": obj.get("action"),
            "request_index_within_turn": obj.get("request_index_within_turn"),
            "finish_reason": obj.get("finish_reason"),
            "usage": obj.get("usage"),
            "raw_message_count": len(messages),
            "context_length_decreased": dropped,
            "context_changes": context_changes,
            "nontext_user_revisions": image_only_revisions,
            "messages": compact_messages,
        })
        previous_signatures, previous_hashes, previous_ids = signatures, hashes, current_ids
    return {
        "schema_version": 2,
        "source": str(path),
        "source_sha256": source_digest.hexdigest(),
        "request_count": request_count,
        "response_count": response_count,
        "context_length_decrease_count": trim_count,
        "message_statistics": dict(stats),
        "code_content_reference_statistics": dict(content_reference_counts),
        "direct_api_reference_statistics": dict(api_counts),
        "response_usage_totals": dict(usage_totals),
        "interpretation_notes": [
            "Every input JSONL event is retained, even with no newly visible messages. Response snapshots can repeat request inputs; response usage does not prove its generated output is present in that snapshot.",
            "source_line is one-based; source_message_index is zero-based. analysis_step/action describe the snapshot where a message first becomes visible, not necessarily its originating model response.",
            "Sequence alignment preserves new messages across history trims. Stable tool-call IDs identify replayed assistant/tool variants. User alignment uses text only so image pruning does not duplicate cues.",
            "reads_animation_api means an AST Name load of last_animation_timeline/last_animation_frames, excluding frame_diff. It is syntactic evidence only: errors, branches, aliases and retained function calls require raw stdout review.",
            "Tool-call counts are distinct emitted calls; name_loads count syntactic occurrences. Neither is a count of successful frame reads or causal hypothesis updates.",
            "User content is an excerpt with image data omitted; long stdout is explicitly marked truncated. Absence in an excerpt cannot prove an observation or effect was absent.",
        ],
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for path in args.paths:
        if args.output_dir:
            destination = args.output_dir / f"{path.parent.name}__{path.stem}.compact.json"
        else:
            destination = path.with_suffix(".compact.json")
        if destination.exists() and not args.overwrite:
            parser.error(f"Output already exists; use a fresh --output-dir or --overwrite: {destination}")
        payload = compact_file(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(f"{path} -> {destination} records={len(payload['records'])} "
              f"requests={payload['request_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
