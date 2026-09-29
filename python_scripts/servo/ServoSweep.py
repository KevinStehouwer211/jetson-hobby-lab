"""Sweep S1/S2. Requires the patched firmware for the speed control.

The board now does the interpolation, so one command per move -- there is no
Python step loop and no per-step sleep to tune. Change SPEED to change how
fast it goes; move() returns once the board has finished.
"""
import Servo

PORT = '/dev/ttyUSB0'
BAUD = 115200
SPEED = 60          # degrees/second, 1-180. 0 = jump instantly (old behaviour)

s = Servo.servo(PORT, BAUD)
s.set_speed(SPEED)

s.move('A', 90)     # no wait: the board's position is unknown until we command it
s.move('B', 90)

for _ in range(3):
    s.move('A', 130)
    s.move('A', 50)

for _ in range(3):
    s.move('B', 130)
    s.move('B', 50)

s.close()
