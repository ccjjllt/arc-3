"""Offline full-output qualification. Exact native acquisition is a root prerequisite."""
from pathlib import Path
import argparse
import hashlib
import json
import math

from full_workload_contract import require, validate_probe, validate_resources, validate_launcher, validate_placeholder_frame

FILES = ['arc3_full_full_workload_receipt.json', 'arc3_full_resource_receipt.json',
         'arc3_full_setup_diagnostic.json', 'arc3_full_input_resolution_diagnostic.json',
         'arc3_full_launcher_receipt.json', 'submission.parquet']


def validate_receipts(full, launcher, resources, setup, inputs):
    require(full['status'] == 'PASS_ORIGINAL_TEN_GAME_PUBLIC_WORKLOAD_ONLY'
            and full['competition_rerun'] is False and full['official_score'] is None
            and full['hidden_qualification_claim'] is False, 'PUBLIC_FULL_STATUS_REQUIRED')
    game = full['game']
    require(game['recipe'] == {'game_count': 10, 'concurrency': 10, 'per_game_seconds': 1500,
                             'max_actions_per_game': None, 'analyzer_timeout': 900.0, 'passes': 1},
            'ORIGINAL_DEMO_RECIPE_DRIFT')
    coverage = game['coverage']
    require(coverage['status'] == 'PASS_COMPLETE_PUBLIC_TERMINAL_COVERAGE'
            and coverage['expected_games'] == coverage['actual_games'] == 10
            and len(coverage['rows']) == 10 and coverage['benchmark_deadline_fired'] is False,
            'EXACT_TEN_TERMINAL_GAMES_REQUIRED')
    expected = coverage['expected_game_sha256']
    require(len(set(expected)) == 10 and sorted(r['game_sha256'] for r in coverage['rows']) == expected,
            'COMPLETE_UNIQUE_COVERAGE_REQUIRED')
    for row in coverage['rows']:
        require(row['state'] in {'won', 'gave_up'} and row['nonreset_actions'] > 0
                and row['reset_actions'] + row['nonreset_actions'] == row['actions']
                and sum(row['actions_per_level']) == row['actions']
                and math.isfinite(row['final_local_score']), 'TERMINAL_ACTION_ACCOUNTING_FAILED')
    validate_probe(game['probe'], expected)
    require(full['resources'] == resources, 'RESOURCE_RECEIPTS_DISAGREE')
    validate_resources(resources)
    validate_launcher(launcher, public=True)
    require(launcher['placeholder_created'] is True and launcher['competition_rerun'] is False,
            'QUALIFIED_PLACEHOLDER_REQUIRED')
    require(setup['status'] == 'PASS' and setup['flags']['source_unchanged'] is True
            and setup['counts']['source_files'] == setup['counts']['verified_copied_files'] == 73
            and setup['counts']['patch_targets'] == 16,
            'QUALIFIED_NONDESTRUCTIVE_SETUP_REQUIRED')
    require(inputs['status'] == 'PASS', 'INPUT_RESOLUTION_REQUIRED')
    return {'status': 'PASS_SOURCE_BOUND_TEN_GAME_PUBLIC_FULL_OUTPUT_ONLY', 'games': 10,
            'official_score': None, 'hidden_runtime_qualified': False, 'submission_authorized': False,
            'resource_limits': 'Observed sampled envelope only; hidden run is longer and has different concurrency.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', required=True, type=Path)
    parser.add_argument('--acquisition-receipt', required=True, type=Path)
    parser.add_argument('--native-version-id', required=True, type=int)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    receipt = json.loads(args.acquisition_receipt.read_bytes())
    require(receipt['status'] == 'PASS_EXACT_NATIVE_FULL_OUTPUT_ACQUISITION'
            and receipt['native_version_id'] == args.native_version_id
            and receipt['source_sha256'] == args.source_sha256
            and receipt['terminal_status_before'] == receipt['terminal_status_after'] == 'COMPLETE'
            and receipt['source_before_sha256'] == receipt['source_after_sha256'] == args.source_sha256
            and receipt['native_url_binding_before_after'] is True,
            'ROOT_EXACT_NATIVE_ACQUISITION_REQUIRED')
    require(set(receipt['files']) == set(FILES), 'EXACT_OUTPUT_INVENTORY_REQUIRED')
    blobs = {}
    for name in FILES:
        path = args.output_directory / name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 262144, 'OUTPUT_FILE_INVALID')
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == receipt['files'][name]['sha256']
                and len(data) == receipt['files'][name]['bytes'], 'EXACT_OUTPUT_HASH_DRIFT')
        if name.endswith('.json'):
            blobs[name] = json.loads(data)
    result = validate_receipts(*(blobs[name] for name in [FILES[0], FILES[4], FILES[1], FILES[2], FILES[3]]))
    import pandas as pd
    validate_placeholder_frame(pd.read_parquet(args.output_directory / 'submission.parquet'))
    require(blobs[FILES[4]]['placeholder_sha256'] == receipt['files']['submission.parquet']['sha256'],
            'PLACEHOLDER_BINDING_DRIFT')
    result.update(native_version_id=args.native_version_id, source_sha256=args.source_sha256)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
