#!/usr/bin/env python3
"""016 score/scheduler audit and selected 015/016 static trajectory extraction.

Reads JSON, parses Python AST/symbol tables, never executes logged model code.
Writes derived evidence only to experiments/016-analysis.
"""
from __future__ import annotations
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics
import symtable

from analyze_005_results import audit_timing
from analyze_011_results import aggregate, score_run
from analyze_011_timing import arm_report, utc
from analyze_014_timing import deadline_report, scheduler_report

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'runs/016-pace-allocation-jiyujia'
OUT = ROOT / 'experiments/016-analysis'
ARMS = ('baseline', 'pace_1x')
SELECTED = ('r11l', 'm0r0', 'tr87', 'sc25', 'su15')

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value): p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def origin(p): return {'path':str(p.relative_to(ROOT)), 'sha256':sha(p), 'bytes':p.stat().st_size}

def extract(p):
    calls, results, order, requests, trim = {}, {}, [], 0, []
    no_tools, seen_no_tools, recovery_events = [], set(), []
    previous_response, previous_recovery_count = None, 0
    prev_count = 0
    for line_no, text in enumerate(p.open(), 1):
        o = json.loads(text); messages = o.get('messages', [])
        if o.get('event') == 'request':
            requests += 1
            if len(messages) < prev_count: trim.append({'line':line_no, 'action':o.get('action')})
            prev_count = len(messages)
            recovery_count=sum('You have not acted yet' in str(m) for m in messages)
            if recovery_count>previous_recovery_count:
                recovery_events.append({'line':line_no,'action':o.get('action'),
                    'new_prompt_count':recovery_count-previous_recovery_count})
            previous_recovery_count=recovery_count
            for m in messages:
                if m.get('role')!='assistant' or m.get('tool_calls'):continue
                signature=json.dumps(m,sort_keys=True)
                if signature in seen_no_tools:continue
                seen_no_tools.add(signature)
                no_tools.append({'first_line':line_no,'action':o.get('action'),
                    'prior_response_finish_reason':(previous_response or {}).get('finish_reason'),
                    'prior_response_usage':(previous_response or {}).get('usage'),
                    'content':m.get('content'),'reasoning':m.get('reasoning_content')})
        elif o.get('event')=='response':previous_response=o
        for m in messages:
            for tc in m.get('tool_calls') or []:
                tid = tc.get('id'); fn = tc.get('function', {})
                if not tid or tid in calls or fn.get('name') != 'python': continue
                try:
                    args = json.loads(fn['arguments']) if isinstance(fn['arguments'], str) else fn['arguments']
                except (ValueError, TypeError): continue
                code = args.get('code', '')
                calls[tid] = {'call_id':tid, 'seq':len(order)+1, 'code_line':line_no,
                    'action':o.get('action'), 'analysis_step':o.get('analysis_step'), 'code':code,
                    'reasoning':str(m.get('reasoning_content') or m.get('reasoning') or m.get('content') or '')}
                order.append(tid)
            tid = m.get('tool_call_id')
            if m.get('role') == 'tool' and tid and tid not in results:
                content = m.get('content', '')
                try: body = json.loads(content)
                except (TypeError, ValueError): body = {'raw':content}
                results[tid] = {'result_line':line_no, 'output':body}
    rows, previous_values = [], {}
    for tid in order:
        c = {**calls[tid], **results.get(tid, {})}; body = c.get('output', {})
        c['error'] = body.get('error'); stdout = str(body.get('stdout',''))
        c['has_action_echo'] = '[action]' in stdout
        c['nameerrors'] = re.findall(r"name ['\"]([^'\"]+)['\"] is not defined",str(body.get('error','')))
        c['prior_nameerror_definitions'] = {n:previous_values.get(n) for n in c['nameerrors']}
        try:
            table = symtable.symtable(c['code'], str(p), 'exec')
            # Root scope only: parameters/local variables inside functions/comprehensions
            # are not cross-snippet namespace consumption.
            refs = {s.get_name() for s in table.get_symbols() if s.is_referenced()}
            assigned = {s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported()}
            tree = ast.parse(c['code']); funcs = {n.name for n in tree.body if isinstance(n,(ast.FunctionDef, ast.AsyncFunctionDef))}
            c['root_references'] = sorted(refs); c['root_assigned'] = sorted(assigned)
            c['defined_functions'] = sorted(funcs)
            c['unbound_root_reads'] = sorted(refs-assigned)
            c['prior_value_reads'] = [{**previous_values[n], 'name':n}
                for n in sorted(refs-assigned) if n in previous_values]
            c['same_action_prior_value_reads'] = [v for v in c['prior_value_reads']
                if v['action'] == c['action'] and not v['error'] and not v['has_action_echo']]
            for name in assigned-funcs:
                previous_values[name] = {'seq':c['seq'], 'line':c['code_line'], 'action':c['action'],
                    'error':bool(c['error']), 'has_action_echo':c['has_action_echo']}
        except (SyntaxError, ValueError) as exc: c['parse_error'] = str(exc)
        rows.append(c)
    return {'source':origin(p), 'request_count':requests, 'trims':trim,
        'no_tool_assistants':no_tools,'not_acted_recovery_events':recovery_events,
        'summary':{'snippets':len(rows), 'errors':sum(bool(r.get('error')) for r in rows),
                   'nameerror_results':sum(bool(r['nameerrors']) for r in rows),
                   'same_action_root_read_candidates':sum(bool(r.get('same_action_prior_value_reads')) for r in rows)},
        'snippets':rows}

def representation_proofs():
    def sn(name,seq):return read(OUT/name)['snippets'][seq-1]
    # Extract logged literal arrays only; no dynamic code is run.
    old=sn('015-baseline-ft09-0d8bbf25.json',19)
    assignment=next(n for n in ast.parse(old['code']).body
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='L' for t in n.targets))
    remembered=ast.literal_eval(assignment.value)[(5,2)]
    crop=sn('015-baseline-ft09-0d8bbf25.json',14)['output']['stdout'].split('pattern 44 28\n')[1]
    pixels=[r.strip() for r in crop.splitlines()[:6]]
    exact=[[pixels[r][c] for c in [0,2,4]] for r in [0,2,4]]
    diff=[{'row':r,'col':c,'remembered':remembered[r][c],'raw_ascii':exact[r][c]}
        for r in range(3) for c in range(3) if remembered[r][c]!=exact[r][c]]
    tr=sn('016-pace_1x-tr87-cd924810.json',41)['output']['stdout']
    rawline=next(l for l in tr.splitlines() if l.strip().startswith('col 15'))
    raw=ast.literal_eval(rawline[rawline.index('['):])
    exact_ink=[''.join('#' if x=='B' else '.' for x in r) for r in raw]
    ext=sn('016-pace_1x-tr87-cd924810.json',47)['output']['stdout'].splitlines()[1]
    observed=list(ast.literal_eval(ext))
    ar=sn('015-native_values-ar25-0c556536.json',42)['output']['stdout']
    yellow_text,black_text=ar.split('BLACK piece\n')
    def printed_rows(text):
        return [m.group(1) for line in text.splitlines()
                if (m:=re.fullmatch(r'\s*\d+ ([A-Za-z]+)',line))]
    yellow=printed_rows(yellow_text);black=printed_rows(black_text)
    dark={(r,c) for r,row in enumerate(black) for c,ch in enumerate(row) if ch=='B'}
    background={(r,c) for r,row in enumerate(black) for c,ch in enumerate(row) if ch=='b'}
    exterior={p for p in background if p[0] in (0,len(black)-1) or p[1] in (0,len(black[0])-1)}
    queue=list(exterior)
    while queue:
        r,c=queue.pop()
        for p in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            if p in background and p not in exterior:exterior.add(p);queue.append(p)
    enclosed=background-exterior
    todo={(r,c) for r,row in enumerate(yellow) for c,ch in enumerate(row) if ch=='Y'}
    components=[]
    while todo:
        first=todo.pop();group={first};queue=[first]
        while queue:
            r,c=queue.pop()
            for p in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if p in todo:todo.remove(p);group.add(p);queue.append(p)
        components.append(len(group))
    proofs={'ft09':{'source_key_crop_line':29,'source_hardcoded_L_line':41,
        'logged_ascii_crop':pixels,'exact_3x3':exact,'hardcoded_3x3':remembered,
        'mismatches':diff,'count':len(diff),
        'note':'CPU parsing of logged literals/crop only; no logged Python execution.'},
      'tr87':{'source_raw_rows_line':85,'source_mask_line':97,
        'logged_raw_pixels':raw,'expected_black_ink':exact_ink,'logged_extracted_mask':observed,
        'matches_one_row_down_shift':observed==['.....']+exact_ink[:-1],
        'expected_black_pixels':sum(r.count('#') for r in exact_ink),
        'observed_black_pixels':sum(r.count('#') for r in observed),
        'coordinate_repair_still_off_by_one':{'source_line':101,'dictionary_A_S':{'actual_ink_rows':[11,15],'SLOTS_argument':11,'bg2_adds':1,'effective_rows':[12,16]},
            'bottom_sky':{'actual_ink_rows':[44,48],'argument':44,'bg2_adds':1,'effective_rows':[45,49]}},
        'note':'Coordinate ranges follow literal function parameters and separately printed pixel bounding boxes. No inferred game rules.'},
      'ar25':{'source_crop_line':83,'logged_black_crop':black,'logged_yellow_crop':yellow,
        'counted_black_color_pixels':len(dark),'counted_enclosed_background_pixels':len(enclosed),
        'black_plus_enclosed_count':len(dark|enclosed),
        'counted_yellow_pixels':sum(components),'four_connected_yellow_component_sizes':sorted(components,reverse=True),
        'note':'Own 4-neighbor graph count over logged ASCII literals; never executes generated code. Filling interior background is a geometric measurement, not proof that every such cell is physical footprint in arbitrary games.'}}
    save(OUT/'representation-proofs.json',proofs)
    levels={}
    for arm in ['baseline','native_values']:
        b=read(ROOT/f'runs/015-native-adoption/{arm}/benchmark.json');levels[arm]={}
        for r in b['game_runs']:
            if r['game_id'][:4] not in ('ft09','ar25'):continue
            cursor=0;rows=[]
            for i,n in enumerate(r['actions_per_level']):
                prefix=r['history'][cursor:cursor+n];cursor+=n
                rows.append({'level':i+1,'completed':i<r['levels_completed'],'actions':n,
                    'recorded_tokens':sum(x.get('generated_tokens',0) for x in prefix),
                    'last_action_elapsed_seconds':prefix[-1]['wallclock_seconds'] if prefix else None})
            levels[arm][r['game_id']]=rows
    save(OUT/'015-level-timing.json',levels)

def score_comparison():
    manifest=read(RUN/'experiment-manifest.json')
    build=read(ROOT/'notebooks/016-pace-allocation-jiyujia/build-manifest.json')
    frozen_notebook=ROOT/'notebooks/016-pace-allocation-jiyujia/experiment.ipynb'
    embedded={}
    for cell in read(frozen_notebook)['cells']:
        source=''.join(cell.get('source',[]))
        if source.startswith('%%writefile /kaggle/research/'):
            first,body=source.split('\n',1)
            path=first[len('%%writefile /kaggle/research/'):]
            embedded[path]=hashlib.sha256(body.encode()).hexdigest()==build['source_hashes'].get(path)
    ids=manifest['experiment']['games']; raw={};meta={};maps={};arms={}
    for a in ARMS:
        raw[a]=read(RUN/a/'benchmark.json');meta[a]=read(RUN/a/'arm-metadata.json')
        assert [r['game_id'] for r in raw[a]['game_runs']] == ids
        rows=[score_run(r) for r in raw[a]['game_runs']]; maps[a]={r['game_id']:r for r in rows}
        timing=audit_timing(raw[a],meta[a])
        arms[a]={'summary':aggregate(rows), 'post_deadline_actions':sum(r['post_deadline_action_count'] for r in timing['runs'].values()),
                 'post_deadline_levels':sum(len(r['post_deadline_completed_levels']) for r in timing['runs'].values())}
    games=[{'game_id':g, **{a:maps[a][g] for a in ARMS},
        'score_delta':maps[ARMS[1]][g]['AE']-maps[ARMS[0]][g]['AE'],
        'levels_delta':maps[ARMS[1]][g]['levels_completed']-maps[ARMS[0]][g]['levels_completed']} for g in ids]
    keys=('mean_AE','mean_completion_ceiling','levels_completed','wins','actions','analyzer_tokens','recorded_tokens')
    delta={k:arms[ARMS[1]]['summary'][k]-arms[ARMS[0]]['summary'][k] for k in keys}
    delta['games_with_added_levels']=sum(g['levels_delta']>0 for g in games)
    delta['games_with_lost_levels']=sum(g['levels_delta']<0 for g in games)
    largest=max(games,key=lambda g:g['score_delta'])
    sensitivity={'largest_winner':largest['game_id'], 'score_delta':largest['score_delta'],
        'contribution_to_mean':largest['score_delta']/25,
        'remaining24_mean_delta':statistics.mean(g['score_delta'] for g in games if g is not largest)}
    gates={'mean_positive':delta['mean_AE']>0, 'coverage_positive':delta['mean_completion_ceiling']>0,
        'total_levels_not_lower':delta['levels_completed']>=0,'two_games_added_levels':delta['games_with_added_levels']>=2,
        'positive_without_largest_winner':sensitivity['remaining24_mean_delta']>0}
    ea,eb=(meta[a]['environment'] for a in ARMS)
    differences={k:[ea.get(k),eb.get(k)] for k in ea.keys()|eb.keys() if ea.get(k)!=eb.get(k)}
    validations={'50_scores_recomputed':True,'source_map_equals_build':manifest['source_hashes']==build['source_hashes'],
        'runtime_config_equals_build':manifest['experiment']==build['config'],
        'frozen_notebook_sha_matches_build':sha(frozen_notebook)==build['notebook_sha256'],
        'all18_embedded_harness_sources_match_build':len(embedded)==18 and all(embedded.values()),
        'same_runtime_sources':meta[ARMS[0]]['source_sha256']==meta[ARMS[1]]['source_sha256'],
        'only_pace_environment_difference':differences=={'ARC3_PRIORITY_PACE':['0','1']},
        'same_game_order':all(meta[a]['game_ids']==ids for a in ARMS),
        'complete_both_arms':all(e['exit_code']==0 and e['complete_pool'] for e in manifest['arms']),
        'equal_7254_budget':all(e['budget_seconds']==7254 for e in manifest['arms']),
        'cache_backend_confirmed':all(e['cache_flush_backend_confirmed'] for e in manifest['arms']),
        'workers_drained':all(not e['lingering_worker_threads'] for e in manifest['arms']),
        'gpu_stopped':manifest['gpu_server_stopped'],
        'no_post_deadline_actions_or_levels':all(not x['post_deadline_actions'] and not x['post_deadline_levels'] for x in arms.values())}
    assert all(validations.values()), validations
    return {'created_at_utc':datetime.now(timezone.utc).isoformat(),'arms':arms,'delta':delta,'games':games,
        'sensitivity':sensitivity,'gates':gates,'passes':all(gates.values()),'validation':validations,
        'environment_differences':differences,'embedded_source_checks':embedded,
        'current_source_snapshot':{'checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'mismatching_current_paths':[p for p,h in manifest['source_hashes'].items()
                if not (ROOT/p).exists() or sha(ROOT/p)!=h],
            'note':'Informational only; later main-source changes do not invalidate frozen 016 provenance.'},
        'session_seconds':manifest['elapsed_seconds'],
        'session_hours':manifest['elapsed_seconds']/3600,'sources':[origin(RUN/'experiment-manifest.json'),origin(ROOT/'notebooks/016-pace-allocation-jiyujia/build-manifest.json')]+[origin(RUN/a/n) for a in ARMS for n in ['benchmark.json','arm-metadata.json']]}

def temporal_comparison(timing):
    rows={}
    for a in ARMS:
        t=read(RUN/a/'inference-timing.json'); bench=read(RUN/a/'benchmark.json'); runs={r['game_id']:r for r in bench['game_runs']}
        rows[a]={}
        for s in t['sessions']:
            gid=s['game_id']; r=runs[gid]; offset=(utc(r['started_at'])-utc(t['clock_origin_utc'])).total_seconds()
            hs=[e['t'] for e in s['events'] if e['kind']=='gate_enqueue_begin' and e.get('operation')=='handover']
            first=hs[0] if hs else None
            prefix=[h for h in r['history'] if first is None or offset+h['wallclock_seconds']<first]
            # ActionRecord signatures are observed events, not a counterfactual replay.
            sig=[h['action'] for h in prefix]
            cursor=0; level_ends=[]
            for index,count in enumerate(r['actions_per_level'][:r['levels_completed']]):
                cursor+=count
                level_ends.append({'level':index+1,'action_count':cursor,
                    'game_seconds':r['history'][cursor-1]['wallclock_seconds'] if cursor else 0})
            rows[a][gid]={'first_handover_t':first,'handover_count':len(hs),'first_handover_game_seconds':None if first is None else first-offset,
                'pre_handover_action_records':len(prefix),'pre_handover_signature':sig,
                'first_handover_levels_completed':sum(e['action_count']<=len(prefix) for e in level_ends),
                'level_completion_times':level_ends,
                'first_action_record_keys':list(prefix[0]) if prefix else [],
                'first_actions':prefix[:5]}
    divergence=[]
    raw={a:{r['game_id']:r for r in read(RUN/a/'benchmark.json')['game_runs']} for a in ARMS}
    for gid in rows[ARMS[0]]:
        histories=[raw[a][gid]['history'] for a in ARMS]
        common=0
        for aa,bb in zip(*histories):
            if aa['action']!=bb['action']:break
            common+=1
        divergence.append({'game_id':gid,'shared_initial_actions':common,
            'first_action_difference_1based':common+1,
            'both_have_handover':all(rows[a][gid]['handover_count']>0 for a in ARMS),
            'different_before_either_first_handover':(
                all(common<len(rows[a][gid]['pre_handover_signature']) for a in ARMS)
                if all(rows[a][gid]['handover_count']>0 for a in ARMS) else None),
            'different_within_initial_slot_or_finished_run':all(common<len(rows[a][gid]['pre_handover_signature']) for a in ARMS),
            'first_different_actions':{a:raw[a][gid]['history'][common]['action'] if common<len(raw[a][gid]['history']) else None for a in ARMS}})
    return {'arms':rows,'divergence':divergence}

def main():
    OUT.mkdir(exist_ok=True)
    comparison=score_comparison(); save(OUT/'comparison.json',comparison)
    timing={}
    if all((RUN/a/'inference-timing.json').exists() for a in ARMS):
        for a in ARMS:
            timing[a]=arm_report(RUN,a)
            if (RUN/a/'request-deadline.json').exists():timing[a]['deadline_audit']=deadline_report(RUN,a,timing[a])
            if (RUN/a/'scheduler-observer.json').exists():timing[a]['scheduler_audit']=scheduler_report(RUN,a,timing[a])
        save(OUT/'timing.json',timing)
        save(OUT/'first-handover.json',temporal_comparison(timing))
    for p in sorted((ROOT/'runs/015-native-adoption').glob('*/*_requests.jsonl')):
        report=extract(p); save(OUT/f'015-{p.parent.name}-{p.name.split("_")[0]}.json',report)
    for p in sorted(RUN.glob('*/*_requests.jsonl')):
        if p.name[:4] in SELECTED:
            report=extract(p);save(OUT/f'016-{p.parent.name}-{p.name.split("_")[0]}.json',report)
    representation_proofs()
    print(json.dumps({'delta':comparison['delta'],'gates':comparison['gates'],'validation':comparison['validation'],'timing_arms':list(timing)},indent=2))

if __name__=='__main__': main()
