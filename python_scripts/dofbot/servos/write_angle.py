#!/usr/bin/env python3
"""Move one servo to an absolute angle, without reading feedback."""
import argparse
from Arm_Lib import Arm_Device

arm = Arm_Device(i2c_bus=7, strict_errors=True)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--servo", type=int, required=True, choices=range(1, 7))
parser.add_argument("--angle", type=int, required=True, help="Absolute target in degrees.")
parser.add_argument("--time-ms", type=int, default=2000,
                    help="Movement duration in milliseconds (default: 2000; 0: fastest).")
args = parser.parse_args()


maximum = 270 if args.servo == 5 else 180
if not 0 <= args.angle <= maximum:
    parser.error(f"Servo {args.servo} angle must be between 0 and {maximum}")
if not 0 <= args.time_ms <= 65535:
    parser.error("--time-ms must be between 0 and 65535")

try:
    arm.Arm_serial_servo_write(args.servo, args.angle, args.time_ms)
    print(f"Command sent: servo {args.servo} -> {args.angle} degrees "
          f"in {args.time_ms} ms. Feedback was not read.")
finally:
    arm.bus.close()
