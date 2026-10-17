"""Fixed observed-queue sensitivity of existing pure scheduler functions."""
import bisect
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
P = ROOT/'research/runtime-bundle/src/ARC3-Inference/inference/agent/priority_scheduler.py'
spec = importlib.util.spec_from_file_location('arc3_scheduler_013', P)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
reference = json.loads(P.with_name('priority_pace_reference.json').read_text())


def utc(s):
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d


def state_at(game, t, origin):
    h = game['history']
    times = [(utc(game['started_at']) - origin).total_seconds()+a['wallclock_seconds'] for a in h]
    n = bisect.bisect_right(times, t)
    b, s = [], 0
    for count in game['actions_per_level'][:game['levels_completed']]:
        s += count
        b.append(s)
    completed = bisect.bisect_right(b, n)
    if completed >= game['number_of_levels']:
        return None
    costs, last = [], 0
    pace = m.ProgressPace()
    for level in range(completed):
        cost = sum(x.get('generated_tokens', 0) for x in h[last:b[level]])
        costs.append(cost)
        pace.record_completion(cost, reference['by_level'].get(str(level+1), reference['fallback_tokens']))
        last = b[level]
    tokens = sum(x.get('generated_tokens', 0) for x in h[last:n])
    return {'level': completed+1, 'actions': n-last, 'tokens': tokens,
            'total_levels': game['number_of_levels'], 'pace': pace.cost_multiplier(),
            'completed_action_attached_token_costs': costs}


reports = []
for qr in json.loads((OUT/'queue-opportunities.json').read_text())['runs']:
    p = ROOT/qr['path']
    timing = json.loads(p.read_text())
    origin = utc(timing['clock_origin_utc'])
    meta = json.loads(p.with_name('arm-metadata.json').read_text())
    deadline = (utc(meta['soft_end_local'])-origin).total_seconds()
    budget = meta['budget_seconds']
    games = {g['game_id']:g for g in json.loads(p.with_name('benchmark.json').read_text())['game_runs']}
    comparisons = []
    for opp in qr['opportunities']:
        if not opp['tail_choice_opportunity']:
            continue
        rows = []
        for c in opp['observed_contenders']:
            game_id = c['game_id']
            enqueues = [q for q in qr['wait_intervals'] if q['game_id']==game_id
                        and q['operation']=='handover' and q['begin'] <= opp['t']+.001 and q['end'] >= opp['t']-.001]
            if not enqueues:
                continue
            q = min(enqueues, key=lambda q: abs(q['begin']-opp['t']))
            st = state_at(games[game_id], q['begin'], origin)
            if st is None:
                continue
            fade = min(1, max(0, (deadline-opp['t'])/(.2*budget)))
            kw = dict(normalize_score=True, tail_fraction=fade)
            plain = m.PrioritySnapshot(st['level'], st['actions'], st['tokens'], 1, st['total_levels'])
            paced = m.PrioritySnapshot(st['level'], st['actions'], st['tokens'], st['pace'], st['total_levels'])
            rows.append({'game_id':game_id, 'enqueue_t':q['begin'], 'observed_return_t':q['end'], **st,
                         'remaining_priority':m.priority_value(plain, tail_lookup='remaining', **kw),
                         'tail_priority':m.priority_value(plain, tail_lookup=True, **kw),
                         'pace_priority':m.priority_value(paced, tail_lookup='remaining', **kw)})
        if len(rows)<2:
            continue
        rank = lambda key: sorted(rows,key=lambda r:(-r[key],r['enqueue_t']))[0]['game_id']
        old, tail, pace = (rank(k) for k in ['remaining_priority','tail_priority','pace_priority'])
        observed = min(rows,key=lambda r:r['observed_return_t'])['game_id']
        comparisons.append({'t':opp['t'], 'baseline_proxy_winner':old, 'tail_proxy_winner':tail,
                            'pace_proxy_winner':pace,'observed_first_return':observed,
                            'baseline_proxy_agrees_with_observed_return':old==observed,
                            'tail_changes_proxy_winner':old!=tail, 'pace_changes_proxy_winner':old!=pace,
                            'states':rows})
    reports.append({'path':qr['path'],'choice_points':len(comparisons),
                    'baseline_proxy_matches':sum(r['baseline_proxy_agrees_with_observed_return'] for r in comparisons),
                    'tail_proxy_winner_changes':sum(r['tail_changes_proxy_winner'] for r in comparisons),
                    'pace_proxy_winner_changes':sum(r['pace_changes_proxy_winner'] for r in comparisons),
                    'comparisons':comparisons})

# Synthetic states isolate the existing formula; they are not game predictions.
grid=[]
for token in [0,31000,62000,93000,124000,186000]:
    row={'tokens':token,'level':4,'actions':25,'total_levels':8}
    for pace in [.5,1,2]:
        row[str(pace)]=m.priority_value(m.PrioritySnapshot(4,25,token,pace,8),normalize_score=True,
                                      tail_lookup='remaining',tail_fraction=1)
    grid.append(row)
result={'kind':'fixed_observed_queue_proxy_sensitivity_not_scheduler_replay',
        'date':'2026-10-17 Asia/Shanghai',
        'source_sha256':{str(P.relative_to(ROOT)):hashlib.sha256(P.read_bytes()).hexdigest(),
                         str(P.with_name('priority_pace_reference.json').relative_to(ROOT)):hashlib.sha256(P.with_name('priority_pace_reference.json').read_bytes()).hexdigest(),
                         str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        'limitations':['Uses observed queues; a policy switch changes future trajectories and queue membership.',
                       'Gate observer did not record PrioritySnapshot or the exact heap admission instant.',
                       'Level/action/token state inferred from benchmark action boundaries at enqueue; action-attached tokens omit no-action/pending costs and may differ from live completion ledger.',
                       'Pace values are proxy accumulation, not recorded live pace. All these runs had PACE=0.',
                       'Baseline disagreement is reported, not repaired using future information. Winner-change counts are mechanism exposure, not expected reward.'],
        'reference':reference,'synthetic_pace_grid':grid,'runs':reports}
(OUT/'scheduler-sensitivity.json').write_text(json.dumps(result,indent=2)+'\n')
for r in reports:
    print({k:v for k,v in r.items() if k!='comparisons'})
print('SYNTHETIC',grid)
