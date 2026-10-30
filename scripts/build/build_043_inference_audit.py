"""Build one inference-audit candidate on frozen 042; no remote operations."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import copy
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'notebooks/042-startup-ready/submission.ipynb'
BASE_SHA = '7e7920ff6f74b4206d617ed46443bf4f2d30978a1261d6fbfd66625adfc98ee9'
HELPER = ROOT / 'src/arc3_research/inference_audit.py'
PUBLIC = ROOT / 'research/snapshots/2026-10-30-candidates/ondrewsha__arc-agi-3-stack-s9/source.ipynb'
OUT = ROOT / 'notebooks/043-inference-audit'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(cell):
    value = cell['source']
    return ''.join(value) if isinstance(value, list) else value


def code(text):
    return dict(cell_type='code', source=text.splitlines(keepends=True), metadata={},
                outputs=[], execution_count=None)


SAVE_BUDGET = '''
# 043 save-only resource bound. Formal startup remains90min and platform9h.
if not TRUE_SUBMISSION:
    import signal
    import threading
    SERVER_STARTUP_TIMEOUT = 45 * 60
    ARC3_SAVE_DONE = threading.Event()
    def _arc3_save_watchdog():
        remaining = max(0.0, 80 * 60 - (time.time() - NOTEBOOK_START_TIME))
        if ARC3_SAVE_DONE.wait(remaining):
            return
        (WORKING_DIR / 'save-budget-failure.json').write_text(
            json.dumps({'status': 'failed', 'reason': '80min_save_limit'}) + '\\n')
        owned = globals().get('proc')
        if owned is not None and owned.poll() is None:
            try:
                os.killpg(owned.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        os._exit(124)
    threading.Thread(target=_arc3_save_watchdog, daemon=True).start()
'''

INSTALL = '''# 043: only H3v2.1; no HF, RESETC, memory or scheduler layer.
import importlib.util
_audit_path = Path('/kaggle/inference_audit.py')
_audit_spec = importlib.util.spec_from_file_location('arc3_043_inference_audit', _audit_path)
ARC3_AUDIT_MODULE = importlib.util.module_from_spec(_audit_spec)
_audit_spec.loader.exec_module(ARC3_AUDIT_MODULE)
import inference.agent.tool_agent as _audit_agent
assert os.environ.get('ARC3_YIELD_RESUME_PROMPT', 'full').strip().lower() == 'full'
ARC3_AUDIT_ORIGINAL = ARC3_AUDIT_MODULE.install_inference_audit(_audit_agent.ToolAgent)
ARC3_AUDIT_INSTALL = {
    'experiment': '043', 'active': True, 'base': '042',
    'helper_sha256': __import__('hashlib').sha256(_audit_path.read_bytes()).hexdigest(),
    'level_tokens': ARC3_AUDIT_MODULE.H3V2_LEVEL_TOKENS,
    'stagnation_tokens': ARC3_AUDIT_MODULE.H3V2_STAGNATION_TOKENS,
    'impossible_count': ARC3_AUDIT_MODULE.H3V2_IMPOSSIBLE_COUNT,
    'min_gap_tokens': ARC3_AUDIT_MODULE.H3V2_MIN_GAP_TOKENS,
    'max_per_level': ARC3_AUDIT_MODULE.H3V2_MAX_PER_LEVEL,
    'formal': TRUE_SUBMISSION,
}
assert [ARC3_AUDIT_INSTALL[k] for k in ('level_tokens', 'stagnation_tokens',
    'impossible_count', 'min_gap_tokens', 'max_per_level')] == [30000, 20000, 3, 12000, 2]
(WORKING_DIR / 'inference-audit-install.json').write_text(json.dumps(ARC3_AUDIT_INSTALL, indent=2) + '\\n')
print('043 inference audit installed:', ARC3_AUDIT_INSTALL, flush=True)
if not TRUE_SUBMISSION:
    # Observe exact prompts without changing them; formal uses the same H3 wrapper directly.
    import threading
    ARC3_AUDIT_EVENTS = []
    _audit_events_lock = threading.Lock()
    _audit_prompt_builder = _audit_agent.ToolAgent._build_user_prompt
    def _audit_observed_prompt(agent, *args, **kwargs):
        before = getattr(agent, '_h3v2_audits', 0)
        prompt = _audit_prompt_builder(agent, *args, **kwargs)
        after = getattr(agent, '_h3v2_audits', 0)
        if after > before:
            frame = kwargs.get('current_frame')
            event = {
                'wall_time': time.time(), 'agent_id': id(agent),
                'action_num': args[0] if args else kwargs.get('action_num'),
                'step': getattr(frame, 'step', None), 'level': getattr(frame, 'level', None),
                'session_tokens': getattr(agent, '_session_generated_tokens', None),
                'level_start_tokens': getattr(agent, '_tokens_at_level_start', None),
                'audit_number': after,
                'text': prompt[prompt.rfind(ARC3_AUDIT_MODULE.H3V2_MARKER):],
            }
            with _audit_events_lock:
                ARC3_AUDIT_EVENTS.append(event)
                with (WORKING_DIR / 'inference-audit-events.jsonl').open('a') as audit_file:
                    audit_file.write(json.dumps(event) + '\\n')
        return prompt
    _audit_agent.ToolAgent._build_user_prompt = _audit_observed_prompt
'''

SAVE_CHECK = '''
if not TRUE_SUBMISSION:
    # A functioning save is necessary, but does not establish score improvement.
    _saved_benchmark = json.loads((WORKING_DIR / 'benchmark.json').read_text())
    _saved_games = _saved_benchmark['game_runs']
    _checks = {
        'ten_games': len(_saved_games) == 10,
        'one_pass': _saved_benchmark['n_passes'] == 1,
        'terminal': all(g['state'] in ('won', 'gave_up') for g in _saved_games),
        'real_actions': all(any(h['action']['id'] != 'RESET' for h in g['history']) for g in _saved_games),
        'real_generation': all(sum(h.get('generated_tokens', 0) for h in g['history']) > 0 for g in _saved_games),
        'audit_actually_triggered': len(ARC3_AUDIT_EVENTS) > 0,
        'audit_prompts_present': all(e['text'].startswith(ARC3_AUDIT_MODULE.H3V2_MARKER) for e in ARC3_AUDIT_EVENTS),
        'model_ready': json.loads((WORKING_DIR / 'startup-readiness.json').read_text())['status'] == 'ready',
    }
    (WORKING_DIR / 'inference-audit-save-check.json').write_text(json.dumps({
        'checks': _checks, 'passed': all(_checks.values()),
        'audit_events': len(ARC3_AUDIT_EVENTS),
        'claim': 'Execution and actual prompt intervention only; not a paired score comparison.'
    }, indent=2) + '\\n')
    assert all(_checks.values()), _checks
'''


def main():
    assert sha(BASE) == BASE_SHA
    base = json.loads(BASE.read_text())
    nb = copy.deepcopy(base)
    assert len(nb['cells']) == 23
    original_h3 = source(json.loads(PUBLIC.read_text())['cells'][20])
    helper = HELPER.read_text()
    # Module packaging may change comments/entry point only; functional AST is identical.
    def body(text):
        return [x for x in ast.parse(text).body if not
                (isinstance(x, ast.If) and '__name__' in ast.unparse(x.test)) and not
                (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant) and isinstance(x.value.value, str))]
    assert ast.dump(ast.Module(body=body(helper), type_ignores=[])) == ast.dump(ast.Module(body=body(original_h3), type_ignores=[]))
    nb['cells'][0]['source'] = (source(base['cells'][0]) + '\n\n043 adds only ondrewsha Stack S9 H3v2.1 inference audit. '
        'Franzen/Tufa upstream attribution is retained. The S9 author-reported32.16 is for the whole stack, '
        'not this isolated layer. Our best official score remains31.16. Save runs10publicgames25min, '
        'with45min readiness/80min total limits; formal retains90min readiness and9h platform budget.\n').splitlines(keepends=True)
    nb['cells'][4]['source'] = (source(base['cells'][4]) + SAVE_BUDGET).splitlines(keepends=True)
    run = source(base['cells'][20])
    anchor = 'if not TRUE_SUBMISSION:\n    # An offline run isn\'t scored'
    assert run.count(anchor) == 1
    run = run.replace(anchor, SAVE_CHECK + '\n' + anchor, 1)
    run += '\nif not TRUE_SUBMISSION:\n    ARC3_SAVE_DONE.set()\n'
    nb['cells'][20]['source'] = run.splitlines(keepends=True)
    nb['cells'][17:17] = [code('%%writefile /kaggle/inference_audit.py\n' + helper), code(INSTALL)]
    for cell in nb['cells']:
        cell['metadata'] = {}
        if cell['cell_type'] == 'code':
            cell['execution_count'] = None
            cell['outputs'] = []
    restored = copy.deepcopy(nb)
    del restored['cells'][17:19]
    changed = [i for i, (a, b) in enumerate(zip(base['cells'], restored['cells'])) if source(a) != source(b)]
    assert changed == [0, 4, 20]
    assert source(restored['cells'][12]) == source(base['cells'][12])
    assert source(restored['cells'][16]) == source(base['cells'][16])
    compiled = []
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] != 'code':
            continue
        text = source(cell)
        if text.startswith('%%writefile '):
            header, text = text.split('\n', 1)
            if header.endswith('.patch'):
                continue
        text = '\n'.join('pass # original shell magic' if line.lstrip().startswith('!') else line for line in text.splitlines())
        compile(text, f'<043-cell-{i}>', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        compiled.append(i)
    metadata = json.loads(BASE.with_name('kernel-metadata.json').read_text())
    metadata.update(id='jiyujia/arc3-043-inference-audit', title='ARC3 043 Inference Audit')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'submission.ipynb').write_text(json.dumps(nb, indent=1) + '\n')
    (OUT/'kernel-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    inputs = [BASE, BASE.with_name('kernel-metadata.json'), HELPER, PUBLIC, Path(__file__).resolve(),
              ROOT/'scripts/checks/check_043_inference_audit.py', ROOT/'experiments/043-preparation/inference-audit-cpu.json']
    manifest = dict(prepared_at_utc=datetime.now(timezone.utc).isoformat(), kernel_ref=metadata['id'],
        notebook_sha256=sha(OUT/'submission.ipynb'), bytes=(OUT/'submission.ipynb').stat().st_size,
        cell_count=len(nb['cells']), base_sha256=BASE_SHA, helper_sha256=sha(HELPER),
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}, changed_base_cells=changed,
        inserted_cells=[17,18], only_solver_intervention='S9_H3v2.1_inference_audit',
        functional_h3_ast_identical=True, original_formal_config_preserved=True,
        original_model_server_launcher_preserved=True, source_input_versions_and_image_preserved=True,
        formal_startup_seconds=5400, formal_platform_timeout_seconds=32400,
        save_startup_seconds=2700, save_total_seconds=4800, save_per_game_seconds=1500,
        save_game_count=10, compiled_cells=compiled, status='BUILT_NOT_PUSHED_OR_SUBMITTED',
        score_improvement_claim=False)
    assert manifest['bytes'] < 1_000_000
    (OUT/'build-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
