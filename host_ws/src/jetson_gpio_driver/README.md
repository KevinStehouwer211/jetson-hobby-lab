# jetson_gpio_driver

Exposes the Jetson's 40-pin header GPIO as `std_msgs/Bool` topics. Runs on the
host; see [../../README.md](../../README.md) for why.

## Three things called "GPIO driver"

| Layer | Source |
|---|---|
| Kernel `tegra234-gpio` → `/dev/gpiochip0/1` | Built into JetPack |
| `Jetson.GPIO` Python library | `pip3 install --user Jetson.GPIO` |
| **This package** | Hand-written — no official ROS 2 GPIO package exists |

## Interface

| Topic | Type | Direction |
|---|---|---|
| `/gpio_driver/output_<pin>` | `std_msgs/Bool` | subscribe — `true` = HIGH |
| `/gpio_driver/input_<pin>` | `std_msgs/Bool` | publish — polled |

Parameters in [config/gpio_params.yaml](config/gpio_params.yaml): `mode` (BOARD =
physical pin numbers), `output_pins`, `input_pins`, `publish_rate_hz`.

## Run

```bash
source /opt/ros/humble/setup.bash
cd ~/jetson-hobby-lab/host_ws
python3 src/jetson_gpio_driver/jetson_gpio_driver/gpio_driver_node.py \
  --ros-args --params-file src/jetson_gpio_driver/config/gpio_params.yaml
```

No `ros2 launch` on this host yet — the launch file works once `ros-base` is installed.
Inspect from the Isaac container: `ros2 topic echo /gpio_driver/input_16`.

## Install prerequisites

The udev rule ships **inside the pip wheel**:

```bash
sudo cp ~/.local/lib/python3.10/site-packages/Jetson/GPIO/99-gpio.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG gpio $USER    # then log out and back in
```

Board detection is automatic (device tree `nvidia,p3767-0005` → `JETSON_ORIN_NANO`).
`JETSON_MODEL_NAME` is only an override — leave it unset.

Verify everything with [`../../../scripts/check-gpio.sh`](../../../scripts/check-gpio.sh).

## Gotchas

- **`input_pull` does nothing.** Jetson.GPIO accepts `pull_up_down` for RPi
  compatibility and discards it — pulls are set by the device-tree pinmux. Wire a
  physical resistor. A floating input reads noise.
- **Inputs are polled, not edge-triggered** — misses pulses shorter than ~50 ms.
  `GPIO.add_event_detect` is the fix, not yet implemented.
- **No PWM.** Hardware PWM exists on pins **15, 32, 33** only; all three
  controllers are exported but the pinmux must be switched via `sudo /opt/nvidia/jetson-io/jetson-io.py`.
- **BOARD ≠ BCM.** BOARD is physical header position (what pinout diagrams show).

## ⚠️ Hardware safety

A **Yahboom hat is currently seated** on the header. All 22 GPIO pins read low and
none are kernel-claimed, but a low reading can't distinguish "unconnected" from
"held low by the hat" — so **don't drive outputs** until the hat is unseated or its
pinout is known. Two drivers fighting one line damages both.

Never jumper a GPIO to 5V (pins 2/4) — the header is 3.3V only.
