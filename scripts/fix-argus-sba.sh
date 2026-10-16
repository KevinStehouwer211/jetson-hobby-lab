#!/usr/bin/env bash
# Build Argus's bundled SBA libraries for the current Linux architecture.
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${1:-"$repo_dir/argus_env/bin/python"}
resources=$("$python_bin" - <<'PY'
import pathlib
import sys
import sysconfig

if sys.platform != 'linux' or sys.prefix == sys.base_prefix:
    raise SystemExit('Run this with a Linux virtual environment Python.')
path = pathlib.Path(sysconfig.get_path('purelib')) / 'argus_gui' / 'resources'
if not (path / 'sba_lib_sources.tar.gz').is_file():
    raise SystemExit(f'Missing Argus SBA sources in {path}')
print(path)
PY
)

build_dir=$(mktemp -d)
trap 'rm -rf -- "$build_dir"' EXIT
# Extract only source files; the archive also contains stale compiled headers.
tar -xzf "$resources/sba_lib_sources.tar.gz" -C "$build_dir" \
    --wildcards --no-wildcards-match-slash './sba-1.6p/*.c' './sba-1.6p/*.h' \
    './sba-1.6p/libsbaprojs/*.c' './sba-1.6p/libsbaprojs/*.h'
cd "$build_dir/sba-1.6p"
"${CC:-gcc}" -O3 -fPIC -shared -Wl,-z,defs -o libsba.so \
    sba_levmar.c sba_levmar_wrap.c sba_lapack.c sba_crsm.c sba_chkjac.c \
    -llapack -lblas -lm
"${CC:-gcc}" -O3 -fPIC -shared -Wl,-z,defs -I. -o libsbaprojs.so \
    libsbaprojs/sbaprojs.c libsbaprojs/imgproj.c \
    -L. -lsba -Wl,-rpath,'$ORIGIN' -lm
# Validate both libraries before placing them in the environment.
"$python_bin" - <<'PY'
import ctypes
from pathlib import Path
for name in ('libsba.so', 'libsbaprojs.so'):
    ctypes.CDLL(str(Path(name).resolve()))
PY
install -m 755 libsba.so libsbaprojs.so "$resources/"
printf 'Installed Linux SBA libraries in %s\n' "$resources"
