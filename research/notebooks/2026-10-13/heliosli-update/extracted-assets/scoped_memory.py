"""Bounded JSON scratch space with game, level and observation lifetimes.

Only model-written data is stored; game frames and executable objects are never
implicitly retained. This module is embedded in the isolated Python runner.
"""
import json
import math

SCOPED_MEMORY_LIMIT = 131072
SCOPED_MEMORY_SCOPES = ("game", "level", "step")


def _memory_json_copy(value):
    count = 0

    def validate(item, depth=0):
        nonlocal count
        count += 1
        if count > 24000 or depth > 20:
            raise ValueError("memory contains too many entries or too much nesting")
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                validate(child, depth + 1)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for key, child in item.items():
                validate(key, depth + 1)
                validate(child, depth + 1)
            return
        raise ValueError("memory accepts only JSON data with string dictionary keys")

    validate(value)
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > SCOPED_MEMORY_LIMIT:
        raise ValueError("memory exceeds the 128 KiB limit")
    return json.loads(encoded)


def restore_scoped_memory(saved, level, step):
    try:
        saved = _memory_json_copy(saved or {})
    except (TypeError, ValueError, OverflowError, RecursionError):
        saved = {}
    if type(saved) is not dict:
        saved = {}
    data = {scope: saved.get(scope, {}) if type(saved.get(scope)) is dict else {}
            for scope in SCOPED_MEMORY_SCOPES}
    identity = saved.get("_identity", {})
    if type(identity) is not dict or identity.get("level") != level:
        data["level"] = {}
        data["step"] = {}
    elif identity.get("step") != step:
        data["step"] = {}
    data["_identity"] = {"level": level, "step": step}
    return data


def refresh_scoped_memory(data, level, step):
    """Clear containers in place so local aliases see the invalidation too."""
    identity = data["_identity"]
    if identity["level"] != level:
        data["level"].clear()
        data["step"].clear()
    elif identity["step"] != step:
        data["step"].clear()
    identity.update(level=level, step=step)


def snapshot_scoped_memory(namespace, previous, level, step):
    try:
        if type(namespace) is not dict or set(namespace) != set(SCOPED_MEMORY_SCOPES):
            raise ValueError("scratch must contain exactly the game, level and step dictionaries")
        if any(type(namespace[s]) is not dict for s in SCOPED_MEMORY_SCOPES):
            raise ValueError("each scratch scope must remain a dictionary")
        saved = _memory_json_copy({**namespace, "_identity": {"level": level, "step": step}})
        return saved, ""
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        return restore_scoped_memory(previous, level, step), (
            "Scratch update was not saved: " + str(exc) + ". Previous valid data was restored."
        )
