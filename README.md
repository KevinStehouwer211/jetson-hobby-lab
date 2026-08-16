# 🤖 Jetson Hobby Lab

Robotics/AI workspace for the **Jetson Orin Nano Super** + Yahboom platform.
Compute runs in containers; hardware (GPIO, I2C, UART) runs on the host.

---

## 📍 Where I left off — 2026-08-16

| Area | Status | Next step |
|---|---|---|
| Isaac ROS container | ✅ Working, `check-env.sh` 8/8 | — |
| GPIO **input** via ROS | ✅ Host node → container reads topic | — |
| GPIO **output** | ⏸️ Untested — Yahboom hat is seated, driving pins risks contention | Unseat hat, then `check-gpio.sh --loopback 18 16` |
| OLED (SH1106, `0x3c`) | ⚠️ **Half working** — text renders but top rows are clipped | See [OLED debugging](#-oled-debugging-unfinished) below |
| Expansion MCU (`0x0e`) | ❌ Untouched, register map unknown | Get Yahboom docs before writing to it |
| UART | ❌ Blocked | `usermod -aG dialout`, `pip install pyserial` |
| Git | ⚠️ Nothing committed since June — `host_ws/`, `scripts/check-gpio.sh`, `scripts/oled_write.py`, `docker/isaac-ros-humble/bashrc` untracked; `run.sh` + this README modified | `git add -A && git commit` |

**Host ROS 2 is a partial install** — `rclpy` works, but there's no `ros2` CLI and no
`launch_ros`, so run nodes with `python3 … --ros-args` and use the container's CLI
to inspect topics. Details in [host_ws/README.md](host_ws/README.md).

### 🔧 OLED debugging (unfinished)

Confirmed: it's an **SH1106** (not SSD1306 despite the label), 128×64, `0x3c` on
I2C bus 7. Page-at-a-time addressing + 2-column offset are already in
[scripts/oled_write.py](scripts/oled_write.py) and text does render.

Remaining bug: the top of each line is cut off. Untested hypotheses, cheapest first:

1. `LINE_HEIGHT = 12` is too tight for the ~11 px font → try `16`
2. Panel hides a few top rows → add a 2–3 px top margin in `render()`
3. Real vertical offset → change `0xD3, 0x00` in `INIT` to `0xD3, 2`
4. Panel is 128×32 → set `HEIGHT = 32`, `0xA8, 0x1F`, `0xDA, 0x02`

---

## 🗂️ Layout

```text
jetson-hobby-lab/
├── docker/isaac-ros-humble/run.sh   # launches NVIDIA's Isaac dev container
├── isaac_ros_ws/                    # mounted into that container
├── ros2_ws/                         # custom container workspace (unused so far)
├── host_ws/                         # runs ON THE HOST — owns GPIO/I2C/UART
└── scripts/                         # check-env.sh, check-gpio.sh, oled_write.py, fix-gpu-perms.sh
```

**The split that matters:** needs the GPU → container. Needs a `/dev` node the host
owns → `host_ws`. See [host_ws/README.md](host_ws/README.md).

---

## 🚀 Quickstart

**Isaac ROS container** (GPU, full ROS 2 CLI):

```bash
~/jetson-hobby-lab/docker/isaac-ros-humble/run.sh   # drops you in /workspaces/isaac_ros-dev
/host_scripts/check-env.sh                          # GPU/CUDA/ROS health, expect 8 passed
```

First run clones needed: `git clone -b release-3.2 https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_common.git`
into `isaac_ros_ws/src/`. The launcher auto-fixes the non-root CUDA "Error 801"
permission bug — full explanation in [scripts/fix-gpu-perms.sh](scripts/fix-gpu-perms.sh).

**Host hardware** (no container):

```bash
./scripts/check-gpio.sh                    # read-only: library, perms, pin survey, I2C scan
./scripts/oled_write.py "Hello" "Jetson"   # write to the OLED
```

---

## 🔗 Links

- [Isaac ROS docs](https://nvidia-isaac-ros.github.io/) · [compatibility matrix](https://nvidia-isaac-ros.github.io/getting_started/index.html)
- [Yahboom Orin Nano course](https://www.yahboom.net/study/Orin-Nano-SUPER) — section 04 = GPIO/UART/I2C
- [Jetson.GPIO](https://github.com/NVIDIA/jetson-gpio) · [Orin Nano pinout](https://jetsonhacks.com/nvidia-jetson-orin-nano-gpio-header-pinout/)
