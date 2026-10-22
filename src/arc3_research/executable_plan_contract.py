"""034 pure host contracts for a model-produced executable plan.

This module neither imports the game runtime nor executes candidate code or
actions.  Its checks establish syntax, current-pixel evidence and the declared
prediction projection, never a correct goal, complete physics or safe action.
The native adapter owns sandboxing, deadlines, lifecycle boundaries and the
actual program replacement.  A reference in ``replaces`` proves only that a
named binding was supplied by that adapter, not that the new code uses it.

Example model returns::

    plan_program(frame) -> {
        "goal": {"target": "move the visible piece onto the marked cell"},
        "actions": [{"action": "RIGHT"}],
        "evidence_pixels": [[4, 6, "A"]],
        "replaces": ["build_target"], "reason": "Re-read the piece footprint"}
    predict(frame, action) -> {
        "scope": "piece pixels in screen row/column coordinates",
        "expected_pixels": [[4, 6, "."], [4, 7, "A"]]}

The adapter may place the returned data in an event containing ``game``,
``level``, ``attempt_event``, ``observation_id``, ``program_hash``, ``before``,
``action``, ``expected``, ``observed`` and ``status``.  This module does not
invent those runtime identities.  In particular, compare only after handling
level changes/death/reset: a changed grid shape produces ``unknown`` here.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
from typing import Any


MAX_CODE_BYTES = 32768
MAX_JSON_BYTES = 65536
MAX_PIXELS = 4096
MAX_ACTIONS = 12
_IMPORTS = {
    "array", "bisect", "collections", "copy", "fractions", "functools",
    "heapq", "itertools", "json", "math", "numpy", "operator", "re", "statistics",
}
_NO_AUTOMATIC_ACTIONS = {"RESET", "UNDO", "ACTION0", "ACTION7"}
_FORBIDDEN_CALLS = {"action", "open", "input", "eval", "exec", "compile", "__import__"}


def json_copy(value: Any, *, max_bytes: int = MAX_JSON_BYTES) -> Any:
    """Return a detached strict-JSON value, with bounded depth, nodes and bytes.

    Reject tuples, non-string keys, non-finite numbers and arbitrary objects
    rather than silently converting them.  Booleans remain JSON booleans, not
    coordinates or integers.  Integers stay within the interoperable JSON range.
    """
    nodes = 0

    def check(item: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > 20000 or depth > 20:
            raise ValueError("JSON structure exceeds its depth/node limit")
        kind = type(item)
        if item is None or kind is bool:
            return
        if kind is int:
            if abs(item) > 2**53 - 1:
                raise ValueError("JSON integer exceeds the exact interoperable range")
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("JSON numbers must be finite")
        elif kind is str:
            if len(item) > max_bytes:
                raise ValueError("JSON string exceeds its size limit")
        elif kind is list:
            for child in item:
                check(child, depth + 1)
        elif kind is dict:
            if any(type(key) is not str for key in item):
                raise ValueError("JSON object keys must be strings")
            for key, child in item.items():
                check(key, depth + 1)
                check(child, depth + 1)
        else:
            raise ValueError("Value is not strict JSON")

    check(value, 0)
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False,
                             sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("Value cannot be encoded as strict UTF-8 JSON") from exc
    if len(encoded) > max_bytes:
        raise ValueError("JSON output exceeds its byte limit")
    return json.loads(encoded)


def stable_hash(value: Any) -> str:
    """SHA256 of bounded, canonical strict JSON (not a semantic certificate)."""
    clean = json_copy(value)
    encoded = json.dumps(clean, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_object(text: str) -> dict[str, Any]:
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("Tool arguments exceed the byte limit")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON object key: " + key)
            result[key] = value
        return result

    try:
        result = json.loads(text, object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(
                                ValueError("Non-finite JSON number")))
    except (ValueError, RecursionError) as exc:
        raise ValueError("Invalid strict JSON tool arguments: " + str(exc)[:160]) from exc
    if type(result) is not dict:
        raise ValueError("Tool arguments must be a JSON object")
    return json_copy(result)


def _parse(code: str, max_bytes: int = MAX_CODE_BYTES) -> ast.Module:
    if type(code) is not str or not code.strip():
        raise ValueError("Provide nonempty Python source")
    try:
        if len(code.encode("utf-8")) > max_bytes:
            raise ValueError("Python source exceeds the byte limit")
        tree = ast.parse(code)
    except (SyntaxError, RecursionError, UnicodeError) as exc:
        raise ValueError("Invalid Python source") from exc
    if sum(1 for _ in ast.walk(tree)) > 12000:
        raise ValueError("Python AST exceeds its node limit")
    return tree


def binding_names(code: str) -> list[str]:
    """Return statically declared module-scope names, never function locals.

    Names inside module control flow are candidates, not proof that the branch
    executed.  The adapter must obtain source from a real current snippet and
    distinguish those references from actual retained runtime functions.
    """
    tree = _parse(code, max_bytes=131072)

    class Bindings(ast.NodeVisitor):
        names: set[str]

        def __init__(self) -> None:
            self.names = set()

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, ast.Store):
                self.names.add(node.id)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.names.add(node.name)

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef

        def visit_Lambda(self, node: ast.Lambda) -> None:
            pass

        def visit_Import(self, node: ast.Import) -> None:
            self.names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            self.names.update(alias.asname or alias.name for alias in node.names if alias.name != "*")

        def visit_ListComp(self, node: ast.AST) -> None:
            # Comprehension targets have their own scope, unlike a module for.
            pass

        visit_SetComp = visit_ListComp
        visit_DictComp = visit_ListComp
        visit_GeneratorExp = visit_ListComp

    visitor = Bindings()
    visitor.visit(tree)
    return sorted(visitor.names)


def extract_definitions(message: dict[str, Any]) -> dict[str, Any]:
    """Extract one Python tool call with definitions/imports only; never exec.

    Required signatures are exactly plan_program(frame) and predict(frame,
    action). Imports use a small computational allowlist including numpy. Decorators,
    defaults, annotations and type parameters can execute while defining a
    function, so they are rejected.  The real sandbox must still block actions
    while evaluating the functions; static checks are not a security boundary.
    """
    if type(message) is not dict or type(message.get("tool_calls")) is not list:
        raise ValueError("Expected an assistant message with one Python tool call")
    calls = message["tool_calls"]
    if len(calls) != 1 or type(calls[0]) is not dict:
        raise ValueError("Return exactly one Python tool call")
    function = calls[0].get("function")
    if type(function) is not dict or function.get("name") != "python":
        raise ValueError("Expected the existing python tool")
    arguments = function.get("arguments")
    arguments = _json_object(arguments) if type(arguments) is str else json_copy(arguments)
    if type(arguments) is not dict or set(arguments) != {"code"}:
        raise ValueError("Python arguments must contain only code")
    code = arguments["code"]
    tree = _parse(code)
    functions: dict[str, ast.FunctionDef] = {}
    seen: set[str] = set()
    for index, node in enumerate(tree.body):
        if (index == 0 and isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant) and type(node.value.value) is str):
            continue
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node
            names = [node.name]
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
            if (isinstance(node, ast.ImportFrom) and node.level) or any(m not in _IMPORTS for m in modules):
                raise ValueError("Import is outside the pure standard-library contract")
            if any(a.name == "*" for a in node.names):
                raise ValueError("Star imports are not supported")
            names = [a.asname or a.name.split(".")[0] for a in node.names]
        else:
            raise ValueError("Return only function definitions and allowed imports")
        for name in names:
            if name in seen or name.startswith("__"):
                raise ValueError("Duplicate or reserved top-level binding: " + name)
            seen.add(name)
    if len(functions) > 32:
        raise ValueError("Too many function definitions")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
            if ((isinstance(node, ast.ImportFrom) and node.level)
                    or any(m not in _IMPORTS for m in modules)
                    or any(a.name == "*" for a in node.names)):
                raise ValueError("Import is outside the pure standard-library contract")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            all_args = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            if args.vararg:
                all_args.append(args.vararg)
            if args.kwarg:
                all_args.append(args.kwarg)
            if (node.decorator_list or args.defaults or any(x is not None for x in args.kw_defaults)
                    or node.returns is not None or any(a.annotation is not None for a in all_args)
                    or getattr(node, "type_params", [])):
                raise ValueError("Definitions cannot have decorators, defaults, annotations or type parameters")
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            raise ValueError("Functions must not mutate global bindings")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _FORBIDDEN_CALLS):
            raise ValueError("Function contains an action or executable-I/O call")
    for name, expected in (("plan_program", ["frame"]), ("predict", ["frame", "action"])):
        node = functions.get(name)
        if node is None:
            raise ValueError("Missing " + name)
        args = node.args
        if ([a.arg for a in [*args.posonlyargs, *args.args]] != expected
                or args.kwonlyargs or args.vararg or args.kwarg):
            raise ValueError("Required signature is " + name + "(" + ", ".join(expected) + ")")
    try:
        compile(tree, "<executable_plan_contract>", "exec")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ValueError("Candidate definitions do not compile") from exc
    return {"code": code, "definitions": sorted(functions),
            "code_sha256": hashlib.sha256(code.encode("utf-8")).hexdigest()}


def _frame(grid: Any, chars: Any) -> tuple[list[list[str]], int, int]:
    if not isinstance(chars, (str, list, tuple)) or not 1 <= len(chars) <= 256:
        raise ValueError("Invalid public color alphabet")
    palette = list(chars)
    if (any(type(c) is not str or len(c) != 1 for c in palette)
            or len(set(palette)) != len(palette)):
        raise ValueError("Public color characters must be unique single characters")
    if not isinstance(grid, (list, tuple)) or not 1 <= len(grid) <= 256:
        raise ValueError("Current pixel grid is unavailable")
    width = len(grid[0]) if isinstance(grid[0], (list, tuple)) else 0
    if not 1 <= width <= 256:
        raise ValueError("Invalid pixel grid width")
    output = []
    for row in grid:
        if not isinstance(row, (list, tuple)) or len(row) != width:
            raise ValueError("Pixel grid must be rectangular")
        if any(type(v) is not int or not 0 <= v < len(palette) for v in row):
            raise ValueError("Pixel grid contains an invalid color index")
        output.append([palette[v] for v in row])
    return output, len(output), width


def _pixels(records: Any, height: int, width: int, chars: Any) -> list[list[Any]]:
    if type(records) is not list or not 1 <= len(records) <= min(MAX_PIXELS, height * width):
        raise ValueError("Pixel projection must be a bounded nonempty list")
    seen: set[tuple[int, int]] = set()
    normalized = []
    for item in records:
        if type(item) is not list or len(item) != 3:
            raise ValueError("Each pixel must be [row, col, color_character]")
        row, col, color = item
        if (type(row) is not int or type(col) is not int
                or not 0 <= row < height or not 0 <= col < width):
            raise ValueError("Pixel coordinate is outside the current frame")
        if type(color) is not str or len(color) != 1 or color not in chars:
            raise ValueError("Pixel has an invalid color character")
        if (row, col) in seen:
            raise ValueError("Duplicate pixel coordinate")
        seen.add((row, col))
        normalized.append([row, col, color])
    return sorted(normalized, key=lambda p: (p[0], p[1]))


def _text(value: Any, label: str, maximum: int) -> str:
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError(label + " must be a bounded nonempty string")
    return value.strip()


def _failure(exc: Exception, status: str = "rejected") -> dict[str, Any]:
    return {"passed": False, "status": status, "errors": [str(exc)[:300]]}


def validate_plan(value: Any, grid: Any, chars: Any, valid_actions: Any,
                  available_bindings: Any) -> dict[str, Any]:
    """Validate schema, a current-program reference and exact observed pixels.

    ``goal`` is a bounded nonempty string/object/list, an explicit hypothesis.
    The adapter must execute plan_program on this frame to obtain ``value``;
    this function cannot establish that provenance from a bare JSON result.
    """
    try:
        plan = json_copy(value)
        observed, height, width = _frame(grid, chars)
        required = {"goal", "actions", "evidence_pixels", "replaces", "reason"}
        if type(plan) is not dict or set(plan) != required:
            raise ValueError("Plan requires exactly goal, actions, evidence_pixels, replaces and reason")
        goal = plan["goal"]
        if type(goal) not in (str, dict, list) or not goal or (type(goal) is str and not goal.strip()):
            raise ValueError("Goal must describe a nonempty hypothesis, not a Boolean or empty result")
        json_copy(goal, max_bytes=8192)
        if type(goal) is str:
            goal = goal.strip()
            if goal.casefold() in {"ok", "true", "passed", "success", "done"}:
                raise ValueError("Goal needs task context, not a success assertion")
        if (type(goal) is dict and all(k.casefold() in {"ok", "true", "passed", "success", "done"}
                                      and type(v) is bool for k, v in goal.items())):
            raise ValueError("Goal needs task context, not only success flags")
        plan["goal"] = goal
        plan["reason"] = _text(plan["reason"], "reason", 2000)
        if not isinstance(valid_actions, (list, tuple, set, frozenset)) or any(type(a) is not str for a in valid_actions):
            raise ValueError("Current public valid_actions are unavailable")
        legal = set(valid_actions)
        actions = plan["actions"]
        if type(actions) is not list or not 1 <= len(actions) <= MAX_ACTIONS:
            raise ValueError("Plan must contain 1..12 actions")
        for action in actions:
            if type(action) is not dict or type(action.get("action")) is not str:
                raise ValueError("Action must contain its existing model API name")
            name = action["action"]
            if name not in legal or name.upper() in _NO_AUTOMATIC_ACTIONS:
                raise ValueError("Action is unavailable or is an automatic RESET/UNDO")
            if name == "MOUSE":
                if (set(action) != {"action", "row", "col"}
                        or type(action["row"]) is not int or type(action["col"]) is not int
                        or not 0 <= action["row"] < height or not 0 <= action["col"] < width):
                    raise ValueError("MOUSE requires exact in-frame integer row/col")
            elif set(action) != {"action"}:
                raise ValueError("Non-MOUSE action has unexpected fields")
        if not isinstance(available_bindings, (dict, list, tuple, set, frozenset)):
            raise ValueError("Current program bindings are unavailable")
        available = set(available_bindings)
        if not available or any(type(n) is not str for n in available):
            raise ValueError("A current code/retained-function binding is required")
        replaces = plan["replaces"]
        if (type(replaces) is not list or not 1 <= len(replaces) <= 32
                or any(type(n) is not str or not n.isidentifier() or len(n) > 128 for n in replaces)):
            raise ValueError("replaces must name current program bindings")
        if len(set(replaces)) != len(replaces) or any(n not in available for n in replaces):
            raise ValueError("Unknown or duplicate replaced binding")
        plan["replaces"] = sorted(replaces)
        evidence = _pixels(plan["evidence_pixels"], height, width, chars)
        differences = [{"row": r, "col": c, "claimed": color, "observed": observed[r][c]}
                       for r, c, color in evidence if color != observed[r][c]]
        if differences:
            return {"passed": False, "status": "rejected_evidence", "errors": ["Evidence differs from current pixels"],
                    "wrong_pixels": len(differences), "differences": differences[:16]}
        plan["evidence_pixels"] = evidence
        return {"passed": True, "status": "validated_current_evidence", "errors": [], "plan": plan,
                "plan_sha256": stable_hash(plan), "input_grid_sha256": stable_hash([list(r) for r in grid]),
                "coverage": {"evidence_pixels": len(evidence), "frame_pixels": height * width,
                             "fraction": len(evidence) / (height * width)},
                "claim": "Executable output schema and declared current pixels only; goal and dynamics unverified"}
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        return _failure(exc)


def validate_prediction(value: Any, grid: Any, chars: Any) -> dict[str, Any]:
    """Freeze a nonempty pixel projection before the adapter sends an action.

    Unchanged predictions are legitimate and counted explicitly.  A single
    matching background pixel is weak coverage, not proof of correct physics.
    """
    try:
        value = json_copy(value)
        observed, height, width = _frame(grid, chars)
        if (type(value) is not dict or "expected_pixels" not in value
                or set(value) - {"expected_pixels", "scope"}):
            raise ValueError("Prediction requires expected_pixels and optional scope")
        scope = _text(value.get("scope", "declared screen pixels (row,col,color)"), "scope", 512)
        pixels = _pixels(value["expected_pixels"], height, width, chars)
        changed = sum(color != observed[r][c] for r, c, color in pixels)
        prediction = {"expected_pixels": pixels, "scope": scope, "grid_shape": [height, width]}
        return {"passed": True, "status": "declared_prediction", "errors": [], "prediction": prediction,
                "prediction_sha256": stable_hash(prediction),
                "input_grid_sha256": stable_hash([list(r) for r in grid]),
                "coverage": {"selected_pixels": len(pixels), "frame_pixels": height * width,
                             "fraction": len(pixels) / (height * width), "predicted_changed_pixels": changed,
                             "predicted_unchanged_pixels": len(pixels) - changed,
                             "unchanged_only": changed == 0},
                "claim": "Pending real transition; no physical correctness or whole-board guarantee"}
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        return _failure(exc, "unknown")


def compare_prediction(frozen_prediction: Any, new_grid: Any, chars: Any) -> dict[str, Any]:
    """Compare only frozen declared pixels with the independently supplied grid.

    Return match/mismatch/unknown.  Never infer a win, material invariant or
    which of the model's interpretation/predictor is wrong.  No model code runs.
    """
    try:
        prediction = json_copy(frozen_prediction)
        observed, height, width = _frame(new_grid, chars)
        if (type(prediction) is not dict
                or set(prediction) != {"expected_pixels", "scope", "grid_shape"}):
            raise ValueError("Expected a frozen validated pixel prediction")
        scope = _text(prediction["scope"], "scope", 512)
        shape = prediction["grid_shape"]
        if type(shape) is not list or len(shape) != 2 or any(type(n) is not int for n in shape):
            raise ValueError("Prediction has invalid source grid shape")
        if shape != [height, width]:
            raise ValueError("Frame shape changed; handle the lifecycle/representation boundary")
        expected = _pixels(prediction["expected_pixels"], height, width, chars)
        actual = [[r, c, observed[r][c]] for r, c, _ in expected]
        differences = [{"row": r, "col": c, "expected": color, "observed": observed[r][c]}
                       for r, c, color in expected if color != observed[r][c]]
        expected_hash, observed_hash = stable_hash(expected), stable_hash(actual)
        # Keep event fields bounded even when the declared projection covers a
        # full frame.  Full hashes preserve differences outside the preview.
        expected_event = {"pixels": expected[:64], "pixel_count": len(expected),
                          "sha256": expected_hash, "truncated": len(expected) > 64}
        observed_event = {"pixels": actual[:64], "pixel_count": len(actual),
                          "sha256": observed_hash, "truncated": len(actual) > 64}
        return {"status": "mismatch" if differences else "match", "scope": scope,
                "expected": expected_event, "observed": observed_event,
                "checked_pixels": len(expected), "different_pixels": len(differences),
                "differences": differences[:16], "prediction_sha256": stable_hash(prediction),
                "observed_projection_sha256": observed_hash,
                "claim": "Agreement/disagreement of declared pixels only"}
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        return {"status": "unknown", "errors": [str(exc)[:300]], "differences": [], "checked_pixels": 0,
                "claim": "No comparable pixel evidence; stop the checked plan suffix"}
