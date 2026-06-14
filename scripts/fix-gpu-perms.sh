#!/usr/bin/env bash
#
# fix-gpu-perms.sh — make non-root CUDA work inside the Isaac ROS dev container.
#
# Run this *inside the container* (run.sh does it automatically on launch; you
# can also run it by hand: `/host_scripts/fix-gpu-perms.sh`).
#
# Why this is needed
# ------------------
# The dev container is --privileged with a private /dev tmpfs. Docker populates
# that /dev by mknod'ing the host's device nodes using their *numeric* gid.
# The GPU's DRM render nodes (/dev/dri/renderD12*) are group 'render' (gid 104)
# on the host; gid 104 maps to an unrelated group inside the container, so the
# non-root container user ('admin', a member of 'video') can't open them. The
# Jetson CUDA driver opens those render nodes during init, the open returns
# EACCES, and CUDA reports it as the misleading "Error 801: operation not
# supported" (confirmed via strace: openat(/dev/dri/renderD128) = EACCES).
#
# Re-grouping the nodes to 'video' (gid 44 — identical on host and container,
# and the container user is already a member) fixes it. We also re-group the
# GPU scheduler nodes, which some CUDA operations touch.
#
# The host udev approach doesn't work here: systemd's 50-udev-default.rules +
# 70-uaccess own the render-node group on the host, and even if overridden the
# fix wouldn't survive the numeric-gid copy into the container. Fixing it
# inside the container is the reliable place.

set -e

# Need root to chgrp/chmod device nodes; admin has passwordless sudo.
if [ "$(id -u)" -ne 0 ]; then
    exec sudo "$0" "$@"
fi

regroup() {
    local n="$1"
    [ -e "$n" ] || return 0
    chgrp video "$n" 2>/dev/null && chmod 0660 "$n" 2>/dev/null && echo "  fixed $n"
}

echo "fix-gpu-perms: re-grouping GPU nodes to 'video'..."

# DRM render nodes — the open() CUDA actually fails on.
for n in /dev/dri/renderD*; do
    regroup "$n"
done

# GPU scheduler nodes — root:root by default; some CUDA ops use them.
for n in \
    /dev/nvgpu/igpu0/sched \
    /dev/nvgpu/igpu0/nvsched \
    /dev/nvgpu/igpu0/nvsched_ctrl_fifo \
    /dev/nvhost-sched-gpu \
    /dev/nvhost-nvsched-gpu \
    /dev/nvhost-nvsched_ctrl_fifo-gpu; do
    regroup "$n"
done

echo "fix-gpu-perms: done."
