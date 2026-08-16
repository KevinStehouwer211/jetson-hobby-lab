# 🔌 host_ws — the host-side ROS 2 workspace

Built and run **on the Jetson host**, not in a container.

## Why

The host owns the hardware: `/dev/gpiochip*` (group `gpio`), `/dev/i2c-*` (`i2c`),
`/dev/ttyTHS*` (`dialout`). Reaching those from a container needs `--privileged`.
Instead, a thin node runs on the host and re-publishes the hardware as ROS topics —
containers stay unprivileged and just subscribe.

```text
HOST: gpio_driver owns /dev/gpiochip*  ──DDS──►  CONTAINER: your nodes
```

Discovery works with no config: the Isaac container runs `--network host`, both
sides use `rmw_fastrtps_cpp`, and neither sets `ROS_DOMAIN_ID` (so both are 0).
**Verified working** — the container reads `/gpio_driver/input_16` live.

## What goes here

✅ Anything needing a host `/dev` node — GPIO, I2C, UART.
❌ Anything needing the GPU — that belongs in `isaac_ros_ws/` or `ros2_ws/`.

## Build and run

> ⚠️ The host's ROS 2 is a **partial install** (114 packages — the `image_pipeline`
> dependency closure, not `ros-base`). `rclpy` and `std_msgs` work, so nodes run,
> but there is **no `ros2` CLI and no `launch_ros`**.

```bash
source /opt/ros/humble/setup.bash
cd ~/jetson-hobby-lab/host_ws
colcon build --symlink-install

# run a node directly — rclpy parses --ros-args without the CLI
python3 src/jetson_gpio_driver/jetson_gpio_driver/gpio_driver_node.py \
  --ros-args --params-file src/jetson_gpio_driver/config/gpio_params.yaml
```

Use the **container's** `ros2` CLI to inspect (`ros2 topic echo /gpio_driver/input_16`).
First query after container start can miss topics — DDS discovery cold start; just run it twice.

> Don't test ROS health with `$ROS_DISTRO` here — this install ships no
> `ros_distro.sh` hook, so it stays empty even when sourcing worked. Use
> `python3 -c "import rclpy"`.

**To get `ros2 launch` + CLI** (optional, adds to the host):

```bash
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=arm64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/ros2.list
sudo apt update && sudo apt install -y ros-humble-ros-base
```

The ROS apt repo is **not currently configured**, so `apt install ros-humble-*` fails until you add it.

## Host prerequisites

| Requirement | Status |
|---|---|
| `rclpy`, `std_msgs`, `colcon` | ✅ |
| `ros2` CLI, `launch_ros`, ROS apt repo | ❌ |
| `Jetson.GPIO` 2.1.12, `gpio` group, `99-gpio.rules` | ✅ |
| `i2c` group, `smbus2`, `i2c-tools` | ✅ |
| `dialout` group, `pyserial` (for UART) | ❌ |

Run [`../scripts/check-gpio.sh`](../scripts/check-gpio.sh) to re-verify all of it.

## Packages

- [`jetson_gpio_driver`](src/jetson_gpio_driver/) — GPIO in/out as `std_msgs/Bool` topics

## Roadmap

Following [Yahboom section 04](https://www.yahboom.net/study/Orin-Nano-SUPER):

- [x] GPIO input (polled) · [x] GPIO output (untested — hat attached)
- [ ] Edge detection instead of polling · [ ] PWM (pins 15/32/33, needs `jetson-io`)
- [ ] `jetson_oled_driver` — wrap [`../scripts/oled_write.py`](../scripts/oled_write.py) as a node
- [ ] `jetson_serial_driver` — blocked on `dialout` + `pyserial`
