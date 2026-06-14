#!/usr/bin/env bash
set -e

REPO_ROOT="$HOME/jetson-hobby-lab"
ISAAC_COMMON="$REPO_ROOT/isaac_ros_ws/src/isaac_ros_common"

if [ ! -d "$ISAAC_COMMON" ]; then
    echo "ERROR: Isaac ROS common not found:"
    echo "$ISAAC_COMMON"
    echo ""
    echo "Clone it first with:"
    echo "cd $REPO_ROOT/isaac_ros_ws/src"
    echo "git clone -b release-3.2 https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_common.git"
    exit 1
fi

CONTAINER_NAME="isaac_ros_dev-aarch64-container"

# The container is --privileged with a private /dev; the GPU's DRM render nodes
# land in a group the non-root 'admin' user can't access, so CUDA fails with
# "Error 801" until they're re-grouped to 'video'. Host udev can't reach inside
# the container, so we fix it here: wait for the container to come up, then run
# fix-gpu-perms.sh as root. Runs in the background so it doesn't block the
# interactive shell run_dev.sh drops us into. See scripts/fix-gpu-perms.sh.
(
    for _ in $(seq 1 60); do
        if docker exec "$CONTAINER_NAME" true 2>/dev/null; then
            docker exec -u root "$CONTAINER_NAME" bash /host_scripts/fix-gpu-perms.sh \
                || echo "run.sh: WARNING — fix-gpu-perms.sh failed; CUDA may not work as non-root"
            exit 0
        fi
        sleep 0.5
    done
    echo "run.sh: WARNING — container '$CONTAINER_NAME' never became ready; GPU perms not fixed"
) &

cd "$ISAAC_COMMON"
# Mount the full isaac_ros_ws as the dev workspace (/workspaces/isaac_ros-dev).
# Without -d, run_dev.sh falls back to mounting isaac_ros_common itself.
# Also bind-mount the repo's helper scripts at /host_scripts (read-only) so
# check-env.sh and friends are available without duplicating them into the ws.
./scripts/run_dev.sh \
    -d "$REPO_ROOT/isaac_ros_ws" \
    -a "-v $REPO_ROOT/scripts:/host_scripts:ro"
