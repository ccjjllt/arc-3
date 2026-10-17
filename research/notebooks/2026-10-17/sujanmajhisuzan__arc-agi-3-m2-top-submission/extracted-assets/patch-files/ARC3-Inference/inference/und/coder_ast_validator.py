"""CONTRACT: AST Validator, Retention Hoister, and Model Hook Registry (Rules 04, 05).

Provides:
- validate_coder_ast: Audits model code against tables, forbidden imports, calls, dunders.
- hoist_retention_constants: Preprocessor hoisting constants and imports into function bodies.
- ModelHook / ModelHookRegistry: Safe compilation and execution of registered model hooks.
- check_model_convergence: Verifies model convergence over last K predictions.
"""
from __future__ import annotations

import ast
import builtins
import collections
from dataclasses import dataclass
import functools
import itertools
import math
from typing import Any, Sequence

from inference.und.config.thresholds import (
    CODER_CONTAINER_MAX_ELEMENTS,
    PREDICTED_TRANSITIONS_CONVERGENCE_K,
)

FORBIDDEN_TRANSITION_ATTRS = frozenset({
    "transition_table", "transition_log", "transitions", "history",
    "observed_transitions", "transition_history", "log_transitions",
})
FRAME_LIKE_NAMES = frozenset({
    "frame", "grid", "frame_hash", "grid_hash", "state_hash", "raw_grid", "before_grid", "after_grid",
})
FRAME_HASH_FUNCS = frozenset({"compute_grid_hash", "hash", "get_grid_hash"})
ALLOWED_IMPORT_MODULES = frozenset({"math", "itertools", "collections", "functools", "typing"})
FORBIDDEN_CALL_NAMES = frozenset({"eval", "exec", "open", "globals", "locals", "__import__", "compile", "getattr", "setattr", "delattr"})


def _is_constant_or_constant_collection(node: ast.AST) -> bool:
    """Check if an AST node is a compile-time constant or literal collection of constants."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_constant_or_constant_collection(elt) for elt in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            (k is not None and _is_constant_or_constant_collection(k)) and _is_constant_or_constant_collection(v)
            for k, v in zip(node.keys, node.values)
        )
    return False


def _is_frame_or_hash_reference(node: ast.AST) -> bool:
    """Check if node refers to a frame, grid, hash, or slice."""
    if isinstance(node, ast.Name) and node.id.lower() in FRAME_LIKE_NAMES:
        return True
    if isinstance(node, ast.Attribute) and node.attr.lower() in FRAME_LIKE_NAMES:
        return True
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id in FRAME_HASH_FUNCS:
            return True
        if isinstance(func, ast.Attribute) and func.attr in FRAME_HASH_FUNCS:
            return True
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
        return True
    return False


def _is_nested_frame_literal(node: ast.AST) -> bool:
    """Check if an AST node represents a 2D grid/frame literal."""
    if isinstance(node, (ast.List, ast.Tuple)) and len(node.elts) >= 2:
        return all(isinstance(elt, (ast.List, ast.Tuple)) and len(elt.elts) >= 2 for elt in node.elts)
    return False


def validate_coder_ast(source: str, max_container_elements: int | None = None) -> list[str]:
    """Statically audit code for table memorization, forbidden imports, calls, and dunders (Rule 04 В§3)."""
    diagnostics: list[str] = []
    max_elements = max_container_elements if max_container_elements is not None else CODER_CONTAINER_MAX_ELEMENTS
    try:
        tree = ast.parse(source, filename="<coder_dsl>")
    except SyntaxError as exc:
        return [f"SyntaxError: {exc.msg} at line {exc.lineno}, col {exc.offset}"]

    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and len(node.elts) > max_elements:
            diagnostics.append(f"Forbidden large container literal ({len(node.elts)} > {max_elements} elements): table memorization is banned (Rule 04 В§3)")
        elif isinstance(node, ast.Dict):
            if len(node.keys) > max_elements:
                diagnostics.append(f"Forbidden large dict literal ({len(node.keys)} > {max_elements} entries): table memorization is banned (Rule 04 В§3)")
            for k, v in zip(node.keys, node.values):
                if k is not None and (_is_nested_frame_literal(k) or _is_frame_or_hash_reference(k)):
                    if _is_nested_frame_literal(v) or _is_frame_or_hash_reference(v):
                        diagnostics.append("Forbidden frame->frame mapping in dict: memorizing transition graphs is banned (Rule 04 В§3)")
                        break
        elif isinstance(node, ast.Compare):
            l_frame, l_const = _is_frame_or_hash_reference(node.left), _is_constant_or_constant_collection(node.left)
            for comp in node.comparators:
                c_frame, c_const = _is_frame_or_hash_reference(comp), _is_constant_or_constant_collection(comp)
                if (l_frame and c_const) or (l_const and c_frame):
                    diagnostics.append("Forbidden comparison of frame, frame-hash, or slice to constant (Rule 04 В§3)")
                    break
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_TRANSITION_ATTRS:
                diagnostics.append(f"Forbidden access to transition log or history attribute {node.attr!r} (Rule 04 В§3)")
            elif node.attr.startswith("__") and node.attr.endswith("__"):
                diagnostics.append(f"Forbidden dunder attribute access {node.attr!r} (Rule 04 В§3)")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_TRANSITION_ATTRS:
                diagnostics.append(f"Forbidden access to transition log or history variable {node.id!r} (Rule 04 В§3)")
            elif node.id.startswith("__") and node.id.endswith("__"):
                diagnostics.append(f"Forbidden dunder name access {node.id!r} (Rule 04 В§3)")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORT_MODULES:
                    diagnostics.append(f"Forbidden import {alias.name!r}: only math, itertools, collections, functools, typing are permitted (Rule 04 В§3)")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORT_MODULES:
                diagnostics.append(f"Forbidden import from {node.module!r}: only math, itertools, collections, functools, typing are permitted (Rule 04 В§3)")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                diagnostics.append(f"Forbidden call to {node.func.id!r}: execution of dynamic or I/O primitives is banned (Rule 04 В§3)")
        elif isinstance(node, ast.Global):
            diagnostics.append("Forbidden global statement: model hooks must be pure (Rule 04 В§3)")
        elif isinstance(node, ast.Nonlocal):
            diagnostics.append("Forbidden nonlocal statement: model hooks must be pure (Rule 04 В§3)")

    return diagnostics


def hoist_retention_constants(
    source: str, available_globals: set[str] | None = None,
) -> tuple[str, list[str], list[str]]:
    """Hoist top-level constants and imports into function bodies for robust retention (Rule 05 В§6 item 1, Rule 07 В§5 item 4)."""
    try:
        tree = ast.parse(source)
    except Exception as exc:
        return source, [], [f"SyntaxError: {exc}"]

    top_constants: dict[str, ast.stmt] = {}
    top_imports: dict[str, ast.stmt] = {}
    funcs: list[ast.FunctionDef] = []
    top_func_names: set[str] = set()

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            funcs.append(node)
            top_func_names.add(node.name)
        elif isinstance(node, ast.Assign) and _is_constant_or_constant_collection(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    top_constants[target.id] = node
        elif isinstance(node, ast.AnnAssign) and node.value and _is_constant_or_constant_collection(node.value):
            if isinstance(node.target, ast.Name):
                top_constants[node.target.id] = node
        elif isinstance(node, ast.Import):
            for alias in node.names:
                top_imports[alias.asname or alias.name.split(".")[0]] = node
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                top_imports[alias.asname or alias.name] = node

    builtins_set = set(dir(builtins))
    avail = set(available_globals or set()) | builtins_set | top_func_names | {"wm", "api"}
    hoisted_symbols: list[str] = []
    unresolved_diags: list[str] = []

    for func in funcs:
        params = {a.arg for a in (*func.args.posonlyargs, *func.args.args, *func.args.kwonlyargs)}
        if func.args.vararg:
            params.add(func.args.vararg.arg)
        if func.args.kwarg:
            params.add(func.args.kwarg.arg)

        local_stores = set(params)
        loaded_names: list[str] = []
        for n in ast.walk(func):
            if isinstance(n, ast.Name):
                if isinstance(n.ctx, ast.Store):
                    local_stores.add(n.id)
                elif isinstance(n.ctx, ast.Load) and n.id not in loaded_names:
                    loaded_names.append(n.id)

        to_insert: list[ast.stmt] = []
        inserted_names: set[str] = set()
        for name in loaded_names:
            if name in local_stores or name in avail:
                continue
            if name in top_constants:
                if name not in inserted_names:
                    to_insert.append(top_constants[name]); inserted_names.add(name); hoisted_symbols.append(name)
            elif name in top_imports:
                if name not in inserted_names:
                    to_insert.append(top_imports[name]); inserted_names.add(name); hoisted_symbols.append(name)
            else:
                unresolved_diags.append(f"Function {func.name!r} references unresolved symbol {name!r}. Pass as argument or define it.")

        if to_insert:
            func.body = to_insert + func.body

    new_source = ast.unparse(tree) if (hoisted_symbols or funcs) else source
    return new_source, hoisted_symbols, unresolved_diags


@dataclass
class ModelHook:
    """Registered and compiled model hook function."""
    hook_name: str
    code: str
    callable: Any


class ModelHookRegistry:
    """Host-resident registry managing validated world model code hooks (Rule 04 В§3, Rule 05 В§4)."""

    def __init__(self) -> None:
        self.hooks: dict[str, ModelHook] = {}

    def register_hook(self, hook_name: str, code: str) -> dict[str, Any]:
        """Validate, hoist constants, compile, and register model hook."""
        diags = validate_coder_ast(code)
        if diags:
            return {"registered": False, "hook_name": hook_name, "error": "; ".join(diags), "diagnostics": diags}

        hoisted_code, _, unresolved = hoist_retention_constants(code)
        if unresolved:
            return {"registered": False, "hook_name": hook_name, "error": "; ".join(unresolved), "diagnostics": unresolved}

        safe_globals = {
            "math": math, "itertools": itertools, "collections": collections, "functools": functools,
            "__builtins__": {k: getattr(builtins, k) for k in dir(builtins) if k not in FORBIDDEN_CALL_NAMES},
        }
        local_ns: dict[str, Any] = {}
        try:
            compiled = compile(hoisted_code, f"<hook_{hook_name}>", "exec")
            exec(compiled, safe_globals, local_ns)
        except Exception as exc:
            return {"registered": False, "hook_name": hook_name, "error": f"Compilation error: {exc}"}

        target_fn = local_ns.get(hook_name)
        if target_fn is None:
            callables = [v for v in local_ns.values() if callable(v)]
            target_fn = callables[0] if callables else None
        if target_fn is None:
            return {"registered": False, "hook_name": hook_name, "error": f"No callable defined in code for hook {hook_name!r}"}

        self.hooks[hook_name] = ModelHook(hook_name=hook_name, code=hoisted_code, callable=target_fn)
        return {"registered": True, "hook_name": hook_name, "error": None}

    def get_hook(self, hook_name: str) -> ModelHook | None:
        return self.hooks.get(hook_name)

    def has_hook(self, hook_name: str) -> bool:
        return hook_name in self.hooks

    def call_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> Any:
        hook = self.hooks.get(hook_name)
        if hook is None:
            raise KeyError(f"Hook {hook_name!r} not registered")
        return hook.callable(*args, **kwargs)

    def list_hooks(self) -> list[str]:
        return list(self.hooks.keys())

    def clear(self) -> None:
        self.hooks.clear()


def check_model_convergence(prediction_history: Sequence[Any], k: int | None = None) -> bool:
    """Verify if a model has converged according to Rule 04 В§3 (last K predictions confirmed as FOLLOW)."""
    required_k = k if k is not None else PREDICTED_TRANSITIONS_CONVERGENCE_K
    if len(prediction_history) < required_k:
        return False
    for entry in prediction_history[-required_k:]:
        verdict: Any = entry
        if isinstance(entry, (tuple, list)) and len(entry) >= 3:
            verdict = entry[2]
        elif isinstance(entry, dict) and "verdict" in entry:
            verdict = entry["verdict"]
        elif hasattr(entry, "verdict"):
            verdict = getattr(entry, "verdict")
        v_str = str(getattr(verdict, "value", verdict))
        if v_str != "FOLLOW":
            return False
    return True
