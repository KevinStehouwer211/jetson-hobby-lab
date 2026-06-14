#!/usr/bin/env bash
#
# check-env.sh — sanity-check a Jetson dev container (Isaac ROS or custom).
# Run this from *inside* the container after launching it.
#
# Exit code is non-zero if any required check fails.

# Don't use `set -e`: we want every check to run and report, not stop on the first failure.

PASS=0
FAIL=0
SKIP=0

green() { printf '\033[0;32m%s\033[0m\n' "$1"; }
red()   { printf '\033[0;31m%s\033[0m\n' "$1"; }
yellow(){ printf '\033[0;33m%s\033[0m\n' "$1"; }

# check <label> <command...> — runs the command, prints PASS/FAIL with its output.
check() {
    local label="$1"; shift
    local out
    if out=$("$@" 2>&1); then
        green "  [PASS] $label"
        [ -n "$out" ] && printf '         %s\n' "$(echo "$out" | head -n 2)"
        PASS=$((PASS + 1))
    else
        red "  [FAIL] $label"
        [ -n "$out" ] && printf '         %s\n' "$(echo "$out" | head -n 2)"
        FAIL=$((FAIL + 1))
    fi
}

# skip_if_missing <binary> — returns 0 (skip) and logs if a tool isn't installed.
have() { command -v "$1" >/dev/null 2>&1; }

echo "=============================================="
echo " Jetson container environment check"
echo "=============================================="

echo ""
echo "Workspace:"
echo "  pwd: $(pwd)"
if [ -d "src" ]; then
    green "  [PASS] src/ exists ($(ls src 2>/dev/null | wc -l) entries)"
    PASS=$((PASS + 1))
else
    yellow "  [SKIP] no src/ here — are you at the workspace root?"
    SKIP=$((SKIP + 1))
fi

echo ""
echo "ROS 2:"
if [ -n "$ROS_DISTRO" ]; then
    green "  [PASS] ROS_DISTRO=$ROS_DISTRO"
    PASS=$((PASS + 1))
else
    red "  [FAIL] ROS_DISTRO not set (did you source the install?)"
    FAIL=$((FAIL + 1))
fi
if have ros2; then
    check "ros2 topic list" ros2 topic list
    # ros2 doctor is ROS 2's own health check — reuse it rather than reimplement.
    check "ros2 doctor" bash -c "ros2 doctor 2>&1 | tail -n 1"
else
    yellow "  [SKIP] ros2 not on PATH"
    SKIP=$((SKIP + 1))
fi

echo ""
echo "GPU / CUDA:"
# nvidia-smi is unreliable on Jetson's iGPU (often errors even when CUDA works),
# so treat it as informational only — the PyTorch check below is authoritative.
if have nvidia-smi; then
    if out=$(nvidia-smi -L 2>&1); then
        green "  [PASS] nvidia-smi (GPU visible)"
        printf '         %s\n' "$(echo "$out" | head -n 1)"
        PASS=$((PASS + 1))
    else
        yellow "  [INFO] nvidia-smi errored — normal on Jetson iGPU; use tegrastats/jtop instead"
        printf '         %s\n' "$(echo "$out" | head -n 1)"
        SKIP=$((SKIP + 1))
    fi
else
    yellow "  [SKIP] nvidia-smi not installed"
    SKIP=$((SKIP + 1))
fi
if have nvcc; then
    check "nvcc --version" bash -c "nvcc --version | tail -n 2 | head -n 1"
else
    yellow "  [SKIP] nvcc not installed (CUDA toolkit absent in this image)"
    SKIP=$((SKIP + 1))
fi

echo ""
echo "Deep learning runtimes:"
if have python3; then
    # assert() makes the check FAIL (non-zero exit) when CUDA isn't actually
    # usable — a plain print exits 0 even on the "Error 801" warning.
    check "PyTorch sees CUDA" python3 -c "import torch; assert torch.cuda.is_available(), 'torch.cuda.is_available() is False'; print('torch', torch.__version__, '/ device:', torch.cuda.get_device_name(0))"
    check "TensorRT" python3 -c "import tensorrt as trt; print('tensorrt', trt.__version__)"
else
    yellow "  [SKIP] python3 not found"
    SKIP=$((SKIP + 1))
fi

echo ""
echo "=============================================="
printf " Result: "
green "$PASS passed"
[ "$FAIL" -gt 0 ] && red "         $FAIL failed"
[ "$SKIP" -gt 0 ] && yellow "         $SKIP skipped"
echo "=============================================="

[ "$FAIL" -eq 0 ]
