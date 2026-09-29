"""Driver for the Yahboom 24-channel servo board.

Wire protocol (USB-C, 115200 8N1):
    $<channel><angle>#      channel A-X = S1-S24, angle 000-180
    $Y<rate>#               slew rate in degrees/second, 000-180; 0 = instant

The $Y rate command and the blocking move() below require the patched
firmware. Do NOT send $Y to the stock firmware: its parser indexes
Angle_J[(25-1)/8][...] without a bounds check and writes past the array.
"""
import time

import serial

FRAME_S = 0.020        # the board's PWM frame, 20 ms
SUBSTEPS = 16          # firmware tracks position in 1/16 degree


class servo():
    def __init__(self, port='/dev/ttyUSB0', baud=115200):
        self.ser = serial.Serial(
            port,
            baud,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=0.5
        )
        self._speed = 0
        self._pos = {}

    def frame(self, channel, angle):
        return '${}{:03d}#'.format(channel, angle).encode('ascii')

    def send(self, channel, angle):
        angle = max(0, min(180, int(angle)))
        self.ser.write(self.frame(channel, angle))
        self._pos[channel] = angle

    def set_speed(self, dps):
        """Set the board's slew rate. 0 = jump instantly (stock behaviour)."""
        dps = max(0, min(180, int(dps)))
        self.ser.write(self.frame('Y', dps))
        self._speed = dps

    def travel_time(self, channel, angle):
        """Seconds the board will take to reach angle, per its own step math."""
        start = self._pos.get(channel)
        if self._speed <= 0 or start is None:
            return 0.0
        step = max(1, (self._speed * SUBSTEPS) // 50)      # 1/16 deg per frame
        units = abs(int(angle) - start) * SUBSTEPS
        frames = -(-units // step)                          # ceil
        return frames * FRAME_S

    def move(self, channel, angle, wait=True):
        """Command a move and block until the board should have finished it."""
        angle = max(0, min(180, int(angle)))
        delay = self.travel_time(channel, angle)
        self.send(channel, angle)
        if wait and delay:
            time.sleep(delay)
        return angle

    def close(self):
        self.ser.close()
