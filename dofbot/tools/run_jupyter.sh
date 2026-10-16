#!/usr/bin/env bash
set -e
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
lab_app_dir="$("$project_dir/tools/run_python.sh" -c 'from pathlib import Path; from jupyter_core.paths import jupyter_path; paths=[p for p in jupyter_path("lab") if (Path(p)/"static/index.html").is_file()]; assert paths, "Installed JupyterLab web assets not found"; print(paths[0])')"
exec "$project_dir/tools/run_python.sh" -m jupyterlab --LabApp.app_dir="$lab_app_dir" \
    --ServerApp.root_dir="$project_dir" --ServerApp.ip=127.0.0.1 \
    --ServerApp.open_browser=False "$@"
