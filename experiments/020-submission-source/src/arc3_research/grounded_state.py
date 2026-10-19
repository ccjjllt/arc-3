"""020: exact public ASCII regions inside the existing Python tool process.

The region object is a live-frame view, not a cache or a physical-world model.
Its immutable ordinary values may be passed directly to user-written solvers.
No game state, action handler, tool schema, or model transport is patched.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import os

from arc3_research import observation_representation as _observation
from arc3_research.observation_representation import (
    ARC_SYMBOLS as _gs_symbols, RegionReader as _gs_reader,
    _reference as _gs_reference,
)


MAX_REGION_CELLS = 1024
PREFIX_ENV = "ARC3_SYSTEM_PROMPT_PREFIX"
GROUND_STATE_PREFIX = (
    "For exact geometry or patterns, the existing Python current_frame additionally "
    "provides region((top,left,bottom,right), foreground='B') and "
    "region_from_node(node, foreground='B', inset=0), passing a node selected from "
    "current_frame.segmentation['nodes']. Bounds are zero-based, "
    "inclusive, at most 1024 cells. Start from segmentation and select only the "
    "needed region. Use region=current_frame.region(...); plan=solve(region.cells) "
    "in the same Python call: pass observed values directly, without retyping a "
    "coordinate table. region.raw_rows are exact strings; cells are character rows; "
    "mask is the selected-color boolean mask; positions() gives selected pixels "
    "in global (row,col) coordinates; origin is (top,left); source records frame "
    "and bounds. Omit foreground when only characters are needed. Inspect a "
    "compact result, not the whole board. Region getters reject old frames after "
    "action(); ordinary values already extracted remain valid historical data, "
    "so retain source when reusing them. Masks preserve holes and disconnected "
    "pixels; collision footprints and crop completeness still require evidence."
)


class GroundedStateError(ValueError):
    """A requested region cannot be obtained from the live public frame."""


class GroundedRegion:
    """Bounded observation with freshness checked on each public accessor.

    Returned tuples/dicts are ordinary detached values: the caller may retain
    them as history. This class does not taint or invalidate an existing plan.
    """

    def __init__(self, frame, get_current, payload, *, foreground_requested):
        self._frame = frame
        self._get_current = get_current
        self._payload = payload
        self._foreground_requested = foreground_requested

    def _checked(self):
        if self._get_current() is not self._frame:
            raise GroundedStateError("stale_frame: re-read current_frame.region(...)")
        reference, _ = _gs_reference(self._frame)
        if reference != self._payload["frame"]:
            raise GroundedStateError("frame_changed: re-read current_frame.region(...)")
        return self._payload

    @property
    def source(self):
        data = self._checked()
        reference = dict(data["frame"])
        reference["shape"] = tuple(reference["shape"])
        source = {"kind": "public_current_frame_ascii", "frame": reference,
                  "bbox": tuple(data["bbox"]), "bbox_order": data["bbox_order"],
                  "foreground": (tuple(data["foreground"])
                                 if self._foreground_requested else None)}
        if "selection" in data:
            source["selection"] = dict(data["selection"])
            source["selection"]["node_bbox"] = tuple(source["selection"]["node_bbox"])
        return source

    @property
    def raw_rows(self):
        return tuple(self._checked()["raw_rows"])

    @property
    def cells(self):
        return tuple(tuple(row) for row in self._checked()["raw_rows"])

    @property
    def mask(self):
        data = self._checked()
        if not self._foreground_requested:
            raise GroundedStateError("mask_requires_foreground: specify observed color symbols")
        return tuple(tuple(char == "1" for char in row) for row in data["mask_rows"])

    @property
    def origin(self):
        return tuple(self._checked()["bbox"][:2])

    @property
    def bbox(self):
        return tuple(self._checked()["bbox"])

    @property
    def shape(self):
        t, l, b, r = self._checked()["bbox"]
        return b - t + 1, r - l + 1

    def positions(self):
        """Selected observed color pixels in global (row, col), row-major."""
        mask = self.mask
        top, left = self.origin
        return tuple((top + row, left + col)
                     for row, values in enumerate(mask)
                     for col, selected in enumerate(values) if selected)

    def __repr__(self):
        data = self._checked()
        return ("GroundedRegion(bbox=" + repr(tuple(data["bbox"]))
                + ", frame_step=" + str(data["frame"]["step"])
                + ", foreground=" + repr(self.source["foreground"]) + ")")


def read_region(frame, get_current, bbox=None, *, foreground=None,
                node=None, inset=0):
    """Read public characters now; no transform, inferred fill or silent fallback.

    Outside the sandbox the caller supplies a live getter. Inside it the getter
    closes over the runtime's current_frame binding and cannot become a cache.
    """
    if not callable(get_current) or get_current() is not frame:
        raise GroundedStateError("stale_frame: use the live current_frame")
    if frame is None:
        raise GroundedStateError("current_frame_unavailable")
    foreground_requested = foreground is not None
    reader = _gs_reader(get_current, max_cells=MAX_REGION_CELLS)
    selected = foreground if foreground_requested else _gs_symbols
    reference = reader.reference()
    if node is None:
        if inset != 0:
            raise GroundedStateError("inset_requires_node_selection")
        payload = reader.read(bbox, foreground=selected, expect_frame=reference)
    else:
        if bbox is not None:
            raise GroundedStateError("choose_bbox_or_node_not_both")
        # A bare ID may be reused after an action. Require the actual current
        # segmentation entry, not an old/detached dict with the same numeric ID.
        if not any(candidate is node for candidate in frame.segmentation["nodes"]):
            raise GroundedStateError("stale_or_unknown_node: select from current_frame.segmentation['nodes']")
        payload = reader.from_node(node.get("id"), foreground=selected,
                                   expect_frame=reference, inset=inset)
    if payload["status"] != "observed":
        raise GroundedStateError("region_unavailable: " + ",".join(payload["diagnostics"]))
    return GroundedRegion(frame, get_current, payload,
                          foreground_requested=foreground_requested)


_FRAME_ANCHOR = "class FrameView:\n"
_REFRESH_ANCHOR = '        runtime_globals["last_action_call_result"] = action_result\n'
_FRAME_METHODS = '''class FrameView:
    def region(self, bbox, *, foreground=None):
        return read_region(self, self._grounded_current, bbox, foreground=foreground)

    def region_from_node(self, node, *, foreground=None, inset=0):
        return read_region(self, self._grounded_current, foreground=foreground,
                           node=node, inset=inset)

    def _grounded_current(self):
        raise GroundedStateError("not_live_current_frame: historical/animation frames have no live region getter")

'''


def build_grounded_bootstrap(bootstrap):
    """Embed the maintained 008 reader; the isolated child has no repo imports."""
    if (bootstrap.count(_FRAME_ANCHOR) != 1
            or bootstrap.count(_REFRESH_ANCHOR) != 1
            or "_grounded_current" in bootstrap):
        raise RuntimeError("Unsupported or already patched FrameView bootstrap")
    observation_source = inspect.getsource(_observation)
    helpers = "\n".join([
        "_gs_observation_scope = {}",
        "exec(" + repr(observation_source) + ", _gs_observation_scope)",
        "_gs_reader = _gs_observation_scope['RegionReader']",
        "_gs_reference = _gs_observation_scope['_reference']",
        "_gs_symbols = _gs_observation_scope['ARC_SYMBOLS']",
        "MAX_REGION_CELLS = " + repr(MAX_REGION_CELLS),
        inspect.getsource(GroundedStateError), inspect.getsource(GroundedRegion),
        inspect.getsource(read_region),
    ])
    modified = helpers + "\n" + bootstrap.replace(_FRAME_ANCHOR, _FRAME_METHODS)
    modified = modified.replace(
        _REFRESH_ANCHOR,
        _REFRESH_ANCHOR + '        if current_frame is not None:\n'
        '            current_frame._grounded_current = lambda: runtime_globals.get("current_frame")\n',
    )
    compile(modified, "<grounded_state_sandbox>", "exec")
    return modified


class GroundedStatePatch:
    def __init__(self, sandbox_module):
        self._module = sandbox_module
        self._before = sandbox_module._SANDBOX_BOOTSTRAP
        self._after = build_grounded_bootstrap(self._before)
        self._previous_prefix = os.environ.get(PREFIX_ENV)
        self.active = False

    def snapshot(self):
        return {"name": "grounded_state", "enabled": self.active,
                "mechanism": "live_FrameView_exact_ASCII_region_methods",
                "max_region_cells": MAX_REGION_CELLS,
                "sandbox_bootstrap_before_sha256": hashlib.sha256(self._before.encode()).hexdigest(),
                "sandbox_bootstrap_after_sha256": hashlib.sha256(self._after.encode()).hexdigest(),
                "observation_representation_sha256": hashlib.sha256(
                    inspect.getsource(_observation).encode()).hexdigest(),
                "prefix_sha256": hashlib.sha256(GROUND_STATE_PREFIX.encode()).hexdigest(),
                "adds_tools": False, "adds_framework_model_calls": False,
                "adds_framework_game_actions": False, "adds_cross_call_memory": False,
                "natural_requests_tokens_and_actions_may_change": True,
                "runtime_adoption_counts": "not collected; inspect request code and tool results",
                "freshness": "live frame object and ASCII reference on read/access; detached ordinary values remain historical data"}

    def uninstall(self):
        if not self.active:
            return
        if self._module._SANDBOX_BOOTSTRAP != self._after:
            raise RuntimeError("Grounded-state bootstrap changed while installed")
        if os.environ.get(PREFIX_ENV) != GROUND_STATE_PREFIX:
            raise RuntimeError("Grounded-state prefix changed while installed")
        self._module._SANDBOX_BOOTSTRAP = self._before
        if self._previous_prefix is None:
            os.environ.pop(PREFIX_ENV, None)
        else:
            os.environ[PREFIX_ENV] = self._previous_prefix
        delattr(self._module, "_research_grounded_state_patch")
        self.active = False


def install_grounded_state(sandbox_module=None):
    """Install in the candidate CPU process before constructing ToolAgent."""
    if os.environ.get(PREFIX_ENV, "").strip():
        raise RuntimeError("Grounded state requires an empty system prefix; refusing replacement or duplicate")
    if sandbox_module is None:
        sandbox_module = importlib.import_module("inference.agent.python_tool_sandbox")
    if hasattr(sandbox_module, "_research_grounded_state_patch"):
        raise RuntimeError("Grounded state is already installed")
    patch = GroundedStatePatch(sandbox_module)
    sandbox_module._SANDBOX_BOOTSTRAP = patch._after
    os.environ[PREFIX_ENV] = GROUND_STATE_PREFIX
    sandbox_module._research_grounded_state_patch = patch
    patch.active = True
    return patch
