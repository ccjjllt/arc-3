"""Pure observation/model computations, executed only in the existing sandbox."""
import copy
import json
import math
import re


def rl_value(value):
    text = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    if len(text) > 12000:
        raise ValueError('State too large; encode the relevant objects/geometry compactly')
    return json.loads(text)


def rl_key(value):
    return json.dumps(rl_value(value), sort_keys=True, ensure_ascii=False)


def rl_brief(value):
    text = json.dumps(value, ensure_ascii=False)
    return value if len(text) < 1100 else text[:1090] + ' [truncated]'


def rl_action(text):
    name = str(text).split('(', 1)[0].strip().upper()
    aliases = {'ACTION1':'UP', 'ACTION2':'DOWN', 'ACTION3':'LEFT',
               'ACTION4':'RIGHT', 'ACTION5':'SPACE', 'ACTION6':'MOUSE', 'ACTION7':'UNDO'}
    name = aliases.get(name, name)
    action = {'action':name}
    if name == 'MOUSE':
        for key in ('row', 'col'):
            match = re.search(key + r'\s*=\s*(-?\d+)', str(text))
            if match is None:
                raise ValueError('Unrecognized observed mouse coordinates: ' + str(text))
            action[key] = int(match.group(1))
    return action


def rl_predict(name, state, action):
    result = RULES[name](copy.deepcopy(state), copy.deepcopy(action))
    if result is None:
        return None  # Explicitly outside this rule's scope; not a successful match.
    if not isinstance(result, dict) or 'state' not in result:
        raise ValueError('Prediction must be {"state": ..., optional "game_over"/"level_completed": bool}, or None')
    if set(result) - {'state','game_over','level_completed'}:
        raise ValueError('Unknown prediction keys')
    for flag in ('game_over','level_completed'):
        if flag in result and type(result[flag]) is not bool:
            raise ValueError(flag + ' must be a boolean')
    return rl_value(result)


def rl_check(names, level, minimum_step=-1, limit=96):
    cases = []
    skipped = 0
    for item in transitions:
        before, after, outcome = item.before_frame, item.after_frame, item.result or {}
        if before is None or after is None or before.level != level or after.step <= minimum_step:
            continue
        if outcome.get('automatic') or str(item.action).upper().startswith('RESET'):
            skipped += 1
            continue
        cases.append(item)
    total = len(cases)
    if total > limit:
        indexes = sorted({round(i*(total-1)/(limit-1)) for i in range(limit)})
        cases = [cases[i] for i in indexes]
    reports = {name:dict(checked=0, matched=0, mismatched=0, errors=0, unsupported=0,
                         changed_cases=0, action_types=[], counterexamples=[]) for name in names}
    for item in cases:
        before, after, outcome = item.before_frame, item.after_frame, item.result or {}
        terminal = bool(outcome.get('game_over') or outcome.get('level_completed') or outcome.get('run_complete') or outcome.get('done'))
        try:
            action = rl_action(item.action)
            state = rl_value(observe(copy.deepcopy(before)))
            actual_state = None if terminal or after.level != before.level else rl_value(observe(copy.deepcopy(after)))
            encoding_error = None
        except Exception as exc:
            encoding_error = type(exc).__name__+': '+str(exc)[:240]
        for name in names:
            report = reports[name]
            if encoding_error:
                report['errors'] += 1
                if len(report['counterexamples']) < 3:
                    report['counterexamples'].append(dict(step=after.step,error=encoding_error))
                continue
            try:
                prediction = rl_predict(name, state, action)
                if prediction is None:
                    report['unsupported'] += 1
                    continue
                # After a completion/death the returned frame may belong to a
                # new level/attempt. Check outcome flags, not old-board geometry.
                observed = {} if terminal or after.level != before.level else {'state':actual_state}
                if 'state' in observed:
                    report['changed_cases'] += int(rl_key(state) != rl_key(observed['state']))
                for flag in ('game_over','level_completed'):
                    if flag in prediction:
                        observed[flag] = bool(outcome.get(flag) or (flag=='level_completed' and (outcome.get('run_complete') or outcome.get('done'))))
                if not observed:
                    report['unsupported'] += 1
                    continue
                report['checked'] += 1
                if action['action'] not in report['action_types']:
                    report['action_types'].append(action['action'])
                mismatch = {key:dict(predicted=rl_brief(prediction.get(key)), observed=rl_brief(value))
                            for key,value in observed.items() if rl_key(prediction.get(key)) != rl_key(value)}
                if mismatch:
                    report['mismatched'] += 1
                    if len(report['counterexamples']) < 3:
                        report['counterexamples'].append(dict(step=after.step, action=action, before=rl_brief(state), differences=mismatch))
                else:
                    report['matched'] += 1
            except Exception as exc:
                report['errors'] += 1
                if len(report['counterexamples']) < 3:
                    report['counterexamples'].append(dict(step=after.step, error=type(exc).__name__+': '+str(exc)[:240]))
    for report in reports.values():
        report['status'] = ('contradicted' if report['mismatched'] else 'code_error' if report['errors']
                            else 'consistent_on_checked_cases' if report['checked'] else 'untested')
        report['coverage_note'] = 'This covers only the encoded state and declared outcome flags; other objects and goals remain unverified.'
    return dict(eligible_transitions=total, selected_transitions=len(cases), skipped_reset_or_automatic=skipped,
                sampled=total>len(cases), rules=reports)


def rl_predictions(names, action):
    state = rl_value(observe(copy.deepcopy(current_frame)))
    predictions = {}
    errors = {}
    for name in names:
        try:
            predicted = rl_predict(name, state, action)
            repeat = rl_predict(name, state, action)
            if rl_key(predicted) != rl_key(repeat):
                raise ValueError('Prediction is not deterministic for the same state/action')
            predictions[name] = predicted
        except Exception as exc:
            errors[name] = type(exc).__name__+': '+str(exc)[:200]
    return dict(state=rl_brief(state), predictions=predictions, errors=errors)


def rl_probes(names, actions, depth=2, node_limit=64):
    if len(names) < 2 or not actions:
        return dict(probes=[], searched_nodes=0, note='Need at least two non-refuted rules and candidate actions')
    state = rl_value(observe(copy.deepcopy(current_frame)))
    frontier = [([], {name:copy.deepcopy(state) for name in names})]
    probes, errors, visited = [], [], 0
    while frontier and visited < node_limit:
        sequence, states = frontier.pop(0)
        for action in actions:
            if visited >= node_limit:
                break
            visited += 1
            try:
                predictions = {name:rl_predict(name, states[name], action) for name in names}
                if any(p is None or p.get('game_over') for p in predictions.values()):
                    continue
                groups = {}
                # Missing terminal predictions cannot be treated as false:
                # compare only outcome fields explicitly predicted by everyone.
                keys = {'state'} | {k for k in ('game_over','level_completed') if all(k in p for p in predictions.values())}
                for name,prediction in predictions.items():
                    groups.setdefault(rl_key({k:prediction[k] for k in keys}), []).append(name)
                path = sequence + [action]
                if len(groups) > 1:
                    entropy = -sum((len(g)/len(names))*math.log2(len(g)/len(names)) for g in groups.values())
                    probes.append(dict(actions=path, predicted_groups=list(groups.values()),
                        predictions={name:rl_brief(p) for name,p in predictions.items()},
                        information_per_action=entropy/len(path), information_bits=entropy))
                elif len(path) < depth and not any(p.get('level_completed') for p in predictions.values()):
                    frontier.append((path,{name:p['state'] for name,p in predictions.items()}))
            except Exception as exc:
                if len(errors)<3:
                    errors.append(type(exc).__name__+': '+str(exc)[:200])
    probes.sort(key=lambda p:(-p['information_per_action'],len(p['actions'])))
    return dict(probes=probes[:3], searched_nodes=visited, errors=errors,
                note='Equal-weight hypothesis discrimination, not predicted score or a safety guarantee. Execute only the first action, then observe and replan.')
