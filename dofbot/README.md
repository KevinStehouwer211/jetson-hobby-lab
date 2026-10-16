# Yahboom DOFBOT on Jetson Orin Nano Super

This folder brings the working DOFBOT Python library, hardware diagnostics, and
Yahboom's manual examples into Jetson Hobby Lab. It uses the existing **Ubuntu
22.04 / JetPack 6 / ROS 2 Humble** installation and existing PyTorch/OpenCV.

**Start with the commands below.** The original vendor files are included for
following the manual, but not every vision/ROS example has been ported or tested.

For a fresh clone, reinstallation, filesystem map and cleanup policy, follow
the **[complete rebuild checklist](docs/REBUILD.md)**. For the simplest angle
commands, use **[python_scripts/dofbot](../python_scripts/dofbot/README.md)**.

## 1. Set up the local environment

```bash
cd ~/jetson-hobby-lab/dofbot
./tools/setup_env.sh
./tools/run_python.sh tools/check_setup.py --offline
```

This creates a local `.venv` with access to the already-installed system Python
packages and a project-local Jupyter kernel. It does **not** run apt, pip, Docker,
calibration, or arm movements. It does not edit `.bashrc` or your other projects.
The environment is generated locally and is not committed to Git.

The launcher gives this folder's `Arm_Lib` priority over the older copy in
`~/yahboom-dofbot`. Use this launcher for scripts and notebooks:

```bash
./tools/run_python.sh examples/read_positions.py
```

Or run the fuller query-only diagnostic:

```bash
./tools/run_python.sh
```

Expected: controller version `0.21`, six pings `0xda`, and valid joint angles.
There is no movement in either command. If access to `/dev/i2c-7` is denied,
check `id` and `ls -l /dev/i2c-7`; the current user needs the device's group access.
Do not make the device world-writable.

## 2. Use the tested 100 kHz boot configuration

The tested setup uses **I²C bus 7**, controller **0x15**, at **100 kHz**.
On this Jetson the optional boot entry is already installed. After reboot,
select **DOFBOT test - I2C7 100 kHz** from the L4T boot list (currently entry `2`).
The menu waits 15 seconds; the default `primary` entry still uses the original
configuration. Check the clock after boot:

```bash
python3 -c 'from pathlib import Path; print(int.from_bytes(Path("/proc/device-tree/bus@0/i2c@c250000/clock-frequency").read_bytes(), "big"))'
```

Expected: `100000`. See [clock setup and rollback](docs/CLOCK-SETUP.md).
The old vendor `setup_i2c_clk_rate.py` helper targets a sysfs interface absent
on this kernel; it is not the setup procedure to use here.

## 3. Follow the manual in JupyterLab

```bash
cd ~/jetson-hobby-lab/dofbot
./tools/run_jupyter.sh
```

Open the localhost URL printed in the terminal on the Jetson. Authentication
remains enabled. Choose the **DOFBOT (Jetson host)** kernel. The launcher serves
only on `127.0.0.1`; it does not expose Jupyter to the network.

First open:

```text
examples/01_read_positions.ipynb
```

Then follow [Yahboom's manual](https://www.yahboom.net/study/Dofbot-Jetson_nano/)
using the recovered notebooks at:

```text
vendor/manual/Dofbot/3.ctrl_Arm/
```

| Manual example | Notebook | Important behavior |
|---|---|---|
| RGB light | `1.rgb.ipynb` | Changes the board LED |
| Buzzer | `2.beep.ipynb` | Sounds the buzzer |
| Single servo | `3.ctrl_servo.ipynb` | Starts with servo 1 at 120°; a later cell repeatedly moves servo 6 between 50°, 120°, and 180° |
| Read angles | `4.read_servo.ipynb` | Contains an infinite read loop **and a later cell that moves servo 6** |
| All servos | `5.ctrl_all.ipynb` | Sends a six-joint pose, then loops through broad joint ranges |
| Left/right, dance, grasping | `6.left_right.ipynb` through `11.heap_up.ipynb` | Perform multi-joint actions; review clearance and poses before execution |
| Learning/action memory | `8.study_mode.ipynb` | May change torque, button mode, or stored actions; review each cell |

**Run individual cells after reviewing them. Do not use “Run All” as a first
hardware test.** Interrupt an infinite loop using Jupyter's stop/interrupt button;
this stops Python but does not necessarily cancel a motion already accepted by
the controller. Only one notebook/script should own the arm at a time.

The original notebooks have not been executed as part of this repository setup.
Their single-joint read/write API was validated with the bounded diagnostics.
Simultaneous six-servo writes, dance sequences, and full-range sweeps still need
separate testing. Do not run `vendor/manual/Dofbot/0.py_install` global installers;
they can replace the working library or dependencies.

### Running your own Python file

```bash
./tools/run_python.sh /path/to/your_script.py
```

For vendor files that use relative images/configuration, change into the file's
folder first, then invoke the launcher by its full path. ROS-backed examples
need their ROS packages built before their imports/services will work.

The public API is unchanged:

```python
from Arm_Lib import Arm_Device
arm = Arm_Device(i2c_bus=7)
angle = arm.Arm_serial_servo_read(1)  # Includes the tested recovery interval.
# This next call MOVES the base joint; choose a target with physical clearance.
arm.Arm_serial_servo_write(1, 105, 2000)
arm.bus.close()
```

Duration is milliseconds. `0` requests the controller's fastest speed, not
instantaneous movement. Joint 5 supports 0–270°; the other joints support 0–180°.
These are API limits, not a guarantee of clearance for the assembled arm.

## 4. What is tested

Verified on this Jetson on **2026-10-16**:

- All six servos: version/ping/position queries.
- Servo 1: repeated 15° movements and a 45° out-and-back at duration `0`.
- Servos 2–6: sequential 10° out-and-back movements, 2000 ms per leg.
- Position feedback reached every tested target within 1°.
- Physical movement was confirmed for servo 1 and the five other joint sweeps.

Position commands intermittently failed to produce motion when issued immediately
after feedback reads. A 100 ms recovery pause produced successful bounded tests.
The bundled `Arm_Device` now waits **100 ms after a position-feedback word read**
before returning, so ordinary callers inherit that recovery time. This adds
about 0.6 seconds to six sequential feedback queries. It is configurable via
`read_recovery_s`; leave the tested default `0.1` in place initially.

The library keeps the native SMBus protocol and joint-angle mappings. Detailed
exceptions are logged; `strict_errors=True` re-raises them. No automatic movement
retries, torque changes, firmware updates, or calibration changes were added.
The tests establish bounded operation at 100 kHz; long-term, high-rate, concurrent,
and 400 kHz behavior remains unverified. See [validation notes](docs/VALIDATION.md).

Optional bounded movement diagnostics (these commands **move hardware**):

```bash
# Servo 1: 15° outward and back, 2 seconds per leg.
./tools/run_python.sh diagnostics/repeat_servo1.py --confirm-motion --step-degrees 15 --moves 2

# Servos 2–6: sequential 10° outward and back, 2 seconds per leg.
./tools/run_python.sh diagnostics/sweep_other_joints.py --confirm-motion
```

Both check the 100 kHz configuration and feedback, and stop on the first failure.
Do not run them while another controller application is active.

## 5. Full Yahboom application, ROS, and vision examples

The [“Must Read Before Use” page](https://www.yahboom.net/study/Dofbot-Jetson_nano/18637/)
assumes Yahboom's preconfigured Docker environment. It starts the full APP and
then describes calibration. The original USB host is Ubuntu 18.04, but its
`dofbot_ai:3.0.2` container uses Ubuntu 22.04 and ROS 2 Humble.

Recovered source is available here:

| Location | Contents / status |
|---|---|
| `colcon_ws/src/Arm_Lib/` | Active patched Python library |
| `colcon_ws/src/dofbot_utils/` | Python helpers available through the launcher |
| Other `colcon_ws/src/` packages | Original copied packages; many still declare ROS 1 `catkin` |
| `vendor/manual/Dofbot/` | Main manual notebooks and local resources |
| `vendor/manual/Dofbot_2D/` | Additional vendor examples and source |
| `vendor/ros2_ws/src/` | Recovered ROS 2 application packages, interfaces, URDF, and assets |
| `vendor/APP_DOFBOT/` | Original APP source; startup scripts/paths not adapted |
| `vendor/Yahboom_Oled/` | Original OLED application; service not installed |

**Do not run `colcon build` over the entire mixed source tree.** The separate
ROS 2 source is staged, not built or sourced. The full application still needs:

1. Replacement of `/root/...` paths with package/project paths.
2. Review of ROS package dependencies and matching message/service names.
3. A project-local build of selected packages; no copying of USB `build/install`.
4. Review of the vendor application kinematics-library dependency
   (`/usr/lib/libdofbot_kin.so`) and its ABI, without overwriting host libraries.
5. Feature-specific camera, model, audio/voice, and API configuration.

`vendor/APP_DOFBOT/YahboomArm.py` has import-time side effects and a six-joint
startup pose. Its `start_app.sh` also points to a container-only `.pyc` path.
Those launchers are included as reference, **not enabled by this setup**.
The ROS 2 kinematics service itself does not fix or replace the I²C transport.

Use the original container only after reviewing its startup hooks and JetPack
compatibility. Do not execute the USB's `install-dc.sh`: it includes a global
apt upgrade and Docker installation. Do not merge `/var/lib/docker`, `/usr`, CUDA,
or drivers from the USB into the host. Existing Isaac ROS/PyTorch containers are
left untouched.

## 6. Git, vendor assets, and recreating this folder

Source/scripts and cleaned notebooks are suitable for review in Git. Notebook
outputs were removed and their kernel set to `dofbot`. Embedded example API
credentials were replaced by environment-variable lookups; supply your own
`YAHBOOM_API_KEY` / `YAHBOOM_SECRET_KEY` where a selected notebook requires them.
No API account or credential is provided by this repository.

Large vendor model files, TensorRT engines, fonts/meshes and native application
binaries are present locally where recovered, but ignored by Git. Existing
TensorRT engines may need rebuilding for the current JetPack; their presence
does not establish compatibility. A fresh clone needs its assets recovered from
the USB or obtained from the vendor. Crash dumps and system images are excluded.

To recover the manual/ROS source and local assets from the **offline** USB into a
fresh clone (not needed on this machine now):

```bash
sudo /usr/bin/python3 tools/import_vendor_sources.py \
  --usb-root /media/kstehouwer/4fecbf10-3b85-4d9a-83c8-9bd721e084a4 --assets-only
```

This reads only the selected image's layer chain; it never starts Docker or runs
vendor code. `--assets-only` restores missing Git-ignored assets and preserves
all existing files and source code. Without that flag, initial source recovery
requires the recovered directories to be absent and refuses to overwrite them.
[Provenance manifest](docs/vendor-import-manifest.json) records image ID and file
hashes. Respect the original vendor notices; this folder adds no license grant
for third-party material.

Run offline tests without accessing hardware:

```bash
./tools/run_python.sh -m unittest discover -s diagnostics -p 'test_*.py' -v
```

The original working folder, backups, and detailed test logs remain at
`~/yahboom-dofbot/`. The canonical repo contains the code and final findings
needed for basic control; it does not depend on that old folder. See the
[filesystem map and asset restoration](docs/REBUILD.md) for what is regenerated
and what requires a separate USB backup. No change to GitHub has been published
automatically; commit and push the reviewed files to make them available to a
future clone.
