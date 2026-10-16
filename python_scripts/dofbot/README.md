# Basic DOFBOT angle scripts

Small examples using the working Yahboom library on I²C bus **7**, address **0x15**:

| Script | Action |
| --- | --- |
| `read_angles.py` | Read all six angles, or one selected servo. No movement. |
| `write_angle.py` | Send one position command. No feedback reads. |
| `write_read_angle.py` | Read the current angle, move once, wait, then read the final angle. |
| `set_dofbot.py` | Move each servo to the angles configured inside the script, one at a time. |

## Startup

For a fresh clone or erased Jetson, first use the
[full rebuild checklist](../../dofbot/docs/REBUILD.md). It covers dependencies,
boot installation, device access, filesystem layout and ignored asset recovery.

1. Power the Jetson and DOFBOT controller. Keep the arm's movement area clear.
2. At boot, select **DOFBOT test - I2C7 100 kHz**. The normal boot entry still defaults to 400 kHz. See [clock setup](../../dofbot/docs/CLOCK-SETUP.md) for the boot menu instructions.
3. Verify the active clock (should print `100000`):

   ```bash
   python3 -c 'from pathlib import Path; print(int.from_bytes(Path("/proc/device-tree/bus@0/i2c@c250000/clock-frequency").read_bytes(), "big"))'
   ```

4. Set up the shared Python environment once (already done on this Jetson):

   ```bash
   cd ~/jetson-hobby-lab/dofbot
   ./tools/setup_env.sh
   ```

5. Open the basic scripts folder:

   ```bash
   cd ~/jetson-hobby-lab/python_scripts/dofbot
   ```

Use `./run.sh` for these scripts. It selects the repo's environment and corrected library, even if another virtual environment is already active. No environment activation or `sudo` is needed with the current device permissions. Keep only one DOFBOT script/application running at a time.

## Why put `./run.sh` before the Python script?

`run.sh` is a launcher: it prepares Python's environment and then runs the script you name. For example:

```bash
./run.sh write_angle.py --servo 1 --angle 120 --time-ms 2000
```

The `./` means “run the file named `run.sh` in this folder.” The launcher:

- Uses `~/jetson-hobby-lab/dofbot/.venv/bin/python3`, regardless of which environment is currently active.
- Sets `PYTHONPATH` so Python imports this repo's corrected `Arm_Lib`, including the tested delay after feedback reads. A plain `python3` command could import a different installed copy.
- Loads the shared project's ROS environment when available, then passes your script and arguments to Python. These basic servo scripts do not need a running ROS node.

The `(.venv)` text in your terminal only indicates that a virtual environment is active; it does not identify which one or guarantee the correct library search path.

Each launch prepares the environment for that script process. It does not change the parent terminal's environment, so use `./run.sh` on each command. This does not reinstall anything or repeat setup. You can run the scripts directly with Python if you first configure the same interpreter and library path yourself; the launcher handles that for you.

## Read angles

```bash
./run.sh
./run.sh read_angles.py --servo 1
```

The first command prints all six positions once. Feedback requests communicate with the controller but do not command movement. Reading all six takes about 0.6 seconds because the corrected library includes the tested 100 ms recovery delay after each read.

## Write an angle

**The following commands move the arm.** Choose a clear target near the angle you just read. These are absolute angles: `--angle 120` means go to 120°, not move another 120°.

```bash
./run.sh write_angle.py --servo 1 --angle 120 --time-ms 2000
```

This sends one command and exits. The servo can continue moving after the script exits. “Command sent” means the I²C write succeeded; this script does not check whether the servo reached its target.

## Write and read feedback

```bash
./run.sh write_read_angle.py --servo 1 --angle 120 --time-ms 2000
```

This prints the starting angle, commands the target, waits the requested duration plus one second, and prints the feedback. It leaves the joint at the new position; it does not return it to the starting angle. Small feedback differences are normal. For `--time-ms 0`, the final read occurs after one second; a large move might still be in progress.

## Set a configured pose

Edit `servos` in `set_dofbot.py` to choose each joint's absolute target angle, and `duration_ms` to set the movement time per joint. All targets are checked before movement starts. After each command, the script waits for the movement duration plus one second before reading and printing feedback. It stops if valid feedback is unavailable. Feedback is shown for comparison with the target; the script does not automatically correct a position difference.

**This command moves all configured joints in list order.** Read the current
`servos` list inside the file before running; targets are editable and are not
a universal safe/home pose. Check that this sequence has clearance:

```bash
./run.sh set_dofbot.py
```

## Parameters and help

- `--servo`: 1 through 6; required for commands that move a joint.
- `--angle`: integer degrees, 0–180 for servos 1, 2, 3, 4 and 6; 0–270 for servo 5. These are protocol limits; the assembled arm and nearby objects can restrict usable travel.
- `--time-ms`: 2000 by default. `0` selects maximum speed; the accepted protocol range is 0–65535 ms. Start with slow, small moves.

```bash
./run.sh read_angles.py --help
./run.sh write_angle.py --help
./run.sh write_read_angle.py --help
```

The scripts use `Arm_Device(i2c_bus=7, strict_errors=True)` from [the corrected library](../../dofbot/colcon_ws/src/Arm_Lib/Arm_Lib/Arm_Lib.py). They do not enable torque, change modes, calibrate joints, or retry commands. Errors stop the script and close the bus connection. Stopping a script does not stop a movement already sent to the controller.

For the full Yahboom examples and installation notes, see [the main DOFBOT README](../../dofbot/README.md).
