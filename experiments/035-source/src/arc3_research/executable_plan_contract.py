"""034 pure host contracts for a model-produced executable plan.

This module neither imports the game runtime nor executes candidate code or
actions.  Its checks establish syntax, current-pixel evidence and the declared
prediction projection, never a correct goal, complete physics or safe action.
The native adapter owns sandboxing, deadlines, lifecycle boundaries and the
actual program replacement.  A reference in ``replaces`` proves only that a
named binding was supplied by that adapter, not that the new code uses it.

Example model returns::

    plan_program(frame) -> {
        "status": "ready",
        "goal": {"target": "move the visible piece onto the marked cell"},
        "actions": [{"action": "RIGHT"}],
        "evidence_pixels": [[4, 6, "A"]],
        "replaces": ["build_target"], "reason": "Re-read the piece footprint"}
    predict(frame, action) -> {
        "mode": "change", "action": {"action": "RIGHT"},
        "object_pixels": [[4, 6, "A"]],
        "target_pixels": [[4, 7, "."]],
        "precondition": "The visible target pixel is free",
        "scope": "piece pixels in screen row/column coordinates",
        "expected_pixels": [[4, 6, "."], [4, 7, "A"]]}

``completed`` and ``abstain`` plans have no actions.  The former reports only
a model-declared local goal, never a completed ARC level.  A predictor may
instead return ``{"mode": "unknown", "reason": "..."}`` to stop this contract
without pretending that unrelated background pixels are useful evidence.

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
MAX_ACTIONS = 3
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


class DefinitionContractError(ValueError):
    """Bounded source diagnostics which can be copied into one repair request.

    ``errors`` retains at most 16 distinct static findings in deterministic
    order. ``total_errors`` and ``truncated_count`` expose any omitted findings.
    These are contract diagnostics, never evidence that candidate code ran.
    """

    def __init__(self, errors: list[dict[str, Any]], *, total_errors: int | None = None,
                 has_side_effect_rejection: bool = False):
        self.errors = [dict(item) for item in errors[:16]]
        self.total_errors = max(len(errors), total_errors or 0)
        self.truncated_count = max(0, self.total_errors - len(self.errors))
        self.has_side_effect_rejection = has_side_effect_rejection
        summary = "; ".join(item["message"] for item in self.errors)
        if self.truncated_count:
            summary += "; " + str(self.truncated_count) + " further contract errors omitted"
        super().__init__(summary)

    def to_dict(self) -> dict[str, Any]:
        return {"errors": [dict(item) for item in self.errors],
                "total_errors": self.total_errors,
                "truncated_count": self.truncated_count,
                "has_side_effect_rejection": self.has_side_effect_rejection}


def _definition_error(code: str, message: str, *, line: int | None = None,
                      column: int | None = None) -> DefinitionContractError:
    item: dict[str, Any] = {"code": code, "line": line, "message": message[:500]}
    if column is not None:
        item["column"] = column
    return DefinitionContractError([item])


def _literal_default(node: ast.AST) -> bool:
    """Recognize only bounded immutable literals without evaluating the AST."""
    nodes = 0

    def check(item: ast.AST, depth: int) -> bool:
        nonlocal nodes
        nodes += 1
        if nodes > 128 or depth > 8:
            return False
        if isinstance(item, ast.Constant):
            kind = type(item.value)
            return (item.value is None or kind in (bool, int, str, bytes)
                    or (kind is float and math.isfinite(item.value)))
        if isinstance(item, ast.Tuple):
            return all(check(child, depth + 1) for child in item.elts)
        if isinstance(item, ast.UnaryOp) and isinstance(item.op, (ast.UAdd, ast.USub)):
            value = item.operand
            return (isinstance(value, ast.Constant)
                    and type(value.value) in (int, float)
                    and check(value, depth + 1))
        return False

    return check(node, 0)


def extract_definitions(message: dict[str, Any], *,
                        expected_tool_name: str = "python",
                        max_nonempty_lines: int | None = None,
                        max_code_bytes: int = MAX_CODE_BYTES,
                        allow_literal_defaults: bool = False) -> dict[str, Any]:
    """Extract a single definitions/imports delivery call, without executing it.

    Required entry signatures are exactly plan_program(frame) and
    predict(frame, action), with no defaults. By default all function defaults
    are rejected, preserving the legacy contract. An adapter may explicitly
    allow bounded immutable literal helper defaults: primitive constants,
    signed numbers and recursively nested tuples. Computed and mutable defaults,
    decorators, annotations and type parameters remain rejected. Source bytes
    and AST nodes stay bounded; a line cap is optional and formatting dependent.
    Static source violations are aggregated into ``DefinitionContractError``.
    The real sandbox must still enforce capabilities and deadlines; these
    static checks are not a security boundary or a proof of plan quality.
    """
    if (type(expected_tool_name) is not str or not expected_tool_name.isidentifier()
            or len(expected_tool_name) > 64):
        raise ValueError("Expected tool name must be a bounded identifier")
    if type(max_code_bytes) is not int or not 1 <= max_code_bytes <= MAX_CODE_BYTES:
        raise ValueError("Code byte limit must be an integer from 1 to " + str(MAX_CODE_BYTES))
    if type(allow_literal_defaults) is not bool:
        raise ValueError("allow_literal_defaults must be a Boolean")
    if (max_nonempty_lines is not None and
            (type(max_nonempty_lines) is not int
             or not 1 <= max_nonempty_lines <= MAX_CODE_BYTES)):
        raise ValueError("Nonempty line limit must be None or an integer from 1 to "
                         + str(MAX_CODE_BYTES))
    if type(message) is not dict or type(message.get("tool_calls")) is not list:
        raise _definition_error("delivery_message", "Expected an assistant message with one "
                                + expected_tool_name + " tool call")
    calls = message["tool_calls"]
    if len(calls) != 1 or type(calls[0]) is not dict:
        raise _definition_error("delivery_call_count", "Return exactly one "
                                + expected_tool_name + " tool call")
    function = calls[0].get("function")
    if type(function) is not dict or function.get("name") != expected_tool_name:
        raise _definition_error("delivery_tool", "Expected the " + expected_tool_name + " tool")
    arguments = function.get("arguments")
    try:
        arguments = _json_object(arguments) if type(arguments) is str else json_copy(arguments)
    except ValueError as exc:
        raise _definition_error("delivery_arguments", str(exc)) from exc
    if type(arguments) is not dict or set(arguments) != {"code"}:
        raise _definition_error("delivery_arguments", "Python arguments must contain only code")
    code = arguments["code"]
    if type(code) is not str or not code.strip():
        raise _definition_error("source_empty", "Provide nonempty Python source")
    try:
        code_bytes = len(code.encode("utf-8"))
    except UnicodeError as exc:
        raise _definition_error("source_encoding", "Invalid UTF-8 Python source") from exc
    nonempty_lines = sum(bool(line.strip()) for line in code.splitlines())
    if code_bytes > max_code_bytes:
        raise _definition_error("source_byte_limit", "Python source has " + str(code_bytes)
                                + " UTF-8 bytes; maximum is " + str(max_code_bytes))
    if max_nonempty_lines is not None and nonempty_lines > max_nonempty_lines:
        raise _definition_error("source_line_limit", "Python source has " + str(nonempty_lines)
                                + " nonempty lines; maximum is " + str(max_nonempty_lines))
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise _definition_error("source_syntax", "Invalid Python source: " + exc.msg,
                                line=exc.lineno, column=exc.offset) from exc
    except (RecursionError, ValueError, UnicodeError) as exc:
        raise _definition_error("source_parse", "Invalid Python source: "
                                + type(exc).__name__) from exc
    if sum(1 for _ in ast.walk(tree)) > 12000:
        raise _definition_error("source_ast_limit", "Python AST exceeds its node limit")

    errors: list[dict[str, Any]] = []
    total_errors = 0
    seen_errors: set[tuple[str, int | None, str]] = set()
    has_side_effect_rejection = False

    def add(code: str, message: str, node: ast.AST | None = None,
            *, line: int | None = None) -> None:
        nonlocal total_errors, has_side_effect_rejection
        if code in {"forbidden_call", "global_binding", "import_module"}:
            has_side_effect_rejection = True
        if line is None:
            line = getattr(node, "lineno", None)
        key = (code, line, message)
        if key in seen_errors:
            return
        seen_errors.add(key)
        total_errors += 1
        if len(errors) < 16:
            errors.append({"code": code, "line": line, "message": message[:500]})

    functions: dict[str, ast.FunctionDef] = {}
    seen: set[str] = set()
    function_count = 0
    for index, node in enumerate(tree.body):
        if (index == 0 and isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant) and type(node.value.value) is str):
            continue
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node
            function_count += 1
            names = [node.name]
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.asname or a.name.split(".")[0] for a in node.names]
        else:
            add("module_statement", "Return only function definitions and allowed imports", node)
            names = []
        for name in names:
            if name in seen or name.startswith("__"):
                add("top_level_binding", "Duplicate or reserved top-level binding: " + name, node)
            seen.add(name)
    if function_count > 32:
        add("function_limit", "Too many function definitions")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
            if ((isinstance(node, ast.ImportFrom) and node.level)
                    or any(m not in _IMPORTS for m in modules)):
                add("import_module", "Import is outside the pure standard-library contract", node)
            if any(a.name == "*" for a in node.names):
                add("import_star", "Star imports are not supported", node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            all_args = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            if args.vararg:
                all_args.append(args.vararg)
            if args.kwarg:
                all_args.append(args.kwarg)
            if node.decorator_list:
                add("function_decorator", "Definitions cannot have decorators", node)
            if node.returns is not None or any(a.annotation is not None for a in all_args):
                add("function_annotation", "Definitions cannot have annotations", node)
            if getattr(node, "type_params", []):
                add("function_type_parameters", "Definitions cannot have type parameters", node)
            defaults = [*args.defaults, *(x for x in args.kw_defaults if x is not None)]
            is_entry = node in tree.body and node.name in ("plan_program", "predict")
            if defaults and not is_entry:
                if not allow_literal_defaults:
                    add("function_default", "Definitions cannot have defaults", node)
                else:
                    for default in defaults:
                        if not _literal_default(default):
                            add("function_default", "Helper defaults must be bounded immutable literals",
                                default)
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            add("global_binding", "Functions must not mutate global bindings", node)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _FORBIDDEN_CALLS):
            add("forbidden_call", "Function contains an action or executable-I/O call", node)
    for name, expected in (("plan_program", ["frame"]), ("predict", ["frame", "action"])):
        node = functions.get(name)
        if node is None:
            add("missing_entry", "Missing " + name)
            continue
        args = node.args
        if ([a.arg for a in [*args.posonlyargs, *args.args]] != expected
                or args.kwonlyargs or args.vararg or args.kwarg or args.defaults
                or any(x is not None for x in args.kw_defaults)):
            add("entry_signature", "Required signature is " + name
                + "(" + ", ".join(expected) + ") with no defaults", node)
    try:
        compile(tree, "<executable_plan_contract>", "exec")
    except SyntaxError as exc:
        add("source_compile", "Candidate definitions do not compile: " + exc.msg,
            line=exc.lineno)
    except (ValueError, RecursionError) as exc:
        add("source_compile", "Candidate definitions do not compile: " + type(exc).__name__)
    if errors:
        raise DefinitionContractError(errors, total_errors=total_errors,
                                      has_side_effect_rejection=has_side_effect_rejection)
    return {"code": code, "definitions": sorted(functions),
            "code_bytes": code_bytes, "nonempty_lines": nonempty_lines,
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


def _action(value: Any, height: int, width: int, legal: set[str] | None = None) -> dict[str, Any]:
    """Normalize the existing model-facing action, not a new action dialect."""
    if type(value) is not dict or type(value.get("action")) is not str:
        raise ValueError("Action must contain its existing model API name")
    name = value["action"]
    if (not name or len(name) > 128 or name.upper() in _NO_AUTOMATIC_ACTIONS
            or (legal is not None and name not in legal)):
        raise ValueError("Action is unavailable or is an automatic RESET/UNDO")
    if name == "MOUSE":
        if (set(value) != {"action", "row", "col"}
                or type(value["row"]) is not int or type(value["col"]) is not int
                or not 0 <= value["row"] < height or not 0 <= value["col"] < width):
            raise ValueError("MOUSE requires exact in-frame integer row/col")
    elif set(value) != {"action"}:
        raise ValueError("Non-MOUSE action has unexpected fields")
    return dict(value)


def _validate_plan_diagnostics(value: Any, grid: Any, chars: Any, valid_actions: Any,
                               available_bindings: Any, *, status_aware: bool,
                               aggregate_errors: bool) -> dict[str, Any]:
    """Collect bounded schema/evidence findings without executing a candidate.

    A duplicate evidence coordinate is an error, not a reason to skip checking
    that record's bounds, color and observed value. No findings normalize or
    repair an invalid plan into an executable one.
    """
    errors: list[dict[str, Any]] = []
    total_errors = 0
    differences: list[dict[str, Any]] = []
    wrong_pixels = 0
    duplicate_coordinates: list[dict[str, Any]] = []
    total_duplicate_coordinates = 0

    def add(code: str, field: str, message: str, **details: Any) -> None:
        nonlocal total_errors
        total_errors += 1
        if len(errors) < (16 if aggregate_errors else 1):
            errors.append({"code": code, "field": field, "message": message[:500], **details})

    def diagnostics() -> dict[str, Any]:
        return {"errors": errors, "total_errors": total_errors,
                "truncated_count": max(0, total_errors - len(errors)),
                "status_aware": status_aware, "aggregate_errors": aggregate_errors,
                "duplicate_coordinates": duplicate_coordinates,
                "total_duplicate_coordinates": total_duplicate_coordinates,
                "wrong_pixels": wrong_pixels, "differences": differences}

    def rejected() -> dict[str, Any]:
        result = {"passed": False,
                  "status": "rejected_evidence" if wrong_pixels else "rejected",
                  "errors": [item["message"] for item in errors],
                  "plan_diagnostics": diagnostics()}
        if wrong_pixels:
            result.update(wrong_pixels=wrong_pixels, differences=differences)
        return result

    try:
        plan = json_copy(value)
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        add("plan_json", "$", str(exc))
        return rejected()
    if type(plan) is not dict:
        add("plan_schema", "$", "Plan requires exactly status, goal, actions, evidence_pixels, replaces and reason")
        return rejected()
    required = {"status", "goal", "actions", "evidence_pixels", "replaces", "reason"}
    if set(plan) != required:
        add("plan_schema", "$", "Plan requires exactly status, goal, actions, evidence_pixels, replaces and reason",
            missing_fields=sorted(required - set(plan)),
            unexpected_fields=[key[:128] for key in sorted(set(plan) - required)[:16]])
    status = plan.get("status")
    if type(status) is not str or status not in ("ready", "completed", "abstain"):
        add("plan_status", "status", "Plan status must be ready, completed or abstain")
    abstain = status_aware and status == "abstain"
    goal = plan.get("goal")
    if type(goal) not in (str, dict, list) or not goal or (type(goal) is str and not goal.strip()):
        add("plan_goal", "goal", "Goal must describe a nonempty hypothesis, not a Boolean or empty result")
    else:
        try:
            json_copy(goal, max_bytes=8192)
        except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
            add("plan_goal_limit", "goal", str(exc))
        if type(goal) is str:
            goal = goal.strip()
            if goal.casefold() in {"ok", "true", "passed", "success", "done"}:
                add("plan_goal_context", "goal", "Goal needs task context, not a success assertion")
        if (type(goal) is dict and all(k.casefold() in {"ok", "true", "passed", "success", "done"}
                                      and type(v) is bool for k, v in goal.items())):
            add("plan_goal_context", "goal", "Goal needs task context, not only success flags")
        plan["goal"] = goal
    try:
        plan["reason"] = _text(plan.get("reason"), "reason", 2000)
    except ValueError as exc:
        add("plan_reason", "reason", str(exc))

    observed = None
    height = width = 0
    try:
        observed, height, width = _frame(grid, chars)
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        add("current_frame", "$frame", str(exc))
    legal = None
    if (not isinstance(valid_actions, (list, tuple, set, frozenset))
            or any(type(action) is not str for action in valid_actions)):
        add("valid_actions", "$valid_actions", "Current public valid_actions are unavailable")
    else:
        legal = set(valid_actions)
    actions = plan.get("actions")
    if type(actions) is not list:
        add("plan_actions", "actions", "Plan actions must be a list")
    else:
        if status == "ready" and not 1 <= len(actions) <= MAX_ACTIONS:
            add("plan_action_count", "actions", "Ready plan must contain 1..3 actions")
        elif status in ("completed", "abstain") and actions:
            add("plan_action_count", "actions", "Completed or abstain plan must contain no actions")
        if observed is not None and legal is not None:
            normalized_actions = []
            for index, action in enumerate(actions):
                try:
                    normalized_actions.append(_action(action, height, width, legal))
                except (ValueError, TypeError) as exc:
                    add("plan_action", "actions[" + str(index) + "]", str(exc))
            if len(normalized_actions) == len(actions):
                plan["actions"] = normalized_actions

    replaces = plan.get("replaces")
    replaces_valid = (type(replaces) is list and len(replaces) <= 32
                      and all(type(name) is str and name.isidentifier() and len(name) <= 128
                              for name in replaces))
    if not replaces_valid or (not abstain and not replaces):
        add("plan_replaces", "replaces", "replaces must name current program bindings"
            + (" or be empty for abstain" if status_aware else ""))
    else:
        if len(set(replaces)) != len(replaces):
            add("plan_replaces_duplicate", "replaces", "Duplicate replaced binding")
        if replaces or not abstain:
            available_valid = (isinstance(available_bindings, (dict, list, tuple, set, frozenset))
                               and bool(available_bindings)
                               and all(type(name) is str for name in available_bindings))
            if not available_valid:
                add("available_bindings", "$available_bindings", "A current code/retained-function binding is required")
            else:
                available = set(available_bindings)
                unknown = [name for name in replaces if name not in available]
                if unknown:
                    add("plan_replaces_unknown", "replaces", "Unknown replaced binding", unknown_bindings=unknown[:16])
        plan["replaces"] = sorted(replaces)

    evidence = plan.get("evidence_pixels")
    normalized_evidence = []
    if type(evidence) is not list:
        add("evidence_type", "evidence_pixels", "Pixel projection must be a bounded nonempty list")
    else:
        maximum = min(MAX_PIXELS, height * width) if observed is not None else MAX_PIXELS
        if len(evidence) > maximum or (not evidence and not abstain):
            add("evidence_count", "evidence_pixels", "Pixel projection must be a bounded "
                + ("list (empty only for abstain)" if status_aware else "nonempty list"),
                pixel_count=len(evidence), maximum=maximum)
        seen: dict[tuple[int, int], int] = {}
        for index, item in enumerate(evidence):
            field = "evidence_pixels[" + str(index) + "]"
            if type(item) is not list or len(item) != 3:
                add("evidence_pixel_shape", field, "Each pixel must be [row, col, color_character]")
                continue
            row, col, color = item
            coordinate_valid = type(row) is int and type(col) is int
            if coordinate_valid:
                coordinate = (row, col)
                if coordinate in seen:
                    total_duplicate_coordinates += 1
                    detail = {"row": row, "col": col, "first_index": seen[coordinate], "index": index}
                    if len(duplicate_coordinates) < 16:
                        duplicate_coordinates.append(detail)
                    add("evidence_duplicate_coordinate", field, "Duplicate pixel coordinate", **detail)
                else:
                    seen[coordinate] = index
            if not coordinate_valid or (observed is not None and not (0 <= row < height and 0 <= col < width)):
                add("evidence_coordinate", field, "Pixel coordinate is outside the current frame")
                coordinate_valid = False
            color_valid = (type(color) is str and len(color) == 1
                           and (observed is None or color in chars))
            if not color_valid:
                add("evidence_color", field, "Pixel has an invalid color character")
            if coordinate_valid and color_valid and observed is not None:
                normalized_evidence.append([row, col, color])
                if color != observed[row][col]:
                    wrong_pixels += 1
                    if len(differences) < 16:
                        differences.append({"row": row, "col": col, "claimed": color,
                                            "observed": observed[row][col], "index": index})
        if wrong_pixels:
            add("evidence_wrong_pixels", "evidence_pixels", "Evidence differs from current pixels",
                wrong_pixels=wrong_pixels, differences=differences)
    if total_errors:
        return rejected()
    plan["evidence_pixels"] = sorted(normalized_evidence, key=lambda pixel: (pixel[0], pixel[1]))
    try:
        plan_hash = stable_hash(plan)
        input_grid_hash = stable_hash([list(row) for row in grid])
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        add("plan_hash_resource", "$", str(exc))
        return rejected()
    return {"passed": True, "status": "validated_current_evidence", "errors": [], "plan": plan,
            "plan_diagnostics": diagnostics(), "plan_sha256": plan_hash,
            "input_grid_sha256": input_grid_hash,
            "coverage": {"evidence_pixels": len(normalized_evidence), "frame_pixels": height * width,
                         "fraction": len(normalized_evidence) / (height * width)},
            "claim": "Executable output schema and declared current pixels only; local goal, dynamics and environment completion unverified"}


def validate_plan(value: Any, grid: Any, chars: Any, valid_actions: Any,
                  available_bindings: Any, *, status_aware: bool = False,
                  aggregate_errors: bool = False) -> dict[str, Any]:
    """Validate schema, a current-program reference and exact observed pixels.

    ``goal`` is a bounded nonempty string/object/list, an explicit hypothesis.
    Only ``ready`` may contain actions; ``completed`` and ``abstain`` end this
    local contract and do not certify an environment outcome.  The adapter
    owns the cumulative action cap across repeated current-frame recomputations.
    Explicit ``status_aware`` allows an honest abstain to provide empty evidence
    and replacements; nonempty entries remain validated. It does not relax
    ready/completed plans. ``aggregate_errors`` reports bounded independent
    findings from one returned plan, including duplicate and wrong-color pixels.
    Both options default off to preserve the original fail-first contract.
    The adapter must execute plan_program on this frame to obtain ``value``;
    this function cannot establish that provenance from a bare JSON result.
    """
    if type(status_aware) is not bool or type(aggregate_errors) is not bool:
        return _failure(ValueError("Plan validation options must be Booleans"))
    if status_aware or aggregate_errors:
        return _validate_plan_diagnostics(value, grid, chars, valid_actions, available_bindings,
                                          status_aware=status_aware,
                                          aggregate_errors=aggregate_errors)
    try:
        plan = json_copy(value)
        observed, height, width = _frame(grid, chars)
        required = {"status", "goal", "actions", "evidence_pixels", "replaces", "reason"}
        if type(plan) is not dict or set(plan) != required:
            raise ValueError("Plan requires exactly status, goal, actions, evidence_pixels, replaces and reason")
        if plan["status"] not in ("ready", "completed", "abstain"):
            raise ValueError("Plan status must be ready, completed or abstain")
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
        if type(actions) is not list:
            raise ValueError("Plan actions must be a list")
        if plan["status"] == "ready":
            if not 1 <= len(actions) <= MAX_ACTIONS:
                raise ValueError("Ready plan must contain 1..3 actions")
        elif actions:
            raise ValueError("Completed or abstain plan must contain no actions")
        plan["actions"] = [_action(action, height, width, legal) for action in actions]
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
                "claim": "Executable output schema and declared current pixels only; local goal, dynamics and environment completion unverified"}
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        return _failure(exc)


def validate_prediction(value: Any, grid: Any, chars: Any,
                        expected_action: Any = None) -> dict[str, Any]:
    """Ground and freeze a declared action effect before a real action.

    Both the object/source and target/effect pixel sets must match the current
    observation.  The frozen projection covers their union exactly, and the
    returned action must equal the host's pending action.  These checks do not
    establish that the named pixels are semantically relevant to that action.
    They prevent undeclared projections, not a dishonest or mistaken model.

    A grounded no-op is legitimate.  Explicit unknown ends this contract and
    is never represented as an accepted empty/background prediction.
    """
    try:
        value = json_copy(value)
        observed, height, width = _frame(grid, chars)
        if type(value) is not dict:
            raise ValueError("Prediction must be an object")
        if value.get("mode") == "unknown":
            if set(value) != {"mode", "reason"}:
                raise ValueError("Unknown prediction requires exactly mode and reason")
            reason = _text(value["reason"], "unknown reason", 1000)
            return {"passed": False, "status": "unknown", "errors": [reason],
                    "declared_unknown": True,
                    "claim": "No action-effect prediction; return to the ordinary solver"}
        required = {"mode", "action", "object_pixels", "target_pixels", "expected_pixels",
                    "precondition", "scope"}
        if set(value) != required or value["mode"] not in ("change", "noop"):
            raise ValueError("Prediction requires mode change/noop, action, object_pixels, target_pixels, expected_pixels, precondition and scope")
        pending = _action(json_copy(expected_action), height, width)
        action = _action(value["action"], height, width)
        if action != pending:
            raise ValueError("Prediction action differs from the host pending action")
        scope = _text(value["scope"], "scope", 512)
        precondition = _text(value["precondition"], "precondition", 1000)
        object_pixels = _pixels(value["object_pixels"], height, width, chars)
        target_pixels = _pixels(value["target_pixels"], height, width, chars)
        current_pixels = {(r, c): color for r, c, color in object_pixels + target_pixels}
        differences = [{"row": r, "col": c, "claimed": color, "observed": observed[r][c]}
                       for r, c, color in object_pixels + target_pixels if color != observed[r][c]]
        if differences:
            return {"passed": False, "status": "unknown", "errors": ["Prediction object/target evidence differs from current pixels"],
                    "wrong_pixels": len(differences), "differences": differences[:16]}
        pixels = _pixels(value["expected_pixels"], height, width, chars)
        if {(r, c) for r, c, _ in pixels} != set(current_pixels):
            raise ValueError("Expected pixels must cover exactly the declared object and target coordinates")
        changed = sum(color != observed[r][c] for r, c, color in pixels)
        if value["mode"] == "change" and not changed:
            raise ValueError("Change prediction requires at least one declared changed pixel")
        if value["mode"] == "noop" and changed:
            raise ValueError("Noop prediction must keep all declared pixels unchanged")
        prediction = {"mode": value["mode"], "action": action, "object_pixels": object_pixels,
                      "target_pixels": target_pixels, "expected_pixels": pixels,
                      "precondition": precondition, "scope": scope, "grid_shape": [height, width]}
        return {"passed": True, "status": "declared_action_prediction", "errors": [], "prediction": prediction,
                "prediction_sha256": stable_hash(prediction),
                "input_grid_sha256": stable_hash([list(r) for r in grid]),
                "coverage": {"selected_pixels": len(pixels), "frame_pixels": height * width,
                             "fraction": len(pixels) / (height * width), "predicted_changed_pixels": changed,
                             "predicted_unchanged_pixels": len(pixels) - changed,
                             "unchanged_only": changed == 0, "object_pixels": len(object_pixels),
                             "target_pixels": len(target_pixels)},
                "action_bound": True, "semantic_relevance_verified": False,
                "claim": "Current object/target pixels and pending action grounded; semantic relevance, precondition and dynamics unverified"}
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
        if (type(prediction) is not dict or set(prediction) != {
                "mode", "action", "object_pixels", "target_pixels", "expected_pixels",
                "precondition", "scope", "grid_shape"}):
            raise ValueError("Expected a frozen validated pixel prediction")
        if prediction["mode"] not in ("change", "noop"):
            raise ValueError("Frozen prediction has invalid mode")
        scope = _text(prediction["scope"], "scope", 512)
        _text(prediction["precondition"], "precondition", 1000)
        shape = prediction["grid_shape"]
        if type(shape) is not list or len(shape) != 2 or any(type(n) is not int for n in shape):
            raise ValueError("Prediction has invalid source grid shape")
        if shape != [height, width]:
            raise ValueError("Frame shape changed; handle the lifecycle/representation boundary")
        action = _action(prediction["action"], height, width)
        source = _pixels(prediction["object_pixels"], height, width, chars)
        target = _pixels(prediction["target_pixels"], height, width, chars)
        expected = _pixels(prediction["expected_pixels"], height, width, chars)
        if {(r, c) for r, c, _ in expected} != {(r, c) for r, c, _ in source + target}:
            raise ValueError("Frozen projection differs from declared object/target coordinates")
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
                "mode": prediction["mode"], "action": action,
                "expected": expected_event, "observed": observed_event,
                "checked_pixels": len(expected), "different_pixels": len(differences),
                "differences": differences[:16], "prediction_sha256": stable_hash(prediction),
                "observed_projection_sha256": observed_hash,
                "semantic_relevance_verified": False,
                "claim": "Agreement/disagreement of frozen declared object/target pixels only; semantic relevance and goal unverified"}
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        return {"status": "unknown", "errors": [str(exc)[:300]], "differences": [], "checked_pixels": 0,
                "claim": "No comparable pixel evidence; stop the checked plan suffix"}
