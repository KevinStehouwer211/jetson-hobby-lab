#!/usr/bin/env python3
"""Read one or all servo angles without commanding movement."""
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--servo", type=int, choices=range(1, 7),
                    help="Read only this servo (default: all six).")
args = parser.parse_args()

from Arm_Lib import Arm_Device
arm = Arm_Device(i2c_bus=7, strict_errors=True)
try:
    for servo in ([args.servo] if args.servo else range(1, 7)):
        angle = arm.Arm_serial_servo_read(servo)
        if angle is None:
            raise RuntimeError(f"Servo {servo}: no valid angle returned")
        print(f"Servo {servo}: {angle} degrees")
finally:
    arm.bus.close()
