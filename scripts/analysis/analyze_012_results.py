#!/usr/bin/env python3
"""Read-only recomputation of012; no model calls or execution of logged code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from analyze_011_results import score_run, aggregate, action_token_section
from analyze_005_results import audit_timing

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'runs/012-current-data'
OUT=ROOT/'experiments/012-analysis'
ARMS=('baseline','current_data')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=read(RUN/'experiment-manifest.json')
    frozen=ROOT/'experiments/012-source'
    build=read(frozen/'build-manifest.json'); index=read(frozen/'source-hashes.json')
    ledger=read(RUN/'current_data/current-data.json')
    sessions={s['binding']['game_id']:s for s in ledger['sessions']}
    raw={};meta={};arms={};maps={};sources=[]
    for a in ARMS:
        raw[a]=read(RUN/a/'benchmark.json');meta[a]=read(RUN/a/'arm-metadata.json')
        assert raw[a]['game_weights'] is None and raw[a]['n_passes']==1
        rows=[score_run(g) for g in raw[a]['game_runs']]
        t=audit_timing(raw[a],meta[a]);maps[a]={g['game_id']:{**g,'timing':t['runs'][g['game_id']]} for g in rows}
        arms[a]={'summary':aggregate(rows),'status':meta[a]['status'],'exit_code':meta[a]['exit_code'],
            'timing':{'requested_seconds':meta[a]['budget_seconds'],
                'benchmark_wall_seconds':meta[a]['benchmark_wall_seconds'],
                'post_deadline_actions':sum(x['post_deadline_action_count'] for x in t['runs'].values()),
                'post_deadline_levels':sum(len(x['post_deadline_completed_levels']) for x in t['runs'].values())},
            'old_interventions':{n:read(RUN/a/(n+'.json')) for n in ['goal-evidence','transient-history','program-state']}}
        sources.extend(RUN/a/n for n in ['benchmark.json','arm-metadata.json','run.log','goal-evidence.json','transient-history.json','program-state.json'])
    ids=manifest['experiment']['games'];assert len(ids)==13
    assert all([g['game_id'] for g in raw[a]['game_runs']]==ids for a in ARMS)
    games=[]
    for gid in ids:
        aa,bb=(maps[a][gid] for a in ARMS);cap=min(aa['history_tokens'],bb['history_tokens'])
        assert aa['number_of_levels']==bb['number_of_levels']
        assert [l['baseline_actions'] for l in aa['levels']]==[l['baseline_actions'] for l in bb['levels']]
        games.append({'game_id':gid,'baseline':aa,'current_data':bb,
            'AE_delta':bb['AE']-aa['AE'],'mean_AE_contribution':(bb['AE']-aa['AE'])/len(ids),
            'levels_delta':bb['levels_completed']-aa['levels_completed'],
            'data_counts':sessions[gid]['counts'],
            'common_action_token_section':{'cap':cap,**{a:action_token_section(
                next(g for g in raw[a]['game_runs'] if g['game_id']==gid),maps[a][gid],cap) for a in ARMS}}})
    keys=['mean_AE','mean_completion_ceiling','mean_efficiency_gap','levels_completed','wins','actions','analyzer_tokens','recorded_tokens','unattached_tokens']
    delta={k:arms['current_data']['summary'][k]-arms['baseline']['summary'][k] for k in keys}
    delta['relative_AE_change']=delta['mean_AE']/arms['baseline']['summary']['mean_AE']
    delta['better_equal_worse']={'better':sum(g['AE_delta']>1e-9 for g in games),'equal':sum(abs(g['AE_delta'])<=1e-9 for g in games),'worse':sum(g['AE_delta']< -1e-9 for g in games)}
    same=['game_ids','requested_game_ids','game_order_sha256','operation_mode','budget_seconds','normalized_budget_seconds','active_streams','concurrency','n_passes','warmup_action_games','analyzer_timeout_seconds','environment']
    sa,sb=(meta[a]['source_sha256'] for a in ARMS)
    validation={'metadata_equal':{k:meta[ARMS[0]][k]==meta[ARMS[1]][k] for k in same},
        'arm_order':manifest['experiment']['arm_order'],
        'config_equals_frozen':manifest['experiment']==build['config'],
        'source_map_equals_frozen':manifest['source_hashes']==build['source_hashes'],
        'archive_hashes_match':{p:sha(frozen/p)==v for p,v in index['files'].items()},
        'common_runtime_source_hashes_equal':{k:sa[k]==sb[k] for k in sorted(sa.keys()&sb.keys())},
        'candidate_module_frozen':sb['current_data.py']==build['source_hashes']['src/arc3_research/current_data.py'],
        'candidate_extra_source_keys':sorted(sb.keys()-sa.keys()),
        'separate_cpu_pids':meta['baseline']['pid']!=meta['current_data']['pid'],
        'cache_flush_statuses':[a['cache_flush_http_status'] for a in manifest['arms']],
        'cache_flush_success_log_count':(RUN/'serve.log').read_text().count('Cache flushed successfully!')}
    sources += [RUN/'experiment-manifest.json', RUN/'current_data/current-data.json', RUN/'serve.log',frozen/'build-manifest.json',frozen/'source-hashes.json',Path(__file__),ROOT/'scripts/analysis/analyze_011_results.py',ROOT/'scripts/analysis/analyze_005_results.py']
    result={'created_at_utc':datetime.now(timezone.utc).isoformat(),'arms':arms,'games':games,'overall_delta':delta,'comparability':validation,
        'current_data':{'counts':ledger['counts'],'recent_queries':ledger['recent_queries'],'snapshot_after_worker_join':ledger['snapshot_after_worker_join']},
        'session':{k:manifest[k] for k in ['status','elapsed_seconds','model_ready_seconds','gpu_server_stopped']},
        'notes':['13 known public games, one baseline-first pair; no significance or causal-harm claim.',
            'Do not directly compare these13-game means to010/01112-game means or the official leaderboard.',
            'Only2 put attempts,1 stored,0 get/context: no cross-snippet model data-reuse chain observed.',
            'Equal wall budgets do not guarantee equal per-game compute; timing audit distinguishes late requests from late actions.',
            'Common action-attached-token prefixes are descriptive, not equal GPU cost or a replacement score.'],
        'sources':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in sources]}
    OUT.mkdir(exist_ok=True);(OUT/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines=['# 012 公开13游戏结果复算','','baseline先、current_data后，差值始终为候选−基线。已知诊断池，不是正式排行榜成绩。','','| 指标 | baseline | current_data | 差值 |','|---|---:|---:|---:|']
    for k in keys:lines.append(f"| {k} | {arms['baseline']['summary'][k]:.6f} | {arms['current_data']['summary'][k]:.6f} | {delta[k]:+.6f} |")
    lines+=['','| 游戏 | AE基线→候选 | 关卡基线→候选 | 均分贡献 | put请求 / get请求 |','|---|---:|---:|---:|---:|']
    for g in games:
        a,b=g['baseline'],g['current_data'];c=g['data_counts'];lines.append(f"| {g['game_id']} | {a['AE']:.4f}→{b['AE']:.4f} | {a['levels_completed']}→{b['levels_completed']}/{a['number_of_levels']} | {g['mean_AE_contribution']:+.4f} | {c.get('put_requests',0)} / {c.get('get_requests',0)} |")
    lines+=['']+[f'- {n}' for n in result['notes']]
    (OUT/'comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'delta':delta,'timing':{a:arms[a]['timing'] for a in ARMS}},indent=2))

if __name__=='__main__':main()
