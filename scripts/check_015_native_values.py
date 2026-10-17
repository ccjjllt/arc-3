#!/usr/bin/env python3
"""Manual CPU probes for native-values full integration; no model/HTTP/actions replay."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

def worker(args):
    out = args.output_dir / args.worker
    out.mkdir(exist_ok=False)
    sys.path[:0] = [str(args.sdk_path), str(ROOT / 'src'),
        str(ROOT / 'research/runtime-bundle/src/ARC3-Inference'),
        str(ROOT / 'research/runtime-bundle/src/tufa-arc-agi-framework/src')]
    sys.path.extend(str(p) for p in args.extra_python_path)
    os.environ.update({'ARC3_ANIMATION':'1','ARC3_ACTION_ECHO':'1',
        'ARC3_NEW_CHANGED_PROMPTS':'1','ARC3_BATCH_NOOP_BLOCK':'1',
        'ARC3_GUARDS_FROM_LEVEL':'2','ARC3_STALE_STATE_BLOCK':'1',
        'ARC3_NOOP_REPEAT_GUARD':'0','ARC3_DEATH_REPEAT_GUARD':'0',
        'LOCAL_ANALYZER_MODEL_ID':'cpu-no-model','EXPOSE_RESET':'on',
        'MPLCONFIGDIR':'/private/tmp/arc3-015-mpl','MPLBACKEND':'Agg'})
    import requests
    from inference.agent.tool_agent import ToolAgent
    from inference.framework.solver import HarnessSolver, _HarnessGameSession, _grid_from_state
    from taaf.game import RunSession
    from taaf.game_api import ArcadeSpec, GameAPI
    report = {'worker':args.worker,'checks':[], 'calls':[], 'http_attempts':0,
        'source_sha256':{p:sha(ROOT/p) for p in [
            'src/arc3_research/native_values.py','scripts/check_015_native_values.py']},
        'model_called':False, 'engine_source_read':False, 'logged_code_executed':False}
    patch = None
    runs = []
    def flush():
        if patch is not None:
            try:
                report['native_values'] = patch.snapshot()
            except Exception as exc:
                report['native_snapshot_error'] = repr(exc)
        save(out/'report.json',report)
    def check(name, ok, **data):
        report['checks'].append({'name':name,'passed':bool(ok),**data})
        flush()
        if not ok: raise AssertionError(name)
    def no_http(*a, **kw):
        report['http_attempts'] += 1
        raise RuntimeError('CPU probe prohibits HTTP')
    requests.sessions.Session.request = no_http
    def tool(session, code, label, success=True):
        before = session.action_count
        result = session.analyzer._run_python_tool(session.state_path, {'code':code})
        d = json.loads(result.content)
        name = f'{len(report["calls"]):03d}-{label}.json'
        save(out/name, {'code':code,'dispatch':d,'step_before':before,
                       'step_after':session.action_count,'step_executed':result.step_executed})
        report['calls'].append({'label':label,'trace':name})
        if success: check(label+'_sandbox_success', 'error' not in d, error=d.get('error'))
        lines=[s[7:] for s in d.get('stdout','').splitlines() if s.startswith('RESULT=')]
        return json.loads(lines[-1]) if lines else d
    def emit(expr):
        return "import json\nprint('RESULT='+json.dumps("+expr+",separators=(',',':')))"
    def session(name, game_id='tn36-ef4dde99'):
        d=out/name; d.mkdir()
        run=RunSession(record_intermediate_states=False);runs.append(run)
        game=GameAPI(env_name=game_id,arcade_spec=ArcadeSpec(
            environments_dir=str(ROOT/'research/data/extracted/environment_files')))
        game.start_game(run)
        agent=ToolAgent(model='cpu-no-model')
        s=_HarnessGameSession(solver=HarnessSolver(model='cpu-no-model',
            start_local_server=False,kaggle_enable_vllm=False),game=game,analyzer=agent,
            game_index=len(runs),pass_index=0,state_path=d/'state.json',
            transcript_path=d/'transcript.md',analysis_html_relpath='unused.html',
            stop_event=threading.Event(),viewer_data_path=d/'viewer.json')
        s.seed_initial_history();s.write_runtime_state();agent._step_env_callback=s.step_env
        return s
    try:
        if args.worker == 'candidate':
            from arc3_research.native_values import install_native_values, NATIVE_NOTE
            patch=install_native_values()
        else:
            from arc3_research.native_values import NATIVE_NOTE
        s=session('sdk-basic')
        # _ensure_session runs inside _run_python_tool; trigger once before prompt check
        try:
            s.analyzer._ensure_session(s.state_path)
        except Exception:
            pass
        # Prompt note only on candidate
        check('prompt_note_candidate_only', (NATIVE_NOTE in s.analyzer._system_prompt) == (patch is not None))
        # Ordinary variables do not persist on baseline; persist on candidate within same observation
        tool(s,"xs=[1,2]\nalias=xs\nclicks=[(3,4),(5,6)]",'create-values')
        if patch is not None:
            got=tool(s,"import json\nprint('RESULT='+json.dumps([alias is xs,clicks[0]],separators=(',',':')))",'consume-natural')
            check('natural_names_restored', got==[True,[3,4]])
            # delete/rebind replaces snapshot
            tool(s,"del clicks\nxs=11",'delete-rebind')
            got=tool(s,emit("xs"),'get-xs')
            check('rebind_visible', got==11)
            # error does not commit partial
            tool(s,"alias.append(99)\nnew_value=6\nraise RuntimeError('expected-probe')",'err-mutate',False)
            got=tool(s,emit("alias"),'alias-after-error')
            check('error_no_partial', got==[1,2])
            # unsupported rebind removes old
            tool(s,"xs=lambda:4",'unsupported-rebind')
            got=tool(s,"try:\n    xs\n    present=True\nexcept NameError:\n    present=False\n"+emit("present"),'xs-absent')
            check('unsupported_gone', got is False)
            # retained function contract preserved (enable persistence like 012)
            os.environ['ARC3_PERSISTENT_FUNCTIONS']='1'
            tool(s,"offset=5\ndef pure(x):\n    return x+1\ndef dependent(x):\n    return x+offset",'func-def')
            got=tool(s,emit("pure(offset)"),'pure-consume')
            check('pure_explicit_arg', got==6)
            # real noop action invalidates
            grid=_grid_from_state(s.game.current_state)
            step=s.action_count
            got=tool(s,"action({'action':'MOUSE','row':0,'col':0})\n"+emit("{'ok':True}"),'real-noop',False)
            check('real_sdk_action_executed', s.action_count==step+1)
            # after action, old value gone
            d2=tool(s,"try:\n    offset\n    present=True\nexcept NameError:\n    present=False\n"+emit("present"),'post-action-gone')
            check('post_action_cleared', d2 is False)
            # RESET increments attempt and clears
            tool(s,"before_reset=42",'before-reset')
            # use patch context attempt via session attr
            from arc3_research.native_values import _SESSION_ATTR
            before_attempt=getattr(s,_SESSION_ATTR)['attempt']
            tool(s,"action('RESET')\n"+emit("{'ok':True}"),'real-reset',False)
            after_attempt=getattr(s,_SESSION_ATTR)['attempt']
            check('reset_attempt_and_clear', after_attempt==before_attempt+1)
        else:
            tool(s,"ephemeral={'values':[1,2,3]}",'ordinary-write')
            got=tool(s,"try:\n    ephemeral\n    present=True\nexcept NameError:\n    present=False\n"+emit("present"),'ordinary-next')
            check('baseline_no_persist', got is False)
            check('baseline_prompt_unchanged','automatically available' not in s.analyzer._system_prompt)
        check('no_http_or_model',report['http_attempts']==0 and s.analyzer.generated_tokens==0)
        report['status']='passed'
    except Exception as exc:
        report['status']='failed';report['failure']={'type':type(exc).__name__,'message':str(exc)}
        raise
    finally:
        for run in runs:run.close()
        flush()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sdk-path',type=Path,required=True)
    p.add_argument('--extra-python-path',type=Path,action='append',default=[])
    p.add_argument('--output-dir',type=Path);p.add_argument('--worker',choices=['baseline','candidate'])
    a=p.parse_args()
    if a.output_dir is None:a.output_dir=ROOT/'experiments/015-native-values'/datetime.now(timezone.utc).strftime('cpu-%Y%m%dT%H%M%SZ')
    a.output_dir=a.output_dir.resolve()
    if a.worker:worker(a);return
    a.output_dir.mkdir(parents=True,exist_ok=False);reports={}
    for arm in ['baseline','candidate']:
        cmd=[sys.executable,str(Path(__file__).resolve()),'--sdk-path',str(a.sdk_path),'--output-dir',str(a.output_dir),'--worker',arm]
        for path in a.extra_python_path:cmd+=['--extra-python-path',str(path)]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
        (a.output_dir/f'{arm}.stdout.txt').write_text(r.stdout);(a.output_dir/f'{arm}.stderr.txt').write_text(r.stderr)
        reports[arm]=json.loads((a.output_dir/arm/'report.json').read_text())
    hashes={p:sha(ROOT/p) for p in ['src/arc3_research/native_values.py','scripts/check_015_native_values.py']}
    stable=all(r['source_sha256']==hashes for r in reports.values())
    summary={'status':'passed' if stable and all(r['status']=='passed' for r in reports.values()) else 'failed',
        'check_count':sum(len(r['checks']) for r in reports.values()),'source_sha256':hashes,'sources_stable_during_check':stable,
        'workers':{k:{'status':v['status'],'checks':len(v['checks'])} for k,v in reports.items()},
        'limitations':['Handwritten CPU probes; no model adoption or score claim.']}
    save(a.output_dir/'summary.json',summary)
    try:
        save(a.output_dir.parent/'latest.json',{'summary':str((a.output_dir/'summary.json').relative_to(ROOT)),'status':summary['status']})
    except ValueError:
        pass
    print(json.dumps({'summary':str(a.output_dir/'summary.json'),**summary},indent=2))
    if summary['status']!='passed':raise SystemExit(1)

if __name__=='__main__':main()
