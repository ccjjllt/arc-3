"""Build the minimal model-readiness repair on the exact041 public source."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import copy
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'notebooks/041-exact-public-v83/submission.ipynb'
BASE_SHA = '3efa7a1cc75156e62599daca754b6349f513ba7591a8d08da30fa4716c549d34'
FRAGMENT = ROOT / 'experiments/042-preparation/readiness-wait.py.txt'
OUT = ROOT / 'notebooks/042-startup-ready'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source(cell):
    s = cell['source']
    return ''.join(s) if isinstance(s, list) else s


def main():
    assert sha(BASE) == BASE_SHA
    baseline = json.loads(BASE.read_text())
    notebook = copy.deepcopy(baseline)
    assert len(notebook['cells']) == 23
    setup = source(notebook['cells'][4])
    assert setup.count('SERVER_STARTUP_TIMEOUT = 12 * 60') == 1
    setup = setup.replace('SERVER_STARTUP_TIMEOUT = 12 * 60', 'SERVER_STARTUP_TIMEOUT = 90 * 60', 1)
    old_comment = (
        '# Kaggle might cancel the run in no action is done in some timeframe.\n'
        '# To prevent this, harness will start up even if backend is not yet ready,\n'
        '# and the first started game will perform a single reset action.\n')
    assert old_comment in setup
    setup = setup.replace(old_comment,
        '# Wait for model readiness before the benchmark opens its scorecard.\n'
        '# Retain the original initial RESET and request retry settings.\n', 1)
    notebook['cells'][4]['source'] = setup.splitlines(keepends=True)
    original_launcher = source(baseline['cells'][12])
    anchor = 'url, t0 = '
    assert original_launcher.count(anchor) == 1
    prefix = original_launcher[:original_launcher.index(anchor)]
    fragment = FRAGMENT.read_text()
    compile(fragment, str(FRAGMENT), 'exec')
    notebook['cells'][12]['source'] = (prefix + fragment).splitlines(keepends=True)
    for cell in notebook['cells']:
        cell['metadata'] = {}
        if cell['cell_type'] == 'code':
            cell['execution_count'] = None
            cell['outputs'] = []
    changed = [i for i, (a, b) in enumerate(zip(baseline['cells'], notebook['cells'])) if source(a) != source(b)]
    assert changed == [4, 12]
    assert source(notebook['cells'][12]).startswith(prefix)
    compiled = []
    for i, cell in enumerate(notebook['cells']):
        if cell['cell_type'] != 'code':
            continue
        s = source(cell)
        if s.startswith('%%writefile '):
            continue
        s = '\n'.join('pass  # retained native shell magic' if line.lstrip().startswith('!') else line for line in s.splitlines())
        compile(s, f'<042-cell-{i}>', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        compiled.append(i)
    metadata = json.loads(BASE.with_name('kernel-metadata.json').read_text())
    metadata.update(id='jiyujia/arc3-042-startup-ready', title='ARC3 042 Startup Ready')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'submission.ipynb'
    path.write_text(json.dumps(notebook, indent=1) + '\n')
    (OUT / 'kernel-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    assert path.stat().st_size < 1_000_000
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in [BASE, FRAGMENT, Path(__file__).resolve()]}
    manifest = {
        'prepared_at_utc': datetime.now(timezone.utc).isoformat(), 'kernel_ref': metadata['id'],
        'notebook_sha256': sha(path), 'bytes': path.stat().st_size, 'cell_count': 23,
        'base_sha256': BASE_SHA, 'source_hashes': hashes, 'changed_cell_indices': changed,
        'change': '90min maximum initial model wait plus required health200/liveprocess before benchmark',
        'solver_interventions': [], 'models_prompts_sampling_scheduler_unchanged': True,
        'formal_gateway_source_unchanged': True, 'original_demo_retained': True,
        'original_model_launch_command_unchanged': True, 'compiled_code_cells': compiled,
        'formal_platform_timeout_seconds': 32400, 'maximum_startup_seconds': 5400,
        'original_save_per_game_seconds': 1500, 'original_save_games': 10,
        'original_formal_solver_seconds': 31920,
        'readiness_report': 'startup-readiness.json',
        'source_basis': 'Local041zero lifecycle audit and contributor753489 control report; not proven cause of041.',
        'risk': 'Kaggle notebook-level inactivity and infrastructure failure remain possible; formal9h cap includes startup.',
        'status': 'BUILT_LOCALLY_NOT_RUN_OR_SUBMITTED',
    }
    (OUT / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    archive = ROOT / 'experiments/042-submission-source'
    assert not archive.exists(), 'Inspect any prior frozen042 before replacing'
    shutil.copytree(OUT, archive)
    for relative in hashes:
        target = archive / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    print(json.dumps({k: manifest[k] for k in ['kernel_ref','notebook_sha256','bytes','cell_count','changed_cell_indices']}, indent=2))


if __name__ == '__main__':
    main()
