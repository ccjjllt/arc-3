#!/usr/bin/env python3
"""Exercise real owned-process-group cleanup with handwritten CPU sleepers.

No GPU, model, network, game, or historical model code is used. Every process
group targeted by this probe is created here with start_new_session=True.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from arc3_research import session_runner


WORKER = r'''
import json,os,signal,sys,time
ignore = sys.argv[1] == 'ignore'
if ignore: signal.signal(signal.SIGTERM,signal.SIG_IGN)
print(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp(),'ignores_term':ignore}),flush=True)
time.sleep(60)
'''

LEADER = r'''
import json,os,signal,subprocess,sys,time
mode,ignore,worker_source=sys.argv[1:]
child=subprocess.Popen([sys.executable,'-u','-c',worker_source,ignore],
                       stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
worker=json.loads(child.stdout.readline())
if ignore == 'ignore':
    signal.signal(signal.SIGTERM,signal.SIG_IGN)
else:
    def terminate(signum,frame):
        try: child.wait(timeout=1)
        except subprocess.TimeoutExpired: pass
        raise SystemExit(0)
    signal.signal(signal.SIGTERM,terminate)
print(json.dumps({'leader':os.getpid(),'pgid':os.getpgrp(),'worker':worker,'mode':mode}),flush=True)
if mode == 'orphan': raise SystemExit(0)
time.sleep(60)
'''


def main():
    report_path=ROOT/'experiments/014-cleanup-checks.json'
    sources=['src/arc3_research/session_runner.py','scripts/check_014_cleanup.py']
    source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    report={'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'running',
            'python':sys.executable,'python_version':sys.version,'source_sha256':source_hashes,
            'checks':[],'scenarios':[],
            'boundary':'Actual os.killpg/subprocesses and real stop_group. Artificial CPU-only sleeper descendants, no GPU or network.'}
    owned=[]
    known_clean=set()
    real_killpg=os.killpg
    signal_audit=[]
    def audit(event,args):
        if event=='os.killpg' and args[1]:
            signal_audit.append({'pgid':args[0],'signal':int(args[1])})
    sys.addaudithook(audit)

    def save():
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(report,indent=2)+'\n')

    def check(name,passed,**details):
        report['checks'].append({'name':name,'passed':bool(passed),**details});save()
        if not passed:raise AssertionError(name)

    def exists(pgid):
        try:real_killpg(pgid,0);return True
        except ProcessLookupError:return False

    def read_ready(process):
        ready,_,_=select.select([process.stdout],[],[],5)
        if not ready:raise RuntimeError('Synthetic child did not become ready')
        line=process.stdout.readline()
        if not line:raise RuntimeError('Synthetic child exited without ready metadata')
        return json.loads(line)

    def launch(mode,ignore):
        process=subprocess.Popen([sys.executable,'-u','-c',LEADER,mode,'ignore' if ignore else 'normal',WORKER],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        owned.append(process)
        return process,read_ready(process)

    try:
        outsider=subprocess.Popen([sys.executable,'-u','-c',WORKER,'normal'],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        owned.append(outsider);outside=read_ready(outsider)
        check('unrelated_control_group_owned_separately',outside['pgid']==outsider.pid and outsider.pid!=os.getpgrp())

        for mode,ignore in [('live',False),('orphan',False),('orphan',True),('live',True)]:
            name=mode+('_ignores_term' if ignore else '_accepts_term')
            process,ready=launch(mode,ignore)
            check(name+'_isolated_same_group',ready['pgid']==process.pid==ready['worker']['pgid']
                  and process.pid!=os.getpgrp())
            check(name+'_worker_handler_ready',ready['worker']['ignores_term'] is ignore)
            if mode=='orphan':
                process.wait(timeout=5)
                check(name+'_leader_dead_descendant_group_alive',process.poll()==0 and exists(process.pid))
            else:
                check(name+'_leader_alive_before_cleanup',process.poll() is None)
            report['active_scenario']={'name':name,'ready':ready};save()
            signal_start=len(signal_audit)
            started=time.monotonic()
            result=session_runner.stop_group(process,grace=.2)
            if result is True:known_clean.add(process.pid)
            signals=signal_audit[signal_start:]
            elapsed=time.monotonic()-started
            row={'name':name,'ready':ready,'leader_returncode':process.returncode,'stop_group_return':result,
                 'elapsed_seconds':elapsed,'signals':signals,'group_exists_after':exists(process.pid)}
            report['scenarios'].append(row);save()
            check(name+'_entire_group_removed',result is True and not row['group_exists_after'])
            check(name+'_only_owned_group_targeted',all(s['pgid']==process.pid for s in signals))
            check(name+'_term_attempted',any(s['signal']==signal.SIGTERM for s in signals))
            if ignore:
                check(name+'_kill_escalation',any(s['signal']==signal.SIGKILL for s in signals))
            check(name+'_bounded_cleanup',elapsed<5)
            check(name+'_leader_reaped',process.poll() is not None)
            signals_before_repeat=len(signal_audit)
            check(name+'_repeat_cleanup_idempotent',session_runner.stop_group(process,grace=.01) is True)
            check(name+'_verified_repeat_sends_no_signal',len(signal_audit)==signals_before_repeat
                  and getattr(process,'_stopped_group_verified',False) is True)
            check(name+'_unrelated_control_survives',outsider.poll() is None and exists(outsider.pid))

        completed=subprocess.Popen([sys.executable,'-c','pass'],start_new_session=True,
                                    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        owned.append(completed);completed.wait(timeout=5)
        check('already_exited_empty_group_returns_true',session_runner.stop_group(completed,grace=.1) is True)
        known_clean.add(completed.pid)
        check('control_group_cleanup',session_runner.stop_group(outsider,grace=.2) is True and not exists(outsider.pid))
        known_clean.add(outsider.pid)
        check('source_unchanged_during_probe',all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                                                for p,h in source_hashes.items()))
        report.pop('active_scenario',None)
        report['status']='passed';save()
        print(json.dumps({'status':'passed','checks':len(report['checks']),'report':str(report_path),
                          'source_sha256':source_hashes},indent=2))
    except BaseException as exc:
        report.update(status='failed',failure={'type':type(exc).__name__,'message':str(exc)})
        save();raise
    finally:
        # Independent last-resort cleanup for every group created by this script.
        cleanup_errors=[]
        for process in owned:
            process.poll()
            if process.pid not in known_clean:
                try:real_killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                except PermissionError as exc:cleanup_errors.append({'pgid':process.pid,'error':str(exc)})
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
            for pipe in (process.stdout,process.stderr):
                if pipe is not None:pipe.close()
        if cleanup_errors:
            report['probe_finally_cleanup_errors']=cleanup_errors
            save()


if __name__=='__main__':
    main()
