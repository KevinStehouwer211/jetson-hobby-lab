#!/usr/bin/env python3
from Arm_Lib import Arm_Device

# Queries only: no movement, torque, calibration, ID, or mode changes.
arm = Arm_Device(i2c_bus=7, strict_errors=True)
try:
    print("Controller:", arm.Arm_get_hardversion())
    for servo_id in range(1, 7):
        status = arm.Arm_ping_servo(servo_id)
        angle = arm.Arm_serial_servo_read(servo_id)
        print(f"Servo {servo_id}: ping={status!r}, angle={angle}")
finally:
    arm.bus.close()
