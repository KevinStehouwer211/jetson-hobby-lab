"""ServoKit-style angle assignments for Yahboom's $Axxx# serial protocol.

This implements the servo[index].angle interface, not the full Adafruit API.
No movement interpolation, command queue or movement delay is hidden here.
"""

import math
from numbers import Real
import time


class _Servo:
    def __init__(self, kit, index):
        self._kit = kit
        self._channel = chr(ord('A') + index)
        self._angle = None

    @property
    def angle(self):
        """Last target sent by this object, or None; not measured position."""
        return self._angle

    @angle.setter
    def angle(self, value):
        if (isinstance(value, bool) or not isinstance(value, Real)
                or not math.isfinite(value) or not 0 <= value <= 180):
            raise ValueError('angle must be a finite number from 0 to 180')
        # The existing UART protocol carries whole degrees only.
        angle = int(value + 0.5)
        packet = ('$%s%03d#' % (self._channel, angle)).encode('ascii')
        if self._kit._serial.write(packet) != len(packet):
            raise IOError('Incomplete serial write')
        self._kit._serial.flush()  # Transmission only; no wait for servo motion.
        self._angle = angle


class ServoKit:
    def __init__(self, channels=24, port='/dev/ttyUSB0', startup_delay=2.0):
        """Open USB serial at 115200 8N1 without sending position commands.

        startup_delay is a one-time boot allowance in case opening USB serial
        resets the board. It is never applied to angle assignments.
        """
        if type(channels) is not int or not 1 <= channels <= 24:
            raise ValueError('channels must be an integer from 1 to 24')
        if not math.isfinite(startup_delay) or startup_delay < 0:
            raise ValueError('startup_delay must be finite and nonnegative')
        import serial

        self._serial = serial.Serial(port, baudrate=115200, timeout=0.1,
                                     write_timeout=1)
        self.servo = tuple(_Servo(self, index) for index in range(channels))
        try:
            if startup_delay:
                time.sleep(startup_delay)
        except BaseException:
            self._serial.close()
            raise

    def close(self):
        """Close serial; the firmware continues holding its last targets."""
        self._serial.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
