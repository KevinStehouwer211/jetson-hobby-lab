#!/usr/bin/env bash
set -e
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [ ! -x "$project_dir/.venv/bin/python3" ]; then
    echo "Run $project_dir/tools/setup_env.sh first." >&2
    exit 2
fi
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
fi
export PATH="$project_dir/.venv/bin:$PATH"
export PYTHONPATH="$project_dir/colcon_ws/src/Arm_Lib:$project_dir/colcon_ws/src/dofbot_utils/src${PYTHONPATH:+:$PYTHONPATH}"
export JUPYTER_PATH="$project_dir/.jupyter/share/jupyter${JUPYTER_PATH:+:$JUPYTER_PATH}"
export JUPYTER_CONFIG_DIR="$project_dir/.jupyter/config"
export IPYTHONDIR="$project_dir/.ipython"
if [ "$#" -eq 0 ]; then
    set -- "$project_dir/diagnostics/servo_diagnostic.py"
fi
exec "$project_dir/.venv/bin/python3" "$@"
