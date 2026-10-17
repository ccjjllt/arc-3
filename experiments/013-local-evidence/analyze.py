"""Read saved research artifacts only. AST parsing never executes model code."""
from __future__ import annotations

import ast
import bisect
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
FOLDERS = ['005-full-baseline', '006-transient-history', '007-program-state',
           '010-retrievable-animation', '011-animation-confirmation', '012-current-data']


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def stamp(value):
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d


def baseline_results():
    runs = []
    for folder in FOLDERS:
        p = ROOT / 'runs' / folder / 'baseline/benchmark.json'
        d = read(p)
        runs.append({'path': str(p.relative_to(ROOT)), 'sha256': sha(p),
                     'games': [{k: r[k] for k in ['game_id', 'final_score', 'levels_completed',
                                'number_of_levels', 'solver_note']} for r in d['game_runs']]})
    common = set.intersection(*(set(r['game_id'] for r in d['games']) for d in runs))
    for d in runs:
        selected = [r for r in d['games'] if r['game_id'] in common]
        d['common_pool_mean'] = statistics.mean(r['final_score'] for r in selected)
        d['common_pool_levels'] = sum(r['levels_completed'] for r in selected)
    return {'common_ids': sorted(common), 'runs': runs,
            'warning': 'Different original pool sizes and concurrent resource exposures; descriptive variability, not replicates or causal estimates.'}


def queue_opportunities():
    reports = []
    for folder in FOLDERS[-2:]:
        for p in sorted((ROOT / 'runs' / folder).glob('*/inference-timing.json')):
            timing, meta = read(p), read(p.with_name('arm-metadata.json'))
            deadline = (stamp(meta['soft_end_local']) - stamp(timing['clock_origin_utc'])).total_seconds()
            intervals, releases, events_by_game = [], [], {}
            for s in timing['sessions']:
                q = {}
                events_by_game[s['game_id']] = s['events']
                for e in s['events']:
                    if e['kind'] == 'gate_enqueue_begin':
                        q[e['gate_call_id']] = e
                    elif e['kind'] == 'gate_admitted_return':
                        begin = q.pop(e['gate_call_id'])
                        intervals.append({'game_id': s['game_id'], 'operation': e['operation'],
                                          'begin': begin['t'], 'end': e['t'], 'wait_s': e['t'] - begin['t']})
                    elif e['kind'] == 'gate_release_credit' and e['t'] < deadline:
                        releases.append({'game_id': s['game_id'], **e})
                assert not q
            opportunities = []
            for release in releases:
                t = release['t']
                # Ignore sub-millisecond return/scheduling ambiguity; add handover caller explicitly.
                pending = [q for q in intervals if q['begin'] < t - 0.001 and q['end'] > t + 0.001]
                entries = [{'game_id': q['game_id'], 'operation': q['operation']} for q in pending]
                if release['operation'] == 'handover':
                    entries.append({'game_id': release['game_id'], 'operation': 'handover'})
                fresh = sum(e['operation'] == 'acquire' for e in entries)
                seasoned = sum(e['operation'] == 'handover' for e in entries)
                opportunities.append({'t': t, 'released_by': release['game_id'], 'operation': release['operation'],
                                      'fresh_waiters': fresh, 'seasoned_contenders': seasoned,
                                      'tail_choice_opportunity': fresh == 0 and seasoned >= 2,
                                      'observed_contenders': entries})
            h = [q for q in intervals if q['operation'] == 'handover']
            reports.append({'path': str(p.relative_to(ROOT)), 'sha256': sha(p),
                'games': len(timing['sessions']), 'handover_calls': len(h),
                'handover_waits_over_1s': sum(q['wait_s'] > 1 for q in h),
                'handover_waits_over_60s': sum(q['wait_s'] > 60 for q in h),
                'handover_wait_sum_s': sum(q['wait_s'] for q in h),
                'deadline_release_count': len(releases),
                'tail_choice_opportunities': sum(e['tail_choice_opportunity'] for e in opportunities),
                'releases_with_fresh_waiter': sum(e['fresh_waiters'] > 0 for e in opportunities),
                'opportunities': opportunities, 'wait_intervals': intervals})
    return {'semantics': 'Potential policy choice points on fixed observed wait intervals; no counterfactual score or exact heap reconstruction. Fresh priority band dominates both tail modes. Timing observer does not save priority snapshots. One millisecond tolerance excludes near-zero waits.', 'runs': reports}


def scan_requests(path):
    calls, outputs, seen = {}, {}, set()
    count = Counter()
    for line_no, line in enumerate(path.open(), 1):
        d = json.loads(line)
        for m in d.get('messages', []):
            for c in m.get('tool_calls', []):
                if c.get('id') in calls:
                    continue
                fn = c.get('function', {})
                if fn.get('name') != 'python':
                    continue
                try:
                    args = json.loads(fn['arguments']) if isinstance(fn.get('arguments'), str) else fn['arguments']
                    code = args.get('code', '')
                except (KeyError, ValueError, TypeError):
                    continue
                calls[c['id']] = {'id': c['id'], 'first_line': line_no, 'request_action': d.get('action'), 'code': code}
            if m.get('role') == 'tool':
                key = m.get('tool_call_id')
                if key and key not in outputs:
                    outputs[key] = {'first_line': line_no, 'content': m.get('content', ''), 'request_action': d.get('action')}
    refs = []
    previous_stores = defaultdict(list)
    definition_history = {}
    for call_id, call in calls.items():
        count['unique_python_calls'] += 1
        code = call['code']
        output = outputs.get(call_id)
        if output:
            count['unique_python_results'] += 1
            content = output['content']
            try:
                body = json.loads(content)
            except (ValueError, TypeError):
                body = {}
            if body.get('returncode') not in (0, None):
                count['nonzero_returncode'] += 1
            names = sorted(set(re.findall(r"(?:NameError: )?name ['\"]([^'\"]+)['\"] is not defined", content)))
            if names:
                count['results_with_nameerror'] += 1
                for name in names:
                    earlier = previous_stores.get(name, [])
                    same_action = [p for p in earlier if p['request_action'] == call['request_action']]
                    refs.append({'kind': 'undefined_name', 'name': name, 'call_id': call_id,
                                 'code_first_line': call['first_line'], 'result_first_line': output['first_line'],
                                 'request_action': call['request_action'],
                                 'earlier_assignments': earlier[-3:], 'same_request_action_earlier_assignment': bool(same_action),
                                 'code_excerpt': code[:1200], 'result_excerpt': content[:1200]})
                    count['nameerror_names'] += 1
                    count['nameerror_with_prior_assignment'] += bool(earlier)
                    count['nameerror_prior_assignment_same_action_proxy'] += bool(same_action)
            rejects = re.findall(r'Your function (.*?) was not retained: (.*?)(?:\. Hint:|\.\\n|\.\n|\.$)', content)
            if 'was not retained:' in content:
                count['results_with_retention_rejection'] += 1
                count['results_with_unavailable_dependencies'] += 'unavailable dependencies:' in content
                refs.append({'kind': 'retention_rejection', 'call_id': call_id,
                             'code_first_line': call['first_line'], 'result_first_line': output['first_line'],
                             'request_action': call['request_action'], 'reasons': rejects,
                             'code_excerpt': code[:1200],
                             'result_excerpt': content[max(0, content.find('Your function')-80):][:1800]})
        try:
            tree = ast.parse(code)
        except (SyntaxError, TypeError):
            count['ast_parse_failures'] += 1
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                normalized = ast.dump(node, include_attributes=False)
                if (node.name, normalized) in definition_history:
                    count['exact_function_redefinitions'] += 1
                definition_history[node.name, normalized] = call['first_line']
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for n in ast.walk(target):
                        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                            previous_stores[n.id].append({'first_line': call['first_line'],
                                                          'call_id': call_id, 'request_action': call['request_action']})
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path),
            'bytes': path.stat().st_size, 'counts': dict(count), 'evidence': refs}


def main():
    baseline = baseline_results()
    (OUT / 'baseline-variation.json').write_text(json.dumps(baseline, indent=2) + '\n')
    queue = queue_opportunities()
    (OUT / 'queue-opportunities.json').write_text(json.dumps(queue, indent=2) + '\n')
    files = [p for folder in FOLDERS for p in sorted((ROOT/'runs'/folder).glob('*/*_requests.jsonl'))]
    reports = []
    for p in files:
        report = scan_requests(p)
        reports.append(report)
        print(report['path'], report['counts'], flush=True)
    counts = Counter()
    for report in reports:
        counts.update(report['counts'])
    result = {'kind': 'available_selected_raw_logs_static_audit', 'date': '2026-10-17 Asia/Shanghai',
              'script_sha256': sha(Path(__file__)), 'file_count': len(reports), 'counts': dict(counts),
              'limitations': ['Only downloaded selected requests logs, not random/all-game sample.',
                  'Tool-call IDs deduplicate cumulative request snapshots within each file.',
                  'Prior assignments are AST source evidence, not proof execution reached assignment or produced serializable/correct data.',
                  'Same request action field is only a no-new-action proxy; not session/frame-identity validation.',
                  'No code from logged model snippets is evaluated or executed.',
                  'AST parse failures are reported; no unsafe unescaping or guessed repairs.'],
              'files': reports}
    (OUT / 'request-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print('TOTAL', dict(counts))
    for r in queue['runs']:
        print('QUEUE', {k:v for k,v in r.items() if k not in ['opportunities','wait_intervals']})
    for r in baseline['runs']:
        print('BASELINE', r['path'], r['common_pool_mean'], r['common_pool_levels'])


if __name__ == '__main__':
    main()
