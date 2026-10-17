"""Original reviewed owned-process supervisor; extracted unchanged from ARC2 tooling."""
from pathlib import Path
import os, signal, subprocess, time

def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def group_members(pgid, deadline):
    """Read-only Linux observation; never signal a potentially reused group ID."""
    members = []
    for entry in Path("/proc").iterdir():
        if time.monotonic() >= deadline:
            raise TimeoutError("PROCESS_GROUP_SCAN_BUDGET_EXHAUSTED")
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == pgid:
                members.append(int(entry.name))
        except FileNotFoundError:
            continue  # Process exited during the snapshot.
    if time.monotonic() >= deadline:
        raise TimeoutError("PROCESS_GROUP_SCAN_BUDGET_EXHAUSTED")
    return members


def supervise(command, *, cwd, env, log, budget_seconds):
    """Keep the child PID reserved until every process-group signal is finished.

    One monotonic budget covers launch, execution, termination and reap checks.
    A timeout reports incomplete cleanup rather than extending the budget.
    Linux /proc observations are conservative and do not prove a sandbox boundary.
    """
    require(all(hasattr(os, name) for name in
                ("waitid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT")),
            "WAITID_WNOWAIT_REQUIRED")
    require(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL,
            "DEFAULT_SIGCHLD_HANDLER_REQUIRED")
    require(Path("/proc/self/stat").is_file(), "LINUX_PROC_REQUIRED")
    require(budget_seconds > 0, "POSITIVE_SUPERVISION_BUDGET_REQUIRED")
    started = time.monotonic()
    deadline = started + budget_seconds
    cleanup_reserve = min(5.0, budget_seconds / 2.0)
    execution_deadline = deadline - cleanup_reserve
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True)
    timed_out = False
    interrupted = False
    cleanup_error = None
    code = 125
    group_gone = False
    leader_reaped = False
    ownership_known = True
    flags = os.WEXITED | os.WNOHANG | os.WNOWAIT
    # No wait(), poll(), communicate(), or waitpid() may precede the final kill.
    try:
        while True:
            if os.waitid(os.P_PID, process.pid, flags) is not None:
                break
            remaining = execution_deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            time.sleep(min(0.05, remaining))
    except KeyboardInterrupt:
        interrupted = True
    except ChildProcessError:
        ownership_known = False
        cleanup_error = "LEADER_OWNERSHIP_LOST_NO_GROUP_SIGNAL"
    except OSError:
        cleanup_error = "WAITID_FAILED"
    # Ignore repeated terminal interrupts only during the bounded cleanup region.
    previous_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        if ownership_known:
            try:
                # Recheck ownership immediately before the FINAL group signal.
                os.waitid(os.P_PID, process.pid, flags)
                os.killpg(process.pid, signal.SIGKILL)
            except ChildProcessError:
                ownership_known = False
                cleanup_error = "LEADER_OWNERSHIP_LOST_NO_GROUP_SIGNAL"
            except ProcessLookupError:
                cleanup_error = "OWNED_GROUP_UNEXPECTEDLY_MISSING"
            except OSError:
                cleanup_error = "PROCESS_GROUP_KILL_FAILED"
        if ownership_known:
            try:
                # All group signals are now finished. Never call killpg below.
                result = process.wait(timeout=max(0.0, deadline - time.monotonic()))
                leader_reaped = True
                code = 130 if interrupted else 124 if timed_out else result
            except subprocess.TimeoutExpired:
                cleanup_error = "LEADER_NOT_REAPED_WITHIN_BUDGET"
            except OSError:
                cleanup_error = "LEADER_REAP_FAILED"
        if leader_reaped:
            try:
                while time.monotonic() < deadline:
                    remaining_members = group_members(process.pid, deadline)
                    if time.monotonic() >= deadline:
                        raise TimeoutError("PROCESS_GROUP_SCAN_BUDGET_EXHAUSTED")
                    if not remaining_members:
                        group_gone = True
                        break
                    time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
            except TimeoutError:
                cleanup_error = "PROCESS_GROUP_SCAN_BUDGET_EXHAUSTED"
            except (OSError, ValueError, IndexError):
                cleanup_error = "PROCESS_GROUP_OBSERVATION_FAILED"
        if not group_gone and cleanup_error is None:
            cleanup_error = "PROCESS_GROUP_NOT_CONFIRMED_GONE_WITHIN_BUDGET"
        if time.monotonic() > deadline:
            cleanup_error = "SUPERVISION_BUDGET_EXHAUSTED"
        if cleanup_error:
            code = 125
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
    return {"exit_code": code, "timed_out": timed_out,
            "interrupted": interrupted, "cleanup_error": cleanup_error,
            "owned_process_group_gone": group_gone,
            "leader_reaped": leader_reaped,
            "total_budget_seconds": budget_seconds,
            "cleanup_reserve_seconds": cleanup_reserve,
            "elapsed_seconds": time.monotonic() - started}
