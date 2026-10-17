#!/usr/bin/env python3
"""Manual 014 tail-allocation packaging check; writes only to a temporary directory."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone

from IPython.core.interactiveshell import InteractiveShell
from IPython.core.inputtransformer2 import TransformerManager
from IPython.utils.capture import capture_output
import nbformat

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notebook-dir', type=Path, default=ROOT / 'notebooks/014-tail-allocation')
    parser.add_argument('--report', type=Path, default=ROOT / 'experiments/014-notebook-checks.json')
    args = parser.parse_args()
    nb_path = args.notebook_dir / 'experiment.ipynb'
    notebook = nbformat.read(nb_path, as_version=4)
    nbformat.validate(notebook)
    manifest = json.loads((args.notebook_dir / 'build-manifest.json').read_text())
    meta = json.loads((args.notebook_dir / 'kernel-metadata.json').read_text())
    config = json.loads((ROOT / 'experiments/014-tail-allocation.json').read_text())
    reference = json.loads((ROOT / 'experiments/005-full-baseline.json').read_text())
    assert manifest['notebook_sha256'] == sha(nb_path)
    assert config == manifest['config']
    assert config['games'] == reference['games']
    assert len(config['games']) == 25 and config['requested_arm_seconds'] == 7254
    assert config['arm_order'] == ['baseline', 'tail_80k']
    assert config['reference_arm'] == 'baseline'
    for key in ['inference_timing','scheduler_observer','request_deadline','strict_arm_budget',
                'preflight_before_serving','require_cache_flush_log','require_drained_workers','require_complete_pool']:
        assert config[key] is True, key
    assert config['arm_environment'] == {
        'baseline': {'ARC3_PRIORITY_TAIL_LOOKUP':'remaining','ARC3_PRIORITY_PACE':'0'},
        'tail_80k': {'ARC3_PRIORITY_TAIL_LOOKUP':'1','ARC3_PRIORITY_PACE':'0'},
    }
    preflight_cells = [i for i,c in enumerate(notebook.cells) if 'arc3_research.preflight' in c.source and 'subprocess.run' in c.source and not c.source.startswith('%%writefile')]
    launcher_cells = [i for i,c in enumerate(notebook.cells) if c.source.startswith('# Paste this entire file into the launcher cell.')]
    assert len(preflight_cells) == len(launcher_cells) == 1 and preflight_cells[0] < launcher_cells[0]
    reference_manifest = json.loads((ROOT / 'experiments/010-source/build-manifest.json').read_text())
    assert manifest['base_source_sha256'] == reference_manifest['base_source_sha256']
    assert config['native_payload_cells'] is True
    assert meta['is_private'] is True and meta['enable_gpu'] is True and meta['enable_internet'] is False
    assert meta['machine_shape'] == 'NvidiaRtxPro6000' and 'id_no' not in meta
    assert meta['id'] == config['kernel_id'] and meta['code_file'] == nb_path.name
    for relative, expected in manifest['source_hashes'].items():
        assert sha(ROOT / relative) == expected, relative
    transformer = TransformerManager()
    source_cells = []
    for index, item in enumerate(notebook.cells):
        if item.cell_type != 'code':
            continue
        transformed = transformer.transform_cell(item.source)
        compile(transformed, f'cell-{index}', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        tree = ast.parse(transformed)
        wrappers = [n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name) and n.func.id in {'exec', 'compile', 'eval'}]
        assert not wrappers, (index, wrappers)
        source_cells.append(index)
    shell = InteractiveShell.instance()
    helper_records = []
    with tempfile.TemporaryDirectory(prefix='arc3-014-notebook-') as temporary:
        temp = Path(temporary)
        for index, item in enumerate(notebook.cells):
            if not item.source.startswith('%%writefile /kaggle/research/'):
                continue
            header, body = item.source.split('\n', 1)
            relative = header.removeprefix('%%writefile /kaggle/research/')
            target = temp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            source = header.replace('/kaggle/research/', str(temp) + '/') + '\n' + body
            with capture_output():
                result = shell.run_cell(source, store_history=False)
            result.raise_error()
            assert sha(target) == manifest['source_hashes'][relative], relative
            ast.parse(target.read_text())
            helper_records.append({'cell': index, 'source': relative, 'sha256': sha(target),
                                   'bytes': target.stat().st_size, 'ends_with_lf': target.read_bytes().endswith(b'\n')})
        expected_helpers = [p for p in manifest['source_hashes'] if p.startswith('src/arc3_research/')]
        expected_helpers.append('scripts/summarize_experiment.py')
        assert {r['source'] for r in helper_records} == set(expected_helpers)
        patch_cells = [c.source for c in notebook.cells if c.source.startswith('%%writefile /kaggle/harness-changes.patch')]
        baseline = json.loads((ROOT / 'research/notebooks/cli-baseline/arc-agi-3-milestone-2-solution.ipynb').read_text())
        original_patch = ''.join(baseline['cells'][2]['source'])
        assert patch_cells == [original_patch]
        patch_path = temp / 'harness-changes.patch'
        with capture_output():
            result = shell.run_cell(original_patch.replace('/kaggle/harness-changes.patch', str(patch_path), 1), store_history=False)
        result.raise_error()
        checked = subprocess.run(['git', 'apply', '--stat', str(patch_path)], text=True, capture_output=True, check=True)
        assert patch_path.read_bytes().endswith(b'\n')
        patch_record = {'source_cell_equal_to_original': True, 'written_sha256': sha(patch_path),
                        'ends_with_lf': True, 'git_apply_stat_returncode': checked.returncode}
    record = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'notebook': str(nb_path.relative_to(ROOT)),
              'notebook_sha256': sha(nb_path), 'notebook_cells': len(notebook.cells),
              'compiled_native_code_cells': source_cells, 'no_added_exec_compile_eval_cell_wrappers': True,
              'payload_helpers_written_via_ipython_and_hash_matched': helper_records, 'inherited_patch': patch_record,
              'frozen_25_game_pool_and_budgets_match': True, 'cpu_preflight_before_model_launcher': True, 'single_tail_factor': True,
              'arm_order': config['arm_order'], 'summary_reference': config['reference_arm'],
              'passive_timing_both_arms': config['inference_timing'], 'shared_deadline_and_scheduler_observer': True, 'private_gpu_offline_metadata_valid': True,
              'boundary': 'CPU packaging only. Does not execute installation, model serving, solver, or remote notebook.'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'report': str(args.report), 'notebook_sha256': record['notebook_sha256'],
                      'code_cells': len(source_cells), 'helpers_written_and_hash_matched': len(helper_records),
                      'inherited_patch_stat_passed': True}, indent=2))


if __name__ == '__main__':
    main()
