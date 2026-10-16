#!/usr/bin/env python3
"""Recover manual examples and ROS application source from an OFFLINE USB image.

Reads Docker metadata/layers directly. Never starts Docker, mounts an image,
executes vendor code, or copies host OS/CUDA/driver libraries. Refuses overwrite.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '.idea', '.ipynb_checkpoints', '__pycache__', '.env',
        'build', 'install', 'log', 'dist', 'core', 'Thumbs.db', '.DS_Store'}
MAPPINGS = {
    'root/Dofbot': 'manual/Dofbot',
    'root/Dofbot_2D': 'manual/Dofbot_2D',
    'root/dofbot_ws/src': 'ros2_ws/src',
}


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def opaque(path):
    try:
        return os.getxattr(path, 'trusted.overlay.opaque') == b'y'
    except OSError:
        return False


def whiteout(path):
    try:
        st = path.lstat()
        return stat.S_ISCHR(st.st_mode) and st.st_rdev == 0
    except FileNotFoundError:
        return False


def merge(source, target):
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        remove(target)
    target.mkdir(parents=True, exist_ok=True)
    if opaque(source):
        for child in target.iterdir(): remove(child)
    for entry in sorted(source.iterdir()):
        if (entry.name in SKIP or entry.suffix in {'.pyc', '.swp', '.swo', '.egg', '.iml'}
                or entry.name.endswith('~') or re.fullmatch(r'core\.\d+', entry.name)): continue
        output = target / entry.name
        if whiteout(entry):
            remove(output)
        elif entry.name == '.wh..wh..opq':
            for child in target.iterdir(): remove(child)
        elif entry.name.startswith('.wh.'):
            remove(target / entry.name[4:])
        elif entry.is_symlink():
            remove(output)
            output.symlink_to(os.readlink(entry))
        elif entry.is_dir():
            merge(entry, output)
        elif entry.is_file():
            remove(output)
            shutil.copyfile(entry, output)
            output.chmod(stat.S_IMODE(entry.stat().st_mode))


def redact_credentials(source):
    pattern = re.compile(r"(API_KEY|SECRET_KEY|ACCESS_TOKEN)(\s*=\s*)([\"'])([^\"']{12,})\3", re.I)
    return pattern.sub(lambda m: m[1] + m[2] + '__import__("os").environ["YAHBOOM_' + m[1].upper() + '"]', source)


def recover(layers, destination_root):
    for layer in layers:
        for prefix, relative in MAPPINGS.items():
            destination = destination_root / relative
            ancestor = layer
            deleted = False
            for part in Path(prefix).parts:
                ancestor = ancestor / part
                if whiteout(ancestor):
                    remove(destination); deleted = True; break
                if ancestor.is_dir() and opaque(ancestor):
                    remove(destination)
            if not deleted and (layer / prefix).is_dir():
                merge(layer / prefix, destination)


def restore_missing_assets(recovered):
    uid, gid = PROJECT.stat().st_uid, PROJECT.stat().st_gid
    copied = 0
    for source in sorted(recovered.rglob('*')):
        if source.is_symlink() or not source.is_file():
            continue
        destination = PROJECT / 'vendor' / source.relative_to(recovered)
        if not destination.resolve().is_relative_to(PROJECT.resolve()):
            raise RuntimeError('Asset destination escapes project through a symlink')
        check = subprocess.run(['git', '-c', 'safe.directory=' + str(PROJECT.parent),
                                '-C', str(PROJECT.parent), 'check-ignore', '-q', '--',
                                str(destination)], check=False)
        if check.returncode not in (0, 1):
            raise RuntimeError('Could not determine Git asset exclusions')
        if check.returncode == 1 or destination.exists():
            continue  # Preserve tracked code and every existing local file.
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        destination.chmod(stat.S_IMODE(source.stat().st_mode))
        os.chown(destination, uid, gid)
        parent = destination.parent
        while parent != PROJECT:
            os.chown(parent, uid, gid); parent = parent.parent
        copied += 1
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--usb-root', type=Path, required=True)
    parser.add_argument('--tag', default='3.0.2')
    parser.add_argument('--assets-only', action='store_true', help='Restore missing Git-ignored runtime assets without overwriting code or existing files')
    args = parser.parse_args()
    storage = args.usb_root / 'var/lib/docker'
    image = storage / 'image/overlay2'
    repository = '192.168.2.51:5000/dofbot_ai'
    refs = json.loads((image / 'repositories.json').read_text())['Repositories'][repository]
    image_id = refs[f'{repository}:{args.tag}']
    config = json.loads((image / 'imagedb/content/sha256' / image_id.split(':')[1]).read_text())
    layers, chain = [], ''
    for diff in config['rootfs']['diff_ids']:
        chain = diff if not chain else 'sha256:' + hashlib.sha256((chain + ' ' + diff).encode()).hexdigest()
        cache = (image / 'layerdb/sha256' / chain.split(':')[1] / 'cache-id').read_text().strip()
        layers.append(storage / 'overlay2' / cache / 'diff')
    if args.assets_only:
        with tempfile.TemporaryDirectory(prefix='.vendor-import-', dir=PROJECT) as scratch:
            recovered = Path(scratch)
            recover(layers, recovered)
            count = restore_missing_assets(recovered)
        print(f'Restored {count} missing ignored assets; code and existing files preserved.')
        return
    for target in MAPPINGS.values():
        if (PROJECT / 'vendor' / target).exists():
            raise RuntimeError(f'Refusing overwrite: vendor/{target}')
    recover(layers, PROJECT / 'vendor')
    files, links = [], []
    for relative in MAPPINGS.values():
        root = PROJECT / 'vendor' / relative
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                links.append({'path': str(path.relative_to(PROJECT)), 'target': os.readlink(path)})
                continue
            if not path.is_file(): continue
            if path.suffix == '.ipynb':
                notebook = json.loads(path.read_text())
                notebook.get('metadata', {}).pop('widgets', None)
                notebook.setdefault('metadata', {})['kernelspec'] = {'name': 'dofbot', 'display_name': 'DOFBOT (Jetson host)', 'language': 'python'}
                for cell in notebook.get('cells', []):
                    if cell.get('cell_type') == 'code':
                        cell['outputs'] = []; cell['execution_count'] = None
                    cell.get('metadata', {}).pop('trusted', None)
                    if cell.get('cell_type') == 'code':
                        cell['source'] = redact_credentials(''.join(cell.get('source', []))).splitlines(keepends=True)
                path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n')
            elif path.suffix == '.py':
                path.write_text(redact_credentials(path.read_text()))
            payload = path.read_bytes()
            files.append({'path': str(path.relative_to(PROJECT)), 'bytes': len(payload),
                          'sha256': hashlib.sha256(payload).hexdigest()})
    manifest = PROJECT / 'docs/vendor-import-manifest.json'
    manifest.write_text(json.dumps({'image': f'{repository}:{args.tag}', 'image_id': image_id,
                                  'architecture': config['architecture'], 'files': files,
                                  'symlinks': links, 'notebook_outputs_removed': True,
                                  'notebook_kernel': 'dofbot', 'embedded_credentials_replaced_by_environment': True,
                                  'crash_dumps_excluded': True}, indent=2) + '\n')
    # Files remain editable by the repository owner when imported with sudo.
    uid, gid = PROJECT.stat().st_uid, PROJECT.stat().st_gid
    for relative in MAPPINGS.values():
        root = PROJECT / 'vendor' / relative
        for path in [root, *root.rglob('*')]: os.chown(path, uid, gid, follow_symlinks=False)
        parent = root.parent
        while parent != PROJECT:
            os.chown(parent, uid, gid); parent = parent.parent
    os.chown(manifest, uid, gid)
    print(f'Recovered {len(files)} files ({sum(p["bytes"] for p in files)} bytes), {len(links)} symlinks.')
    print('No container or vendor program was started. Model/binary assets stay Git-ignored.')


if __name__ == '__main__':
    main()
