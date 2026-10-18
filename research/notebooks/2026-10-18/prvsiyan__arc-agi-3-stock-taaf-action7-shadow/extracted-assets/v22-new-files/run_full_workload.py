"""Native-only original V1 workload with qualified setup and owned supervision.

Public: exact ten demo games, 25 min/game, concurrency ten. Competition: original
all-gateway-game recipe and nine-hour target, with retained V17 deadline reserve.
This file neither launches Kaggle jobs nor submits to a competition.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request

from run_native_canary import (execute_prepared, check_small_asset_locks, digest,
                              safe_child_diagnostic, validate_scratch, SOURCE_SHA,
                              CURRENT_V3_IMAGE)
from nondestructive_runtime import prepare_bundle
from mount_resolution import resolve_inputs
from owned_supervisor import supervise
from full_workload_contract import (require, summarize_runs, validate_resources,
                                   validate_launcher, validate_placeholder_frame,
                                   PUBLIC_NATIVE_SECONDS, PUBLIC_SUPERVISED_SECONDS,
                                   HIDDEN_NATIVE_SECONDS, HIDDEN_SUPERVISED_SECONDS,
                                   HIDDEN_SOFT_SECONDS)
from resource_observer import ResourceObserver

HERE = Path(__file__).resolve().parent
PUBLIC_STATUS = 'PASS_ORIGINAL_TEN_GAME_PUBLIC_WORKLOAD_ONLY'


def competition_rerun():
    return os.environ.get('KAGGLE_IS_COMPETITION_RERUN', '').strip().lower() in {'1', 'true'}


def validate_runtime(admission):
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'NATIVE_LINUX_X86_64_REQUIRED')
    require(tuple(sys.version_info[:3]) == (3, 12, 13), 'PUBLIC_DECLARED_PYTHON_3_12_13_REQUIRED')
    require(admission['source_native_version_id'] == 354090904 and admission['source_sha256'] == SOURCE_SHA,
            'EXACT_ORIGINAL_SOURCE_REQUIRED')
    require(admission['docker_image'] == CURRENT_V3_IMAGE and admission['image_is_historical_v1'] is False,
            'CURRENT_IMAGE_BINDING_REQUIRED')
    require(admission['machine_shape'] == 'NvidiaRtxPro6000' and admission['internet_enabled'] is False,
            'EXACT_OFFLINE_GPU_REQUIRED')
    require(admission['model_native_version_ids'] == [1007514, 1007009], 'EXACT_MODEL_VERSIONS_REQUIRED')
    require(admission['proposed_native_timeout_seconds'] == PUBLIC_NATIVE_SECONDS
            and admission['supervised_budget_seconds'] == PUBLIC_SUPERVISED_SECONDS,
            'EXPLICIT_PUBLIC_FULL_BUDGET_REQUIRED')
    require(admission['competition_native_seconds'] == HIDDEN_NATIVE_SECONDS
            and admission['competition_supervised_seconds'] == HIDDEN_SUPERVISED_SECONDS,
            'ORIGINAL_NINE_HOUR_COMPETITION_BUDGET_REQUIRED')
    parsed = datetime.fromisoformat(admission['verified_at_utc'])
    require(parsed.tzinfo is not None and datetime.now(timezone.utc) >= parsed and admission['evidence_reference'],
            'DATED_RUNTIME_BINDING_REQUIRED')
    require(admission['freshness_policy'] == 'ROOT_DISPATCH_WITHIN_900_SECONDS_NATIVE_START_RECORDED',
            'DISPATCH_FRESHNESS_POLICY_REQUIRED')
    require(admission['dispatch_verifier_sha256'] == digest(HERE / 'verify_dispatch.py'), 'EXACT_DISPATCH_VERIFIER_REQUIRED')


def recipe(name, namespace):
    bindings = json.loads((HERE / 'recipe_bindings.json').read_bytes())
    path = HERE / name
    require(digest(path) == bindings['files'][name]['sha256'], 'RECIPE_SOURCE_DRIFT')
    exec(compile(path.read_text(), str(path), 'exec'), namespace)


async def benchmark(namespace, native_started_epoch):
    bm, target = namespace['bm'], namespace['target']
    hidden = namespace['TRUE_SUBMISSION']
    require(bm.solver.start_local_server is False and target.setup_commands == []
            and target.teardown_commands == [], 'QUALIFIED_EXTERNAL_SERVER_CONTRACT_REQUIRED')
    recipe('public_v1_customization.py', namespace)
    recipe('public_v1_game_selection.py', namespace)
    require(bm.n_passes == 1 and bm.game_weights is None and bm.solver.max_actions_per_game is None,
            'ORIGINAL_UNCAPPED_SINGLE_PASS_REQUIRED')
    require(bm.solver.analyzer_timeout == 900 and namespace['USE_PRIORITY_SCHEDULING'] is True,
            'ORIGINAL_ANALYZER_AND_SCHEDULER_REQUIRED')
    if hidden:
        require(bm.solver.concurrency == 120 and bm.solver.max_runtime_s_per_game == 532*60,
                'ORIGINAL_COMPETITION_RECIPE_REQUIRED')
        os.environ.setdefault('ARC_API_KEY', 'test-key-123')
        os.environ.setdefault('ARC_BASE_URL', 'http://gateway:8001/')
        namespace['_wait_for_gateway'](os.environ['ARC_BASE_URL'])
        bm.games = namespace['_competition_games']()
        # Original dynamic gateway coverage; never guess or truncate to 110.
        soft_end = datetime.fromtimestamp(native_started_epoch + HIDDEN_SOFT_SECONDS)
    else:
        require(bm.solver.concurrency == 10 and bm.solver.max_runtime_s_per_game == 25*60,
                'EXACT_TEN_GAME_25_MINUTE_RECIPE_REQUIRED')
        bm.games = namespace['_offline_games'](str(namespace['RESOLVED_INPUTS']['environment_files']))
        # Original public soft deadline is nine hours minus ten minutes. The
        # independent 4380-second supervisor is an explicit qualification cap.
        soft_end = datetime.fromtimestamp(namespace['NOTEBOOK_START_EPOCH'] + target.max_runtime_s - 600)
    ids = [game.env_name for game in bm.games]
    require(ids and len(ids) == len(set(ids)), 'NONEMPTY_UNIQUE_GAME_IDS_REQUIRED')
    if not hidden:
        require(len(ids) == 10, 'TEN_ORIGINAL_DEMO_GAMES_REQUIRED')
    os.environ['RECORDINGS_DIR'] = str(namespace['WORKING_DIR'] / 'server_recording')
    recipe('v17_timing.py', namespace)
    probe = None
    try:
        if not hidden:
            from full_game_probe import install_probe
            probe = install_probe(expected_game_ids=ids)
        await bm.run(soft_end_time=soft_end, runtime_environment=target, minimal_diagnostics=hidden)
        coverage = summarize_runs(bm, ids, public=not hidden)
        if probe:
            probe.assert_meaningful_coverage()
    finally:
        try:
            if probe:
                probe.close()
        finally:
            if namespace['V17_TIMING']['on']:
                import requests
                require(requests.Session.send is namespace['_v17_timed_send'], 'TIMING_WRAPPER_OWNERSHIP_LOST')
                requests.Session.send = namespace['_v17_original_send']
    timing = {'enabled': False}
    if not hidden:
        recipe('v17_timing_summary.py', namespace)
        timing = namespace['v17_timing_summary'](namespace['V17_TIMING']['path'], slots=10)
        timing['logging_errors'] = namespace['V17_TIMING']['logging_errors']
        timing['measurement'] = 'CLIENT_REQUEST_SEND_INTERVALS_NOT_GPU_UTILIZATION_OR_FULL_GENERATION_LATENCY'
    return {'coverage': coverage, 'probe': probe.summary() if probe else None, 'client_timing': timing,
            'recipe': {'game_count': len(ids), 'concurrency': bm.solver.concurrency,
                       'per_game_seconds': bm.solver.max_runtime_s_per_game, 'max_actions_per_game': None,
                       'analyzer_timeout': bm.solver.analyzer_timeout, 'passes': bm.n_passes}}


def child(arguments, admission):
    validate_runtime(admission)
    run = Path(arguments.run_directory)
    validate_scratch(run, arguments.output_root)
    def stage(name):
        with (run / ('phase_' + name + '.json')).open('x') as stream:
            json.dump({'phase': name, 'monotonic_seconds': time.monotonic()}, stream)
    stage('setup')
    inputs = resolve_inputs(run)
    ns = {'__name__': 'arc3_full_original_workload', 'CANARY_RUN_DIR': run,
          'PREPARED_SOURCE': HERE / 'prepared_v1', 'prepare_bundle': prepare_bundle, 'RESOLVED_INPUTS': inputs}
    execute_prepared('setup.py', ns)
    arc_runtime = run / 'arc-runtime'
    stage('competition_runtime')
    require(not arc_runtime.exists(), 'FRESH_RUNTIME_TARGET_REQUIRED')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '--no-index',
                    '--disable-pip-version-check', '--target', str(arc_runtime), '--find-links',
                    str(inputs['competition_wheels']), 'arc-agi'], check=True)
    sys.path.insert(0, str(arc_runtime))
    os.environ['PYTHONPATH'] = str(arc_runtime) + os.pathsep + os.environ.get('PYTHONPATH', '')
    execute_prepared('source_imports.py', ns)
    stage('wheel_prefetch')
    execute_prepared('precache.py', ns)
    require(digest(Path(ns['WHEELHOUSE_DIR']) / 'requirements.lock') ==
            '4b0ee12848c1e7c3a51b0819de3a1ae63a967313fd1f62b9e2ca6b9c82b8da02', 'ORIGINAL_WHEEL_LOCK_REQUIRED')
    stage('serving_prepare')
    execute_prepared('serving_prepare.py', ns)
    census = subprocess.run([ns['PYTHON'], '-c',
        'import torch,json; assert torch.cuda.device_count()==1; assert torch.cuda.get_device_capability(0)==(12,0); '
        'print(json.dumps({"torch":torch.__version__,"cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(0),'
        '"capability":torch.cuda.get_device_capability(0),"gpu_bytes":torch.cuda.get_device_properties(0).total_memory}))'],
        env=ns['env'], check=True, capture_output=True, text=True)
    runtime = json.loads(census.stdout.strip().splitlines()[-1])
    ns['precache_model_thread'].start()
    stage('server_health')
    resources = ResourceObserver(run).start()
    try:
        with (run / 'serve.log').open('xb') as log:
            server = subprocess.Popen(ns['args'], env=ns['env'], stdout=log,
                                      stderr=subprocess.STDOUT, start_new_session=False)
            deadline, healthy = ns['NOTEBOOK_START_TIME'] + ns['SERVER_STARTUP_TIMEOUT'], False
            while time.time() < deadline:
                require(server.poll() is None, 'SERVER_EXITED_DURING_STARTUP')
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{ns['SERVED_MODEL_PORT']}/health", timeout=5) as response:
                        if response.status == 200:
                            healthy = True
                            break
                except Exception:
                    time.sleep(1)
            # Preserve original V1/V17 warmup behavior: the first game's retry
            # window may finish startup, but an exited server is always fatal.
            require(server.poll() is None, 'SERVER_NOT_ALIVE_BEFORE_GAMES')
            check_small_asset_locks(ns['BUNDLE_DIR'], arguments.small_asset_locks)
            execute_prepared('restore_benchmark.py', ns)
            stage('original_full_workload')
            game_result = asyncio.run(benchmark(ns, arguments.native_started_epoch))
            require(server.poll() is None, 'SERVER_EXITED_BEFORE_COMPLETION')
    finally:
        resource_summary = resources.close()
        with (run / 'resource_receipt.json').open('x') as stream:
            json.dump(resource_summary, stream, indent=2)
    resource_gate = validate_resources(resource_summary)
    result = {'status': 'COMPETITION_WORKLOAD_FINISHED' if competition_rerun() else PUBLIC_STATUS,
              'competition_rerun': competition_rerun(), 'game': game_result,
              'runtime_census': runtime, 'startup_health_observed_before_deadline': healthy,
              'resources': resource_summary, 'resource_gate': resource_gate,
              'historical_v1_image_reproduction': False, 'official_score': None,
              'submission_authorized': False, 'hidden_qualification_claim': False}
    with (run / 'full_workload_receipt.json').open('x') as stream:
        json.dump(result, stream, indent=2)
    if not competition_rerun():
        import pandas as pd
        frame = pd.DataFrame([['1_0', '1', True, 1]], columns=['row_id', 'game_id', 'end_of_game', 'score'])
        staged = run / 'qualified_placeholder.parquet'
        require(not staged.exists(), 'FRESH_PLACEHOLDER_PATH_REQUIRED')
        frame.to_parquet(staged, index=False)
        validate_placeholder_frame(pd.read_parquet(staged))


def main():
    native_start = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-admission', required=True)
    parser.add_argument('--small-asset-locks', required=True)
    parser.add_argument('--run-parent', default='/kaggle/arc3-full-runs')
    parser.add_argument('--output-root', default='/kaggle/working')
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--run-directory')
    parser.add_argument('--native-started-epoch', type=float)
    args = parser.parse_args()
    admission = json.loads(Path(args.runtime_admission).read_bytes())
    validate_runtime(admission)
    if args.child:
        try:
            child(args, admission)
        except Exception as error:
            diagnostic = safe_child_diagnostic(error, args.run_directory)
            diagnostic['error_code'] = 'NATIVE_FULL_WORKLOAD_CHILD_EXCEPTION'
            with (Path(args.run_directory) / 'child_diagnostic.json').open('x') as stream:
                json.dump(diagnostic, stream, indent=2)
            raise
        return
    output = Path(args.output_root).resolve()
    require(output.is_dir() and not list(output.iterdir()), 'CLEAN_OUTPUT_ROOT_REQUIRED_NO_FILES_REMOVED')
    parent = Path(args.run_parent)
    validate_scratch(parent, output)
    parent.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='arc3-v1-full-', dir=parent))
    command = [sys.executable, str(Path(__file__).resolve()), '--child', '--run-directory', str(run),
               '--output-root', str(output), '--native-started-epoch', str(native_start.timestamp()),
               '--runtime-admission', str(Path(args.runtime_admission).resolve()),
               '--small-asset-locks', str(Path(args.small_asset_locks).resolve())]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='0', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               HF_DATASETS_OFFLINE='1', UV_OFFLINE='1', UV_PYTHON_DOWNLOADS='never', PYTHONUNBUFFERED='1')
    public = not competition_rerun()
    with (run / 'native_full.log').open('xb') as log:
        result = supervise(command, cwd=run, env=env, log=log,
                           budget_seconds=PUBLIC_SUPERVISED_SECONDS if public else HIDDEN_SUPERVISED_SECONDS)
    result.update(native_started_at_utc=native_start.isoformat(), source_verified_at_utc=admission['verified_at_utc'],
                  source_binding_age_at_native_start_seconds=(native_start - datetime.fromisoformat(admission['verified_at_utc'])).total_seconds(),
                  competition_rerun=not public, submission_created=False, submission_authorized=False)
    try:
        validate_launcher(result, public=public)
        receipt = json.loads((run / 'full_workload_receipt.json').read_bytes())
        require(receipt['status'] == (PUBLIC_STATUS if public else 'COMPETITION_WORKLOAD_FINISHED'), 'WORKLOAD_GATE_FAILED')
        if public:
            import pandas as pd
            staged = run / 'qualified_placeholder.parquet'
            validate_placeholder_frame(pd.read_parquet(staged))
            # Export only after child success AND proven model/group cleanup.
            with (output / 'submission.parquet').open('xb') as stream:
                stream.write(staged.read_bytes())
            result['placeholder_created'] = True
            result['placeholder_sha256'] = digest(output / 'submission.parquet')
    except Exception as error:
        result['qualification_error_type'] = type(error).__name__
        result['exit_code'] = result['exit_code'] or 65
    for name in ['full_workload_receipt.json', 'resource_receipt.json', 'child_diagnostic.json',
                 'setup_diagnostic.json', 'input_resolution_diagnostic.json']:
        path = run / name
        if path.is_file():
            with (output / ('arc3_full_' + name)).open('xb') as stream:
                stream.write(path.read_bytes())
    with (output / 'arc3_full_launcher_receipt.json').open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
    raise SystemExit(result['exit_code'])


if __name__ == '__main__':
    main()
