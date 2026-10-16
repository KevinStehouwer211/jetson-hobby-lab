#!/usr/bin/env python3
"""Move each servo to its configured angle, one at a time."""
import time
from Arm_Lib import Arm_Device

servos = [(1, 45), (2, 90), (3, 90), (4, 0), (5, 90), (6, 90)]
duration_ms = 1000

# Check every target before sending any movement commands.
for servo, angle in servos:
    if servo not in range(1, 7):
        raise ValueError("Servo ID must be between 1 and 6")
    maximum = 270 if servo == 5 else 180
    if not 0 <= angle <= maximum:
        raise ValueError(f"Servo {servo} angle must be between 0 and {maximum}")
if not isinstance(duration_ms, int) or not 0 <= duration_ms <= 65535:
    raise ValueError("duration_ms must be an integer between 0 and 65535")

arm = Arm_Device(i2c_bus=7, strict_errors=True)
try:
    for servo, angle in servos:
        arm.Arm_serial_servo_write(servo, angle, duration_ms)
        print(f"Command sent: servo {servo} -> {angle} degrees "
              f"in {duration_ms} ms.", flush=True)
        
        # Let the movement finish and the controller settle before querying.
        time.sleep(duration_ms / 1000 + 1.0)
        feedback = arm.Arm_serial_servo_read(servo)
        if feedback is None:
            raise RuntimeError(f"Servo {servo}: no valid feedback; remaining moves cancelled")
        print(f"Servo {servo}: target={angle}, feedback={feedback} degrees", flush=True)

finally:
    arm.bus.close()
