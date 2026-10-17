"""Class-based servo control with interleaved one-degree position commands.

Run directly to move to TARGETS and then reset to 90 degrees. All I2C traffic
uses one scheduler: no grouped writes and no competing hardware threads.
"""
import math
import time
from threading import Lock

TARGETS = {1: 45, 2: 90, 3: 45, 4: 60, 5: 90, 6: 170}
SPEED = 60  # Nominal maximum degrees/second per joint.
STEP_DEGREES = 1 # Maximum degrees per incremental command. Lower values reduce overshoot and vibration, but increase total movement time.
COMMAND_GAP_S = .005 # Minimum time between commands to the same servo. Lower values reduce total movement time, but may cause I2C errors if the controller is busy.    
FEEDBACK_TOLERANCE = 5 # Maximum degrees difference between commanded and actual position before stopping all movement. Lower values reduce overshoot, but may cause false stalls if the controller is busy or the servo is noisy.


class Servo:
    def __init__(self, arm, servo_id, min_angle=0, max_angle=180,
                 speed=SPEED, lock=None):
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError('Speed must be positive and finite')
        self.arm = arm
        self.servo_id = servo_id
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.speed = speed
        self.lock = lock if lock is not None else Lock()
        self.angle = None
        self.commanded = None
        self.target = None

    def validate(self, target):
        if (not math.isfinite(target) or int(target) != target
                or not self.min_angle <= target <= self.max_angle):
            raise ValueError(f'Servo {self.servo_id}: target must be an integer '
                             f'between {self.min_angle} and {self.max_angle}')

    def read(self):
        for attempt in range(3):
            with self.lock:
                value = self.arm.Arm_serial_servo_read(self.servo_id)
            if (value is not None and math.isfinite(value)
                    and self.min_angle <= value <= self.max_angle):
                self.angle = value
                return value
            if attempt < 2:
                time.sleep(.1)
        raise RuntimeError(f'Servo {self.servo_id}: no valid feedback after 3 reads')

    def move(self, target):
        """Queue a target; the shared scheduler sends the incremental commands."""
        self.validate(target) # Validate feasibility of the target angle.
        self.read()  # Ensure the current position is valid before moving.
        self.commanded = self.angle
        self.target = int(target)

    @property
    def moving(self):
        return self.target is not None and self.commanded != self.target

    def step(self):
        if not self.moving:
            return False

        total = self.target - self.commanded

        if abs(total) < 1e-6:
            self.moving = False
            return False

        # Movement progress: 0 at start, 1 at target
        remaining = self.target - self.angle

        if abs(remaining) < 1e-6:
            self.moving = False
            return False

        x = abs(remaining) / abs(total)

        # Quadratic gain: 0 at endpoints, 1 at midpoint
        gain = 4 * x * (1 - x)

        # Prevent zero speed at start and end
        MIN_GAIN = 0.2
        gain = MIN_GAIN + (1 - MIN_GAIN) * gain

        distance = min(STEP_DEGREES, abs(remaining))
        next_angle = self.commanded + math.copysign(distance, remaining)

        # Lower gain -> longer duration -> slower motion
        duration_ms = max(
            1,
            math.ceil(distance / (self.speed * gain) * 1000)
        )

        with self.lock:
            self.arm.Arm_serial_servo_write(
                self.servo_id,
                next_angle,
                duration_ms
            )

        self.commanded = next_angle

        return True

    def verify(self):
        actual = self.read()
        if abs(actual - self.commanded) > FEEDBACK_TOLERANCE:
            raise RuntimeError(f'Servo {self.servo_id}: commanded {self.commanded}°, '
                               f'feedback {actual}°; remaining moves cancelled')
        # Keep the planned position separate from rounded/noisy feedback.

    def reset(self):
        self.move(90)


def move_interleaved(servos, targets):

    ordered = [servos[sid] for sid in sorted(servos)]

    # Validate all targets before sending any movement commands.
    for servo in ordered:
        servo.move(targets[servo.servo_id])
        
    cycle = max(math.ceil(STEP_DEGREES / servo.speed * 1000) / 1000
                for servo in ordered)
    while any(servo.moving for servo in ordered):
        started = time.monotonic()
        last_command = started
        for servo in ordered:
            if servo.step():
                last_command = time.monotonic()
                time.sleep(COMMAND_GAP_S)
        # Keep each joint's steps on a steady cadence. Only the final round
        # waits for the last joint to finish before querying feedback.
        deadline = started + cycle if any(s.moving for s in ordered) else last_command + cycle
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
    # Reads include controller recovery delays, so keep them outside motion.

    # Verify if target has been reached.
    for servo in ordered:
        servo.verify()
    for servo in ordered:
        print(f'Servo {servo.servo_id}: target={servo.target}°, '
              f'feedback={servo.angle}°', flush=True)


def run(arm):
    lock = Lock()
    servos = {sid: Servo(arm, sid, 0, 270 if sid == 5 else 180, lock=lock)
              for sid in range(1, 7)}
    try:
        move_interleaved(servos, TARGETS)
        move_interleaved(servos, dict.fromkeys(servos, 90))
    finally:
        arm.bus.close()


def main():
    from Arm_Lib import Arm_Device
    try:
        run(Arm_Device(i2c_bus=7, strict_errors=True))
    except (RuntimeError, OSError, ValueError) as error:
        raise SystemExit(f'Movement stopped: {error}')


if __name__ == '__main__':
    main()
