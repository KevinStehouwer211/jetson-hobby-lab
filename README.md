# 🤖 Jetson Hobby Lab

Personal robotics and AI development repository for the **NVIDIA Jetson Orin Nano / Yahboom** platform.

This repository keeps the Jetson workflow organized. It contains Docker startup scripts, ROS 2 workspaces, Isaac ROS workspace files, notes, and helper scripts.

> [!NOTE]
> Large generated files (models, datasets, ROS bags, container images) are **not** committed. See [.gitignore](.gitignore) for what stays local.

---

## 📑 Table of contents

- [Hardware and software target](#-hardware-and-software-target)
- [Repository layout](#-repository-layout)
- [Why Docker is used](#-why-docker-is-used)
- [Workflow: working inside the Isaac ROS environment](#-workflow-working-inside-the-isaac-ros-environment)
- [Workflow: working inside the custom environment](#-workflow-working-inside-the-custom-environment)
- [Workspaces explained](#-workspaces-explained)
- [Useful links](#-useful-links)

---

## 🧰 Hardware and software target

### Hardware

- NVIDIA Jetson Orin Nano / Orin Nano Super
- Yahboom robot platform

### Host system

The Jetson host system should stay as **clean as possible**.

The host is mainly responsible for:

- JetPack / L4T
- NVIDIA drivers
- CUDA driver integration
- Docker (with the [NVIDIA Container Runtime](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/index.html))
- SSH access
- Basic system tools

Most robotics and AI development should happen **inside Docker containers**.

---

## 🗂️ Repository layout

```text
jetson-hobby-lab/
├── docker/                     # Container startup scripts (no images committed)
│   ├── isaac-ros-humble/       # Launcher for the NVIDIA Isaac ROS dev container
│   │   └── run.sh
│   └── jetson-humble-ai/       # Launcher for the custom ROS 2 + AI image
├── isaac_ros_ws/               # Workspace mounted into the Isaac ROS container
│   └── src/
│       └── isaac_ros_common/   # NVIDIA Isaac ROS tooling (cloned, not committed)
├── ros2_ws/                    # Custom ROS 2 workspace (your own packages)
│   └── src/
├── scripts/                    # Helper scripts
├── notes/                      # Personal notes and references
└── README.md
```

---

## 🐳 Why Docker is used

Docker is used because robotics and AI development on Jetson depends on many version-sensitive packages.

A ROS/AI setup can depend on:

- ROS 2 version
- Ubuntu version
- CUDA version
- TensorRT version
- PyTorch version
- OpenCV version
- Python dependencies
- NVIDIA Jetson runtime libraries

Installing everything directly on the Jetson host can make the system messy and hard to reproduce. One wrong package upgrade can break ROS, CUDA, PyTorch, camera support, or Isaac ROS.

Docker separates the host system from the development environment:

```text
Host system
├── JetPack / NVIDIA drivers / Docker runtime
└── Containers
    ├── ROS 2 Humble environment      (custom)
    ├── PyTorch / OpenCV environment   (custom)
    └── Isaac ROS environment          (NVIDIA-provided)
```

> [!TIP]
> Two parallel toolchains live in this repo: the **Isaac ROS** environment (managed by NVIDIA's tooling) and a **custom** environment you build yourself. Pick the one that matches your task — they each have their own workspace and launcher.

---

## 🚀 Workflow: working inside the Isaac ROS environment

The Isaac ROS environment is built and managed by NVIDIA's [`isaac_ros_common`](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_common) tooling. The launcher script wraps NVIDIA's `run_dev.sh`, which **builds the image (first run only) and drops you into a container** with the workspace mounted.

### 1. One-time setup — clone the Isaac ROS common tooling

The `isaac_ros_common` repo is **not committed** to this repository — clone it into the Isaac workspace `src/` folder:

```bash
cd ~/jetson-hobby-lab/isaac_ros_ws/src
git clone -b release-3.2 https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_common.git
```

> [!WARNING]
> The branch (`release-3.2`) must match the Isaac ROS release you target. Mixing release branches with an incompatible JetPack version is the most common cause of build failures. Check the [Isaac ROS release compatibility matrix](https://nvidia-isaac-ros.github.io/getting_started/index.html) before choosing a branch.

### 2. Start the container

```bash
~/jetson-hobby-lab/docker/isaac-ros-humble/run.sh
```

What this does (see [docker/isaac-ros-humble/run.sh](docker/isaac-ros-humble/run.sh)):

- Verifies `isaac_ros_common` exists (and tells you how to clone it if not).
- Calls NVIDIA's `run_dev.sh` with `-d isaac_ros_ws`, which builds (or pulls a pre-built) Isaac dev image on first run and starts the container.

> [!NOTE]
> The first run **downloads several GB**. If a matching pre-built base image exists on NGC it is pulled (fast); otherwise it builds locally (slow). Subsequent starts reuse the cached image.

> [!WARNING]
> Always launch through `run.sh` (or pass `-d ~/jetson-hobby-lab/isaac_ros_ws` yourself). If you run `run_dev.sh` with **no arguments** from inside `isaac_ros_common`, it falls back to mounting `isaac_ros_common` as the workspace instead of `isaac_ros_ws` — you'll end up in the wrong tree.

### 3. Work inside the container

The launcher drops you into the **workspace root**, mounted at `/workspaces/isaac_ros-dev` — this is your host `isaac_ros_ws`, with your packages under `src/`. You are the non-root `admin` user (use `sudo` if needed). Build and source from here:

```bash
cd /workspaces/isaac_ros-dev   # = host isaac_ros_ws; src/ holds your packages
colcon build --symlink-install
source install/setup.bash
```

> [!TIP]
> Your code under `isaac_ros_ws/src` is **mounted**, not copied — edit files on the host with your normal editor and rebuild inside the container. Nothing is lost when the container exits.

### 4. Verify the environment

Before building real work, confirm the container actually has GPU, CUDA, and ROS 2 wired up. The wrapper bind-mounts this repo's `scripts/` at `/host_scripts`, so the helper is available inside the container:

```bash
/host_scripts/check-env.sh
```

It wraps the standard tools (`ros2 doctor`, `nvidia-smi`, `nvcc`, torch/TensorRT imports) into one PASS / FAIL / SKIP summary for:

| Check | What it confirms |
|-------|------------------|
| `pwd` + `src/` | You're at the workspace root, not inside `isaac_ros_common` |
| `ROS_DISTRO`, `ros2 topic list` | ROS 2 Humble is sourced and responding |
| `nvidia-smi` | The GPU is visible (NVIDIA runtime is active) |
| `nvcc --version` | CUDA toolkit is present |
| PyTorch / TensorRT | DL runtimes import **and see CUDA** (`torch.cuda.is_available()` → `True`) |

> [!WARNING]
> If `nvidia-smi` fails or `torch.cuda.is_available()` returns `False`, the container can't reach the GPU — everything will silently fall back to CPU. Fix that before debugging anything else.

> [!NOTE]
> **PyTorch shows CUDA "Error 801: operation not supported"?** This is a *permissions* gotcha, not a broken GPU. The dev container is `--privileged` with a private `/dev`, and the Jetson GPU's DRM render nodes (`/dev/dri/renderD12*`) land in a group the non-root `admin` user can't open, so CUDA init fails. The launcher fixes this automatically — [run.sh](docker/isaac-ros-humble/run.sh) runs [scripts/fix-gpu-perms.sh](scripts/fix-gpu-perms.sh) (re-groups those nodes to `video`) right after the container starts. If you ever launch the container another way, or hit Error 801 on a fresh container, just run it by hand inside the container:
> ```bash
> /host_scripts/fix-gpu-perms.sh   # auto-sudoes; re-checks with /host_scripts/check-env.sh
> ```

> [!TIP]
> For live monitoring (GPU load, CUDA, JetPack version) install [`jetson-stats`](https://github.com/rbonghi/jetson-stats) on the **host** and run `jtop`, or use `tegrastats`. For a real end-to-end test, run an Isaac ROS quickstart (e.g. **AprilTag** or **image_proc**) — clone the package into `src/`, build, and run its launch file against a sample image to confirm the GPU (NITROS) pipeline works.

---

## 🛠️ Workflow: working inside the custom environment

The custom environment is your own ROS 2 Humble + AI (PyTorch / OpenCV) image, kept under [docker/jetson-humble-ai/](docker/jetson-humble-ai/), with code in the [ros2_ws/](ros2_ws/) workspace.

### 1. Build the custom image

```bash
cd ~/jetson-hobby-lab/docker/jetson-humble-ai
# docker build -t jetson-humble-ai .   # once a Dockerfile is added here
```

> [!NOTE]
> This folder is currently a placeholder. Add a `Dockerfile` (base it on an [NVIDIA L4T / Jetson container](https://catalog.ngc.nvidia.com/containers)) and a `run.sh` launcher, then update this section.

### 2. Start the container

When launching by hand, always request the GPU and mount the custom workspace:

```bash
docker run --rm -it \
  --runtime nvidia \
  --network host \
  -v ~/jetson-hobby-lab/ros2_ws:/workspace/ros2_ws \
  jetson-humble-ai
```

> [!WARNING]
> Without `--runtime nvidia` the container starts but **cannot see the GPU** — CUDA, TensorRT, and PyTorch will silently fall back to CPU or fail. Confirm GPU access inside the container with `nvidia-smi` or a quick `python3 -c "import torch; print(torch.cuda.is_available())"`.

### 3. Work inside the container

```bash
cd /workspace/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

---

## 🧩 Workspaces explained

| Workspace | Used by | Purpose |
|-----------|---------|---------|
| [`isaac_ros_ws/`](isaac_ros_ws/) | Isaac ROS container | NVIDIA Isaac ROS packages and `isaac_ros_common` tooling |
| [`ros2_ws/`](ros2_ws/) | Custom container | Your own ROS 2 packages and experiments |

> [!CAUTION]
> Keep build artifacts out of git. `build/`, `install/`, and `log/` are already ignored — don't force-add them. They are container- and architecture-specific and will not work if checked out elsewhere.

---

## 🔗 Useful links

- [Isaac ROS documentation](https://nvidia-isaac-ros.github.io/)
- [Isaac ROS getting started & compatibility](https://nvidia-isaac-ros.github.io/getting_started/index.html)
- [`isaac_ros_common` on GitHub](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_common)
- [ROS 2 Humble documentation](https://docs.ros.org/en/humble/)
- [NGC catalog — Jetson / L4T containers](https://catalog.ngc.nvidia.com/containers)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/index.html)
- [JetPack SDK](https://developer.nvidia.com/embedded/jetpack)
