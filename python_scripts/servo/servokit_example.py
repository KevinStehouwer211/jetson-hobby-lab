from yahboom_servokit import ServoKit
import time


kit = ServoKit(channels=24, port='/dev/ttyUSB0')

kit.servo[0].angle = 90  # A: sends $A090#
kit.servo[1].angle = 90  # B: sends $B090#
time.sleep(1.0)  # Allow the initial targets to settle; adjust as needed.

# A: 90 -> 0, in 1-degree steps. 0.1 seconds per step ~ 10 degrees/s.
for angle in range(90, 0, -1):
    kit.servo[0].angle = angle
    time.sleep(0.01)
time.sleep(0.5)  # Optional settling allowance at 45 degrees.

# This loop only starts after the preceding loop and wait finish.
for angle in range(0, 90, 1):
    kit.servo[0].angle = angle
    time.sleep(0.01)
time.sleep(0.5)
