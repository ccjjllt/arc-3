"""CoreModel: Deterministic Lightweight Simulation Engine and In-Memory Planner.

Architecture Invariants (Contract 04):
1. Purity: CoreModel.step is a pure function (no time, no randomness, no files, no network, no LLM calls).
2. ObservedEdgesOverlay: Factual observed transitions have unconditional priority over model predictions.
3. Zero-action planning: A*/BFS search executes entirely in simulation memory, spending 0 environment actions.
4. Routing Cost Model: Evaluates min(MemoryRoute, UndoChain, ResetAndRoute).
5. Anti-Specification Gaming (Contract 01): Invariant to field size (2x2..64x64) and palette (0..15).
"""

from __future__ import annotations

import hashlib
import heapq
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from inference.und.config.thresholds import (
    ENABLE_CORE_MODEL_SIMULATION,
    ENABLE_OBSERVED_EDGES_OVERLAY,
    ENABLE_SYMBOLIC_UNDO,
    PLAN_TIME_BUDGET_S,
    UNDO_MAX_DEPTH,
)
from inference.und.actions import (
    ACTION_VECTORS,
    COORDINATE_ACTION_ID,
    DISCRETE_ACTION_IDS,
    DUCK_TO_ENGINE_MAP,
    LEGAL_ACTION_IDS,
    RESET_ACTION_ID,
    UNDO_ACTION_ID,
    VECTOR_ACTION_IDS,
)
from inference.und.claim_graph import Claim, ClaimGraph, ClaimStatus

logger = logging.getLogger(__name__)


# =============================================================================
# 1. Simulation State and Outcomes
# =============================================================================

def _compute_grid_hash(grid: Sequence[Sequence[int]]) -> str:
    canonical_repr = "\n".join("".join(format(int(c) & 0xF, "x") for c in row) for row in grid)
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SimState:
    """Immutable hashable simulation state representing the grid world."""
    grid: tuple[tuple[int, ...], ...]
    grid_hash: str
    actor_color: int | None = None
    actor_coords: tuple[tuple[int, int], ...] = ()
    collected_count: int = 0
    step_count: int = 0
    history_actions: tuple[str, ...] = ()

    @classmethod
    def from_grid(
        cls,
        grid: list[list[int]] | tuple[tuple[int, ...], ...],
        actor_color: int | None = None,
        actor_coords: Sequence[tuple[int, int]] | None = None,
        collected_count: int = 0,
        step_count: int = 0,
        history_actions: Sequence[str] = (),
    ) -> SimState:
        g = tuple(tuple(int(c) for c in row) for row in grid)
        coords = tuple(actor_coords or ())
        if not coords and actor_color is not None:
            H = len(g)
            W = len(g[0]) if H > 0 else 0
            found = []
            for r in range(H):
                for c in range(W):
                    if g[r][c] == actor_color:
                        found.append((r, c))
            coords = tuple(found)
        ghash = _compute_grid_hash(g)
        return cls(
            grid=g,
            grid_hash=ghash,
            actor_color=actor_color,
            actor_coords=coords,
            collected_count=collected_count,
            step_count=step_count,
            history_actions=tuple(history_actions),
        )

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    @property
    def actor_centroid(self) -> tuple[float, float] | None:
        if not self.actor_coords:
            return None
        r_sum = sum(r for r, _ in self.actor_coords)
        c_sum = sum(c for _, c in self.actor_coords)
        n = len(self.actor_coords)
        return (r_sum / n, c_sum / n)


@dataclass(frozen=True)
class StepNext:
    """Transition to next non-terminal state."""
    state: SimState
    is_idle: bool = False
    reward: float = 0.0


@dataclass(frozen=True)
class StepTerminal:
    """Transition to terminal state (WIN or GAME_OVER)."""
    state: SimState
    status: str  # "WIN" | "GAME_OVER"
    reward: float = 0.0


@dataclass(frozen=True)
class StepUnknown:
    """Simulation encountered unmodelled or non-deterministic transition."""
    state: SimState
    reason: str


StepResult = StepNext | StepTerminal | StepUnknown


# =============================================================================
# 2. ObservedEdgesOverlay (Contract 04, Section 5)
# =============================================================================

@dataclass(frozen=True)
class ObservedEdge:
    """A factual environment transition observed in live execution."""
    before_hash: str
    action_id: str
    after_hash: str
    is_terminal: bool = False
    terminal_status: str | None = None  # "WIN" | "GAME_OVER"
    zero_delta: bool = False
    after_grid: tuple[tuple[int, ...], ...] | None = None


class ObservedEdgesOverlay:
    """Overlay storing factual transitions observed in live execution.
    
    Observed edges have unconditional priority over model predictions.
    """
    def __init__(self) -> None:
        self._edges: dict[tuple[str, str], ObservedEdge] = {}

    def record(
        self,
        before_hash: str,
        action_id: str,
        after_hash: str,
        is_terminal: bool = False,
        terminal_status: str | None = None,
        zero_delta: bool = False,
        after_grid: Sequence[Sequence[int]] | None = None,
    ) -> None:
        act = str(action_id).upper()
        a_grid = tuple(tuple(int(c) for c in row) for row in after_grid) if after_grid else None
        self._edges[(before_hash, act)] = ObservedEdge(
            before_hash=before_hash,
            action_id=act,
            after_hash=after_hash,
            is_terminal=is_terminal,
            terminal_status=terminal_status,
            zero_delta=zero_delta,
            after_grid=a_grid,
        )

    def lookup(self, before_hash: str, action_id: str) -> ObservedEdge | None:
        return self._edges.get((before_hash, str(action_id).upper()))

    def has_edge(self, before_hash: str, action_id: str) -> bool:
        return (before_hash, str(action_id).upper()) in self._edges

    def clear(self) -> None:
        self._edges.clear()

    def __len__(self) -> int:
        return len(self._edges)


# =============================================================================
# 3. CoreModel: Deterministic Pure Simulation Function (Contract 04, Section 1)
# =============================================================================

class CoreModel:
    """Deterministic simulation engine parameterized by ClaimGraph world laws."""

    def __init__(
        self,
        claim_graph: ClaimGraph | None = None,
        overlay: ObservedEdgesOverlay | None = None,
        background_color: int = 0,
        target_color: int | None = None,
    ) -> None:
        self.claim_graph = claim_graph or ClaimGraph()
        self.overlay = overlay or ObservedEdgesOverlay()
        self.background_color = background_color
        self.target_color = target_color

    def step(self, s: SimState, action_id: str) -> StepResult:
        """Pure deterministic step function: (SimState, Action) -> StepResult."""
        act = str(action_id).upper()

        # 1. Overlay priority (Contract 04, Section 5)
        if ENABLE_OBSERVED_EDGES_OVERLAY and self.overlay.has_edge(s.grid_hash, act):
            obs_edge = self.overlay.lookup(s.grid_hash, act)
            if obs_edge is not None:
                if obs_edge.is_terminal:
                    return StepTerminal(
                        state=s,
                        status=obs_edge.terminal_status or "GAME_OVER",
                        reward=1.0 if obs_edge.terminal_status == "WIN" else -1.0,
                    )
                if obs_edge.zero_delta:
                    return StepNext(state=s, is_idle=True, reward=0.0)
                if obs_edge.after_grid is not None:
                    next_s = SimState.from_grid(
                        grid=obs_edge.after_grid,
                        actor_color=s.actor_color,
                        collected_count=s.collected_count,
                        step_count=s.step_count + 1,
                        history_actions=(*s.history_actions, act),
                    )
                    return StepNext(state=next_s, is_idle=False, reward=0.0)

        # 2. Kinematic displacement resolution
        dy, dx = 0, 0
        kinematic_found = False
        canonical_act = DUCK_TO_ENGINE_MAP.get(act, act)

        # Check ClaimGraph confirmed/active action_effect claims
        for claim in self.claim_graph.active_claims():
            if claim.kind == "action_effect" and claim.subject and str(claim.subject[0]).upper() in (act, canonical_act):
                dy = int(claim.predicate.get("dy", 0))
                dx = int(claim.predicate.get("dx", 0))
                kinematic_found = True
                break

        # Canonical fallback if not yet probed in ClaimGraph
        if not kinematic_found:
            if canonical_act in ACTION_VECTORS:
                dy, dx = ACTION_VECTORS[canonical_act]
                kinematic_found = True
            elif canonical_act == RESET_ACTION_ID:
                return StepTerminal(state=s, status="GAME_OVER", reward=-0.1)
            else:
                return StepUnknown(state=s, reason=f"Unknown kinematics for {act}")

        # If action is pure zero-displacement
        if dy == 0 and dx == 0:
            return StepNext(state=s, is_idle=True, reward=0.0)

        # 3. Resolve actor coordinates
        actor_coords = list(s.actor_coords)
        actor_color = s.actor_color
        if not actor_coords and actor_color is not None:
            for r in range(s.height):
                for c in range(s.width):
                    if s.grid[r][c] == actor_color:
                        actor_coords.append((r, c))

        if not actor_coords:
            # Try to identify actor from ClaimGraph controlled claims
            for claim in self.claim_graph.active_claims():
                if claim.kind == "controlled" and "sig" in claim.predicate:
                    cand_col = claim.predicate["sig"][0]
                    found = [(r, c) for r in range(s.height) for c in range(s.width) if s.grid[r][c] == cand_col]
                    if found:
                        actor_color = cand_col
                        actor_coords = found
                        break

        if not actor_coords:
            return StepUnknown(state=s, reason="Actor coordinates could not be grounded in simulation")

        # 4. Propose displacement and check boundary collisions
        new_coords = [(r + dy, c + dx) for r, c in actor_coords]
        H, W = s.height, s.width

        # Check out of grid bounds
        for r, c in new_coords:
            if r < 0 or r >= H or c < 0 or c >= W:
                # Wall/boundary hit -> zero delta, IDLE transition (Contract 02, Section 7)
                return StepNext(state=s, is_idle=True, reward=0.0)

        # 5. Check cell interactions for newly occupied cells
        old_set = set(actor_coords)
        entering_cells = [(r, c) for r, c in new_coords if (r, c) not in old_set]

        # Query ClaimGraph passability, lethal, collectible claims
        blocks_colors: set[int] = set()
        lethal_colors: set[int] = set()
        collectible_colors: set[int] = set()

        for claim in self.claim_graph.active_claims():
            sig = claim.subject[0] if claim.subject else None
            col = sig[0] if (sig and isinstance(sig, (tuple, list))) else None
            if col is None:
                continue
            if claim.kind == "passability" and claim.predicate.get("blocks", True):
                blocks_colors.add(col)
            elif claim.kind == "lethal" and claim.predicate.get("lethal", True):
                lethal_colors.add(col)
            elif claim.kind == "collectible" and claim.predicate.get("collectible", True):
                collectible_colors.add(col)

        # Inspect obstacle, lethal, collectible, and target collisions
        new_collected = s.collected_count
        cleared_cells: set[tuple[int, int]] = set()
        is_lethal = False
        is_win = False

        for r, c in entering_cells:
            cell_col = s.grid[r][c]
            if cell_col == self.background_color:
                continue

            # Passability check (ISO-11: zero delta on known obstacle yields IDLE)
            if cell_col in blocks_colors:
                return StepNext(state=s, is_idle=True, reward=0.0)

            # Lethality check
            if cell_col in lethal_colors:
                is_lethal = True

            # Collectible check
            if cell_col in collectible_colors:
                new_collected += 1
                cleared_cells.add((r, c))

            # Target / Goal check
            if self.target_color is not None and cell_col == self.target_color:
                is_win = True

        # 6. Apply state mutation to create next SimState
        grid_copy = [list(row) for row in s.grid]

        # Clear old actor cells that are not in new_coords
        for r, c in actor_coords:
            if (r, c) not in new_coords:
                grid_copy[r][c] = self.background_color

        # Clear collected cells
        for r, c in cleared_cells:
            grid_copy[r][c] = self.background_color

        # Paint actor in new positions
        act_col_val = actor_color if actor_color is not None else 1
        for r, c in new_coords:
            grid_copy[r][c] = act_col_val

        next_state = SimState.from_grid(
            grid=grid_copy,
            actor_color=actor_color,
            actor_coords=new_coords,
            collected_count=new_collected,
            step_count=s.step_count + 1,
            history_actions=(*s.history_actions, act),
        )

        if is_lethal:
            return StepTerminal(state=next_state, status="GAME_OVER", reward=-1.0)
        if is_win:
            return StepTerminal(state=next_state, status="WIN", reward=1.0)

        return StepNext(state=next_state, is_idle=False, reward=0.0)


# =============================================================================
# 4. RoutingCostModel (Contract 04, Section 4)
# =============================================================================

@dataclass(frozen=True)
class RouteCandidate:
    route_type: str  # "memory" | "undo" | "reset"
    cost: int
    actions: tuple[str, ...]


class RoutingCostModel:
    """Evaluates routing candidates to reach a target state class by minimal cost.
    
    Formula (Contract 04, Section 4):
    1. Known memory edges: length of shortest path.
    2. Undo chain: k edges (if ENABLE_SYMBOLIC_UNDO and undo_exact confirmed).
    3. RESET + route from S0: 1 + d.
    Tie breaker strictly prefers non-RESET routes.
    """
    def __init__(
        self,
        enable_symbolic_undo: bool = ENABLE_SYMBOLIC_UNDO,
        undo_max_depth: int = UNDO_MAX_DEPTH,
    ) -> None:
        self.enable_symbolic_undo = enable_symbolic_undo
        self.undo_max_depth = undo_max_depth

    def select_best_route(
        self,
        current_hash: str,
        target_hash: str,
        memory_graph: dict[str, list[tuple[str, str]]],  # src_hash -> [(action, dst_hash)]
        initial_hash: str,
        recent_history_hashes: Sequence[str] = (),
        undo_exact_confirmed: bool = False,
        is_game_over: bool = False,
    ) -> RouteCandidate | None:
        """Select minimal cost route to target_hash."""
        # After GAME_OVER, RESET + route is the only permissible route
        if is_game_over:
            path_from_s0 = self._bfs_shortest_path(initial_hash, target_hash, memory_graph)
            if path_from_s0 is not None:
                return RouteCandidate(
                    route_type="reset",
                    cost=1 + len(path_from_s0),
                    actions=(RESET_ACTION_ID, *path_from_s0),
                )
            return None

        candidates: list[RouteCandidate] = []

        # 1. Memory route (shortest path from current state)
        if current_hash == target_hash:
            return RouteCandidate(route_type="memory", cost=0, actions=())

        mem_path = self._bfs_shortest_path(current_hash, target_hash, memory_graph)
        if mem_path is not None:
            candidates.append(RouteCandidate(route_type="memory", cost=len(mem_path), actions=tuple(mem_path)))

        # 2. Undo chain
        if self.enable_symbolic_undo and undo_exact_confirmed and recent_history_hashes:
            hist = list(recent_history_hashes)
            if hist and hist[-1] == current_hash:
                hist.pop()
            rev_history = list(reversed(hist))
            for k, past_h in enumerate(rev_history[:self.undo_max_depth], start=1):
                if past_h == target_hash:
                    candidates.append(
                        RouteCandidate(
                            route_type="undo",
                            cost=k,
                            actions=tuple(UNDO_ACTION_ID for _ in range(k)),
                        )
                    )
                    break

        # 3. RESET + route from initial state
        path_from_init = self._bfs_shortest_path(initial_hash, target_hash, memory_graph)
        if path_from_init is not None:
            candidates.append(
                RouteCandidate(
                    route_type="reset",
                    cost=1 + len(path_from_init),
                    actions=(RESET_ACTION_ID, *path_from_init),
                )
            )

        if not candidates:
            return None

        # Sort by cost; on tie, prefer non-RESET routes
        def tie_sort_key(c: RouteCandidate) -> tuple[int, int]:
            reset_penalty = 1 if c.route_type == "reset" else 0
            return (c.cost, reset_penalty)

        return min(candidates, key=tie_sort_key)

    @staticmethod
    def _bfs_shortest_path(
        start_hash: str,
        goal_hash: str,
        graph: dict[str, list[tuple[str, str]]],
    ) -> list[str] | None:
        """Standard BFS finding shortest action sequence in memory graph."""
        if start_hash == goal_hash:
            return []
        queue: list[tuple[str, list[str]]] = [(start_hash, [])]
        visited: set[str] = {start_hash}
        while queue:
            curr, path = queue.pop(0)
            for act, next_h in graph.get(curr, []):
                if next_h == goal_hash:
                    return path + [act]
                if next_h not in visited:
                    visited.add(next_h)
                    queue.append((next_h, path + [act]))
        return None


# =============================================================================
# 5. SimulationPlanner (Zero-Action In-Memory Planning)
# =============================================================================

@dataclass
class PlanResult:
    success: bool
    actions: list[str]
    final_state: SimState | None = None
    nodes_expanded: int = 0
    reason: str = ""


class SimulationPlanner:
    """A*/BFS search planner executing purely in simulation memory (0 environment actions)."""

    def __init__(
        self,
        core_model: CoreModel,
        available_actions: Sequence[str] = VECTOR_ACTION_IDS,
        max_search_nodes: int = 4000,
        time_budget_s: float = PLAN_TIME_BUDGET_S,
    ) -> None:
        self.core_model = core_model
        # Rule 04 В§4 item 3: UNDO must NEVER appear in search paths produced by wm.plan / planner
        self.available_actions = [
            a for a in available_actions if str(a).upper() not in ("ACTION7", "UNDO")
        ]
        self.max_search_nodes = max_search_nodes
        self.time_budget_s = time_budget_s

    def plan_to_target(
        self,
        start_state: SimState,
        target_pos: tuple[int, int] | None = None,
        target_color: int | None = None,
        collect_all: bool = False,
    ) -> PlanResult:
        """Search for action sequence reaching target position, target color, or winning condition."""
        if target_color is not None:
            self.core_model.target_color = target_color

        # Priority queue entries: (f_score, cost, sequence_id, state)
        seq_id = 0
        frontier: list[tuple[float, int, int, SimState]] = []
        h0 = self._heuristic(start_state, target_pos)
        heapq.heappush(frontier, (h0, 0, seq_id, start_state))

        came_from: dict[str, tuple[SimState, str]] = {}
        cost_so_far: dict[str, int] = {start_state.grid_hash: 0}
        visited_hashes: set[str] = set()

        nodes_expanded = 0
        start_time = time.monotonic()

        while frontier and nodes_expanded < self.max_search_nodes:
            if (nodes_expanded & 63 == 0) and (time.monotonic() - start_time > self.time_budget_s):
                return PlanResult(
                    success=False, actions=[], final_state=None, nodes_expanded=nodes_expanded,
                    reason=f"Planning time budget exceeded ({self.time_budget_s}s)",
                )

            _, current_cost, _, current_state = heapq.heappop(frontier)
            curr_h = current_state.grid_hash

            if curr_h in visited_hashes:
                continue
            visited_hashes.add(curr_h)
            nodes_expanded += 1

            # Check goal condition
            if self._is_goal(current_state, target_pos, target_color, collect_all):
                actions = self._reconstruct_path(came_from, start_state.grid_hash, curr_h)
                return PlanResult(
                    success=True,
                    actions=actions,
                    final_state=current_state,
                    nodes_expanded=nodes_expanded,
                    reason="Goal reached",
                )

            # Expand neighbors
            for act in self.available_actions:
                step_res = self.core_model.step(current_state, act)

                if isinstance(step_res, StepTerminal):
                    if step_res.status == "WIN":
                        actions = self._reconstruct_path(came_from, start_state.grid_hash, current_state.grid_hash) + [act]
                        return PlanResult(
                            success=True,
                            actions=actions,
                            final_state=step_res.state,
                            nodes_expanded=nodes_expanded,
                            reason="Terminal WIN state reached",
                        )
                    # GAME_OVER is pruned
                    continue

                if isinstance(step_res, StepUnknown):
                    # Unknown edge gets heuristic exploration penalty
                    continue

                if isinstance(step_res, StepNext):
                    if step_res.is_idle:
                        # Idle transitions (wall collisions, etc.) pruned from search
                        continue

                    next_s = step_res.state
                    next_h = next_s.grid_hash
                    new_cost = current_cost + 1

                    if next_h not in cost_so_far or new_cost < cost_so_far[next_h]:
                        cost_so_far[next_h] = new_cost
                        came_from[next_h] = (current_state, act)
                        seq_id += 1
                        priority = new_cost + self._heuristic(next_s, target_pos)
                        heapq.heappush(frontier, (priority, new_cost, seq_id, next_s))

        return PlanResult(
            success=False,
            actions=[],
            final_state=None,
            nodes_expanded=nodes_expanded,
            reason=f"Exhausted search space ({nodes_expanded} nodes expanded)",
        )

    def _is_goal(
        self,
        s: SimState,
        target_pos: tuple[int, int] | None,
        target_color: int | None,
        collect_all: bool,
    ) -> bool:
        if target_pos is not None and s.actor_coords:
            if target_pos in s.actor_coords or s.actor_coords[0] == target_pos:
                return True
        if target_color is not None:
            # Check if actor reached cell with target_color
            for r in range(s.height):
                for c in range(s.width):
                    if s.grid[r][c] == target_color:
                        return False
            # If target_color is no longer on grid (collected/absorbed), goal reached
            return True
        return False

    @staticmethod
    def _heuristic(s: SimState, target_pos: tuple[int, int] | None) -> float:
        if target_pos is None or not s.actor_coords:
            return 0.0
        ar, ac = s.actor_coords[0]
        tr, tc = target_pos
        return float(abs(ar - tr) + abs(ac - tc))

    @staticmethod
    def _reconstruct_path(
        came_from: dict[str, tuple[SimState, str]],
        start_hash: str,
        goal_hash: str,
    ) -> list[str]:
        curr = goal_hash
        actions: list[str] = []
        while curr != start_hash and curr in came_from:
            parent_s, act = came_from[curr]
            actions.append(act)
            curr = parent_s.grid_hash
        actions.reverse()
        return actions
