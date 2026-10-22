#!/usr/bin/env python3
"""Derive 007 A/B comparisons from completed outputs; manual CPU analysis only."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_005_results import audit_timing, source
from summarize_experiment import summarize_benchmark


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('runs/007-program-state'))
    parser.add_argument('--output-dir', type=Path, default=Path('experiments/007-analysis'))
    args = parser.parse_args()
    names = ('baseline', 'program_state')
    summaries, metadata, timing, raw, sources = {}, {}, {}, {}, []
    for arm in names:
        directory = args.root / arm
        raw[arm] = read(directory / 'benchmark.json')
        metadata[arm] = read(directory / 'arm-metadata.json')
        summaries[arm] = summarize_benchmark(arm, directory / 'benchmark.json', 'local-experiment')
        timing[arm] = audit_timing(raw[arm], metadata[arm])
        sources.extend(source(directory / file) for file in
                       ('benchmark.json', 'arm-metadata.json', 'program-state.json'))
    manifest = read(args.root / 'experiment-manifest.json')
    intervention = read(args.root / 'program_state/program-state.json')
    sources.append(source(args.root / 'experiment-manifest.json'))
    events = defaultdict(list)
    for event in intervention['events']:
        events[event['run_ref'].rsplit('_p', 1)[0]].append(event)
    run_maps = {arm: {r['game_id']: r for r in summaries[arm]['runs']} for arm in names}
    if set(run_maps['baseline']) != set(run_maps['program_state']):
        raise ValueError('Different A/B game sets')
    rows = []
    for game in metadata['baseline']['game_ids']:
        a, b = (run_maps[arm][game] for arm in names)
        rows.append({
            'game_id': game, 'baseline': {**a, **timing['baseline']['runs'][game]},
            'program_state': {**b, **timing['program_state']['runs'][game]},
            'score_delta': b['score'] - a['score'],
            'ceiling_delta': b['completion_ceiling'] - a['completion_ceiling'],
            'levels_delta': b['levels_completed'] - a['levels_completed'],
            'analyzer_tokens_delta': b['analyzer_reported_generated_tokens'] - a['analyzer_reported_generated_tokens'],
            'direct_missing_snapshot_events': len(events[game]),
            'nonempty_preservation_events': sum(e['retained_function_count'] > 0 for e in events[game]),
            'preserved_function_occurrences': sum(e['retained_function_count'] for e in events[game]),
        })
    total = sum(row['score_delta'] for row in rows)
    for row in rows:
        row['mean_score_contribution'] = row['score_delta'] / len(rows)
    groups = {}
    for label, selected in (
        ('direct_event_games', [r for r in rows if r['direct_missing_snapshot_events']]),
        ('zero_direct_event_games', [r for r in rows if not r['direct_missing_snapshot_events']]),
        ('tr87_sc25', [r for r in rows if r['game_id'][:4] in ('tr87', 'sc25')]),
    ):
        groups[label] = {'games': [r['game_id'] for r in selected],
                         'mean_score_contribution': sum(r['score_delta'] for r in selected) / len(rows),
                         'levels_delta': sum(r['levels_delta'] for r in selected)}
    compare_fields = ('game_ids', 'game_order_sha256', 'budget_seconds', 'normalized_budget_seconds',
                      'active_streams', 'concurrency', 'n_passes', 'warmup_action_games',
                      'analyzer_timeout_seconds', 'source_sha256', 'environment')
    result = {
        'sources': sources,
        'arms': {arm: {'summary': summaries[arm]['summary'], 'warnings': summaries[arm]['warnings'],
                      'post_deadline_actions': sum(r['post_deadline_action_count'] for r in timing[arm]['runs'].values()),
                      'post_deadline_levels': sum(len(r['post_deadline_completed_levels']) for r in timing[arm]['runs'].values()),
                      'status': metadata[arm]['status'], 'exit_code': metadata[arm]['exit_code'],
                      'forced_cpu_process_exit': metadata[arm]['forced_cpu_process_exit']}
                 for arm in names},
        'overall_delta': {'score': total / len(rows),
                          'ceiling': statistics.fmean(r['ceiling_delta'] for r in rows),
                          'completed_levels': sum(r['levels_delta'] for r in rows),
                          'wins': summaries['program_state']['summary']['wins'] - summaries['baseline']['summary']['wins'],
                          'analyzer_tokens': sum(r['analyzer_tokens_delta'] for r in rows),
                          'games_better_equal_worse': [sum(r['score_delta'] > 1e-8 for r in rows),
                                                     sum(abs(r['score_delta']) <= 1e-8 for r in rows),
                                                     sum(r['score_delta'] < -1e-8 for r in rows)]},
        'games': rows, 'descriptive_groups': groups, 'intervention': intervention,
        'comparability': {'equal_metadata_fields': {f: metadata['baseline'].get(f) == metadata['program_state'].get(f)
                                                   for f in compare_fields},
                          'distinct_cpu_pids': metadata['baseline']['pid'] != metadata['program_state']['pid'],
                          'arm_order': manifest['experiment']['arm_order']},
        'notes': [
            'Same 12 known public games, one run each, baseline first, shared 10-stream scheduling; no independent random-seed replications.',
            'Event groups are post hoc descriptive accounting, not treatment-effect estimates. Zero direct events do not exclude shared scheduling effects.',
            'Baseline disabled-patch diagnostics are empty by design; baseline timeout counts require raw-trace inspection.',
            'Scores are public-development results, not hidden leaderboard scores. No promotion supported by this run.',
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['overall_delta'], indent=2))
    print(json.dumps(groups, indent=2))
    print('Equal metadata:', all(result['comparability']['equal_metadata_fields'].values()))
    for arm in names:
        print(arm, 'post-deadline actions/levels:', result['arms'][arm]['post_deadline_actions'], result['arms'][arm]['post_deadline_levels'])


if __name__ == '__main__':
    main()
