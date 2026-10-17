"""CONTRACT: Deterministic Mechanics Digest generator without goal leakage (Rules 01, 04, 05).

Generates structured, compact mechanics digests for the LLM thinker:
- Zero goal leakage (Rule 01, Contract 01): describes physical mechanics only,
  never specifies victory objectives or winning instructions.
- Strict token budget: bounded by DIGEST_MAX_TOKENS (<= 800 tokens, Rule 05 В§7).
- Deterministic canonical formatting: actions and color properties are sorted
  alphabetically/numerically to preserve prompt cache stability (Prefix Cache).
- Incorporates kinematics, passability, lethality, reactivity, and timer telemetry.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Sequence

from inference.und.config.thresholds import DEFAULT_THRESHOLDS, ThresholdsConfig
from inference.und.texts import DIGEST_HEADER_TEMPLATE

if TYPE_CHECKING:
    from inference.und.session import UndSession

logger = logging.getLogger(__name__)

# Forbidden goal-leak phrases (Anti-Specification Gaming, Rule 01)
FORBIDDEN_GOAL_TERMS: tuple[str, ...] = (
    "victory goal",
    "win condition",
    "objective is to",
    "goal is to",
    "collect all to win",
    "reach the end to win",
    "winning objective",
)


@dataclass
class MechanicsDigest:
    """Structured representation of active environment mechanics."""
    game_id: str
    level: int
    step: int
    field_shape: tuple[int, int] = (0, 0)
    actor_color: int | None = None
    kinematics: dict[str, str] = field(default_factory=dict)
    obstacles: list[int] = field(default_factory=list)
    hazards: list[int] = field(default_factory=list)
    reactives: dict[int, str] = field(default_factory=dict)
    timer_info: dict[str, Any] = field(default_factory=dict)
    confirmed_laws_count: int = 0
    hypotheses: list[str] = field(default_factory=list)
    animation_trajectory: str = ""

    def to_text(self, max_tokens: int = 800) -> str:
        """Render deterministic plain-text digest within character and token limits."""
        lines: list[str] = []

        # 1. Header
        steps_rem = self.timer_info.get("estimated_remaining_steps")
        steps_rem_str = str(steps_rem) if steps_rem is not None else "unlimited"
        has_t_str = "yes" if self.timer_info.get("has_timer") else "no"
        header = DIGEST_HEADER_TEMPLATE.format(
            level=self.level,
            step=self.step,
            steps_remaining=steps_rem_str,
            has_timer=has_t_str,
        )
        lines.append(header.strip())

        # 2. Dimensions & Field
        h, w = self.field_shape
        lines.append(f"Grid Size: {h}x{w} (boundary walls are impassable)")

        # 3. Controlled Actor & Kinematics
        if self.actor_color is not None:
            lines.append(f"Controlled Actor: Color {self.actor_color}")
        else:
            lines.append("Controlled Actor: Unknown / ungrounded")

        if self.kinematics:
            lines.append("Controls & Movement:")
            for act in sorted(self.kinematics.keys()):
                lines.append(f"  - {act}: {self.kinematics[act]}")
        else:
            lines.append("Controls: No confirmed kinematic effects yet")

        # 4. Collisions & Obstacles
        if self.obstacles:
            obs_str = ", ".join(f"Color {c}" for c in sorted(self.obstacles))
            lines.append(f"Solid Barriers (block movement): {obs_str}")
        else:
            lines.append("Solid Barriers: None confirmed")

        # 5. Lethal Hazards
        if self.hazards:
            haz_str = ", ".join(f"Color {c}" for c in sorted(self.hazards))
            lines.append(f"Lethal Hazards (cause reset/game over): {haz_str}")

        # 6. Reactives & Mutations (Physical only, NO goal statement)
        if self.reactives:
            lines.append("Interactive Elements:")
            for c in sorted(self.reactives.keys()):
                lines.append(f"  - Color {c}: {self.reactives[c]}")

        # 7. Timer & Probe Pressure
        if self.timer_info.get("has_timer"):
            t_type = self.timer_info.get("timer_type", "countdown")
            p_rem = self.timer_info.get("probe_budget_remaining", 0)
            burn = self.timer_info.get("burn_rate", 1.0)
            lines.append(
                f"Timer Telemetry: type={t_type}, remaining={steps_rem_str} steps, "
                f"burn_rate={burn} steps/act, exploratory probe allowance={p_rem}"
            )
            if self.timer_info.get("is_critical"):
                lines.append("  [CRITICAL]: <= 4 actions remaining! Suppress exploration.")

        # 8. Dynamic Animation
        if self.animation_trajectory:
            lines.append(f"Dynamic Animation: {self.animation_trajectory}")

        # 9. Knowledge Base
        lines.append(
            f"Knowledge Base: {self.confirmed_laws_count} confirmed invariant laws, "
            f"{len(self.hypotheses)} active hypotheses"
        )
        if self.hypotheses:
            for hyp in sorted(self.hypotheses)[:3]:
                lines.append(f"  - ? {hyp}")

        text = "\n".join(lines)

        # 10. Budget safety truncation (~4 chars per token)
        char_limit = max_tokens * 4
        if len(text) > char_limit:
            text = text[: char_limit - 40].rstrip() + "\n[... truncated by DIGEST_MAX_TOKENS]"

        return text

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "level": self.level,
            "step": self.step,
            "field_shape": list(self.field_shape),
            "actor_color": self.actor_color,
            "kinematics": dict(self.kinematics),
            "obstacles": list(self.obstacles),
            "hazards": list(self.hazards),
            "reactives": dict(self.reactives),
            "timer_info": dict(self.timer_info),
            "confirmed_laws_count": self.confirmed_laws_count,
            "hypotheses": list(self.hypotheses),
            "animation_trajectory": self.animation_trajectory,
        }


def build_mechanics_digest(
    session: Any,
    max_tokens: int | None = None,
) -> str:
    """Build a deterministic, non-leaking mechanics digest from active UndSession."""
    cfg = getattr(session, "config", DEFAULT_THRESHOLDS)
    max_tok: int = int(max_tokens) if max_tokens is not None else int(getattr(cfg, "digest_max_tokens", 800))

    # 1. Dimensions
    f_shape = (0, 0)
    grid = None
    if getattr(session, "current_frame", None) is not None:
        grid = session.current_frame.grid
        if grid:
            f_shape = (len(grid), len(grid[0]) if grid[0] else 0)

    # 2. Extract ClaimGraph and roles
    cg = getattr(session, "claim_graph", None)
    active_claims = cg.active_claims() if cg else []
    confirmed_claims = cg.confirmed_claims() if cg else []
    roles = cg.project_entity_roles() if cg else {}

    # Actor color
    actor_color = None
    for color, role in roles.items():
        if role == "actor":
            actor_color = color
            break

    # Kinematics
    kinematics: dict[str, str] = {}
    for c in active_claims:
        if c.kind == "action_effect" and c.subject:
            act_name = str(c.subject[0]).upper()
            dy = int(c.predicate.get("dy", 0))
            dx = int(c.predicate.get("dx", 0))
            direction = []
            if dy < 0:
                direction.append(f"up {-dy}")
            elif dy > 0:
                direction.append(f"down {dy}")
            if dx < 0:
                direction.append(f"left {-dx}")
            elif dx > 0:
                direction.append(f"right {dx}")
            dir_str = ", ".join(direction) if direction else "zero displacement (idle)"
            status_tag = "verified law" if c.status.value == "+" else "hypothesis"
            kinematics[act_name] = f"translates ({dy:+d}, {dx:+d}) [{dir_str}] ({status_tag})"

    # Obstacles & Hazards from projected roles
    obstacles: list[int] = []
    hazards: list[int] = []
    reactives: dict[int, str] = {}
    for color, role in roles.items():
        if role == "obstacle":
            obstacles.append(color)
        elif role == "hazard":
            hazards.append(color)
        elif role in ("collectible", "target", "portal"):
            reactives[color] = "vanishes or mutates on actor contact (score/state alters)"

    # Add background color
    if grid:
        # Detect solid static background
        color_counts: dict[int, int] = {}
        for r in grid:
            for cell in r:
                color_counts[cell] = color_counts.get(cell, 0) + 1
        if color_counts:
            bg_col = max(color_counts, key=color_counts.get)  # type: ignore
            if bg_col not in obstacles and bg_col not in hazards:
                # Background is free space
                pass

    # 3. Timer telemetry
    timer = getattr(session, "timer", None)
    probes_used = int(getattr(session, "probes_used_on_level", 0))
    timer_info = timer.status(getattr(session, "level", 0), probes_used=probes_used).to_dict() if timer else {}

    # 4. Hypotheses list
    hypotheses: list[str] = []
    for c in active_claims:
        if c.status.value == "?":
            hypotheses.append(f"{c.kind}: {c.subject} -> {c.predicate}")

    anim_info = getattr(session, "last_animation_info", None)
    anim_traj = str(anim_info.get("summary_phrase", "")) if anim_info else ""

    digest_obj = MechanicsDigest(
        game_id=getattr(session, "game_id", ""),
        level=getattr(session, "level", 0),
        step=getattr(session, "step_index", 0),
        field_shape=f_shape,
        actor_color=actor_color,
        kinematics=kinematics,
        obstacles=sorted(obstacles),
        hazards=sorted(hazards),
        reactives=reactives,
        timer_info=timer_info,
        confirmed_laws_count=len(confirmed_claims),
        hypotheses=hypotheses,
        animation_trajectory=anim_traj,
    )

    text = digest_obj.to_text(max_tokens=max_tok)

    # Sanity check against forbidden goal leaks
    lowered = text.lower()
    for forbidden in FORBIDDEN_GOAL_TERMS:
        if forbidden in lowered:
            logger.error("Goal leak detected in mechanics digest: '%s'", forbidden)
            text = text.replace(forbidden, "[REDACTED_MECHANIC]")

    return text


def build_turn0_digest(
    grid: Sequence[Sequence[int]] | None,
    valid_actions: Sequence[Any] | None = None,
    max_object_classes: int = 12,
) -> str:
    """Build compact structural digest for Turn 0 (before first action is taken).

    Adheres strictly to Anti-Specification Gaming Contract (no goal hints, no puzzle IDs).
    Provides:
    - Grid dimensions and background color.
    - Active palette colors present on the grid.
    - Object classes grouped by (color, shape, area) with centroids.
    - Control modality: Pure Mouse, Pure Keyboard, or Hybrid (Mouse + Keyboard).
    """
    if not grid or not grid[0]:
        return "INITIAL STRUCTURE: None available."

    h = len(grid)
    w = len(grid[0])
    lines: list[str] = [f"INITIAL STRUCTURE: Grid {h}x{w}"]

    # 1. Palette
    unique_colors = sorted({int(c) for row in grid for c in row})
    lines.append(f"Active Palette: {unique_colors} (colors {', '.join(str(c) for c in unique_colors)})")

    # 2. Control modality
    if valid_actions:
        norm_actions = [str(a).strip().upper() for a in valid_actions]
        has_mouse = any("MOUSE" in a or "ACTION6" in a or "CLICK" in a for a in norm_actions)
        has_keys = any(
            any(k in a for k in ("UP", "DOWN", "LEFT", "RIGHT", "ACTION1", "ACTION2", "ACTION3", "ACTION4", "SPACE", "ACTION5"))
            for a in norm_actions
        )
        if has_mouse and has_keys:
            modality = "Hybrid (Mouse + Keyboard)"
        elif has_mouse:
            modality = "Pure Mouse (Coordinate Clicks)"
        elif has_keys:
            modality = "Pure Keyboard (Discrete Moves)"
        else:
            modality = ", ".join(norm_actions)
        lines.append(f"Control Modality: {modality} (Valid: {', '.join(norm_actions)})")

    # 3. Object classes from ARGA-Lite
    try:
        from inference.und.perception.arga_lite import extract_arga_snapshot
        grid_list = [list(r) for r in grid]
        snapshot = extract_arga_snapshot(grid_list)
        bg = snapshot.background_color
        lines.append(f"Background Color: {bg}")

        # Group non-background objects by (color, height, width, area)
        classes: dict[tuple[int, int, int, int], list[Any]] = {}
        for obj in snapshot.objects:
            if obj.color == bg:
                continue
            key = (obj.color, obj.bbox.height, obj.bbox.width, obj.area)
            if key not in classes:
                classes[key] = []
            classes[key].append(obj)

        if classes:
            lines.append("Detected Object Classes:")
            for idx, ((col, bh, bw, area), objs) in enumerate(sorted(classes.items(), key=lambda x: -len(x[1]))[:max_object_classes]):
                count = len(objs)
                centroids = [f"({o.centroid.row:.1f},{o.centroid.col:.1f})" for o in objs[:3]]
                pos_str = ", ".join(centroids) + ("..." if count > 3 else "")
                lines.append(f"  - c{idx+1}: Color {col}, size {bh}x{bw} (area {area}), count {count}, pos [{pos_str}]")
    except Exception as e:
        logger.debug("Turn-0 ARGA snapshot extraction failed: %s", e)

    return "\n".join(lines)
