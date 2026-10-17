#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$script_dir/../.." && pwd)"
if [ "$#" -eq 0 ]; then
    set -- read_angles.py
fi
case "$1" in
    read_angles.py|write_angle.py|write_read_angle.py|set_dofbot.py)
        script="$script_dir/$1"
        shift
        ;;
    *)
        echo "Usage: $0 [read_angles.py|write_angle.py|write_read_angle.py|set_dofbot.py] [options]" >&2
        exit 2
        ;;
esac
exec "$repo_dir/dofbot/tools/run_python.sh" "$script" "$@"
