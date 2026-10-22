#!/usr/bin/env python3
"""Manual CPU probes of the actual SDK/ToolAgent/sandbox, with no model calls."""
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

ROOT = Path(__file__).resolve().parents[2]

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
        'MPLCONFIGDIR':'/private/tmp/arc3-012-mpl','MPLBACKEND':'Agg'})
    import requests
    from inference.agent.tool_agent import ToolAgent
    from inference.framework.solver import HarnessSolver, _HarnessGameSession, _grid_from_state
    from taaf.game import RunSession
    from taaf.game_api import ArcadeSpec, GameAPI
    report = {'worker':args.worker,'checks':[], 'calls':[], 'http_attempts':0,
        'source_sha256':{p:sha(ROOT/p) for p in [
            'src/arc3_research/current_data.py','scripts/checks/check_012_current_data.py']},
        'model_called':False, 'engine_source_read':False, 'logged_code_executed':False}
    patch = None
    runs = []
    def flush():
        if patch is not None:
            report['current_data'] = patch.snapshot()
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
        if label=='real-noop-invalidate': check('sdk_reports_executed_gameplay_noop','NO-OP (executed' in d.get('stdout',''))
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
            from arc3_research.current_data import install_current_data
            patch=install_current_data()
        s=session('sdk-noop-reset')
        got=tool(s,"try:\n    current_data\n    cd=True\nexcept NameError:\n    cd=False\ntry:\n    animation_at\n    ar=True\nexcept NameError:\n    ar=False\n"+emit("{'current_data':cd,'archive':ar}"),'visibility')
        check('candidate_only_api_no010',got=={'current_data':patch is not None,'archive':False})
        tool(s,"ephemeral={'values':[1,2,3]}",'ordinary-variable-write')
        got=tool(s,"try:\n    ephemeral\n    present=True\nexcept NameError:\n    present=False\n"+emit("present"),'ordinary-variable-next-snippet')
        check('ordinary_variables_still_not_persistent',got is False)
        if patch is not None:
            before=s.state_path.read_bytes();step=s.action_count
            p=tool(s,"v={'nested':[1,True,None,{'text':'数据','v':1.25}]}\na=current_data.context()['context']\nr=current_data.put('v',v,at=a)\nv['nested'][0]=999\n"+emit('r'),'put-copy')
            check('stored_ack_no_value',p['status']=='stored' and 'value' not in p)
            got=tool(s,"r=current_data.get('v')\nr['value']['nested'][0]=888\n"+emit("current_data.get('v')"),'get-copy')
            check('exact_copy_without_alias',got['status']=='current' and got['value']['nested']==[1,True,None,{'text':'数据','v':1.25}])
            check('queries_do_not_mutate_state',s.state_path.read_bytes()==before and s.action_count==step)
            got=tool(s,emit("current_data.put('v',float('nan'))"),'reject-nan')
            check('reject_preserves_valid',got['status']=='rejected' and tool(s,emit("current_data.get('v')['value']['nested'][0]"),'valid-after-reject')==1)
            os.environ['ARC3_PERSISTENT_FUNCTIONS']='1'
            tool(s,"def stored_number():\n    return current_data.get('v')['value']['nested'][0]",'retained-definition')
            check('retained_function_can_read',tool(s,emit('stored_number()'),'retained-next')==1)
            other=session('independent-sdk')
            got=tool(other,emit("current_data.get('v')"),'cross-session')
            check('independent_session_no_value',got['status']=='missing' and 'value' not in got)
            # Handwritten background click: gameplay no-op; HUD pixels may still change.
            grid=_grid_from_state(s.game.current_state)
            got=tool(s,"at=current_data.context()['context']\naction({'action':'MOUSE','row':0,'col':0})\n"+emit("{'get':current_data.get('v'),'pinned':current_data.put('v',7,at=at),'at':current_data.context()['context']}"),'real-noop-invalidate')
            check('real_sdk_action_executed',s.action_count==step+1, settled_grid_unchanged=_grid_from_state(s.game.current_state)==grid)
            check('noop_stale_no_payload',got['get']['status']=='stale' and 'value' not in got['get'])
            check('pinned_old_write_refused',got['pinned']['status']=='stale_context')
            tool(s,emit("current_data.put('v',{'x':3})"),'put-before-reset')
            previous=got['at']
            got=tool(s,"action('RESET')\n"+emit("{'v':current_data.get('v'),'at':current_data.context()['context']}"),'real-reset')
            check('reset_stale_and_attempt',got['v']['status']=='stale' and 'value' not in got['v'] and got['at']['attempt']==previous['attempt']+1)
            tool(s,"r=current_data.put('ack_error',[4,5])\nassert r['status']=='stored'\nraise RuntimeError('intentional-probe')",'put-then-error',False)
            check('ack_survives_snippet_error',tool(s,emit("current_data.get('ack_error')['value']"),'get-after-error')==[4,5])
            old=s.analyzer._python_timeout;s.analyzer._python_timeout=0.5
            timeout=tool(s,"r=current_data.put('ack_timeout',[6,7])\nassert r['status']=='stored'\ncurrent_data.put('after_ack_marker',True)\nwhile True:\n    pass",'put-then-timeout',False)
            s.analyzer._python_timeout=old
            timeout_error=str(timeout.get('error','')).lower()
            check('actual_sandbox_timeout',('timed out' in timeout_error or 'timeout' in timeout_error), dispatch=timeout)
            check('first_ack_received_before_timeout',tool(s,emit("current_data.get('after_ack_marker')['value']"),'after-ack-marker') is True)
            check('timeout_ack_commit_survives',tool(s,emit("current_data.get('ack_timeout')['value']"),'get-after-timeout')==[6,7], dispatch=timeout)
            # Replay only four ordinary public actions from an already saved baseline;
            # no logged Python, solver or game implementation is executed.
            ft=session('sdk-level-transition','ft09-0d8bbf25')
            b=json.loads((ROOT/'runs/011-animation-confirmation/baseline/benchmark.json').read_text())
            g=next(x for x in b['game_runs'] if x['game_id'].startswith('ft09-'))
            report['level_probe_action_source']='runs/011-animation-confirmation/baseline/benchmark.json'
            report['level_probe_action_source_sha256']=sha(ROOT/report['level_probe_action_source'])
            for index,entry in enumerate(g['history'][:4]):
                a=entry['action'];assert a['id']=='ACTION6'
                body="current_data.put('before_level', {'marker':1})\n" if index==3 else ''
                body+=f"action({{'action':'MOUSE','row':{a['data']['y']},'col':{a['data']['x']}}})\n"
                tool(ft,body,f'level-action-{index+1}')
            got=tool(ft,emit("{'v':current_data.get('before_level'),'at':current_data.context()['context']}"),'after-real-level')
            check('real_level_completed',ft.game.current_state.levels_completed==1 and got['at']['level']==2)
            check('level_change_stale_no_value',got['v']['status']=='stale' and 'value' not in got['v'])
        else:
            check('baseline_not_installed',not hasattr(ToolAgent,'_research_current_data_patch'))
            check('baseline_prompt_unchanged','current_data' not in s.analyzer._system_prompt)
        os.environ['ARC3_ANIMATION']='0'
        got=tool(s,"try:\n    last_animation_frames\n    fr=True\nexcept NameError:\n    fr=False\ntry:\n    last_animation_timeline\n    tl=True\nexcept NameError:\n    tl=False\ntry:\n    current_data\n    cd=True\nexcept NameError:\n    cd=False\n"+emit("{'frames':fr,'timeline':tl,'current_data':cd}"),'latest-disabled')
        check('latest_disabled_preserved',got=={'frames':False,'timeline':False,'current_data':patch is not None})
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
    if a.output_dir is None:a.output_dir=ROOT/'experiments/012-current-data'/datetime.now(timezone.utc).strftime('cpu-%Y%m%dT%H%M%SZ')
    a.output_dir=a.output_dir.resolve()
    if a.worker:worker(a);return
    a.output_dir.mkdir(parents=True,exist_ok=False);reports={}
    for arm in ['baseline','candidate']:
        cmd=[sys.executable,str(Path(__file__).resolve()),'--sdk-path',str(a.sdk_path),'--output-dir',str(a.output_dir),'--worker',arm]
        for path in a.extra_python_path:cmd+=['--extra-python-path',str(path)]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
        (a.output_dir/f'{arm}.stdout.txt').write_text(r.stdout);(a.output_dir/f'{arm}.stderr.txt').write_text(r.stderr)
        reports[arm]=json.loads((a.output_dir/arm/'report.json').read_text())
    hashes={p:sha(ROOT/p) for p in ['src/arc3_research/current_data.py','scripts/checks/check_012_current_data.py']}
    stable=all(r['source_sha256']==hashes for r in reports.values())
    summary={'status':'passed' if stable and all(r['status']=='passed' for r in reports.values()) else 'failed',
        'check_count':sum(len(r['checks']) for r in reports.values()),'source_sha256':hashes,'sources_stable_during_check':stable,
        'workers':{k:{'status':v['status'],'checks':len(v['checks'])} for k,v in reports.items()},
        'limitations':['Handwritten CPU delivery probes; no model adoption or score claim.','No production concurrency pressure or real fatal auto-reset sequence.','Local aliases already returned to Python do not auto-invalidate.']}
    save(a.output_dir/'summary.json',summary);save(a.output_dir.parent/'latest.json',{'summary':str((a.output_dir/'summary.json').relative_to(ROOT)),'status':summary['status']})
    print(json.dumps({'summary':str(a.output_dir/'summary.json'),**summary},indent=2))
    if summary['status']!='passed':raise SystemExit(1)

if __name__=='__main__':main()
