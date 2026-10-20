"""Apply the level interpreter to the pinned original harness, fail on drift."""
import hashlib
import ast
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent

def replace(source,before,after):
    if source.count(before)!=1:raise RuntimeError('Patch context mismatch: '+before[:100])
    return source.replace(before,after,1)

def patch(root):
    path=root/'inference/agent/tool_agent.py';source=path.read_text(encoding='utf-8')
    marker='# V6_LEVEL_PYTHON'
    if marker in source:return
    original=hashlib.sha1(b'blob '+str(len(source.encode())).encode()+b'\0'+source.encode()).hexdigest()
    if original!='84a9cdda9c851ea2dcf3eea9f0b3158d437bea16':raise RuntimeError('Expected original tool agent')
    source=replace(source,'        sandbox_result = run_sandboxed_python(\n',
        '        # V6_LEVEL_PYTHON\n'
        '        from inference.agent.persistent_python import run_for_agent\n'
        '        sandbox_result = run_for_agent(self, state_path,\n')
    # Retain the conservative original safe function pool for new levels, but
    # do not tell the model that other live definitions disappeared mid-level.
    source=replace(source,'        self._record_retained_functions(sandbox_result, payload)\n',
        '        self._record_retained_functions(sandbox_result, payload)\n'
        '        payload.pop("function_retention", None)\n'
        '        payload["python_state"] = {"scope": "current level", "name_count": sandbox_result.get("live_name_count", 0), "lost": bool(sandbox_result.get("python_state_lost"))}\n')
    source=replace(source,'            notice = getattr(self, "_retained_clear_notice", "")\n',
        '            worker = getattr(self, "_level_python_worker", None)\n'
        '            level = (self._last_step_summary or {}).get("level")\n'
        '            if worker is not None and worker.process is not None and worker.scope[1] == level:\n'
        '                return "\\n\\nPython names retained on this level: " + ", ".join(worker.names[:40]) + ". Cached board data must be checked against current_frame after actions."\n'
        '            notice = getattr(self, "_retained_clear_notice", "")\n')
    # One concise semantics change in each original prompt variant.
    source=source.replace('Python variables reset between tool calls.',
        'Python variables and imports persist between tool calls on the same level; they are cleared on a new level or after a tool timeout. Re-read the refreshed current_frame after actions before using cached board-specific values.')
    source=source.replace('Run one ephemeral Python snippet','Run one Python snippet in the current level session')
    source=source.replace('Python code to run. The snippet is ephemeral and is not saved across tool calls.',
        'Python code to run. Variables, functions and imports persist within the current level.')
    source=replace(source,'        runtime_dir = state_path.parent\n        if self._session_runtime_dir != runtime_dir:\n',
        '        runtime_dir = state_path.parent\n        if self._session_runtime_dir != runtime_dir:\n'
        '            from inference.agent.persistent_python import close_agent\n            close_agent(self)\n')
    compile(source,str(path),'exec');path.write_text(source,encoding='utf-8')
    (root/'inference/agent/persistent_python.py').write_text((ROOT/'persistent_python.py').read_text(encoding='utf-8'),encoding='utf-8')
    path=root/'inference/agent/prompts.py';source=path.read_text(encoding='utf-8')
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PERSISTENT_FUNCTIONS_LINE' for t in n.targets))
    lines=source.splitlines(True)
    guidance=(
        '- Variables, functions, imports, search queues and computed plans persist across Python calls within the current level. Reuse them directly instead of rebuilding them.\n'
        '- A new level clears ordinary variables and imports. Only self-contained function definitions with supported imports may carry across levels; the next turn lists them. Reinitialize board-specific data from the new frame.\n'
        '- current_frame, previous_frame, history and action results are refreshed by the runtime; your other cached variables are not automatically updated after actions. Check them against current_frame before acting.\n'
        '- A tool timeout or process failure clears Python variables, but does not undo actions already executed. The error will report this.\n')
    source=''.join(lines[:node.lineno-1])+ 'PERSISTENT_FUNCTIONS_LINE = '+repr(guidance)+'\n'+''.join(lines[node.end_lineno:])
    source=source.replace('one ephemeral `code` string','one `code` string')
    compile(source,str(path),'exec');path.write_text(source,encoding='utf-8')
    path=root/'inference/framework/solver.py';source=path.read_text(encoding='utf-8')
    source=replace(source,'        finally:\n            if gate is not None:\n                gate.release()\n',
        '        finally:\n            from inference.agent.persistent_python import close_agent\n'
        '            try:\n                close_agent(self.analyzer)\n'
        '            finally:\n                if gate is not None:\n                    gate.release()\n')
    compile(source,str(path),'exec');path.write_text(source,encoding='utf-8')
    print('PATCHED_LEVEL_PYTHON')

if __name__=='__main__':patch(Path(sys.argv[1]))
