#!/usr/bin/env python3
"""Strip repeated request history so a human can read 003 traces.

Writes compact JSON next to the source by default, or to --output. Does not
execute tool code. User prompts keep only animation/transient cues plus a
short prefix; assistant reasoning, tool calls, and tool stdout stay intact
unless a single stdout exceeds 80k characters.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ANIMATION_HINT = re.compile(
    r"animation|transient|last_animation|changed and changed back|"
    r"last_animation_timeline|last_animation_frames",
    re.I,
)
CODE_HINT = re.compile(
    r"last_animation_timeline|last_animation_frames|frame_diff|"
    r"\['animation'\]|\[\"animation\"\]|\.get\(\s*['\"]animation",
    re.I,
)


def _user_excerpt(content: str) -> dict:
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    lines = [line for line in text.splitlines() if ANIMATION_HINT.search(line)]
    return {
        "chars": len(text),
        "prefix": text[:500],
        "animation_lines": lines[:40],
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
        tool_calls.append({
            "id": call.get("id"),
            "name": function.get("name"),
            "code": code,
            "arguments": arguments if code is None else None,
            "reads_animation_api": bool(code and CODE_HINT.search(code)),
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
    seen = 0
    request_count = 0
    response_count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        event = obj.get("event")
        if event == "request":
            request_count += 1
        elif event == "response":
            response_count += 1
        messages = obj.get("messages") or []
        new = messages[seen:]
        seen = len(messages)
        compact_messages = []
        for message in new:
            role = message.get("role")
            item = {
                "role": role,
                "analysis_step": obj.get("analysis_step"),
                "action": obj.get("action"),
                "event": event,
            }
            if role == "assistant":
                item.update(_assistant(message))
            elif role == "tool":
                item["tool_call_id"] = message.get("tool_call_id")
                item.update(_tool_content(message.get("content")))
            elif role == "user":
                item.update(_user_excerpt(message.get("content")))
            else:
                item["content_prefix"] = str(message.get("content"))[:400]
            compact_messages.append(item)
        if not compact_messages:
            continue
        records.append({
            "event": event,
            "analysis_step": obj.get("analysis_step"),
            "action": obj.get("action"),
            "finish_reason": obj.get("finish_reason"),
            "usage": obj.get("usage"),
            "messages": compact_messages,
        })
    return {
        "source": str(path),
        "request_count": request_count,
        "response_count": response_count,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    for path in args.paths:
        payload = compact_file(path)
        if args.output_dir:
            destination = args.output_dir / f"{path.parent.name}__{path.stem}.compact.json"
        else:
            destination = path.with_suffix(".compact.json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(f"{path} -> {destination} records={len(payload['records'])} "
              f"requests={payload['request_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
