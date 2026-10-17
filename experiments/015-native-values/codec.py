"""Bounded exact-built-in DAG codec; stdlib-only and embeddable in the child.

This serializes data, never code or object protocols. Container aliases survive
within and across roots; cycles are rejected. Scalars retain exact Python type.
"""
import json
import math


NV_LIMITS = {"bytes": 65536, "names": 32, "depth": 16, "nodes": 4096,
             "scalar_bytes": 16384, "int_bits": 4096}


class NativeValueError(ValueError):
    pass


def _nv_name(name):
    return (type(name) is str and 0 < len(name) <= 128 and name.isidentifier()
            and not name.startswith("__") and len(name.encode("utf-8")) <= 128)


def encode_values(values, limits=None):
    """Encode an entire namespace atomically, preserving container aliases."""
    limits = NV_LIMITS if limits is None else limits
    if type(values) is not dict or len(values) > limits["names"]:
        raise NativeValueError("name_capacity")
    # Check every alias path: a memoized short path must not hide a longer
    # path exceeding the depth cap. Count repeated paths to bound this pass.
    preflight_count = 0
    preflight_active = set()

    def preflight(item, depth):
        nonlocal preflight_count
        preflight_count += 1
        if preflight_count > limits["nodes"]:
            raise NativeValueError("node_capacity")
        if depth > limits["depth"]:
            raise NativeValueError("depth_capacity")
        kind = type(item)
        if kind not in (list, tuple, dict, set, frozenset):
            return
        if id(item) in preflight_active:
            raise NativeValueError("cycle")
        if len(item) > limits["nodes"]:
            raise NativeValueError("node_capacity")
        preflight_active.add(id(item))
        if kind is dict:
            for key, value in item.items():
                preflight(key, depth + 1)
                preflight(value, depth + 1)
        else:
            for value in item:
                preflight(value, depth + 1)
        preflight_active.remove(id(item))

    for value in values.values():
        preflight(value, 0)
    nodes, seen, active = [], {}, set()
    count, charged = 0, 0

    def charge(amount):
        nonlocal charged
        charged += amount
        if charged > limits["bytes"]:
            raise NativeValueError("byte_capacity")

    def visit(item, depth):
        nonlocal count
        count += 1
        if count > limits["nodes"]:
            raise NativeValueError("node_capacity")
        if depth > limits["depth"]:
            raise NativeValueError("depth_capacity")
        kind = type(item)
        if item is None:
            charge(8)
            return ["n"]
        if kind is bool:
            charge(16)
            return ["b", item]
        if kind is int:
            if item.bit_length() > limits["int_bits"]:
                raise NativeValueError("integer_capacity")
            value = str(item)
            charge(len(value) + 16)
            return ["i", value]
        if kind is float:
            if not math.isfinite(item):
                raise NativeValueError("nonfinite_float")
            value = item.hex()
            charge(len(value) + 16)
            return ["f", value]
        if kind is str:
            if len(item) > limits["scalar_bytes"]:
                raise NativeValueError("scalar_capacity")
            try:
                encoded = json.dumps(item, ensure_ascii=False).encode("utf-8")
            except UnicodeError:
                raise NativeValueError("invalid_unicode") from None
            if len(encoded) > limits["scalar_bytes"]:
                raise NativeValueError("scalar_capacity")
            charge(len(encoded) + 16)
            return ["s", item]
        if kind not in (list, tuple, dict, set, frozenset):
            raise NativeValueError("unsupported_type")
        object_id = id(item)
        if object_id in active:
            raise NativeValueError("cycle")
        if object_id in seen:
            charge(24)
            return ["r", seen[object_id]]
        if len(item) > limits["nodes"]:
            raise NativeValueError("node_capacity")
        charge(48)
        index = len(nodes)
        seen[object_id] = index
        nodes.append(None)
        active.add(object_id)
        if kind is dict:
            content = [[visit(k, depth + 1), visit(v, depth + 1)] for k, v in item.items()]
        else:
            content = [visit(v, depth + 1) for v in item]
        active.remove(object_id)
        nodes[index] = [kind.__name__, content]
        return ["r", index]

    roots = []
    for name, value in values.items():
        if not _nv_name(name):
            raise NativeValueError("invalid_name")
        charge(len(name.encode("utf-8")) + 16)
        roots.append([name, visit(value, 0)])
    blob = json.dumps({"version": 1, "roots": roots, "nodes": nodes},
                      ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(blob) > limits["bytes"]:
        raise NativeValueError("byte_capacity")
    return blob


def decode_values(blob, limits=None):
    """Validate untrusted wire data before restoring only exact built-ins."""
    limits = NV_LIMITS if limits is None else limits
    if type(blob) is not bytes or len(blob) > limits["bytes"]:
        raise NativeValueError("invalid_blob")
    try:
        data = json.loads(blob)
    except (ValueError, UnicodeError, RecursionError):
        raise NativeValueError("invalid_json") from None
    if (type(data) is not dict or set(data) != {"version", "roots", "nodes"}
            or type(data["version"]) is not int or data["version"] != 1
            or type(data["roots"]) is not list or type(data["nodes"]) is not list
            or len(data["roots"]) > limits["names"] or len(data["nodes"]) > limits["nodes"]):
        raise NativeValueError("invalid_schema")
    nodes, memo, active = data["nodes"], {}, set()
    count = 0

    def read(node, depth):
        nonlocal count
        count += 1
        if count > limits["nodes"] or depth > limits["depth"]:
            raise NativeValueError("decode_capacity")
        if type(node) is not list or not node or type(node[0]) is not str:
            raise NativeValueError("invalid_node")
        tag = node[0]
        if tag == "n" and len(node) == 1:
            return None
        if len(node) != 2:
            raise NativeValueError("invalid_node")
        value = node[1]
        if tag == "b" and type(value) is bool:
            return value
        if tag == "s" and type(value) is str:
            if len(value.encode("utf-8")) > limits["scalar_bytes"]:
                raise NativeValueError("scalar_capacity")
            return value
        if tag == "i" and type(value) is str:
            if len(value) > limits["int_bits"]:
                raise NativeValueError("integer_capacity")
            try:
                item = int(value)
            except ValueError:
                raise NativeValueError("invalid_integer") from None
            if str(item) != value or item.bit_length() > limits["int_bits"]:
                raise NativeValueError("invalid_integer")
            return item
        if tag == "f" and type(value) is str and len(value) <= 32:
            try:
                item = float.fromhex(value)
            except (ValueError, OverflowError):
                raise NativeValueError("invalid_float") from None
            if not math.isfinite(item) or item.hex() != value:
                raise NativeValueError("invalid_float")
            return item
        if tag != "r" or type(value) is not int or not 0 <= value < len(nodes):
            raise NativeValueError("invalid_reference")
        if value in active:
            raise NativeValueError("cycle")
        if value in memo:
            return memo[value]
        record = nodes[value]
        if (type(record) is not list or len(record) != 2 or type(record[0]) is not str
                or type(record[1]) is not list or len(record[1]) > limits["nodes"]):
            raise NativeValueError("invalid_container")
        kind, content = record
        active.add(value)
        if kind == "dict":
            item = {}
            for pair in content:
                if type(pair) is not list or len(pair) != 2:
                    raise NativeValueError("invalid_pair")
                key, val = read(pair[0], depth + 1), read(pair[1], depth + 1)
                try:
                    if key in item:
                        raise NativeValueError("duplicate_key")
                    item[key] = val
                except TypeError:
                    raise NativeValueError("unhashable_key") from None
        elif kind in ("list", "tuple", "set", "frozenset"):
            children = [read(child, depth + 1) for child in content]
            try:
                item = {"list": list, "tuple": tuple, "set": set, "frozenset": frozenset}[kind](children)
            except TypeError:
                raise NativeValueError("unhashable_member") from None
            if kind in ("set", "frozenset") and len(item) != len(children):
                raise NativeValueError("duplicate_member")
        else:
            raise NativeValueError("invalid_container_tag")
        active.remove(value)
        memo[value] = item
        return item

    result = {}
    try:
        for root in data["roots"]:
            if type(root) is not list or len(root) != 2 or not _nv_name(root[0]) or root[0] in result:
                raise NativeValueError("invalid_root")
            result[root[0]] = read(root[1], 0)
        if len(memo) != len(nodes):
            raise NativeValueError("unreachable_nodes")
        # Apply encoder bounds/canonical scalar constraints also on host input.
        encode_values(result, limits)
    except (UnicodeError, RecursionError):
        raise NativeValueError("invalid_value") from None
    return result


def capture_namespace(namespace, reserved, limits=None):
    """Successful snapshots replace all saved names; rejected rebinds vanish."""
    limits = NV_LIMITS if limits is None else limits
    if type(namespace) is not dict:
        raise NativeValueError("invalid_namespace")
    values, rejected = {}, []
    for name, value in namespace.items():
        if not _nv_name(name) or name in reserved:
            continue
        if len(values) + len(rejected) >= limits["names"]:
            raise NativeValueError("name_capacity")
        try:
            encode_values({name: value}, limits)
        except NativeValueError as exc:
            rejected.append({"name": name, "reason": str(exc)})
            continue
        values[name] = value
    return encode_values(values, limits), rejected
