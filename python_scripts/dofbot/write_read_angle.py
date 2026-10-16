#!/usr/bin/env python3
"""Read a servo angle, move to an absolute target, then read feedback."""
import argparse
import time

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

from Arm_Lib import Arm_Device
arm = Arm_Device(i2c_bus=7, strict_errors=True)
try:
    before = arm.Arm_serial_servo_read(args.servo)
    if before is None:
        raise RuntimeError("No valid starting angle; no movement commanded")
    print(f"Before: servo {args.servo} = {before} degrees", flush=True)
    arm.Arm_serial_servo_write(args.servo, args.angle, args.time_ms)
    time.sleep(args.time_ms / 1000 + 1.0)
    after = arm.Arm_serial_servo_read(args.servo)
    if after is None:
        raise RuntimeError("Command sent, but no valid final angle returned")
    print(f"Target: {args.angle} degrees; feedback: {after} degrees")
finally:
    arm.bus.close()
