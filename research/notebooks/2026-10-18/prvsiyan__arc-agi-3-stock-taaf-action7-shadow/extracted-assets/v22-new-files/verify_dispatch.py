"""Read-only ARC3 dispatch gate. No launch, submission, or notebook mutation.

Root must run this gate and then --check-admission immediately before unchanged
safe_push. A valid receipt is necessary, not sufficient: global job admission,
independent source review and all safe_push checks remain required.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse
import ast
import base64
import hashlib
import json
import sys
import urllib.request
import uuid
import zlib

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
REF = 'prvsiyan/arc-agi-3-stock-taaf-action7-shadow'
IMAGE = 'gcr.io/kaggle-private-byod/python@sha256:57e612b484cf3df5026ee4dcc3cb176974b22b2bc0937fb1e16132a8be4cb13c'
V3_SHA = '88a379f17c3a4ba8c98715fc23155346ccd6eb289bdafebadfc61a3178f9d9bd'
V1_SHA = '0a2c570976b61a43aab52f426e3951b43b78699ac20f7a12a8481d0553f00f07'
MAX_AGE = 900
DATASETS = {'dfranzen/pennyroyal-v253': 12273106,
            'dfranzen/taaf-kaggle-source-bundle-copy': 12250142}
MODELS = {
    'dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default': (755365, 1007514),
    'dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default': (755057, 1007009),
}


class GateError(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise GateError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes())


def age(timestamp):
    parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'TIMEZONE_REQUIRED')
    seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
    require(0 <= seconds <= MAX_AGE, 'DISPATCH_FRESHNESS_EXPIRED_OR_FUTURE')
    return seconds


def safe_member(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts,
            'UNSAFE_PAYLOAD_PATH')
    require(path.resolve().is_relative_to(root.resolve()) and not path.is_symlink(),
            'PAYLOAD_PATH_ESCAPE')
    return path


def source_text(cell):
    value = cell['source']
    return ''.join(value) if isinstance(value, list) else value


def local_checks(args):
    receipt_path = Path(args.receipt).resolve()
    raw = receipt_path.read_bytes()
    receipt = json.loads(raw)
    require(receipt['ref'] == REF and receipt['fresh_owner_version'] == 21,
            'OWNER_CONTRACT_DRIFT')
    require(receipt['status'] == 'SOURCE_ONLY_NOT_LAUNCHED', 'CANDIDATE_STATE_INVALID')
    candidate = Path(receipt['candidate']).resolve()
    require(candidate.parent == receipt_path.parent, 'CANDIDATE_LOCATION_DRIFT')
    data = candidate.read_bytes()
    require(sha(data) == receipt['source_sha256'] == args.expected_candidate_sha256,
            'CANDIDATE_SOURCE_DRIFT')
    require(len(data) == receipt['source_bytes'], 'CANDIDATE_SIZE_DRIFT')
    age(receipt['runtime_admission']['verified_at_utc'])
    packet = Path(args.packet).resolve()
    freeze_raw = (packet / 'SOURCE_FREEZE.json').read_bytes()
    require(sha(freeze_raw) == receipt['source_freeze_sha256'] == args.expected_freeze_sha256,
            'SOURCE_FREEZE_DRIFT')
    freeze = json.loads(freeze_raw)
    for name, descriptor in freeze['files'].items():
        file_data = safe_member(packet, name).read_bytes()
        require(sha(file_data) == descriptor['sha256'], 'FROZEN_FILE_DRIFT')
        require(len(file_data) == descriptor['bytes'], 'FROZEN_FILE_SIZE_DRIFT')
    from payload_codec import decode_sources, verify_preservation
    notebook = json.loads(data)
    original_raw = (packet / 'BASE_V21_SOURCE.source.json').read_bytes()
    require(sha(original_raw) == receipt['fresh_original_sha256'] == 'feecdd3bfb626003680e7ac8765031e381ca208b47ff27278faf96d3cb91a6cb', 'BASE_V21_SOURCE_DRIFT')
    verify_preservation(json.loads(original_raw), notebook)
    sources = decode_sources(notebook, full=True)
    hashes = {name: sha(content.encode()) for name, content in sources.items()}
    require(hashes == receipt['source_payload_sha256'], 'EMBEDDED_PAYLOAD_DRIFT')
    for name, content in sources.items():
        if name != 'runtime_admission.json':
            require(name in freeze['files'], 'UNFROZEN_RUNTIME_SOURCE')
            require(sha(content.encode()) == freeze['files'][name]['sha256'], 'RUNTIME_SOURCE_DRIFT')
            require(content == safe_member(packet, name).read_text(), 'RUNTIME_SOURCE_TEXT_DRIFT')
    require(json.loads(sources['runtime_admission.json']) == receipt['runtime_admission'],
            'EMBEDDED_ADMISSION_DRIFT')
    admission = receipt['runtime_admission']
    require(admission['freshness_policy'] == 'ROOT_DISPATCH_WITHIN_900_SECONDS_NATIVE_START_RECORDED'
            and admission['dispatch_verifier_sha256'] == sha(Path(__file__).read_bytes())
            and hashes.get('verify_dispatch.py') == sha(Path(__file__).read_bytes()),
            'DISPATCH_VERIFIER_POLICY_OR_HASH_DRIFT')
    require(admission['source_native_version_id'] == 354090904 and admission['source_sha256'] == V1_SHA,
            'SCORED_V1_BINDING_DRIFT')
    require(admission['docker_image'] == IMAGE and admission['image_is_historical_v1'] is False,
            'RUNTIME_BINDING_DRIFT')
    require(admission['model_native_version_ids'] == [1007514, 1007009], 'MODEL_BINDING_DRIFT')
    overrides = receipt['overrides']
    require(overrides['docker_image'] == IMAGE and overrides['docker_image_pinning_type'] == 'original'
            and overrides['machine_shape'] == 'NvidiaRtxPro6000'
            and overrides['enable_internet'] is False and overrides['enable_gpu'] is True
            and overrides['enable_tpu'] is False and overrides['is_private'] is False,
            'LAUNCH_RUNTIME_OVERRIDE_DRIFT')
    require(set(overrides['dataset_sources']) == set(DATASETS)
            and set(overrides['model_sources']) == {ref + '/1' for ref in MODELS}
            and overrides['competition_sources'] == ['arc-prize-2026-arc-agi-3']
            and overrides['kernel_sources'] == [], 'LAUNCH_ASSET_OVERRIDE_DRIFT')
    require(receipt['native_timeout_seconds'] == 4500 and receipt['supervised_budget_seconds'] == 4380,
            'RESOURCE_BUDGET_DRIFT')
    guard = PROJECT / 'research/claude_campaign_20261002/tools/safe_push.py'
    require(receipt['safe_push_path'] == str(guard.relative_to(PROJECT))
            and sha(guard.read_bytes()) == receipt['safe_push_sha256'], 'SAFE_PUSH_SOURCE_DRIFT')
    metadata = read_json(receipt_path.parent / 'kernel-metadata.json')
    require(metadata['id'] == REF and metadata['id_no'] == 128810290
            and {k: metadata[k] for k in ('id_no', 'title', 'code_file')} == receipt['expected_identity'],
            'OWNER_IDENTITY_DRIFT')
    return receipt, sha(raw), metadata


def public_pull(ref):
    url = 'https://www.kaggle.com/api/v1/kernels/pull/' + ref
    with urllib.request.urlopen(url, timeout=25) as response:
        require(response.geturl() == url, 'PUBLIC_PULL_REDIRECT')
        return json.load(response)


def fresh_checks(args, receipt, metadata, output):
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.datasets.types.dataset_api_service import ApiGetDatasetRequest
    api = KaggleApi()
    api.authenticate()
    api.kernels_pull(REF, path=str(output / 'fresh_server'), metadata=True, quiet=True)
    fresh = read_json(output / 'fresh_server/kernel-metadata.json')
    require(fresh == metadata, 'FULL_OWNER_METADATA_DRIFT')
    original = (output / 'fresh_server' / metadata['code_file']).read_bytes()
    require(sha(original) == receipt['fresh_original_sha256'], 'FRESH_OWNER_SOURCE_DRIFT')
    own = public_pull(REF)
    require(own['metadata']['currentVersionNumber'] == 21 and own['metadata']['id'] == 128810290
            and own['metadata']['isPrivate'] is False and own['metadata']['ref'] == REF,
            'PUBLIC_OWNER_VERSION_OR_IDENTITY_DRIFT')
    require(sha(own['blob']['source'].encode()) == sha(original), 'FRESH_OWNER_READS_DISAGREE')
    upstream = public_pull('dfranzen/arc-agi-3-milestone-2-solution')
    require(upstream['metadata']['currentVersionNumber'] == 3
            and upstream['metadata']['id'] == 136499478 and upstream['metadata']['isPrivate'] is False
            and upstream['metadata']['dockerImage'] == IMAGE
            and upstream['metadata']['machineShape'] == 'NvidiaRtxPro6000'
            and sha(upstream['blob']['source'].encode()) == V3_SHA, 'CURRENT_V3_RUNTIME_SOURCE_DRIFT')
    datasets = {}
    with api.build_kaggle_client() as client:
        for ref, native_id in DATASETS.items():
            request = ApiGetDatasetRequest()
            request.owner_slug, request.dataset_slug = ref.split('/')
            info = client.datasets.dataset_api_client.get_dataset(request).to_dict()
            require(info['id'] == native_id and info['currentVersionNumber'] == 1
                    and len(info['versions']) == 1 and info['versions'][0]['versionNumber'] == 1,
                    'DATASET_NATIVE_V1_DRIFT')
            datasets[ref] = {'dataset_id': native_id, 'version_number': 1,
                             'metadata_sha256': sha(json.dumps(info, sort_keys=True, default=str).encode())}
    models = {}
    for ref, (instance_id, version_id) in MODELS.items():
        info = api.model_instance_get(ref).to_dict()
        require(info['id'] == instance_id and info['versionId'] == version_id
                and info['versionNumber'] == 1 and info['slug'] == 'default'
                and 'Qwen Community License 1.0' in info['overview'], 'MODEL_NATIVE_V1_OR_LICENSE_DRIFT')
        versions = api.model_instance_versions_list(ref, page_size=20).to_dict()
        require(not versions.get('nextPageToken'), 'MODEL_VERSIONS_PAGINATION_UNEXPECTED')
        entries = versions['versionList']['versions']
        require(len(entries) == 1 and entries[0]['id'] == version_id
                and entries[0]['versionNumber'] == 1 and entries[0]['modelInstanceId'] == instance_id
                and entries[0]['ownerSlug'] == ref.split('/')[0]
                and entries[0]['modelSlug'] == ref.split('/')[1]
                and entries[0]['framework'] == 'MODEL_FRAMEWORK_TRANSFORMERS'
                and entries[0]['variationSlug'] == 'default',
                'MODEL_VERSION_LIST_DRIFT')
        models[ref + '/1'] = {'model_instance_id': instance_id, 'native_version_id': version_id,
                             'version_number': 1,
                             'metadata_sha256': sha(json.dumps(info, sort_keys=True, default=str).encode())}
    require(str(api.kernels_status(REF).status).split('.')[-1] == 'COMPLETE', 'OWNER_NOT_TERMINAL_COMPLETE')
    final_own = public_pull(REF)
    require(final_own['metadata']['currentVersionNumber'] == 21
            and sha(final_own['blob']['source'].encode()) == sha(original), 'OWNER_CHANGED_DURING_CHECK')
    local_checks(args)
    return {'owner_public_version': 21, 'owner_source_sha256': sha(original),
            'owner_full_metadata_sha256': sha(json.dumps(metadata, sort_keys=True).encode()),
            'owner_terminal_status': 'COMPLETE', 'runtime_public_version': 3,
            'runtime_source_sha256': V3_SHA, 'docker_image': IMAGE,
            'datasets': datasets, 'models': models,
            'native_script_version_id': None,
            'native_script_version_note': 'Supported pull API exposes public version number and exact source, not native scriptVersionId.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--expected-candidate-sha256', required=True)
    parser.add_argument('--expected-freeze-sha256', required=True)
    parser.add_argument('--packet', default=str(HERE))
    parser.add_argument('--output-dir')
    parser.add_argument('--check-admission', help='Recheck an existing PASS immediately before root invokes unchanged safe_push.')
    args = parser.parse_args()
    receipt, receipt_sha, _ = local_checks(args)
    if args.check_admission:
        evidence = read_json(args.check_admission)
        require(evidence['schema'] == 'arc3-root-dispatch-admission/1' and evidence['status'] == 'PASS_READ_ONLY_DISPATCH_CHECKS',
                'DISPATCH_RECEIPT_INVALID')
        age(evidence['verified_at_utc'])
        require(evidence['candidate_sha256'] == args.expected_candidate_sha256
                and evidence['candidate_receipt_sha256'] == receipt_sha
                and evidence['source_freeze_sha256'] == args.expected_freeze_sha256
                and evidence['verifier_sha256'] == sha(Path(__file__).read_bytes()), 'DISPATCH_RECEIPT_BINDING_DRIFT')
        print(json.dumps({'status': 'DISPATCH_RECEIPT_VALID', 'candidate_sha256': args.expected_candidate_sha256}))
        return
    parent = Path(args.output_dir).resolve() if args.output_dir else Path(args.receipt).resolve().parent
    output = parent / ('dispatch_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_' + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    _, _, metadata = local_checks(args)
    live = fresh_checks(args, receipt, metadata, output)
    verified = datetime.now(timezone.utc)
    evidence = {'schema': 'arc3-root-dispatch-admission/1', 'status': 'PASS_READ_ONLY_DISPATCH_CHECKS',
                'verified_at_utc': verified.isoformat(), 'checked_at_utc': verified.isoformat(),
                'expires_at_utc': (verified + timedelta(seconds=MAX_AGE)).isoformat(),
                'candidate_sha256': args.expected_candidate_sha256, 'candidate_receipt_sha256': receipt_sha,
                'source_freeze_sha256': args.expected_freeze_sha256, 'verifier_sha256': sha(Path(__file__).read_bytes()),
                'candidate_path': receipt['candidate'], 'fresh_bindings': live,
                'global_job_admission_and_peer_review_still_required': True,
                'launch_performed': False, 'submission_performed': False}
    path = output / 'DISPATCH_ADMISSION.json'
    with path.open('x') as stream:
        json.dump(evidence, stream, indent=2)
    print(json.dumps({'status': evidence['status'], 'admission_receipt': str(path),
                      'sha256': sha(path.read_bytes()), 'verified_at_utc': evidence['verified_at_utc']}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'HOLD_DISPATCH', 'error_type': type(error).__name__,
                          'reason': str(error) if isinstance(error, GateError) else 'DETAILS_NOT_EXPORTED'}), file=sys.stderr)
        raise SystemExit(1)
