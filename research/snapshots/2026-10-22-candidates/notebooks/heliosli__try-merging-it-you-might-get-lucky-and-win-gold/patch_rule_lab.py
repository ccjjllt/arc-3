"""Attach rule experiments and checked action execution to the pinned original."""
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent


def replace(source, old, new):
    if source.count(old)!=1:
        raise RuntimeError('Pinned source anchor mismatch: '+old[:100])
    return source.replace(old,new,1)


def patch(root):
    root=Path(root)
    path=root/'inference/agent/tool_agent.py'
    source=path.read_text(encoding='utf-8')
    if '# EXECUTABLE_RULE_LAB' in source:
        return
    data=source.encode()
    if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!='84a9cdda9c851ea2dcf3eea9f0b3158d437bea16':
        raise RuntimeError('Expected exact original actor before rule-lab patch')
    source=replace(source,'        if self._session_runtime_dir != runtime_dir:\n',
        '        if self._session_runtime_dir != runtime_dir:\n'
        '            prior_rule_lab = getattr(self, "_rule_lab_state", None)\n'
        '            if prior_rule_lab is not None and prior_rule_lab.worker is not None:\n'
        '                prior_rule_lab.worker.close()\n'
        '            self._rule_lab_state = None\n')
    source=replace(source,'        ]\n\n    def _harness_template_kwargs(self)',
        '        ] + [__import__("inference.agent.rule_lab", fromlist=["TOOL"]).TOOL]\n\n    def _harness_template_kwargs(self)')
    source=replace(source,'        sandbox_result = run_sandboxed_python(\n',
        '        # EXECUTABLE_RULE_LAB\n'
        '        from inference.agent.rule_lab import guarded_actions\n'
        '        sandbox_result = run_sandboxed_python(\n')
    source=replace(source,'            action_handler=_handle_action,\n',
        '            action_handler=guarded_actions(self, state_path, _handle_action),\n')
    source=replace(source,'                (remaining or [(action_name, action_data)])\n',
        '                (getattr(self, "_rule_lab_guard_remaining", None) or remaining or [(action_name, action_data)])\n')
    source=replace(source,'            self._guard_death_override_batch = False\n',
        '            if not getattr(self, "_rule_lab_continue_guard", False):\n'
        '                self._guard_death_override_batch = False\n')
    source=replace(source,'        payload: dict[str, Any] = {"tool": "python"}\n',
        '        payload: dict[str, Any] = {"tool": "python"}\n'
        '        rule_checks = [item["rule_feedback"] for item in action_results if item.get("rule_feedback")]\n'
        '        if rule_checks:\n'
        '            payload["rule_checks"] = rule_checks\n')
    source=replace(source,'        if name == "python":\n            return self._run_python_tool(state_path, arguments)\n',
        '        if name == "rule_lab":\n'
        '            from inference.agent.rule_lab import dispatch\n'
        '            return dispatch(self, state_path, arguments)\n'
        '        if name == "python":\n            return self._run_python_tool(state_path, arguments)\n')
    source=replace(source,'        tokens_at_turn_start = self._session_generated_tokens\n',
        '        tokens_at_turn_start = self._session_generated_tokens\n        rule_notice_injected = False\n')
    source=replace(source,'                self._maybe_handover()\n                latest_request_messages = json.loads(json.dumps(messages))',
        '                self._maybe_handover()\n'
        '                from inference.agent.rule_lab import notice\n'
        '                rule_notice = notice(self, state_path)\n'
        '                if rule_notice and not rule_notice_injected:\n'
        '                    rule_notice_injected = True\n'
        '                    self._append_context_message(messages, {"role": "user", "content": rule_notice})\n'
        '                    append_transcript("RULE EXPERIMENT", rule_notice)\n'
        '                    messages = self._trim_messages_for_context(messages, tools=tools)\n'
        '                latest_request_messages = json.loads(json.dumps(messages))')
    source=replace(source,'                self._history_messages = self._persistent_history_messages(messages, tools=self._tools(state_path))\n',
        '                self._history_messages = self._persistent_history_messages(messages, tools=self._tools(state_path))\n'
        '                if rule_notice_injected:\n'
        '                    from inference.agent.rule_lab import acknowledge\n'
        '                    acknowledge(self, state_path)\n')
    compile(source,str(path),'exec')
    path.write_text(source,encoding='utf-8')
    path=root/'inference/agent/python_tool_sandbox.py'
    source=path.read_text(encoding='utf-8')
    source=replace(source,'        class TerminalStateActionError(BaseException):\n',
        '        class RuleCorrectionRequired(BaseException):\n'
        '            pass  # The real action happened; remaining model-based actions must be reconsidered.\n\n'
        '        class TerminalStateActionError(BaseException):\n')
    source=replace(source,'            _refresh_state(reply.get("state") or {})\n',
        '            _refresh_state(reply.get("state") or {})\n'
        '            if action_result.get("rule_interrupt"):\n'
        '                raise RuleCorrectionRequired(str(action_result.get("stop_detail") or "Inspect the real rule counterexample."))\n')
    source=replace(source,'            KnownNoOpActionError,\n            RepeatedActionInStateError,\n',
        '            RuleCorrectionRequired,\n            KnownNoOpActionError,\n            RepeatedActionInStateError,\n')
    compile(source,str(path),'exec')
    path.write_text(source,encoding='utf-8')
    for name in ('rule_lab.py','rule_lab_eval.py','rule_lab_python.py'):
        (root/'inference/agent'/name).write_text((ROOT/name).read_text(encoding='utf-8'),encoding='utf-8')
    print('PATCHED_RULE_LAB')


if __name__=='__main__':
    patch(Path(sys.argv[1]))
