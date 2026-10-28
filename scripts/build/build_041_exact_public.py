"""Prepare original public scoredv83 cells without any source modifications."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import copy
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / 'experiments/037-highscore-source/the-agi-boys-i-am-better-v83.ipynb'
EXPECTED = '8221f1e64ad7d4c8b3ecbbcbd83f68c9469707246484b0bbcaa5254da809905e'
OUT = ROOT / 'notebooks/041-exact-public-v83'


def source(cell):
    value = cell['source']
    return ''.join(value) if isinstance(value, list) else value


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(ORIGINAL) == EXPECTED
    original = json.loads(ORIGINAL.read_text())
    assert len(original['cells']) == 23
    notebook = copy.deepcopy(original)
    # Remove only previous execution artifacts. Never rewrite any source string,
    # including its native %%writefile directive and line endings.
    for cell in notebook['cells']:
        cell['metadata'] = {}
        if cell['cell_type'] == 'code':
            cell['outputs'] = []
            cell['execution_count'] = None
    notebook['metadata'].pop('papermill', None)
    notebook['metadata'].setdefault('kaggle', {}).update(
        accelerator='nvidiaRtxPro6000', isGpuEnabled=True, isInternetEnabled=False)
    metadata = json.loads((ROOT / 'notebooks/038-highscore-baseline-jiyujia/kernel-metadata.json').read_text())
    metadata.update(id='jiyujia/arc3-041-exact-public-v83',
                    title='ARC3 041 Exact Public V83', code_file='submission.ipynb')
    compared = []
    compiled = []
    for index, (left, right) in enumerate(zip(original['cells'], notebook['cells'])):
        assert left['cell_type'] == right['cell_type'] and left['source'] == right['source']
        compared.append({'index': index, 'same_source_value': True,
                         'source_sha256': hashlib.sha256(source(left).encode()).hexdigest()})
        if right['cell_type'] != 'code':
            continue
        text = source(right)
        if text.startswith('%%writefile '):
            continue
        text = '\n'.join('pass  # retained shell magic' if line.lstrip().startswith('!') else line
                         for line in text.splitlines())
        compile(text, f'<041-cell-{index}>', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        compiled.append(index)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'submission.ipynb'
    path.write_text(json.dumps(notebook, indent=1) + '\n')
    assert path.stat().st_size < 1_000_000
    (OUT / 'kernel-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    result = {
        'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
        'kernel_ref': metadata['id'], 'cell_count': 23,
        'notebook_sha256': sha(path), 'bytes': path.stat().st_size,
        'upstream_ref': 'romantamrazov/the-agi-boys-i-am-better',
        'upstream_version': 83, 'upstream_script_version_id': 359573474,
        'upstream_historical_public_score': 35.35,
        'original_file_sha256': EXPECTED, 'all_23_sources_identical': True,
        'source_comparison': compared, 'compiled_code_cells': compiled,
        'source_modifications': [], 'solver_interventions': [],
        'execution_artifact_changes': ['Clear old outputs/execution counts/cell metadata',
                                       'Remove notebook papermill execution metadata'],
        'platform_changes': ['Private jiyujia ownership/title',
                             'Explicit RTX PRO6000 GPU: correct upstream isGpuEnabledfalse metadata discrepancy',
                             'Reuse v83Docker31401 and exact5input-version pins'],
        'save_behavior': 'Original10public-game25minute demo, no short-save adapter',
        'formal_behavior': 'Original gateway,1pass,120tasks,10streams,31920s,soft_endNone',
        'formal_submission_not_created': True,
    }
    (OUT / 'build-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    frozen = ROOT / 'experiments/041-submission-source'
    assert not frozen.exists(), 'Do not overwrite an existing frozen041 candidate'
    shutil.copytree(OUT, frozen)
    print(json.dumps({k: result[k] for k in ['kernel_ref','notebook_sha256','bytes','cell_count','all_23_sources_identical']}, indent=2))


if __name__ == '__main__':
    main()
