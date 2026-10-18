"""Pure qualification rules; these observe the original solver, never modify it."""
import hashlib
import json
import math

PUBLIC_GAMES = 10
PUBLIC_NATIVE_SECONDS = 4500
PUBLIC_SUPERVISED_SECONDS = 4380
HIDDEN_NATIVE_SECONDS = 32400
HIDDEN_SUPERVISED_SECONDS = 32100
HIDDEN_SOFT_SECONDS = 31860


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def game_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_probe(probe, expected_hashes):
    require(probe['schema'] == 'arc3-full-game-model-tool-action-probe-v1'
            and probe['status'] == 'PASS' and probe['coverage_complete'] is True
            and probe['closed'] is True and probe['observation_errors'] == []
            and probe['missing_game_id_sha256'] == [], 'PROBE_COVERAGE_NOT_QUALIFIED')
    require(probe['raw_wire_response_observed'] is False and probe['native_parser_flags_changed'] is False,
            'OBSERVATION_BOUNDARY_DRIFT')
    require(sorted(probe['per_game']) == sorted(expected_hashes) == probe['expected_game_id_sha256'],
            'PROBE_GAME_COVERAGE_DRIFT')
    for key, game in probe['per_game'].items():
        require(game['qualified_clean_action_count'] > 0, 'CLEAN_MODEL_ACTION_MISSING')
        chain = game['first_witness']
        require(len(chain) == 4 and [e['kind'] for e in chain] ==
                ['model_response', 'tool_dispatch_begin', 'engine_action', 'tool_dispatch_return'],
                'INVALID_MODEL_ACTION_WITNESS')
        model, dispatch, action, returned = chain
        require(model['sequence'] < dispatch['sequence'] < action['sequence'] < returned['sequence'],
                'WITNESS_ORDER_INVALID')
        require(model['output_tokens'] > 0 and dispatch['matches_model_response'] is True
                and dispatch['tool_is_python'] is True
                and dispatch['arguments_sha256'] in model['python_argument_sha256']
                and dispatch['response_event'] == model['sequence'], 'MODEL_TO_TOOL_LINK_INVALID')
        require(action['game_id_sha256'] == key and action['same_agent'] is True
                and action['expected_game'] is True and action['executed'] is True
                and action['automatic'] is False and action['non_reset'] is True
                and action['action_name'] != 'RESET' and action['appended_once'] is True
                and action['qualified'] is True and action['history_after'] == action['history_before'] + 1
                and action['response_event'] == model['sequence'] and action['dispatch_event'] == dispatch['sequence'],
                'MODEL_TO_ENGINE_LINK_INVALID')
        require(returned['dispatch_event'] == dispatch['sequence'] and returned['step_executed'] is True
                and returned['clean_python_completion'] is True and returned['tool_error'] is False
                and action['sequence'] in returned['qualified_action_events'], 'UNCLEAN_TOOL_RETURN')
    counts = probe['global_counts']
    for kind in ['model_calls', 'tool_dispatch_calls', 'action_calls']:
        require(counts[kind + '_started'] == counts[kind + '_returned'] + counts[kind + '_failed'],
                'INCOMPLETE_PROBE_CALL_ACCOUNTING')
    require(probe['storage']['active_dispatches'] == 0 and probe['storage']['response_contexts'] == 0,
            'PROBE_NOT_CLOSED_CLEANLY')


def summarize_runs(bm, expected_ids, *, public):
    """The benchmark swallows solver failures, so inspect every actual run."""
    require(expected_ids and len(expected_ids) == len(set(expected_ids)), 'UNIQUE_GAME_SELECTION_REQUIRED')
    if public:
        require(len(expected_ids) == PUBLIC_GAMES, 'EXACT_TEN_PUBLIC_GAMES_REQUIRED')
    runs = list(bm.game_runs)
    require(len(runs) == len(expected_ids), 'COMPLETE_GAME_RUN_COUNT_REQUIRED')
    require({r.game_id for r in runs} == set(expected_ids), 'EXACT_GAME_RUN_COVERAGE_REQUIRED')
    require(bm.end_time is not None, 'BENCHMARK_END_REQUIRED')
    rows = []
    for run in runs:
        history = list(run.history)
        counts = list(run.actions_per_level)
        require(all(type(n) is int and n >= 0 for n in counts) and sum(counts) == len(history),
                'ACTION_HISTORY_COUNTER_INVARIANT_FAILED')
        state = run.state
        allowed = {'won', 'gave_up'} if public else {'won', 'gave_up', 'cancelled'}
        require(state in allowed, 'UNHEALTHY_OR_INCOMPLETE_GAME_STATE')
        score = run.final_score
        require(type(score) in (int, float) and math.isfinite(score), 'FINITE_FINAL_LOCAL_SCORE_REQUIRED')
        actions = [item.action.id.name for item in history]
        nonreset = sum(name != 'RESET' for name in actions)
        if public:
            require(nonreset > 0, 'RESET_ONLY_GAME_CANNOT_QUALIFY')
            require(not str(run.solver_note or '').startswith(('error:', 'analyzer failed ')),
                    'TERMINAL_SOLVER_FAILURE_CANNOT_QUALIFY')
        rows.append({'game_sha256': game_hash(run.game_id), 'state': state,
                     'actions': len(actions), 'nonreset_actions': nonreset,
                     'reset_actions': len(actions) - nonreset, 'actions_per_level': counts,
                     'levels_completed': run.levels_completed, 'final_local_score': score,
                     'history_generated_tokens': sum(item.generated_tokens for item in history),
                     'final_generated_tokens': run.final_generated_tokens,
                     'token_note': 'History accounting may omit terminal no-action tokens; probe separately counts model output.'})
    return {'status': 'PASS_COMPLETE_PUBLIC_TERMINAL_COVERAGE' if public else 'COMPETITION_TERMINAL_COVERAGE',
            'expected_games': len(expected_ids), 'actual_games': len(runs),
            'expected_game_sha256': sorted(game_hash(i) for i in expected_ids),
            'rows': rows, 'benchmark_deadline_fired': bool(getattr(bm, '_deadline_fired', False)),
            'official_score': None}


def validate_resources(summary):
    require(summary['samples'] >= 2 and summary['errors'] == [], 'RESOURCE_OBSERVATION_REQUIRED')
    require(summary['host_available_min_bytes'] >= 512 * 1024**2, 'SAMPLED_HOST_MEMORY_RESERVE_FAILED')
    require(summary['scratch_free_min_bytes'] >= 1024**3, 'SAMPLED_SCRATCH_RESERVE_FAILED')
    require(0 < summary['gpu_used_peak_bytes'] <= summary['gpu_total_bytes'], 'SAMPLED_GPU_ENVELOPE_FAILED')
    require(summary['owned_group_rss_peak_bytes'] > 0, 'OWNED_GROUP_MEMORY_OBSERVATION_REQUIRED')
    return {'status': 'PASS_SAMPLED_RESOURCE_ENVELOPE',
            'host_reserve_bytes': 512 * 1024**2, 'scratch_reserve_bytes': 1024**3,
            'limitation': 'Sampled peaks are lower bounds, not exact maxima or proof of hidden-run capacity.'}


def validate_launcher(receipt, *, public):
    budget = PUBLIC_SUPERVISED_SECONDS if public else HIDDEN_SUPERVISED_SECONDS
    require(receipt['exit_code'] == 0 and receipt['timed_out'] is False and receipt['interrupted'] is False,
            'CHILD_MUST_EXIT_CLEANLY')
    require(receipt['cleanup_error'] is None and receipt['owned_process_group_gone'] is True
            and receipt['leader_reaped'] is True, 'OWNED_CLEANUP_MUST_BE_PROVEN')
    require(receipt['total_budget_seconds'] == budget and 0 <= receipt['elapsed_seconds'] <= budget,
            'SUPERVISED_BUDGET_FAILED')


def validate_placeholder_frame(frame):
    require(list(frame.columns) == ['row_id', 'game_id', 'end_of_game', 'score'], 'PLACEHOLDER_COLUMNS_INVALID')
    require(len(frame) == 1 and frame.iloc[0].tolist() == ['1_0', '1', True, 1], 'PLACEHOLDER_CONTENT_INVALID')
    require(str(frame.dtypes['end_of_game']) == 'bool' and str(frame.dtypes['score']) == 'int64',
            'PLACEHOLDER_TYPES_INVALID')
