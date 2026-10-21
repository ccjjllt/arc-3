"""031 exact component pixels on the existing segmentation node interface.

Only adds ``runs = [[row, first_col, last_col_inclusive], ...]`` to each
original node. Component ordering, colors, contours, hashes and adjacency are
unchanged. No model request, game rule or new model-callable tool is added.
"""
from __future__ import annotations

from functools import wraps
import inspect


FIELD_GUIDANCE = (
    " Segmentation nodes also include `runs`: exact occupied pixel row ranges "
    "`[row, col_start, col_end_inclusive]` in absolute frame coordinates. "
    "Use these to build exact pixel sets; `boundary` is an outer contour and "
    "does not fill enclosed holes."
)
SYSTEM_FIELD_ANCHOR = "`pixels` (cell count), `boundary`"
SYSTEM_FIELD_CONTRACT = (
    "`pixels` (cell count), `runs` (exact occupied pixel row ranges as "
    "`[row, col_start, col_end_inclusive]` in absolute frame coordinates; "
    "both column endpoints are inclusive), `boundary`"
)


def _attach_row_runs(layer, result):
    """Attach exact 4-connected memberships in the original reading order."""
    height = len(layer)
    width = len(layer[0]) if height else 0
    seen = set()
    component_id = 0
    nodes = result["nodes"]
    for sr in range(height):
        for sc in range(width):
            if (sr, sc) in seen:
                continue
            value = layer[sr][sc]
            seen.add((sr, sc))
            stack = [(sr, sc)]
            by_row = {}
            while stack:
                row, col = stack.pop()
                by_row.setdefault(row, []).append(col)
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = row + dr, col + dc
                    if (0 <= nr < height and 0 <= nc < width
                            and (nr, nc) not in seen and layer[nr][nc] == value):
                        seen.add((nr, nc))
                        stack.append((nr, nc))
            runs = []
            for row in sorted(by_row):
                cols = sorted(by_row[row])
                start = end = cols[0]
                for col in cols[1:]:
                    if col == end + 1:
                        end = col
                    else:
                        runs.append([row, start, end])
                        start = end = col
                runs.append([row, start, end])
            node = nodes[component_id]
            if node["id"] != component_id:
                raise ValueError("Segmentation component reading order changed")
            node["runs"] = runs
            component_id += 1
    if component_id != len(nodes):
        raise ValueError("Segmentation component count changed")
    return result


_INSTALLED = None


class SegmentationRunsPatch:
    def __init__(self):
        from inference.utils import segmentation
        from inference.agent import python_tool_sandbox
        from inference.agent import prompts
        from inference.agent import tool_agent

        self.segmentation = segmentation
        self.sandbox = python_tool_sandbox
        self.tool_agent = tool_agent
        self.prompts = prompts
        self.original_segment_layer = segmentation.segment_layer
        self.original_bootstrap = python_tool_sandbox._SANDBOX_BOOTSTRAP
        self.original_description = tool_agent._PYTHON_TOOL_DESCRIPTION
        self.original_prompt_addendum = prompts.STRUCTURED_RUNTIME_STATE_ADDENDUM
        self.original_agent_addendum = tool_agent.STRUCTURED_RUNTIME_STATE_ADDENDUM
        for addendum in (self.original_prompt_addendum, self.original_agent_addendum):
            if addendum.count(SYSTEM_FIELD_ANCHOR) != 1:
                raise ValueError("System segmentation node field contract changed")
        self.prompt_addendum = self.original_prompt_addendum.replace(
            SYSTEM_FIELD_ANCHOR, SYSTEM_FIELD_CONTRACT, 1)
        self.agent_addendum = self.original_agent_addendum.replace(
            SYSTEM_FIELD_ANCHOR, SYSTEM_FIELD_CONTRACT, 1)
        original = self.original_segment_layer

        @wraps(original)
        def segment_layer(layer, color_chars):
            return _attach_row_runs(layer, original(layer, color_chars))

        # The isolated tool embeds a static copy of segmentation.py at import
        # time. Patch that copy too, before any Python process is started.
        injection = (
            "_031_original_segment_layer = segment_layer\n\n"
            + inspect.getsource(_attach_row_runs)
            + "\ndef segment_layer(layer, color_chars):\n"
              "    return _attach_row_runs(layer, _031_original_segment_layer(layer, color_chars))\n\n"
        )
        anchor = "HOST_STDOUT = sys.stdout\n"
        if self.original_bootstrap.count(anchor) != 1:
            raise ValueError("Sandbox segmentation insertion point changed")
        self.bootstrap = self.original_bootstrap.replace(anchor, injection + anchor, 1)
        compile(self.bootstrap, "<segmentation-runs-bootstrap>", "exec")
        self.segment_layer = segment_layer
        segmentation.segment_layer = segment_layer
        python_tool_sandbox._SANDBOX_BOOTSTRAP = self.bootstrap
        self.description = self.original_description + FIELD_GUIDANCE
        tool_agent._PYTHON_TOOL_DESCRIPTION = self.description
        prompts.STRUCTURED_RUNTIME_STATE_ADDENDUM = self.prompt_addendum
        tool_agent.STRUCTURED_RUNTIME_STATE_ADDENDUM = self.agent_addendum

    def snapshot(self):
        return {
            "patch": "segmentation-runs-v2",
            "field": "nodes[*].runs",
            "coordinates": "absolute row, inclusive column start/end",
            "membership": "exact original 4-connected equal-color components",
            "modified_original_fields": [],
            "new_model_tools": False,
            "new_model_requests": False,
            "system_field_contract_updated": (
                self.prompts.STRUCTURED_RUNTIME_STATE_ADDENDUM == self.prompt_addendum
                and self.tool_agent.STRUCTURED_RUNTIME_STATE_ADDENDUM == self.agent_addendum
            ),
            "active": self.segmentation.segment_layer is self.segment_layer,
        }

    def uninstall(self):
        global _INSTALLED
        if self.segmentation.segment_layer is self.segment_layer:
            self.segmentation.segment_layer = self.original_segment_layer
        if self.sandbox._SANDBOX_BOOTSTRAP is self.bootstrap:
            self.sandbox._SANDBOX_BOOTSTRAP = self.original_bootstrap
        if self.tool_agent._PYTHON_TOOL_DESCRIPTION == self.description:
            self.tool_agent._PYTHON_TOOL_DESCRIPTION = self.original_description
        if self.prompts.STRUCTURED_RUNTIME_STATE_ADDENDUM == self.prompt_addendum:
            self.prompts.STRUCTURED_RUNTIME_STATE_ADDENDUM = self.original_prompt_addendum
        if self.tool_agent.STRUCTURED_RUNTIME_STATE_ADDENDUM == self.agent_addendum:
            self.tool_agent.STRUCTURED_RUNTIME_STATE_ADDENDUM = self.original_agent_addendum
        if _INSTALLED is self:
            _INSTALLED = None


def install_segmentation_runs():
    global _INSTALLED
    if _INSTALLED is None:
        _INSTALLED = SegmentationRunsPatch()
    return _INSTALLED
