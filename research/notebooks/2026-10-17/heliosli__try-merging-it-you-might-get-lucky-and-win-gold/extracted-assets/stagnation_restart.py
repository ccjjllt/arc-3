"""One fresh reasoning context after a very expensive unfinished level.

Only observed level progress and actual generated tokens are used. The game,
action history, death ledger, model sampling and accounting are untouched.
"""
import logging

LEVEL_TOKEN_LIMIT = 96 * 1024
log = logging.getLogger(__name__)


def maybe_restart(agent, frame):
    if frame is None or int(frame.level) <= 0:
        return ""
    level = int(frame.level)
    generated = int(agent._session_generated_tokens)
    pending = getattr(agent, "_stagnation_pending_notice", None)
    if pending is not None:
        pending_level, at_tokens, notice = pending
        if pending_level == level and generated <= at_tokens:
            # A failed HTTP request must not lose the explanatory fresh opener.
            agent._resume_after_yield = False
            agent._resume_reason = ""
            return notice
        agent._stagnation_pending_notice = None
    seen = getattr(agent, "_stagnation_restarted_levels", set())
    if level in seen or (agent._last_step_summary or {}).get("run_complete"):
        return ""
    spent = max(0, generated - int(agent._tokens_at_level_start))
    if spent < LEVEL_TOKEN_LIMIT:
        return ""

    # Run only between analyzer invocations, after outstanding tool calls finish.
    # The next request is a complete current-board opener, never a yield resume
    # asking the model to continue reasoning that is no longer in its context.
    old_messages = len(agent._history_messages)
    agent._history_messages = []
    agent._kept_functions = {}
    agent._retained_clear_notice = ""
    agent._resume_after_yield = False
    agent._resume_reason = ""
    agent._text_chars_per_token = None
    agent._note_history_evicted()
    agent._stagnation_restarted_levels = seen | {level}
    notice = (
        f"Fresh review of the current level: {spent} tokens of earlier reasoning "
        "have not completed this level. That reasoning and retained Python functions "
        "have been cleared once to reconsider the problem from its observations. "
        "No game action or game reset was performed by this context change: the "
        "current board, completed levels, remaining action budget, and recorded "
        "history are unchanged. Python history, transitions and death_ledger still "
        "contain the actual observations. Re-establish what counts as success and "
        "what the controls do from the board and those observations; treat earlier "
        "interpretations as hypotheses. Check a concrete prediction with a safe "
        "action before committing to another long search.\n\n"
    )
    agent._stagnation_pending_notice = (level, generated, notice)
    log.warning("stagnation_context_restart level=%d step=%d tokens=%d old_messages=%d",
                level, int(frame.step), spent, old_messages)
    return notice
