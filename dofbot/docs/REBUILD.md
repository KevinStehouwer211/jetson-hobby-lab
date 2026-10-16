# Reproduce the working DOFBOT setup

This is the rebuild checklist for the work completed on 2026-10-16. It covers
direct servo control, local Python/Jupyter startup, manual-source recovery, and
the filesystem layout. The full vendor ROS/vision application is still staged
source, not a completed installation. See [validation](VALIDATION.md).

## Resume on this Jetson

1. Power both the Jetson and controller. Use the existing controller/header
   connection and keep the arm clear. A fresh hardware assembly must follow the
   Yahboom wiring diagram; do not infer wiring from Linux bus numbers.
2. On the directly connected monitor, choose **DOFBOT test - I2C7 100 kHz** at
   the L4T boot list. The normal unattended default remains `primary` (400 kHz).
3. Run:

   ```bash
   cd ~/jetson-hobby-lab/dofbot
   ./tools/setup_env.sh
   ./tools/run_python.sh tools/check_setup.py
   ./tools/run_python.sh
   cd ../python_scripts/dofbot
   ./run.sh
   ```

The checker sends no controller commands. The final two commands query the
controller without commanding movement. Expected: version 0.21, pings 0xda,
valid angles. Servo positions depend on the last physical pose.

For basic movement commands, follow [the basic scripts README](../../python_scripts/dofbot/README.md).
For notebooks, return to `~/jetson-hobby-lab/dofbot` and run `./tools/run_jupyter.sh`.

## Rebuild after a fresh clone or reinstallation

### 1. Restore the platform and repository

The tested host is ARM64, Ubuntu 22.04.5, Python 3.10.12, Jetson Linux
**R36.4.7**, JetPack 6, Jetson Orin Nano Super. The separate ROS examples use
ROS 2 Humble at `/opt/ros/humble`. Direct servo scripts do not require ROS.
The exact host package record is [environment-reference.json](environment-reference.json).

Install the board-compatible NVIDIA OS through NVIDIA's normal process if the
machine has been erased. This repository does not contain an OS image, drivers,
CUDA installation, or a portable replacement for the Jetson's existing AI stack.
Do not copy `/usr`, `/lib`, `/var/lib/docker`, or `.bashrc` from the old USB OS.

```bash
cd ~
git clone git@github.com:KevinStehouwer211/jetson-hobby-lab.git
cd ~/jetson-hobby-lab/dofbot
```

The clone requires these local changes to have been committed and pushed first.
If the repository is already present, use it rather than cloning over it.

### 2. Supply only missing Python dependencies

On the current Jetson, skip installation and run `./tools/setup_env.sh`.
That script reuses existing system packages; it does not install dependencies.

On a fresh Ubuntu 22.04 host without the required packages, install the small
build/setup prerequisites, then put the servo dependencies in the local venv:

```bash
sudo apt install python3-venv python3-dev build-essential i2c-tools device-tree-compiler
cd ~/jetson-hobby-lab/dofbot
/usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python3 -m pip install -r requirements-servo.txt
./tools/setup_env.sh
./tools/run_python.sh tools/check_setup.py --offline
```

`smbus` builds a native extension, so use the Jetson's ARM64 Python, not an x86
venv copied from another computer. The local venv is recreated after a move or
reinstallation. The tested host versions of torch/OpenCV/NumPy are a reference,
not a request to install generic PyPI replacements. Keep the NVIDIA-compatible
AI environment when restoring vision features; servo control needs none of it.

For notebooks, reuse installed `ipykernel` and `jupyterlab`. If absent, install
them in this local environment only, then rerun `./tools/setup_env.sh`:

```bash
.venv/bin/python3 -m pip install ipykernel jupyterlab
./tools/setup_env.sh
```

If the venv was originally created without pip, enable pip locally first with
`.venv/bin/python3 -m ensurepip`. Do not use `sudo pip` or the vendor global
installers. Optional notebook dependencies vary by feature; the full vision
environment has not been recreated from scratch or declared reproducible.

### 3. Restore bus access and the 100 kHz boot entry

```bash
ls -l /dev/i2c-7
id
```

If `/dev/i2c-7` is absent, check board/header configuration and the I2C adapter
mapping before continuing. If its group is `i2c` and your account lacks access:

```bash
sudo usermod -aG i2c "$USER"
```

Log out and back in for the group change. If the device belongs to another
group, inspect the actual udev rule rather than using `chmod 666`.

Follow [CLOCK-SETUP.md](CLOCK-SETUP.md) to compile, validate and install the
overlay and a separate boot entry. Reboot and select it. This step changes boot
configuration; normal script startup never does it for you. Recheck the active
clock after every reboot. A future JetPack update may require revalidating the
DTB path, overlay compatibility and boot entry.

### 4. Verify source and queries before movements

```bash
cd ~/jetson-hobby-lab/dofbot
./tools/run_python.sh tools/check_setup.py
./tools/run_python.sh -m unittest discover -s diagnostics -p 'test_*.py' -v
./tools/run_python.sh
```

The first command checks configuration only, the second uses fake hardware,
and the third queries real hardware. Keep one owner of the arm at a time.
Only after these checks, use a small deliberate motion from the basic README.
The library retains the native SMBus protocol and adds 100 ms after feedback
reads. Scripts that read after a movement also wait for its duration plus a
settling interval; reading immediately after a write returned raw zero during
the user's pose-script test. That timing fix was checked offline, not by a new
agent-run movement test.

## Filesystem map and what must be backed up

| Path | Purpose / recreation |
| --- | --- |
| `~/jetson-hobby-lab/dofbot/` | Canonical patched library, diagnostics, manual source, setup tools and configuration source; keep in Git. |
| `~/jetson-hobby-lab/python_scripts/dofbot/` | Basic top-to-bottom scripts and editable pose targets; keep in Git. |
| `dofbot/.venv`, `.jupyter`, `.ipython` | Generated runtime state, ignored; regenerate with `setup_env.sh` and launchers. |
| `dofbot/vendor/` | Manual notebooks and ROS/application reference source; ignored runtime assets are restored separately. |
| `/boot/dofbot-i2c7-100khz.dtbo` | Compiled overlay; rebuild from `dofbot/config/dofbot-i2c7-100khz.dts`. |
| `/boot/extlinux/extlinux.conf` | Machine-specific boot entries; rebuild the extra entry using that machine's existing boot arguments. Never copy another disk's PARTUUID. |
| `/opt/ros/humble` | Existing host ROS installation, optional for basic scripts; provision separately for ROS examples. |
| `~/yahboom-dofbot/` | Original working checkout, dated backups and raw investigation logs; retained locally, not needed to run the canonical repo. |
| `/media/kstehouwer/4fecbf10-3b85-4d9a-83c8-9bd721e084a4/` | Original vendor USB filesystem and offline Docker image; keep a separate USB/disk backup. Its mount name can change. |

No DOFBOT system service, startup application, calibration, firmware update or
global Python installation was added by this workflow. The full APP can move
the arm on startup; it has deliberately not been enabled.

## Restore ignored assets and keep the repo small

Basic servo scripts need no model, mesh, image archive or native kinematics
binary. Git contains their complete library and scripts. Vendor notebook source
and small example images remain available; generated state, dumps, models,
engines, meshes, fonts, native binaries and archives are ignored. Vendor IDE
settings, editor swap/backup files, `Thumbs.db` and prebuilt Python eggs are also
ignored and excluded from future source recovery. See
[local-assets.json](local-assets.json) for the inventory and hashes of ignored
runtime files on this machine, and [vendor-import-manifest.json](vendor-import-manifest.json)
for source provenance.

For missing assets under `vendor/manual/` and `vendor/ros2_ws/`, attach the original
USB filesystem and run:

```bash
cd ~/jetson-hobby-lab/dofbot
sudo /usr/bin/python3 tools/import_vendor_sources.py \
  --usb-root /media/kstehouwer/4fecbf10-3b85-4d9a-83c8-9bd721e084a4 --assets-only
```

Use the actual mount path if different (`lsblk -f` helps identify it). The tool
reads the offline `dofbot_ai:3.0.2` image, does not start Docker, and restores only
missing ignored files. It preserves source and existing assets. Without this USB,
those exact ignored assets cannot be reconstructed from Git alone. Preserve the
USB separately; its private registry address is not a public download fallback.

The legacy `colcon_ws/src/dofbot_garbage_yolov11/best.engine` lies outside that
importer's mappings. It is unused for servo control. If needed, recover it from
the same relative `colcon_ws/src/dofbot_garbage_yolov11/best.engine` path under
`~/yahboom-dofbot/` or the USB's `/home/jetson/` tree; verify against the asset
inventory. TensorRT engines are platform-specific and may need rebuilding.

Do not delete ignored models using `git clean -fdx`: Git is not their backup.
Only transient `__pycache__` and notebook checkpoint directories were removed
during cleanup; source, vendor assets and the original recovery folder remain.
Raw old investigation logs stay outside Git; the final findings and limitations
are recorded in [VALIDATION.md](VALIDATION.md).

## Save the completed setup to GitHub

Review and commit the DOFBOT paths and the root README, then push using your
normal Git workflow. Until then, these changes exist only on this Jetson:

```bash
cd ~/jetson-hobby-lab
git status --short
git add README.md dofbot/ python_scripts/dofbot/
git diff --cached --stat
git diff --cached --check
git commit -m "Add reproducible DOFBOT setup and basic servo scripts"
git push
```

Git ignores are applied to untracked files when staging; previously tracked
files stay tracked. No commit, push, reflash, dependency install or boot change
is performed automatically by the rebuild documentation or setup checker.
