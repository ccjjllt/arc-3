"""Original stdlib support for fresh ARC3 canary copies; never delete or replace."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import shutil
import stat
import subprocess


def validate_patch(patch_text):
    paths = []
    current = None
    for line in patch_text.splitlines():
        if line.startswith(('deleted file mode ', 'rename from ', 'rename to ', 'copy from ', 'copy to ')):
            raise ValueError('PATCH_DELETION_RENAME_OR_COPY_REFUSED')
        if line.startswith(('new file mode ', 'old mode ', 'new mode ')) and line.split()[-1] not in {'100644', '100755'}:
            raise ValueError('PATCH_NONREGULAR_FILE_MODE_REFUSED')
        if line.startswith(('--- ', '+++ ')):
            name = line[4:]
            expected = ('a/' if line.startswith('--- ') else 'b/') + str(current)
            if current is None or name not in {expected, '/dev/null'}:
                raise ValueError('PATCH_HEADER_PATH_MISMATCH')
            if line.startswith('+++ ') and name == '/dev/null':
                raise ValueError('PATCH_FILE_DELETION_REFUSED')
        if not line.startswith('diff --git '):
            continue
        pieces = line.split()
        if len(pieces) != 4 or not pieces[2].startswith('a/') or not pieces[3].startswith('b/'):
            raise ValueError('UNEXPECTED_PATCH_HEADER')
        left, right = pieces[2][2:], pieces[3][2:]
        if left != right:
            raise ValueError('PATCH_PATH_IDENTITY_CHANGE_REFUSED')
        path = PurePosixPath(left)
        if path.is_absolute() or '..' in path.parts or not left.startswith('ARC3-Inference/'):
            raise ValueError('PATCH_OUTSIDE_EXPECTED_SOURCE_TREE')
        if path.suffix == '.ipynb' or path.name == 'kernel-metadata.json':
            raise ValueError('PATCH_NOTEBOOK_ARTIFACT_REFUSED')
        paths.append(left)
        current = left
    if not paths or len(paths) != len(set(paths)):
        raise ValueError('EMPTY_OR_DUPLICATE_PATCH_TARGETS')
    return paths


def prepare_bundle(source, destination, patch_file):
    source, destination, patch_file = map(Path, (source, destination, patch_file))
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Existing run bundle preserved; use a new run directory')
    paths = validate_patch(patch_file.read_text())
    files = []
    total_bytes = 0
    entry_count = 0
    for entry in source.rglob('*'):
        entry_count += 1
        if entry_count > 2048:
            raise ValueError('SOURCE_ENTRY_BUDGET_EXCEEDED')
        mode = entry.lstat().st_mode
        if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise ValueError('SOURCE_SYMLINK_OR_SPECIAL_FILE_REFUSED')
        if entry.is_file():
            files.append(entry)
            total_bytes += entry.stat().st_size
            if len(files) > 512 or total_bytes > 16 * 1024 * 1024:
                raise ValueError('SMALL_SOURCE_BUNDLE_BUDGET_EXCEEDED')
    # copytree refuses an existing destination. A partial copy is retained on error.
    shutil.copytree(source, destination, symlinks=False)
    copied = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for name, expected in copied.items():
        if hashlib.sha256((destination / name).read_bytes()).hexdigest() != expected:
            raise ValueError('COPIED_SOURCE_HASH_MISMATCH')
    command = ['git', 'apply', '--include=ARC3-Inference/*', str(patch_file.resolve())]
    patch_env = os.environ.copy()
    for key in ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR']:
        patch_env.pop(key, None)
    # Do not let a surrounding research checkout change Git's path interpretation.
    patch_env['GIT_CEILING_DIRECTORIES'] = str(destination.resolve())
    subprocess.run(command[:2] + ['--check'] + command[2:], cwd=destination / 'src', env=patch_env, check=True)
    subprocess.run(command, cwd=destination / 'src', env=patch_env, check=True)
    receipt = {'copied_source_sha256': copied, 'patched_paths': paths,
               'patch_sha256': hashlib.sha256(patch_file.read_bytes()).hexdigest(),
               'source_unchanged': all(hashlib.sha256(p.read_bytes()).hexdigest() == copied[str(p.relative_to(source))] for p in files)}
    if not receipt['source_unchanged']:
        raise RuntimeError('READ_ONLY_SOURCE_CHANGED')
    with (destination.parent / 'bundle_copy_receipt.json').open('x') as output:
        json.dump(receipt, output, indent=2)
    return destination
