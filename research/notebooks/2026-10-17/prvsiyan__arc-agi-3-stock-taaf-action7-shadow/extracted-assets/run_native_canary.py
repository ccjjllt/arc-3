"""Bounded native ARC3 serving + one-model-action canary. Preparation only here.

Run only under root-coordinator admission on Kaggle. Does not submit or produce
submission.parquet. Original mounted model weights are never copied or rehosted.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse
import asyncio
import hashlib
import importlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request

from nondestructive_runtime import prepare_bundle
from owned_supervisor import supervise

HERE = Path(__file__).resolve().parent
SOURCE_SHA = '0a2c570976b61a43aab52f426e3951b43b78699ac20f7a12a8481d0553f00f07'
CURRENT_V3_IMAGE = 'gcr.io/kaggle-private-byod/python@sha256:57e612b484cf3df5026ee4dcc3cb176974b22b2bc0937fb1e16132a8be4cb13c'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def validate_runtime(admission):
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'NATIVE_LINUX_X86_64_REQUIRED')
    require(tuple(sys.version_info[:3]) == (3, 12, 13), 'PUBLIC_DECLARED_PYTHON_3_12_13_REQUIRED')
    require(os.environ.get('KAGGLE_IS_COMPETITION_RERUN', '').strip().lower() not in {'1', 'true'},
            'CANARY_MUST_NOT_RUN_IN_COMPETITION_RERUN')
    require(admission.get('source_native_version_id') == 354090904 and admission.get('source_sha256') == SOURCE_SHA,
            'EXACT_V1_SOURCE_ADMISSION_REQUIRED')
    require(admission.get('docker_image') == CURRENT_V3_IMAGE and admission.get('image_is_historical_v1') is False,
            'SEPARATELY_BOUND_CURRENT_IMAGE_ADMISSION_REQUIRED')
    require(admission.get('machine_shape') == 'NvidiaRtxPro6000' and admission.get('internet_enabled') is False,
            'RTX_PRO6000_OFFLINE_ADMISSION_REQUIRED')
    require(admission.get('model_native_version_ids') == [1007514, 1007009], 'EXACT_ORIGINAL_MODEL_V1_MOUNTS_REQUIRED')
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(admission['verified_at_utc'])).total_seconds()
    require(age >= 0 and admission.get('evidence_reference'), 'DATED_SOURCE_RUNTIME_BINDING_REQUIRED')
    require(admission.get('freshness_policy') == 'ROOT_DISPATCH_WITHIN_900_SECONDS_NATIVE_START_RECORDED',
            'CONCRETE_ROOT_DISPATCH_FRESHNESS_POLICY_REQUIRED')
    require(admission.get('dispatch_verifier_sha256') == digest(HERE / 'verify_dispatch.py'),
            'BOUND_ROOT_DISPATCH_VERIFIER_REQUIRED')


def execute_prepared(name, namespace):
    path = HERE / 'prepared_v1' / name
    receipt = json.loads((HERE / 'prepared_v1/ADAPTER_RECEIPT.json').read_text())
    require(digest(path) == receipt['generated_files_sha256'][name], 'PREPARED_SOURCE_DRIFT: ' + name)
    exec(compile(path.read_text(), str(path), 'exec'), namespace)


def validate_scratch(path, output_root):
    resolved = Path(path).resolve()
    require(not resolved.is_relative_to(Path('/kaggle/working').resolve()),
            'SCRATCH_MUST_BE_OUTSIDE_FIXED_KAGGLE_PUBLIC_OUTPUT_ROOT')
    require(not resolved.is_relative_to(Path(output_root).resolve()),
            'SCRATCH_MUST_BE_OUTSIDE_CONFIGURED_OUTPUT_ROOT')


def check_small_asset_locks(bundle, lock_file):
    locks = json.loads(Path(lock_file).read_text())
    required = {'deploy_target.pkl', 'benchmark_initial.pkl'}
    require(set(locks.get('sha256', {})) >= required, 'BOTH_ORIGINAL_PICKLE_HASHES_REQUIRED')
    require(locks.get('static_setup_teardown_review') == 'NO_DESTRUCTIVE_COMMANDS',
            'EXACT_SETUP_TEARDOWN_STATIC_REVIEW_REQUIRED')
    for name in required:
        require(digest(bundle / name) == locks['sha256'][name], 'ORIGINAL_SMALL_ASSET_HASH_MISMATCH: ' + name)


def tiny_completion(port, model):
    request = {'model': model, 'messages': [{'role': 'user', 'content': 'Reply with one short word: ready.'}],
               'max_tokens': 32, 'temperature': 0, 'stream': False}
    started = time.monotonic()
    req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',
                                 data=json.dumps(request).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.load(response)
    choices = result.get('choices', [])
    require(bool(choices), 'TINY_COMPLETION_CHOICES_MISSING')
    message = choices[0].get('message', {})
    value = message.get('content') or message.get('reasoning_content')
    tokens = result.get('usage', {}).get('completion_tokens', 0)
    require(isinstance(value, str) and bool(value.strip()) and isinstance(tokens, int) and tokens > 0,
            'TINY_COMPLETION_VALID_TEXT_AND_TOKEN_USAGE_REQUIRED')
    return {'valid': True, 'completion_tokens': tokens,
            'message_sha256': hashlib.sha256(json.dumps(message, sort_keys=True).encode()).hexdigest(),
            'elapsed_seconds': time.monotonic() - started}


async def one_public_game(namespace):
    import arc_agi
    import taaf.game_api
    from agent_probe import install_probe
    bm, target = namespace['bm'], namespace['target']
    require(getattr(bm.solver, 'start_local_server', None) is False, 'ORIGINAL_EXTERNAL_SERVER_CONFIGURATION_REQUIRED')
    require(target.setup_commands == [] and target.teardown_commands == [], 'EMPTY_RESTORED_TARGET_COMMANDS_REQUIRED')
    environment_dir = '/kaggle/input/competitions/arc-prize-2026-arc-agi-3/environment_files'
    spec = taaf.game_api.ArcadeSpec(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=environment_dir)
    arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=environment_dir)
    excluded = ['bp35', 'cd82', 'cn04', 'dc22', 'g50t', 'ka59', 'lf52', 'ls20',
                'm0r0', 's5i5', 'sk48', 'sp80', 'su15', 'tn36', 'wa30']
    ids = sorted(item.game_id for item in arcade.available_environments
                 if not any(item.game_id.startswith(prefix) for prefix in excluded))
    require(bool(ids), 'PUBLIC_V1_DEMO_GAME_REQUIRED')
    selected = ids[0]
    bm.games = [taaf.game_api.GameAPI(env_name=selected, arcade_spec=spec)]
    bm.solver.max_actions_per_game = 2  # Original warmup RESET plus at most one model action.
    bm.solver.max_runtime_s_per_game = 90.0
    bm.solver.analyzer_timeout = 75.0
    bm.solver.concurrency = 1
    bm.solver.save_request_logs = False
    bm.n_passes, bm.game_weights = 1, None
    observer = install_probe(expected_game_id=selected)
    try:
        await asyncio.wait_for(bm.run(soft_end_time=datetime.now() + timedelta(seconds=90),
                                     runtime_environment=target, minimal_diagnostics=False), timeout=105)
        observer.assert_meaningful_step()
        runs = list(bm.game_runs)
        require(len(runs) == 1, 'EXACTLY_ONE_PUBLIC_GAME_RUN_REQUIRED')
        return {'selected_public_game_sha256': hashlib.sha256(selected.encode()).hexdigest(),
                'game_runs': len(runs), 'probe': observer.summary(), 'game_action_cap': 2,
                'warmup_reset_retained': True, 'score_claim': False}
    finally:
        observer.close()


def child(arguments, admission):
    validate_runtime(admission)
    run = Path(arguments.run_directory)
    validate_scratch(run, arguments.output_root)
    def stage(name):
        with (run / ('phase_' + name + '.json')).open('x') as out:
            json.dump({'phase': name, 'monotonic_seconds': time.monotonic()}, out)
    stage('setup')
    namespace = {'__name__': 'arc3_native_canary_setup', 'CANARY_RUN_DIR': run,
                 'PREPARED_SOURCE': HERE / 'prepared_v1', 'prepare_bundle': prepare_bundle}
    execute_prepared('setup.py', namespace)
    # Install the same competition wheel dependency set into a new private target,
    # preserving the host environment and any notebook artifacts it contains.
    arc_runtime = run / 'arc-runtime'
    stage('competition_runtime')
    require(not arc_runtime.exists(), 'FRESH_ARC_RUNTIME_TARGET_REQUIRED')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '--no-index',
                    '--disable-pip-version-check', '--target', str(arc_runtime), '--find-links',
                    '/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels', 'arc-agi'], check=True)
    sys.path.insert(0, str(arc_runtime))
    os.environ['PYTHONPATH'] = str(arc_runtime) + os.pathsep + os.environ.get('PYTHONPATH', '')
    execute_prepared('source_imports.py', namespace)
    stage('wheel_prefetch')
    execute_prepared('precache.py', namespace)
    require(digest(Path(namespace['WHEELHOUSE_DIR']) / 'requirements.lock') ==
            '4b0ee12848c1e7c3a51b0819de3a1ae63a967313fd1f62b9e2ca6b9c82b8da02', 'EXACT_PUBLIC_PENNYROYAL_LOCK_REQUIRED')
    stage('serving_prepare')
    execute_prepared('serving_prepare.py', namespace)
    census = subprocess.run([namespace['PYTHON'], '-c',
        'import torch,json; assert torch.cuda.device_count()==1; assert torch.cuda.get_device_capability(0)==(12,0); '
        'print(json.dumps({"torch":torch.__version__,"cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(0),'
        '"capability":torch.cuda.get_device_capability(0),"gpu_bytes":torch.cuda.get_device_properties(0).total_memory}))'],
        env=namespace['env'], check=True, capture_output=True, text=True)
    runtime_census = json.loads(census.stdout.strip().splitlines()[-1])
    # Preserve original model prefetch ordering and all assembled scientific flags.
    namespace['precache_model_thread'].start()
    stage('server_health')
    with (run / 'serve.log').open('xb') as log:
        server = subprocess.Popen(namespace['args'], env=namespace['env'], stdout=log,
                                  stderr=subprocess.STDOUT, start_new_session=False)
        # Server inherits the outer supervisor's owned group. This child never
        # kills or reuses any unrelated process, and never detaches the server.
        deadline = namespace['NOTEBOOK_START_TIME'] + namespace['SERVER_STARTUP_TIMEOUT']
        while time.time() < deadline:
            require(server.poll() is None, 'SERVER_EXITED_BEFORE_HEALTH')
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{namespace['SERVED_MODEL_PORT']}/health", timeout=5) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('ORIGINAL_720_SECOND_STARTUP_WINDOW_EXHAUSTED')
        stage('tiny_completion')
        serving = tiny_completion(namespace['SERVED_MODEL_PORT'], namespace['SERVED_MODEL_NAME'])
        check_small_asset_locks(namespace['BUNDLE_DIR'], arguments.small_asset_locks)
        execute_prepared('restore_benchmark.py', namespace)
        stage('one_public_game')
        game = asyncio.run(one_public_game(namespace))
        result = {'status': 'SERVING_AND_ONE_MODEL_GAME_ACTION_PASS_ONLY', 'serving': serving, 'game': game,
                  'historical_v1_image_reproduction': False, 'official_score': None,
                  'runtime_census': runtime_census,
                  'full_run_authorized': False, 'submission_created': False}
        with (run / 'integration_receipt.json').open('x') as out:
            json.dump(result, out, indent=2)


def main():
    native_started_at = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-admission', required=True)
    parser.add_argument('--small-asset-locks', required=True)
    parser.add_argument('--run-parent', default='/kaggle/arc3-canary-runs')
    parser.add_argument('--output-root', default='/kaggle/working')
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--run-directory')
    arguments = parser.parse_args()
    admission = json.loads(Path(arguments.runtime_admission).read_text())
    validate_runtime(admission)
    if arguments.child:
        try:
            child(arguments, admission)
        except Exception as error:
            run = Path(arguments.run_directory)
            validate_scratch(run, arguments.output_root)
            phases = []
            for path in run.glob('phase_*.json'):
                phases.append(json.loads(path.read_text()))
            phases.sort(key=lambda item: item['monotonic_seconds'])
            with (run / 'child_diagnostic.json').open('x') as out:
                json.dump({'status': 'FAILED', 'started_phase_markers': [item['phase'] for item in phases],
                           'last_started_phase': phases[-1]['phase'] if phases else None,
                           'error_type': type(error).__name__,
                           'error_code': 'NATIVE_CANARY_CHILD_EXCEPTION',
                           'raw_exception_details': 'RETAINED_IN_PRIVATE_SCRATCH_LOG'}, out, indent=2)
            raise
        return
    parent = Path(arguments.run_parent)
    validate_scratch(parent, arguments.output_root)
    parent.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='arc3-v1-canary-', dir=parent))
    command = [sys.executable, str(Path(__file__).resolve()), '--child', '--run-directory', str(run),
               '--output-root', str(Path(arguments.output_root).resolve()),
               '--runtime-admission', str(Path(arguments.runtime_admission).resolve()),
               '--small-asset-locks', str(Path(arguments.small_asset_locks).resolve())]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='0', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               HF_DATASETS_OFFLINE='1', UV_OFFLINE='1', UV_PYTHON_DOWNLOADS='never', PYTHONUNBUFFERED='1')
    with (run / 'native_canary.log').open('xb') as log:
        result = supervise(command, cwd=run, env=env, log=log, budget_seconds=1500)
    result['native_started_at_utc'] = native_started_at.isoformat()
    result['source_verified_at_utc'] = admission['verified_at_utc']
    result['source_binding_age_at_native_start_seconds'] = (
        native_started_at - datetime.fromisoformat(admission['verified_at_utc'])).total_seconds()
    result['queue_provisioning_age_note'] = (
        'Root compares native_started_at_utc with the separate actual dispatch receipt; '
        'source-binding age includes any pre-dispatch delay and is not exact queue duration.')
    integration = run / 'integration_receipt.json'
    result['integration_receipt_exists'] = integration.is_file()
    result['full_run_authorized'] = False
    result['submission_created'] = False
    if result['exit_code'] == 0:
        if not integration.is_file() or json.loads(integration.read_text()).get('status') != 'SERVING_AND_ONE_MODEL_GAME_ACTION_PASS_ONLY':
            result['exit_code'] = 65
    output = Path(arguments.output_root)
    with (output / 'arc3_v1_canary_launcher_receipt.json').open('x') as out:
        json.dump(result, out, indent=2)
    if integration.is_file():
        with (output / 'arc3_v1_canary_integration_receipt.json').open('xb') as out:
            out.write(integration.read_bytes())
    if (run / 'child_diagnostic.json').is_file():
        with (output / 'arc3_v1_canary_child_diagnostic.json').open('xb') as out:
            out.write((run / 'child_diagnostic.json').read_bytes())
    print(json.dumps(result))
    raise SystemExit(result['exit_code'])


if __name__ == '__main__':
    main()
