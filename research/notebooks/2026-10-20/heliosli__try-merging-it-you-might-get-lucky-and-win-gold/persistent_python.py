"""One isolated Python interpreter per game level, with the original tool IPC.

Only model-created Python objects persist. The host still supplies every real
frame/action result. No game code, files, network, or scoring metadata is added
to the model namespace. A timeout kills this interpreter; actions are never
replayed. Safe function sources remain the fallback for the next level.
"""
from __future__ import annotations
import atexit
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import weakref

from inference.agent.python_tool_sandbox import (
    _SANDBOX_BOOTSTRAP, _sandbox_env, _send_json_line,
    _kill_process_group, _wait_for_process_exit, _sanitize_host_error_text,
)
from inference.utils.grid_utils import ARC_COLOR_CHARS


def _replace(source, before, after):
    if source.count(before) != 1:
        raise RuntimeError('Persistent Python bootstrap no longer matches pinned source: '+before[:60])
    return source.replace(before,after,1)


def bootstrap():
    source = _SANDBOX_BOOTSTRAP
    # The host retains the original per-call wall timeout. A cumulative hard
    # RLIMIT_CPU of 31 seconds would incorrectly kill a reused interpreter.
    source = _replace(source,
        '        (getattr(resource, "RLIMIT_CPU", None), cpu_limit),',
        '        (getattr(resource, "RLIMIT_AS", None), 1024 * 1024 * 1024),')
    source = _replace(source,'def main():\n', '_LIVE_GLOBALS = None\n_BASE_NAMES = None\n_LIVE_FUNCTION_CODES = {}\n\ndef main():\n    global _LIVE_GLOBALS, _BASE_NAMES\n')
    source = _replace(source,
        "if name in previous and value.__code__.co_filename == '<retained>':",
        "if name in previous and (value.__code__.co_filename == '<retained>' or _LIVE_FUNCTION_CODES.get(name) is value.__code__):")
    source = _replace(source,
        '                **_retention_options)\n            return {\n                "keepable_functions":',
        '                **_retention_options)\n'
        '            _LIVE_FUNCTION_CODES.clear()\n'
        '            _LIVE_FUNCTION_CODES.update({n: runtime_globals[n].__code__ for n in kept})\n'
        '            return {\n                "keepable_functions":')
    source = _replace(source,'    runtime_globals = {\n',
        '    _was_live = _LIVE_GLOBALS is not None\n    _fresh_globals = {\n')
    source = _replace(source,'    runtime_globals["__builtins__"]["__import__"] = _safe_import',
        '    runtime_globals = _LIVE_GLOBALS if _was_live else {}\n'
        '    runtime_globals.update(_fresh_globals)\n'
        '    _LIVE_GLOBALS = runtime_globals\n'
        '    runtime_globals["__builtins__"]["__import__"] = _safe_import')
    source = _replace(source,
        '    _available_names = set(runtime_globals) | set(runtime_globals["__builtins__"])\n    if _persistence_enabled:',
        '    if _BASE_NAMES is None:\n        _BASE_NAMES = set(runtime_globals)\n'
        '    _available_names = set(_BASE_NAMES) | set(runtime_globals["__builtins__"])\n'
        '    if _persistence_enabled and _was_live:\n'
        '        for _src in initial.get("kept_functions") or []:\n'
        '            try:\n                _name, _source, _reads = _function_record(_src, retain_imports=True)\n'
        '            except Exception:\n                continue\n'
        '            _kept_pool[_name] = _source\n'
        '    if _persistence_enabled and not _was_live:')
    # Both the success and exception replies contain this payload. This
    # bookkeeping only reads dictionary keys and cannot depend on a user
    # binding such as current_frame, which may have been overwritten.
    source = _replace(source,'    def _collect_retention_payload():\n',
        '    def _collect_safe_functions():\n')
    source = _replace(source,'    try:\n        _code_text = str(initial.get("code", ""))',
        '    def _collect_retention_payload():\n'
        '        payload = _collect_safe_functions()\n'
        '        try:\n'
        '            names = sorted(k for k in runtime_globals if isinstance(k, str) and k not in _BASE_NAMES and not k.startswith("__"))\n'
        '            payload["live_names"] = names[:80]\n'
        '            payload["live_name_count"] = len(names)\n'
        '        except Exception:\n'
        '            payload["live_names"] = []\n'
        '        return payload\n\n'
        '    try:\n        _code_text = str(initial.get("code", ""))')
    source = _replace(source,'if __name__ == "__main__":\n    main()',
        'if __name__ == "__main__":\n    while True:\n        main()')
    compile(source,'<persistent-bootstrap>','exec')
    return source


_WORKERS = weakref.WeakSet()


class LevelPython:
    def __init__(self):
        self.process = None
        self.directory = None
        self.messages = None
        self.scope = None
        self.names = []
        self.restarts = 0
        _WORKERS.add(self)

    def close(self):
        process,self.process = self.process,None
        if process is not None:
            if process.poll() is None:
                if os.name == 'nt':
                    process.kill()
                else:
                    _kill_process_group(process)
            _wait_for_process_exit(process)
            for handle in (process.stdin,process.stdout,process.stderr):
                if handle:
                    handle.close()
        directory,self.directory = self.directory,None
        if directory is not None:
            directory.cleanup()
        self.names=[]

    def _start(self,scope):
        self.close()
        self.scope=scope
        self.directory=tempfile.TemporaryDirectory(prefix='arc3_level_python_')
        path=Path(self.directory.name)/'worker.py'
        path.write_text(bootstrap(),encoding='utf-8')
        self.process=subprocess.Popen([sys.executable,'-I','-S',str(path)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,encoding='utf-8',cwd=self.directory.name,
            env=_sandbox_env(),start_new_session=True)
        self.messages=queue.Queue()
        process,messages=self.process,self.messages
        def reader():
            try:
                for line in process.stdout:
                    messages.put(line)
            finally:
                messages.put(None)
        threading.Thread(target=reader,daemon=True).start()

    def run(self,*,scope,code,timeout_seconds,initial_state,action_handler,
            animation_handler=None,kept_functions=None,retain_imports=False,repair_hints=False):
        level=(initial_state.get('current_frame') or {}).get('level')
        key=(str(scope),level)
        lost=False
        if self.process is None or self.process.poll() is not None or self.scope != key:
            lost=self.scope==key
            self.restarts += int(lost)
            self._start(key)
        process=self.process
        host_actions=[]
        def failed(message):
            self.close()
            return dict(error=message+' Python variables for this level were cleared; rebuild needed state. Executed actions were kept and will not be replayed.',
                        stdout='',action_results=list(host_actions),live_names=[],python_state_lost=True)
        try:
            _send_json_line(process.stdin,dict(code=code,kept_functions=list(kept_functions or []),
                persistence_enabled=kept_functions is not None,retain_imports=retain_imports,
                repair_hints=repair_hints,animation_enabled=animation_handler is not None,
                timeout_seconds=timeout_seconds,sandbox_cwd=self.directory.name,
                state=initial_state,color_chars=ARC_COLOR_CHARS))
        except (OSError,ValueError):
            return failed('Python worker stopped before this call was sent.')
        deadline=time.monotonic()+max(1,int(timeout_seconds))
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:
                return failed(f'Tool timed out after {timeout_seconds}s.')
            try:
                line=self.messages.get(timeout=remaining)
            except queue.Empty:
                continue
            if line is None:
                detail=_sanitize_host_error_text(process.stderr.read())
                return failed(detail)
            try:
                message=json.loads(line)
            except (ValueError,TypeError):
                return failed('Sandbox process returned an invalid response.')
            kind=message.get('type')
            if kind=='animation':
                try:
                    if animation_handler is None:
                        raise RuntimeError('Animation unavailable')
                    value=animation_handler(dict(message.get('request') or {}))
                    _send_json_line(process.stdin,dict(type='animation_result',animation=value))
                except Exception:
                    _send_json_line(process.stdin,dict(type='animation_error',error='animation failed in sandbox host.'))
            elif kind=='action':
                try:
                    value=action_handler(list(message.get('actions') or []),stale_after=message.get('stale_after'))
                    action=value.get('action_result') or {}
                    if isinstance(action,dict):host_actions.append(dict(action))
                    _send_json_line(process.stdin,dict(type='action_result',action_result=action,state=value.get('state') or {}))
                except Exception:
                    _send_json_line(process.stdin,dict(type='action_error',error='action failed in sandbox host.'))
            elif kind in {'final','error'}:
                self.names=list(message.get('live_names') or [])
                return dict(stdout=str(message.get('stdout','') or ''),result=message.get('result'),
                    error=str(message.get('error','') or ''),action_results=list(message.get('action_results') or host_actions),
                    keepable_functions=list(message.get('keepable_functions') or []),
                    retention_rejected=message.get('retention_rejected') or [],
                    live_names=self.names,live_name_count=message.get('live_name_count',len(self.names)),python_state_lost=lost)
            else:
                return failed('Sandbox process returned an unknown message type.')


def run_for_agent(agent,state_path,**kwargs):
    worker=getattr(agent,'_level_python_worker',None)
    if worker is None:
        worker=agent._level_python_worker=LevelPython()
    return worker.run(scope=state_path.parent,**kwargs)


def close_agent(agent):
    worker=getattr(agent,'_level_python_worker',None)
    if worker is not None:
        worker.close()
        agent._level_python_worker=None


@atexit.register
def close_workers():
    for worker in list(_WORKERS):
        worker.close()
