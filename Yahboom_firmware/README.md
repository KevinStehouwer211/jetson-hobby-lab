# Yahboom 24-channel servo controller firmware

This folder contains the firmware for the **Yahboom 24-channel dual PWM servo control debugging board**, using the **STM32F103RCT6** controller.

It lets the Jetson control servos through the board's **USB-C connection**, while keeping the voltage/current display and buzzer functions. The owner confirmed the board works as expected after flashing and restarting it.

**Flash [stree_free_ii.hex](stree_free_ii.hex) in this folder.** Other HEX files deeper in the source folders belong to older builds or other projects.

## What was done

1. Cloned the repository and selected the `2DOF_No handle` controller project.
2. Built the existing source from commit [65ffd42](https://github.com/KevinStehouwer211/jetson-hobby-lab/commit/65ffd425ef4f5271f3f780f519b844e3eae7b74b) using Keil ARM Compiler 5.06 update 7 (build 960) on Windows.
3. Checked the build for errors and verified all 1,552 HEX records, flash boundaries, startup address and stack address.
4. Replaced this folder's HEX and pushed it in commit [e8bacdf](https://github.com/KevinStehouwer211/jetson-hobby-lab/commit/e8bacdf98a88c3118d1c1fcfde3810536881ae8b).
5. Flashed from the Jetson over USB-C. The flashing tool verified the written data, and the owner confirmed operation after reset.

The source was already edited in the repository. This rebuild added **no source changes**: it included the existing USB command fix and newer servo speed-control code. The linker also enforced the chip's 256 KiB flash and 48 KiB RAM limits.

Initially the OLED was blank and servos did not respond after flashing. The board was still in its **bootloader**, the built-in program that receives new firmware. **Releasing BOOT and resetting started the application and resolved this. No additional firmware fix was needed or pushed.**

## How it works

The Jetson sends a short text command over USB. The controller reads the command, stores the requested angle and repeatedly sends a pulse to the servo. The pulse width tells the servo which position to move toward.

Pulses repeat every **20 milliseconds (50 times per second)**. This version uses a timer interrupt and GPIO outputs to generate them in software, with 20-microsecond timing steps. A new command replaces the previous target for that channel; there is no movement queue.

By default, the next pulse frame uses the new target without a firmware speed limit. The servo still takes time to move physically. An optional speed command makes the controller change its requested position gradually instead.

All target positions start at **90 degrees**. The controller also reads voltage/current sensors and updates the OLED. It does not measure actual servo positions, so sending a command does not confirm physical arrival.

### USB connection and commands

| Setting | Value |
| --- | --- |
| Connection | Jetson USB host port to controller USB-C port |
| Typical Linux device | `/dev/ttyUSB0`; check your actual device |
| Application serial settings | **115200 baud, 8N1** |
| Servo channels | `A`–`X`, corresponding to `S1`–`S24` |
| Position range | `000`–`180` degrees |

The vendor USB handler originally echoed incoming bytes. The existing change in `BSP/bsp_usart.c` passes them to `deal_bluetooth()` instead, allowing USB commands to control servos. The separate USART3 header and UART5 Bluetooth interface still use 9600 baud; USB-C uses 115200.

Each command starts with `$`, has a letter and **exactly three digits**, and ends with `#`:

| Command | Meaning |
| --- | --- |
| `$A090#` | Set servo S1's target to 90 degrees |
| `$B045#` | Set servo S2's target to 45 degrees |
| `$X180#` | Set servo S24's target to 180 degrees |
| `$Y060#` | Set the shared movement rate to approximately 60 degrees/second |
| `$Y000#` | Disable the firmware speed limit; this is the startup default |

`Y` is a speed setting, not a 25th servo. It applies to all channels until changed or the controller restarts. Nonzero settings are `001`–`180`; actual rates are approximate because movement is calculated in small steps.

Send valid short commands and use one sender at a time. The existing parser does not safely handle arbitrary long or malformed input.

## Flash from the Jetson

### 1. Get the latest HEX

Run in a Jetson terminal, including a VS Code SSH terminal connected to the Jetson:

```bash
cd ~/jetson-hobby-lab
git pull --ff-only
sudo apt update
sudo apt install stm32flash python3-serial
```

Optional file check:

```bash
sha256sum Yahboom_firmware/stree_free_ii.hex
```

For this build, the expected SHA256 is:

```text
706e407bbdcd5b38eaea53abb765feaec836971889c4ae01915235999e4bd8e9
```

### 2. Enter flashing mode

Stop Python/ROS servo programs and close serial monitors. Hold **BOOT** while connecting the board's USB-C cable to the Jetson. If already powered, hold **BOOT** while pressing and releasing **RESET**.

Identify the board's port:

```bash
ls -l /dev/serial/by-id/
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

Replace `/dev/ttyUSB0` below if the board has another device path.

### 3. Write and verify

From the repository root on the Jetson:

```bash
sudo stm32flash -b 115200 \
  -w Yahboom_firmware/stree_free_ii.hex \
  -v /dev/ttyUSB0
```

Wait for `Wrote and verified ... (100.00%) Done.` The bootloader uses **8E1**, selected automatically by stm32flash. Normal servo commands use **8N1**.

### 4. Start the firmware — do not skip this

**The command above writes and verifies the firmware; it does not start it.**

Release **BOOT**, then press **RESET**. Alternatively, disconnect **both USB and external power**, then reconnect with BOOT released. Removing USB alone does not restart a board that still has external power.

The OLED should start again. Allow room for the servos to move to their initial 90-degree positions. Use the appropriate external servo supply; USB alone is not the servo power supply and may produce a low-voltage warning.

## Try a servo command

After restarting, run this on the Jetson to set S1 and S2 to 90 degrees:

```bash
sudo python3 - <<'PY'
import serial
import time

with serial.Serial('/dev/ttyUSB0', 115200, timeout=1) as board:
    time.sleep(0.2)
    board.write(b'$Y000#$A090#$B090#')
    board.flush()
PY
```

More examples are in [python_scripts/servo](../python_scripts/servo/).

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Blank OLED and no response immediately after flashing | Release BOOT and reset, or disconnect both power sources and reconnect. The board may still be in its bootloader. |
| Flashing cannot connect | Enter BOOT/reset mode again; check the device path, USB data cable and competing serial programs. |
| OLED works but servos do not move | Check external servo power, the board's switch, servo plug orientation, channel and 115200 baud. |
| Low-voltage message or buzzer | Check external power; USB-only operation can trigger the existing warning. |

If it remains blank after a full restart, keep the complete flashing output for diagnosis.

## Source and rebuilding

The active source project is:

```text
24-ChannelServoDriveBoard_Code/STM32_Code_Additional/2DOF_No handle/
```

| File | Purpose |
| --- | --- |
| `USER/main.c` | Set startup positions and run voltage/current display updates |
| `BSP/bsp_usart.c` | Receive serial commands, including USB-C traffic |
| `APP/user_bluetooth.c` | Read angle commands and the `Y` speed setting |
| `BSP/bsp_servo.c` | Store target positions, intermediate positions and speed |
| `BSP/bsp_timer.c` | Move intermediate positions toward targets and generate pulses |
| `APP/user_vol.c` | Format voltage/current readings and alarm messages |

On Windows, open `USER/steer_freeII.uvprojx` in Keil uVision and select target **steer_free_II** with **ARM Compiler 5.06 update 7 (build 960)**. This project is configured for Compiler 5; switching to Compiler 6 needs separate porting and validation. Set the target limits to 256 KiB flash and 48 KiB RAM.

The output is `OBJ/stree_free_ii.hex`. For this release, uVision's build stalled, so the installed Compiler 5 tools were called directly with the project's source list, C99, O0, microlib, defines and include paths. The resulting HEX was copied to this folder's root for flashing.

A compiler license is needed for rebuilding. The compiled HEX does not expire or require that license to flash. Build/image checks and the owner's confirmation establish this release's verification; pulse accuracy and every channel were not bench-measured.

## References

- [Yahboom USB-C flashing and BOOT-button instructions](https://www.yahboom.net/public/upload/upload-html/1705379178/Download%20program.html)
- [stm32flash command reference](https://manpages.ubuntu.com/manpages/bionic/man1/stm32flash.1.html)
