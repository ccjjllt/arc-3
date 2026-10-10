# Cell 0 (markdown)
# # Flash Duck-transfer arena competition candidate
# Public validation: 110 independent cyclic replicas of the 20 public games,
# 1800 s of gameplay. Competition rerun: discover the hidden gateway roster,
# nine hours total including setup and a ten-minute cleanup reserve.
# One RTX PRO 6000 Blackwell 96 GB; fixed winning model/agent/scheduler settings.
# Public replicas test scaling and stability, not hidden-game generalization.
# The gateway records actions and creates the real submission artifact.

# Cell 1 (code)
from pathlib import Path
import hashlib, json, subprocess, sys, tarfile, time
assert sys.version_info[:2] == (3, 12), 'Select the Python 3.12 notebook image'
NOTEBOOK_START_EPOCH = time.time()
roots = [Path('/kaggle/input/datasets/richardcsaky/arc-arena-hero-v2-runb-runtime'), Path('/kaggle/input/arc-arena-hero-v2-runb-runtime')]
mount = next((p for p in roots if p.is_dir()), None)
assert mount is not None, 'Attach the prepared richardcsaky/arc-arena-hero-v2-runb-runtime dataset'
blob = mount / 'arena-flash-competition-hero-v2-runb-v1.tar.gz.blob'
with blob.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == '9733cae149b3fecdc58b1bf1bb12c9dba98f039cf473f71fe77ad5d6008a4cb5', 'Runtime archive differs from reviewed build'
bundle = Path('/tmp/arena-runtime')
bundle.mkdir(exist_ok=False)
with tarfile.open(blob, 'r:gz') as archive:
    archive.extractall(bundle, filter='data')
command = [sys.executable, str(bundle / 'bootstrap_arena.py'), '--bundle', str(bundle), '--working', '/tmp/arena',
           '--output', '/kaggle/working/arena', '--max-seconds', '4500', '--notebook-start-epoch', str(NOTEBOOK_START_EPOCH)]
result = subprocess.run(command, check=False)
print(json.dumps({'bootstrap_exit': result.returncode, 'elapsed': time.time() - NOTEBOOK_START_EPOCH}))

# Cell 2 (code)
import json, os
from pathlib import Path
EXPECTED_PREVIEW_TRIALS = 1
rerun = os.environ.get('KAGGLE_IS_COMPETITION_RERUN', '').lower() in ('1', 'true')
report_path = Path('/kaggle/working/arena/trials/study.json')
if not report_path.is_file():
    raise RuntimeError(f'Arena stopped before final report: bootstrap_exit={result.returncode}')
record = json.loads(report_path.read_text())
acceptable = {'complete', 'complete_with_preemptions', 'error'} if rerun else {'complete'}
trials = record.get('trials', [])
expected = 1 if rerun else EXPECTED_PREVIEW_TRIALS
# On the hidden rerun the gateway scorecard is already closed: only a missing or unacceptable
# gateway trial fails the notebook, never the bootstrap exit code or the preview-only checks.
if len(trials) != expected or any(t.get('status') not in acceptable for t in trials) or (result.returncode and not rerun):
    raise RuntimeError('Arena validation failed; inspect saved runtime and trial reports')
for row in record.get('comparison', []):
    print(json.dumps(row))
if not rerun:
    import pandas as pd
    pd.DataFrame([['1_0', '1', True, 1]],
                 columns=['row_id', 'game_id', 'end_of_game', 'score']).to_parquet(
                     '/kaggle/working/submission.parquet', index=False)
    print('Public validation completed. The placeholder selects the notebook for a hidden rerun.')
else:
    print('Hidden gateway scorecard closed; the competition gateway produces the submission artifact.')

