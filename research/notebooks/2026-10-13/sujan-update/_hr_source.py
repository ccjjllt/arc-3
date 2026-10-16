"""Sovereign Hyper-Resilience Network Adapter & Connection Armor."""

from __future__ import annotations

import os
import sys
import time
import random
import socket
import logging
from typing import Any
import requests
from requests.adapters import HTTPAdapter

log = logging.getLogger("sovereign.hyper_resilience")

# Configuration Constants
_MIN_READ_TIMEOUT_DEFAULT = 180.0
_MAX_RETRIES_TIMEOUT = 3
_BASE_BACKOFF = 1.0

_GLOBAL_SESSION: requests.Session | None = None


def get_hardened_session() -> requests.Session:
    """Return a process-wide hardened singleton requests.Session."""
    global _GLOBAL_SESSION
    if _GLOBAL_SESSION is not None:
        return _GLOBAL_SESSION

    session = requests.Session()

    # Configure Socket Keepalive & No-Delay
    socket_options = [
        (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
        (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),
    ]
    if hasattr(socket, "TCP_KEEPIDLE"):
        socket_options.append((socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60))
    if hasattr(socket, "TCP_KEEPINTVL"):
        socket_options.append((socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 15))
    if hasattr(socket, "TCP_KEEPCNT"):
        socket_options.append((socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5))

    adapter = HTTPAdapter(
        pool_connections=64,
        pool_maxsize=64,
        max_retries=0,  # We manage application-level retries with jitter
    )
    # Inject socket options into urllib3 poolmanager
    try:
        adapter.init_poolmanager(
            connections=64,
            maxsize=64,
            socket_options=socket_options,
        )
    except Exception as exc:
        log.warning("Could not set advanced socket options: %s", exc)

    session.mount("http://", adapter)
    session.mount("https://", adapter)
    _GLOBAL_SESSION = session
    return _GLOBAL_SESSION


def robust_post(
    url: str,
    headers: dict[str, str] | None = None,
    json_data: dict[str, Any] | None = None,
    timeout: Any = None,
    max_retries: int = _MAX_RETRIES_TIMEOUT,
    **extra_kwargs: Any,
) -> requests.Response:
    """Execute HTTP POST with hardened session, timeout floor, and backoff."""
    min_floor = float(os.environ.get("ARC3_MIN_READ_TIMEOUT", str(_MIN_READ_TIMEOUT_DEFAULT)))
    if isinstance(timeout, (tuple, list)):
        conn_to = float(timeout[0]) if len(timeout) > 0 and timeout[0] is not None else 10.0
        read_to = float(timeout[1]) if len(timeout) > 1 and timeout[1] is not None else min_floor
        effective_timeout: Any = (conn_to, max(min_floor, read_to))
    elif timeout is not None:
        effective_timeout = max(min_floor, float(timeout))
    else:
        effective_timeout = (10.0, min_floor)

    session = get_hardened_session()
    attempt = 0

    while True:
        attempt += 1
        try:
            resp = session.post(
                url,
                headers=headers,
                json=json_data,
                timeout=effective_timeout,
            )
            # Transient 5xx retry
            if resp.status_code in (500, 502, 503, 504) and attempt <= max_retries:
                sleep_s = _BASE_BACKOFF * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                log.warning(
                    "Server returned %d. Retrying in %.2fs (attempt %d/%d)...",
                    resp.status_code,
                    sleep_s,
                    attempt,
                    max_retries,
                )
                time.sleep(sleep_s)
                continue
            return resp

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            if attempt <= max_retries:
                sleep_s = _BASE_BACKOFF * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                log.warning(
                    "Network transient error (%s). Retrying in %.2fs (attempt %d/%d)...",
                    type(exc).__name__,
                    sleep_s,
                    attempt,
                    max_retries,
                )
                time.sleep(sleep_s)
                continue
            log.error("Exhausted retries on network request to %s: %s", url, exc)
            raise


# ---- Geometric Pole of Inaccessibility (True Interior Targeting) ----

def compute_interior_click_target(cells: set[tuple[int, int]]) -> tuple[int, int]:
    """Find the interior cell furthest from any non-component background cell."""
    if not cells:
        return 32, 32
    if len(cells) == 1:
        return next(iter(cells))

    min_r = min(r for r, _ in cells)
    max_r = max(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    max_c = max(c for _, c in cells)

    best_cell = next(iter(cells))
    best_dist = -1.0

    for r, c in cells:
        d_edge = min(r - min_r, max_r - r, c - min_c, max_c - c)
        neighbors = sum(1 for dr, dc in ((-1,0), (1,0), (0,-1), (0,1)) if (r+dr, c+dc) in cells)
        score = d_edge * 10.0 + neighbors

        if score > best_dist:
            best_dist = score
            best_cell = (r, c)

    return best_cell


# ---- 64-bit Zobrist Hash & Cycle Breaker ----

class ZobristCycleBreaker:
    """O(1) cycle detection and anti-oscillation tracker."""

    def __init__(self, memory_size: int = 128, max_loop_visits: int = 2):
        self.memory_size = memory_size
        self.max_loop_visits = max_loop_visits
        self.history: list[int] = []
        self.visit_counts: dict[int, int] = {}
        rng = random.Random(42)
        self.table = [
            [[rng.getrandbits(64) for _ in range(16)] for _ in range(64)]
            for _ in range(64)
        ]

    def hash_grid(self, grid: Any) -> int:
        h = 0
        try:
            rows = len(grid)
            cols = len(grid[0]) if rows > 0 else 0
            for r in range(min(64, rows)):
                for c in range(min(64, cols)):
                    val = int(grid[r][c]) % 16
                    h ^= self.table[r][c][val]
        except Exception:
            pass
        return h

    def record_and_check_cycle(self, grid: Any) -> bool:
        """Returns True if state is part of a repeated loop (k >= 2)."""
        zh = self.hash_grid(grid)
        self.history.append(zh)
        if len(self.history) > self.memory_size:
            evicted = self.history.pop(0)
            self.visit_counts[evicted] = max(0, self.visit_counts.get(evicted, 1) - 1)

        self.visit_counts[zh] = self.visit_counts.get(zh, 0) + 1
        return self.visit_counts[zh] >= self.max_loop_visits


def install_hyper_resilience(tool_agent_mod: Any, solver_mod: Any) -> str:
    """Install connection pooling, robust retries, and timeout floor."""
    installed = []

    # 1. Patch ToolAgent HTTP caller
    if hasattr(tool_agent_mod, "ToolAgent"):
        ta_cls = tool_agent_mod.ToolAgent
        if hasattr(ta_cls, "_chat_completion"):
            orig_cc = ta_cls._chat_completion

            def hardened_chat_completion(self, messages, **kwargs):
                req_to = kwargs.get("request_timeout_seconds")
                min_floor = float(os.environ.get("ARC3_MIN_READ_TIMEOUT", str(_MIN_READ_TIMEOUT_DEFAULT)))
                if req_to is not None:
                    kwargs["request_timeout_seconds"] = max(min_floor, float(req_to))
                return orig_cc(self, messages, **kwargs)

            hardened_chat_completion._is_hardened = True
            ta_cls._chat_completion = hardened_chat_completion
            installed.append("tool_agent._chat_completion_timeout_floor")

    # 2. Patch solver request_timeout_seconds
    if hasattr(solver_mod, "_HarnessGameSession"):
        sess_cls = solver_mod._HarnessGameSession
        if hasattr(sess_cls, "request_timeout_seconds"):
            orig_rto = sess_cls.request_timeout_seconds

            def hardened_rto(self):
                cand = orig_rto(self)
                min_floor = float(os.environ.get("ARC3_MIN_READ_TIMEOUT", str(_MIN_READ_TIMEOUT_DEFAULT)))
                if cand is not None:
                    return max(min_floor, float(cand))
                return min_floor

            sess_cls.request_timeout_seconds = hardened_rto
            installed.append("solver._HarnessGameSession.request_timeout_seconds_floor")

    # 3. Patch global requests.post so all tool_agent calls use hardened session + retry + floor
    orig_requests_post = requests.post
    if not getattr(orig_requests_post, "_is_hardened", False):
        def patched_post(url, *args, **kwargs):
            timeout = kwargs.pop("timeout", None)
            min_floor = float(os.environ.get("ARC3_MIN_READ_TIMEOUT", str(_MIN_READ_TIMEOUT_DEFAULT)))
            if isinstance(timeout, (tuple, list)):
                conn_to = float(timeout[0]) if len(timeout) > 0 and timeout[0] is not None else 10.0
                read_to = float(timeout[1]) if len(timeout) > 1 and timeout[1] is not None else min_floor
                effective_to: Any = (conn_to, max(min_floor, read_to))
            elif timeout is not None:
                effective_to = max(min_floor, float(timeout))
            else:
                effective_to = (10.0, min_floor)
            headers = kwargs.pop("headers", None)
            json_data = kwargs.pop("json", None)
            session = get_hardened_session()
            if args or kwargs:
                return session.post(url, *args, headers=headers, json=json_data, timeout=effective_to, **kwargs)
            return robust_post(url, headers=headers, json_data=json_data, timeout=effective_to)

        patched_post._is_hardened = True
        requests.post = patched_post
        installed.append("requests.post_hardened_session")

    msg = f"#HYPER_RESILIENCE ok: {', '.join(installed)}"
    print(msg, flush=True)
    return msg
