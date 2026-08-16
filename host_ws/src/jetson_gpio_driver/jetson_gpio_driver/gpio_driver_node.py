#!/usr/bin/env python3
"""GPIO driver node for NVIDIA Jetson, exposing board GPIO over ROS 2.

Runs on the *host*, which owns /dev/gpiochip* and the 'gpio' group, so compute
containers (Isaac ROS, etc.) never need privileged device access -- they just
publish/subscribe over DDS. With the Isaac container on --network host and a
matching ROS_DOMAIN_ID (+ RMW_IMPLEMENTATION), discovery is automatic.

Pin I/O is exposed with stock std_msgs/Bool so no custom interface package is
needed:
  * each output pin gets a subscription   ~/output_<pin>  (True -> HIGH)
  * each input pin gets a publisher        ~/input_<pin>   (polled at rate)

Configure pins via parameters (see config/gpio_params.yaml).
"""

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import ParameterDescriptor
from std_msgs.msg import Bool

try:
    import Jetson.GPIO as GPIO
except ImportError as exc:  # hardware/host-only dependency
    GPIO = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class GpioDriver(Node):
    """Bridges Jetson board GPIO to ROS 2 topics."""

    def __init__(self):
        super().__init__('gpio_driver')

        dyn = ParameterDescriptor(dynamic_typing=True)
        self.declare_parameter('mode', 'BOARD')
        self.declare_parameter('output_pins', [], dyn)
        self.declare_parameter('input_pins', [], dyn)
        self.declare_parameter('input_pull', 'PUD_OFF')
        self.declare_parameter('publish_rate_hz', 20.0)

        if GPIO is None:
            raise RuntimeError(
                f'Jetson.GPIO is not importable ({_IMPORT_ERROR}). This node '
                'must run where Jetson.GPIO is installed (the host).')

        mode_name = self.get_parameter('mode').value
        pull_name = self.get_parameter('input_pull').value
        output_pins = list(self.get_parameter('output_pins').value or [])
        input_pins = list(self.get_parameter('input_pins').value or [])
        rate = float(self.get_parameter('publish_rate_hz').value)

        modes = {
            'BOARD': GPIO.BOARD,
            'BCM': GPIO.BCM,
            'CVM': GPIO.CVM,
            'TEGRA_SOC': GPIO.TEGRA_SOC,
        }
        pulls = {
            'PUD_OFF': GPIO.PUD_OFF,
            'PUD_UP': GPIO.PUD_UP,
            'PUD_DOWN': GPIO.PUD_DOWN,
        }
        if mode_name not in modes:
            raise ValueError(f'Unknown mode {mode_name!r}; pick one of {list(modes)}')
        if pull_name not in pulls:
            raise ValueError(f'Unknown input_pull {pull_name!r}; pick one of {list(pulls)}')

        GPIO.setwarnings(False)
        GPIO.setmode(modes[mode_name])

        # Outputs: one Bool subscription per pin; True -> HIGH, False -> LOW.
        self._output_subs = []
        for pin in output_pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            self._output_subs.append(
                self.create_subscription(
                    Bool, f'~/output_{pin}', self._make_output_cb(pin), 10))
            self.get_logger().info(f'output pin {pin} -> ~/output_{pin}')

        # Inputs: one Bool publisher per pin, polled by a single timer.
        self._input_pins = list(input_pins)
        self._input_pubs = {}
        for pin in self._input_pins:
            GPIO.setup(pin, GPIO.IN, pull_up_down=pulls[pull_name])
            self._input_pubs[pin] = self.create_publisher(Bool, f'~/input_{pin}', 10)
            self.get_logger().info(f'input pin {pin} -> ~/input_{pin}')

        if self._input_pins and rate > 0.0:
            self._timer = self.create_timer(1.0 / rate, self._poll_inputs)

        self.get_logger().info(
            f'gpio_driver up: mode={mode_name}, outputs={output_pins}, '
            f'inputs={input_pins}')

    def _make_output_cb(self, pin):
        def cb(msg):
            GPIO.output(pin, GPIO.HIGH if msg.data else GPIO.LOW)
            self.get_logger().debug(f'pin {pin} <- {"HIGH" if msg.data else "LOW"}')
        return cb

    def _poll_inputs(self):
        for pin, pub in self._input_pubs.items():
            pub.publish(Bool(data=bool(GPIO.input(pin))))


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = GpioDriver()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if GPIO is not None:
            GPIO.cleanup()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
