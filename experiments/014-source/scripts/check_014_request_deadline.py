#!/usr/bin/env python3
"""Manual CPU checks of real ToolAgent/session/gate with synthetic transport.

No model, GPU, game engine, or logged Python is run. Invoke with an SDK path and
the same extra package paths used by earlier local harness checks.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import MethodType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-path', type=Path, required=True)
    parser.add_argument('--extra-python-path', type=Path, action='append', default=[])
    parser.add_argument('--output-dir', type=Path, default=ROOT/'experiments/014-deadline-checks')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(args.sdk_path), str(ROOT/'src'),
        str(ROOT/'research/runtime-bundle/src/ARC3-Inference'),
        str(ROOT/'research/runtime-bundle/src/tufa-arc-agi-framework/src')]
    sys.path.extend(str(p) for p in args.extra_python_path)
    os.environ.update(ARC3_HTTP_RETRIES='0', ARC3_HTTP_RETRY_INITIAL_SECONDS='0',
        ARC3_HTTP_RETRY_BASE_SECONDS='0', ARC3_HTTP_RETRY_MAX_SECONDS='0',
        ARC3_PRIORITY_REFRESH_QUEUE='0', ARC3_PRIORITY_PACE='0', ARC3_PRIORITY_TAIL_FADE='0',
        ARC3_MEMORY_SECTIONS='off', ARC3_WARMUP_ACTION_GAMES='0', OPENROUTER_STREAM='true',
        MPLCONFIGDIR='/private/tmp/arc3-014-mpl', MPLBACKEND='Agg')
    import requests
    import arcengine
    from inference.agent import tool_agent as ta
    from inference.framework import solver as sm
    from arc3_research.request_deadline import (install_request_deadline,
        RequestDeadlineCheckFailed, RequestDeadlineReached)
    from arc3_research.inference_timing import install_inference_timing

    paths = ['src/arc3_research/request_deadline.py','scripts/check_014_request_deadline.py',
             'research/runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py',
             'research/runtime-bundle/src/ARC3-Inference/inference/framework/solver.py']
    sha = lambda p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    report = {'created_at_utc':datetime.now(timezone.utc).isoformat(), 'status':'running',
              'python':sys.executable, 'python_version':sys.version, 'argv':sys.argv,
              'source_sha256':{p:sha(p) for p in paths}, 'checks':[],
              'boundary':'Actual ToolAgent chat/analyze, Session.play/_play_inner and PriorityGate; synthetic grid/session game and controlled transport. No engine actions or models.'}
    patch = None
    wire, responses = [], []
    state = {'transport':None,'failures':0,'exception':requests.ConnectionError('synthetic-connect-error')}
    real_session_request = requests.sessions.Session.request
    real_post = requests.post
    original_ta_gate, original_sm_gate = ta._priority_gate, sm._priority_gate
    gate_holder = {'gate':None}
    ta._priority_gate = lambda:gate_holder['gate']
    sm._priority_gate = lambda:gate_holder['gate']
    session_counter = 0

    def save():
        if patch is not None:
            report['deadline_snapshot'] = patch.snapshot()
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

    def check(name, passed, **details):
        report['checks'].append({'name':name,'passed':bool(passed),**details})
        save()
        if not passed:
            raise AssertionError(name)

    def deny_real_network(*a, **kw):
        raise AssertionError('Real network forbidden by CPU deadline check')

    class Response:
        status_code = 200
        text = ''
        def __init__(self):
            self.json_reads = self.stream_reads = 0
        def raise_for_status(self):
            return None
        def json(self):
            self.json_reads += 1
            return {'choices':[{'message':{'role':'assistant','content':'synthetic ok'},'finish_reason':'stop'}],
                    'usage':{'completion_tokens':7,'total_tokens':12}}
        def iter_lines(self,decode_unicode=False):
            self.stream_reads += 1
            yield b'data: {"choices":[{"index":0,"delta":{"role":"assistant","content":"synthetic ok"},"finish_reason":null}]}'
            yield b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"completion_tokens":7,"total_tokens":12}}'
            yield b'data: [DONE]'

    def fake_post(*a, **kw):
        # Keep synthetic headers only; never serialize a real user's credentials.
        wire.append({'url':a[0], 'payload':json.loads(json.dumps(kw['json'])),
                     'timeout':kw['timeout'],'stream':kw['stream']})
        if state['transport'] is not None:
            return state['transport'](*a,**kw)
        if state['failures']:
            state['failures'] -= 1
            raise state['exception']
        r=Response();responses.append(r);return r

    requests.sessions.Session.request = deny_real_network
    requests.post = fake_post
    messages = [{'role':'user','content':'synthetic CPU only'}]

    def request(agent):
        return agent._chat_completion(messages,tools=None,request_timeout_seconds=12.5,max_tokens=9)

    def make_session(label, body=None, *, streaming=False, use_gate=True):
        nonlocal session_counter
        session_counter += 1
        directory=out/f'{session_counter:02d}-{label}';directory.mkdir(exist_ok=True)
        agent=ta.ToolAgent(model='cpu-no-model',provider='openrouter' if streaming else 'vllm',
                           base_url='http://cpu.invalid/v1',api_key='synthetic-not-secret')
        agent._tool_steps=1
        run=SimpleNamespace(game_id=label,state='playing',history=[],solver_note=None,final_score=None,
                            solver_analysis_html=None)
        game=SimpleNamespace(game_run=run,number_of_levels=6,
            current_state=SimpleNamespace(frame=SimpleNamespace(data=[[0]*8 for _ in range(8)]),
                levels_completed=0,won=False,available_actions=[1],raw=SimpleNamespace(state=arcengine.GameState.NOT_FINISHED)))
        finish=[]
        def finish_game():
            finish.append(run.state);run.final_score=0
        game.finish_game=finish_game
        clock={'remaining':100.0}
        solver=SimpleNamespace(max_runtime_s_per_game=None,max_actions_per_game=None,
            max_generated_tokens_per_game=None,soft_time_remaining_seconds=lambda:clock['remaining'],
            _claim_warmup_slot=lambda:False,job_dir=None)
        s=sm._HarnessGameSession(solver=solver,game=game,analyzer=agent,game_index=session_counter,
            pass_index=0,state_path=directory/'state.json',transcript_path=directory/'transcript.md',
            analysis_html_relpath='unused.html',stop_event=threading.Event(),viewer_data_path=directory/'viewer.json')
        # Synthetic viewer only. Keep real state writer, analyze, play, stop and cleanup.
        s._append_initial_viewer_event=lambda:None
        s._append_analysis_viewer_event=lambda *a:None
        s.write_viewer_payload=lambda:None
        s._write_analysis_html=lambda:None
        if body is not None:
            s._play_inner=MethodType(lambda self:body(self),s)
        gate_holder['gate']=ta._PriorityGate(1) if use_gate else None
        return s, clock, finish, gate_holder['gate']

    try:
        agent=ta.ToolAgent(model='cpu-no-model',provider='vllm',base_url='http://cpu.invalid/v1',api_key='synthetic-not-secret')
        baseline=request(agent);baseline_wire=wire[-1]
        patch=install_request_deadline(max_events=32)
        check('idempotent_install',install_request_deadline(max_events=32) is patch)
        check('global_requests_module_unchanged',requests.post is fake_post)
        check('request_exception_types_passthrough',ta.requests.RequestException is requests.RequestException)
        raw_chat=patch._original_chat;identities=[]
        def spy(agent,*a,**kw):
            value=raw_chat(agent,*a,**kw);identities.append(value);return value
        patch._original_chat=spy
        got=[]
        s,c,f,g=make_session('before-deadline',lambda s:got.append(request(s.analyzer)))
        s.play()
        check('before_deadline_payload_timeout_unchanged',wire[-1]==baseline_wire)
        check('before_deadline_original_return_identity',got[-1] is identities[-1])
        check('json_consumed_once_by_original',responses[-1].json_reads==1 and responses[-1].stream_reads==0)
        check('normal_slot_release_once',g._free==1 and not g._waiting and not g._admitted)
        s,c,f,g=make_session('stream',lambda s:got.append(request(s.analyzer)),streaming=True)
        s.play();check('stream_original_consumes_once',responses[-1].stream_reads==1 and responses[-1].json_reads==0)
        # Calls with no Session.play scope retain exact original behavior.
        before=len(wire);request(agent);check('outside_session_passthrough',len(wire)==before+1)

        for reason in ['soft','cancel']:
            s,c,f,g=make_session('entry-'+reason,lambda s:request(s.analyzer))
            if reason=='soft':c['remaining']=0
            else:s.stop_event.set()
            before=len(wire);ret=s.play()
            check('chat_entry_'+reason+'_zero_http',len(wire)==before and ret is None and s.game.game_run.state=='cancelled')
            check('chat_entry_'+reason+'_slot_release',g._free==1 and not g._waiting)

        s,c,f,g=make_session('known-stop-clock-fault',lambda s:request(s.analyzer))
        s.stop_event.set()
        def bad_secondary_clock():raise RuntimeError('secondary clock must not mask cancellation')
        s.solver.soft_time_remaining_seconds=bad_secondary_clock
        # Original play configures the gate's clock first; disable that unrelated
        # setup here to isolate stop precedence at the request boundary.
        gate_holder['gate']=None
        before=len(wire);s.play()
        check('known_stop_precedes_secondary_clock_failure',len(wire)==before and s.game.game_run.state=='cancelled')

        # Deadline moves during original request construction, after chat-entry check.
        s,c,f,g=make_session('payload-expiry',lambda s:request(s.analyzer))
        orig_headers=s.analyzer._headers
        def expire_headers():
            result=orig_headers();c['remaining']=0;return result
        s.analyzer._headers=expire_headers
        before=len(wire);s.play()
        check('http_entry_rechecks_after_payload_build',len(wire)==before and s.game.game_run.state=='cancelled')

        # Retry is original; only a new attempt after deadline is prevented.
        os.environ['ARC3_HTTP_RETRIES']='1'
        s,c,f,g=make_session('retry-expiry',lambda s:request(s.analyzer))
        def fail_and_expire(*a,**kw):
            c['remaining']=0;raise requests.ConnectionError('synthetic-first-attempt')
        state['transport']=fail_and_expire
        before=len(wire);s.play();state['transport']=None
        check('retry_after_deadline_not_sent',len(wire)==before+1 and g._free==1)
        s,c,f,g=make_session('retry-before',lambda s:got.append(request(s.analyzer)))
        state['failures']=1;before=len(wire);s.play()
        check('before_deadline_original_retry_count',len(wire)==before+2)
        os.environ['ARC3_HTTP_RETRIES']='0'

        # Original transport failures propagate unchanged when not handled by analyze.
        s,c,f,g=make_session('exception-identity',lambda s:request(s.analyzer))
        state['failures']=1
        try:s.play()
        except requests.ConnectionError as exc:check('original_transport_exception_identity',exc is state['exception'])
        else:raise AssertionError('expected original error')
        check('exception_slot_release',g._free==1)

        # A broken authoritative check must prevent transmission and remain loud.
        s,c,f,g=make_session('failed-check',lambda s:request(s.analyzer))
        sentinel=RuntimeError('controlled-stop-check-failure')
        def broken():raise sentinel
        s.should_stop=broken;before=len(wire)
        try:s.play()
        except RequestDeadlineCheckFailed as exc:check('check_failure_preserves_cause_and_no_send',exc.__cause__ is sentinel and len(wire)==before)
        else:raise AssertionError('expected check failure')
        check('check_failure_releases_slot',g._free==1)
        s,c,f,g=make_session('foreign-cancel',lambda s:request(s.analyzer))
        foreign=RequestDeadlineReached(object(),'foreign')
        def foreign_stop():raise foreign
        s.should_stop=foreign_stop
        try:s.play()
        except RequestDeadlineReached as exc:check('foreign_cancel_not_swallowed',exc is foreign)
        else:raise AssertionError('expected foreign cancellation')
        check('foreign_cancel_releases_slot',g._free==1)

        # Real gate wait: B takes the released slot, expires A, then releases.
        entered=threading.Event();queued=threading.Event();errors=[];order=[]
        def body_a(s):
            entered.set()
            if not queued.wait(3):raise AssertionError('B did not enqueue')
            s.analyzer._context_was_trimmed=True
            s.analyzer._last_step_summary={'level':1,'end_action_num':0}
            s.analyzer._maybe_handover()
            request(s.analyzer)
        s,c,f,g=make_session('real-handover-expiry',body_a)
        def competitor():
            try:
                if not entered.wait(3):raise AssertionError('A did not enter')
                # Notify A only after B's real heap entry is observable.
                g.acquire(99999999);order.append('B');c['remaining']=0;g.release()
            except BaseException as exc:errors.append(repr(exc))
        def run_a():
            try:s.play();order.append('A-ended')
            except BaseException as exc:errors.append(repr(exc))
        before=len(wire);t1=threading.Thread(target=run_a);t2=threading.Thread(target=competitor)
        t1.start();t2.start()
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            with g._cond:pending=bool(g._waiting)
            if pending:queued.set();break
            time.sleep(.001)
        t1.join(3);t2.join(3)
        check('real_handover_late_wakeup_zero_http',not errors and len(wire)==before and order==['B','A-ended'],errors=errors,order=order)
        check('real_handover_no_duplicate_release',g._free==1 and not g._waiting and not g._admitted and not t1.is_alive() and not t2.is_alive())

        # Full original play -> _play_inner -> analyze; handover expires mid-call.
        s,c,f,g=make_session('full-analyze-handover')
        original_handover=g.handover
        def expire_handover(*a,**kw):
            value=original_handover(*a,**kw);c['remaining']=0;return value
        g.handover=expire_handover
        s.analyzer._context_was_trimmed=True
        before=len(wire);s.play()
        check('full_analyze_cancel_not_crashed_or_retryable',len(wire)==before and s.game.game_run.state=='cancelled'
              and s.game.game_run.solver_note.startswith('tokens='),note=s.game.game_run.solver_note)
        check('full_analyze_original_finally_cleanup',g._free==1 and len(f)==1 and not s.state_path.exists()
              and s.analyzer._step_env_callback is None and s.analyzer._current_valid_actions==[])

        # Summary hook occurs before analyze's inner try/finally in this harness.
        s,c,f,g=make_session('early-summary-cancel')
        def early_summary(*a,**kw):
            c['remaining']=0;request(s.analyzer)
        s.analyzer._maybe_append_rolling_summary=early_summary
        before=len(wire);s.play()
        check('early_summary_zero_send_and_cleanup',len(wire)==before and g._free==1 and len(f)==1
              and s.analyzer._step_env_callback is None and s.analyzer._current_valid_actions==[])

        # Already admitted responses remain original: no retroactive discard.
        s,c,f,g=make_session('inflight-finish',lambda s:got.append(request(s.analyzer)))
        def complete_after_deadline(*a,**kw):
            c['remaining']=0;r=Response();responses.append(r);return r
        state['transport']=complete_after_deadline;before=len(wire);s.play();state['transport']=None
        check('inflight_result_not_discarded',len(wire)==before+1 and got[-1] is identities[-1])

        # Telemetry cannot suppress a stop if recording itself fails.
        # _record's own implementation is fail-open; exercise its clock call.
        original_time=__import__('arc3_research.request_deadline',fromlist=['time']).time
        deadline_module=__import__('arc3_research.request_deadline',fromlist=['time'])
        deadline_module.time=SimpleNamespace(monotonic=lambda:(_ for _ in ()).throw(RuntimeError('clock fault')))
        s,c,f,g=make_session('diagnostic-clock-fault',lambda s:request(s.analyzer));c['remaining']=0
        before=len(wire);s.play();deadline_module.time=original_time
        check('diagnostic_failure_does_not_suppress_cancel',len(wire)==before and g._free==1 and s.game.game_run.state=='cancelled')

        # Production composition order: deadline, then timing observer.
        observer=install_inference_timing(max_sessions=4,max_events_per_session=64)
        s,c,f,g=make_session('timing-composition',lambda s:got.append(request(s.analyzer)))
        s.play()
        s,c,f,g=make_session('timing-cancel',lambda s:request(s.analyzer));c['remaining']=0
        before=len(wire);s.play();snap=observer.snapshot()
        check('timing_composition_returns_and_cancels',len(wire)==before and g._free==1
              and not snap['provisional'] and snap['sessions_recorded']==2)
        try:patch.uninstall()
        except RuntimeError:check('uninstall_refuses_overwriting_later_hooks',True)
        else:raise AssertionError('expected uninstall-order refusal')
        observer.uninstall()
        report['timing_snapshot']=snap

        snapshot=patch.snapshot()
        check('bounded_events_and_no_active_sessions',len(snapshot['events'])<=32 and snapshot['events_dropped']>0
              and snapshot['active_sessions']==0)
        check('all_three_boundaries_blocked_in_probes',all(snapshot['boundary_counts'].get('request_blocked:'+b,0)>0
              for b in ['after_handover','chat_entry','http_entry']))

        # CPU-only bound on hook overhead; fake response path, not serving speed.
        iterations=500;durations=[]
        def many(session):
            started=time.perf_counter()
            for _ in range(iterations):request(session.analyzer)
            durations.append(time.perf_counter()-started)
        s,c,f,g=make_session('microbenchmark-guarded',many);s.play()
        guarded_seconds=durations[-1]
        patch.uninstall()
        check('uninstall_restores_originals',ta.ToolAgent._chat_completion is patch._original_chat
              and sm._HarnessGameSession.play is patch._original_play and ta.requests is patch._original_requests)
        # _original_chat was the return-identity spy; restore the real source after checking.
        ta.ToolAgent._chat_completion=raw_chat
        s,c,f,g=make_session('microbenchmark-control',many);s.play()
        control_seconds=durations[-1]
        report['microbenchmark']={'iterations':iterations,'guarded_seconds':guarded_seconds,
            'control_seconds':control_seconds,'delta_microseconds_per_request':1e6*(guarded_seconds-control_seconds)/iterations,
            'boundary':'Synthetic payload/JSON response loop; guarded side also appends result-identity spy. No real transport/model/GPU.'}
        check('source_files_unchanged_during_probe',all(sha(p)==h for p,h in report['source_sha256'].items()))
        report['status']='passed';report['transport_calls']=len(wire)
        report['limitations']=['No real serving/network latency or resource-pressure run.',
            'A race remains between final client check and actual socket send; server arrival after deadline is not ruled out.',
            'Existing in-flight generations and their timeouts are unchanged.',
            'Viewer/game are synthetic; real play/analyze/gate code paths execute, no game engine actions.']
        save()
        print(json.dumps({'status':report['status'],'checks':len(report['checks']),'output':str(out/'report.json'),
                          'source_sha256':report['source_sha256']},indent=2))
    except BaseException as exc:
        report['status']='failed';report['failure']={'type':type(exc).__name__,'message':str(exc)};save();raise
    finally:
        requests.sessions.Session.request=real_session_request
        requests.post=real_post
        ta._priority_gate=original_ta_gate;sm._priority_gate=original_sm_gate


if __name__=='__main__':
    main()
