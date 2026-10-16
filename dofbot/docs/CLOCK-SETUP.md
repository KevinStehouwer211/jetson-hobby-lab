# I²C clock configuration

The validated DOFBOT setup uses `/dev/i2c-7`, address `0x15`, with its device-tree
`clock-frequency` set to **100000 Hz**. This is a configured value; physical SCL
frequency was not measured with an oscilloscope.

## This Jetson: already installed

A separate `DOFBOT100K` entry exists in `/boot/extlinux/extlinux.conf`. Reboot,
watch the directly connected monitor, and select **DOFBOT test - I2C7 100 kHz**
(currently number `2`). The L4T menu accepts the number key. Its timeout is 15
seconds. `DEFAULT primary` is preserved, so an unattended reboot selects the
original configuration rather than automatically enabling the test overlay.

After boot:

```bash
python3 -c 'from pathlib import Path; print(int.from_bytes(Path("/proc/device-tree/bus@0/i2c@c250000/clock-frequency").read_bytes(), "big"))'
```

Expected: `100000`. Then run `./tools/run_python.sh` from `dofbot/` for queries.
No movement is needed to check which configuration loaded.

Installed test entry uses:

```text
FDT /boot/dtb/kernel_tegra234-p3768-0000+p3767-0005-nv-super.dtb
OVERLAYS /boot/dofbot-i2c7-100khz.dtbo
```

The overlay source is [../config/dofbot-i2c7-100khz.dts](../config/dofbot-i2c7-100khz.dts).
It changes only `/bus@0/i2c@c250000/clock-frequency` to 100000. All devices on bus
7, including the OLED, share the slower bus configuration.

## A fresh installation

Do not copy this Jetson's full boot configuration or root PARTUUID onto another
machine. The following procedure targets the same Orin Nano Super board and
R36.4.x layout. For a different board/release, first review the source's
`compatible` values, bus node and board-compatible DTB. Install
`device-tree-compiler` if `dtc`, `fdtoverlay` or `fdtget` is missing.

### Compile and validate without changing the running system

```bash
cd ~/jetson-hobby-lab/dofbot
mkdir -p results/clock
dofbot_base_dtb=/boot/dtb/kernel_tegra234-p3768-0000+p3767-0005-nv-super.dtb
test -f "$dofbot_base_dtb"
dtc -@ -I dts -O dtb -o results/clock/dofbot-i2c7-100khz.dtbo config/dofbot-i2c7-100khz.dts
fdtoverlay -i "$dofbot_base_dtb" -o results/clock/merged-test.dtb results/clock/dofbot-i2c7-100khz.dtbo
fdtget -t u results/clock/merged-test.dtb /bus@0/i2c@c250000 clock-frequency
```

The final command must print `100000`. The merged DTB is only a local validation
artifact; do not install it over the board's base DTB. The variable above must
identify the current board-compatible file, not just any file with that name.
Check `/proc/device-tree/compatible` and the existing boot configuration when
rebuilding after an OS/board change.

### Install a separate entry

These commands change boot files. Stop if a DOFBOT entry/overlay already exists;
inspect it instead of adding duplicates or overwriting it. Run each step only
after the previous one succeeds.

```bash
sudo cp -a /boot/extlinux/extlinux.conf "/boot/extlinux/extlinux.conf.dofbot-backup-$(date +%Y%m%dT%H%M%S)"
sudo install -m 0644 results/clock/dofbot-i2c7-100khz.dtbo /boot/dofbot-i2c7-100khz.dtbo
sudoedit /boot/extlinux/extlinux.conf
```

In the editor, leave the existing working entries intact. Duplicate the working
`primary` stanza as `LABEL DOFBOT100K`, retaining its exact `LINUX`, `INITRD`
and **entire `APPEND` line from this machine**. Add the explicit `FDT` and
`OVERLAYS` lines shown below. Set the top-level `TIMEOUT 150` (15 seconds) and
retain `DEFAULT primary`. This is a template, not a complete file to paste over
the existing configuration:

```text
LABEL DOFBOT100K
      MENU LABEL DOFBOT test - I2C7 100 kHz
      LINUX /boot/Image
      FDT /boot/dtb/kernel_tegra234-p3768-0000+p3767-0005-nv-super.dtb
      INITRD /boot/initrd
      APPEND <copy the full existing primary APPEND value here>
      OVERLAYS /boot/dofbot-i2c7-100khz.dtbo
```

Do not leave the angle-bracket placeholder in the installed entry. If your
working entry uses additional overlays, preserve the ones you need and validate
their combination separately. On this machine the separate `JetsonIO` entry
contains the dual-IMX219 camera overlay; the tested DOFBOT entry includes only
the clock overlay, so combining camera and DOFBOT overlays is not yet validated.

Review the final file with `cat /boot/extlinux/extlinux.conf`. Reboot with a
monitor and keyboard directly connected, watch the L4T boot list, and press the
number next to the DOFBOT label before timeout. `sudo reboot` initiates the
restart; the selection happens on the monitor during boot, not in the old
terminal. If you enter the UEFI screen with Escape, continue booting to reach
the L4T list; the boot-device menu and this kernel-entry list are different.
Check the active clock using the command at the top of this document.

No launcher in this folder installs or activates this configuration automatically.

NVIDIA guidance for the same Orin Nano Super configuration confirms an overlay
requires an explicit `FDT` selection; `OVERLAYS` alone did not apply:

- [Exact-board I²C overlay discussion](https://forums.developer.nvidia.com/t/jetpack-6-2-orin-nano-device-tree-overlay-to-change-i2c7-frequency/347656)
- [UEFI and device-tree selection](https://docs.nvidia.com/jetson/archives/r36.4.4/DeveloperGuide/SD/Bootloader/UEFI.html)

Yahboom's old `setup_i2c_clk_rate.py` writes to a `bus_clk_rate` sysfs file that
is absent on this JetPack 6 kernel. Do not try to recreate that file or alter the
BPMP input clock as though it were the I²C bus frequency.

## Rollback

Select `primary` on the next reboot to use the original boot configuration.
The original configuration backup on this machine is:

```text
/boot/extlinux/extlinux.conf.dofbot-backup-20261016T104021
```

A later backup before the menu-timeout change is also present:

```text
/boot/extlinux/extlinux.conf.before-menu-timeout-20261016T104857
```

Review later edits before restoring a whole backup. To remove the optional test,
remove only its `DOFBOT100K` stanza and overlay file while preserving other boot
entries. Nothing in this repository has changed the default to `DOFBOT100K`.
