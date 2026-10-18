"""018: one short system-prefix instruction using the unmodified harness hook.

No agent methods, tools, observations, actions, or memory are patched. Install
only in the candidate's isolated CPU process, before constructing ToolAgent.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any


PREFIX_ENV = "ARC3_SYSTEM_PROMPT_PREFIX"
GROUNDING_PREFIX = (
    "When converting visual geometry or patterns into program state, use segmentation "
    "to locate relevant regions, then read only the necessary small crops from "
    "current_frame.ascii. A node's boundary or bounding rectangle does not mean every "
    "enclosed cell has its color: preserve observed holes and disconnected parts in "
    "color masks. Physical or collision footprints may differ and require interaction "
    "evidence. Keep the crop's actual characters, origin, row/col mapping, and bounds "
    "explicit; check crop bounds against the current frame and key encoded cells "
    "against observed characters before searching or executing "
    "a derived plan. Pixel count alone is not proof. Do not substitute a box center "
    "for observed geometry. Re-read changed regions on a new level; reuse supported "
    "rules, not old coordinates. Apply this extra inspection only when exact geometry "
    "or patterns are needed."
)


class GroundingPrefix:
    def __init__(self, previous: str | None) -> None:
        self.previous = previous
        self.active = True

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": "observation_grounding",
            "enabled": self.active,
            "mechanism": "existing_system_prompt_prefix",
            "environment_key": PREFIX_ENV,
            "prefix_sha256": hashlib.sha256(GROUNDING_PREFIX.encode()).hexdigest(),
            "prefix_characters": len(GROUNDING_PREFIX),
            "prefix_words": len(GROUNDING_PREFIX.split()),
            "adds_tools": False,
            "adds_framework_model_calls": False,
            "adds_framework_game_actions": False,
            "changes_memory_contract": False,
            "natural_requests_tokens_and_actions_may_change": True,
        }

    def uninstall(self) -> None:
        if not self.active:
            return
        if os.environ.get(PREFIX_ENV) != GROUNDING_PREFIX:
            raise RuntimeError("Observation-grounding prefix changed while installed.")
        if self.previous is None:
            os.environ.pop(PREFIX_ENV, None)
        else:
            os.environ[PREFIX_ENV] = self.previous
        self.active = False


def install_observation_grounding() -> GroundingPrefix:
    previous = os.environ.get(PREFIX_ENV)
    if previous is not None and previous.strip():
        raise RuntimeError("Observation grounding requires an empty system prefix; "
                           "refusing an existing prefix or duplicate installation.")
    handle = GroundingPrefix(previous)
    os.environ[PREFIX_ENV] = GROUNDING_PREFIX
    return handle
