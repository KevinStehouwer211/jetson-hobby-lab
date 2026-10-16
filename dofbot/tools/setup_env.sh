#!/usr/bin/env bash
# Create only a local venv/kernel. Reuse existing Jetson packages; no pip/apt upgrades.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [ ! -f "$project_dir/.venv/pyvenv.cfg" ]; then
    /usr/bin/python3 -m venv --system-site-packages --without-pip "$project_dir/.venv"
fi
"$project_dir/.venv/bin/python3" - "$project_dir" <<'PY'
import importlib.util
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
for module in ['smbus', 'smbus2']:
    if importlib.util.find_spec(module) is None:
        raise SystemExit(f'Missing dependency: {module}. No global changes were made.')
if importlib.util.find_spec('ipykernel'):
    directory = root / '.jupyter/share/jupyter/kernels/dofbot'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'kernel.json').write_text(json.dumps({
        'argv': [str(root / '.venv/bin/python3'), '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
        'display_name': 'DOFBOT (Jetson host)', 'language': 'python'
    }, indent=2) + '\n')
print('Local environment ready:', root / '.venv')
print('No apt/pip installs, global kernel registration, or hardware commands.')
PY
