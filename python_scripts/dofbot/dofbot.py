import math
import time
from threading import Thread, Lock, Event
from Arm_Lib import Arm_Device


class Servo:
    def __init__(self, arm, servo_id, lock, min_angle=0, max_angle=180, traj="smooth"):
        self.arm = arm
        self.servo_id = servo_id
        self.lock = lock
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.traj = traj
        self.angle = None
        self.commanded = None
        self.target = None

    def validate(self, angle):
        if (
            not math.isfinite(angle)
            or not self.min_angle <= angle <= self.max_angle
        ):
            raise ValueError(
                f"Servo {self.servo_id}: invalid angle {angle}"
            )

    def read(self):
        for attempt in range(3):
            with self.lock:
                angle = self.arm.Arm_serial_servo_read(self.servo_id)

            if (
                angle is not None
                and math.isfinite(angle)
                and self.min_angle <= angle <= self.max_angle
            ):
                self.angle = angle
                return angle

            time.sleep(0.1)

        raise RuntimeError(
            f"Servo {self.servo_id}: no valid feedback"
        )

    def prepare(self, target):
        self.validate(target)

        self.commanded = self.read()
        self.target = target

        return abs(self.target - self.commanded)

    @staticmethod
    def smoothstep(t):
        return 3 * t**2 - 2 * t**3

    @staticmethod
    def linearstep(t):
        return t

    @staticmethod
    def timeStep(x, traj="smooth"):
        low, high = 0.0, 1.0

        for _ in range(20):
            mid = (low + high) / 2

            if traj == "linear":
                if Servo.linearstep(mid) < x:
                    low = mid
                else:
                    high = mid

            elif traj == "smooth":
                if Servo.smoothstep(mid) < x:
                    low = mid
                else:
                    high = mid

        return (low + high) / 2

    def move(self, duration, step_degrees, start_event,
             stop_event, start_time):

        start_angle = self.commanded
        delta = self.target - start_angle

        if abs(delta) < 1e-6:
            return

        steps = math.ceil(abs(delta) / step_degrees)

        start_event.wait()

        for step in range(1, steps + 1):
            if stop_event.is_set():
                return

            progress = step / steps

            # Determine when this step should occur
            time_fraction = self.timeStep(progress, self.traj)

            command_time = start_time[0] + duration * time_fraction
            remaining = command_time - time.monotonic()

            if remaining > 0:
                if stop_event.wait(remaining):
                    return

            next_angle = start_angle + delta * progress

            with self.lock:
                if stop_event.is_set():
                    return

                self.arm.Arm_serial_servo_write(
                    self.servo_id,
                    int(round(next_angle)),
                    10
                )

            self.commanded = next_angle

    def verify(self, tolerance=5):
        actual = self.read()

        if abs(actual - self.target) > tolerance:
            raise RuntimeError(
                f"Servo {self.servo_id}: "
                f"target={self.target}, actual={actual}"
            )

        print(
            f"Servo {self.servo_id}: "
            f"target={self.target}, actual={actual}"
        )


class Arm:
    def __init__(
        self,
        servo_count=6,
        speed=60,
        step_degrees=1,
        traj="smooth",
        i2c_bus=7
    ):
        if servo_count < 1 or servo_count > 6:
            raise ValueError("Servo count must be between 1 and 6")

        if not math.isfinite(speed) or speed <= 0:
            raise ValueError("Speed must be positive")

        if not math.isfinite(step_degrees) or step_degrees <= 0:
            raise ValueError("Step size must be positive")

        self.arm = Arm_Device(
            i2c_bus=i2c_bus,
            strict_errors=True
        )

        self.lock = Lock()
        self.speed = speed
        self.step_degrees = step_degrees
        self.traj = traj

        self.servos = {
            sid: Servo(
                arm=self.arm,
                servo_id=sid,
                lock=self.lock,
                min_angle=0,
                max_angle=270 if sid == 5 else 180,
                traj=self.traj
            )
            for sid in range(1, servo_count + 1)
        }

    def move(self, targets):
        """
        Move the selected servos simultaneously.

        The servo with the largest displacement determines
        the movement duration.
        """
        speed = self.speed  # Reset speed to initial value

        if not targets:
            return

        # Validate the complete request before hardware movement
        for sid, target in targets.items():
            if sid not in self.servos:
                raise ValueError(f"Unknown servo ID: {sid}")
            self.servos[sid].validate(target)

        # Read positions and prepare movements
        movements = {
            sid: self.servos[sid].prepare(target)
            for sid, target in targets.items()
        }
        largest_servo = max(movements, key=movements.get)
        largest_diff = movements[largest_servo]

        if largest_diff < 1e-6:
            return

        # Increase speed if servo 1 or 5 travels the largest angle
        speed = speed * 2 if largest_servo in (1, 5, 6) else speed

        # Smoothstep peak speed = 1.5 * average speed
        # Therefore duration is increased to limit peak speed.
        duration = 1.5 * largest_diff / speed

        print(f"\nMovement duration: {duration:.2f} s")

        start_event = Event()
        stop_event = Event()
        start_time = [0.0]
        errors = []
        threads = []

        def worker(servo):
            try:
                servo.move(
                    duration=duration,
                    step_degrees=self.step_degrees,
                    start_event=start_event,
                    stop_event=stop_event,
                    start_time=start_time
                )
            except Exception as error:
                errors.append(error)
                stop_event.set()

        for sid in targets:
            thread = Thread(
                target=worker,
                args=(self.servos[sid],)
            )
            thread.start()
            threads.append(thread)

        # Start all movement schedules from a common timestamp
        start_time[0] = time.monotonic()
        start_event.set()

        for thread in threads:
            thread.join()

        if errors:
            raise RuntimeError(
                f"Movement failed: {errors[0]}"
            )

        # Allow the last movement commands to settle
        time.sleep(0.05)

        # Often verification fails due to servo feedback lag. 
        # Consider increasing the sleep time if verification fails.
        # for sid in targets:
        #     self.servos[sid].verify()

    def reset(self):
        """Move all configured servos to 90 degrees."""
        self.move({
            sid: 90
            for sid in self.servos
        })

    def read(self):
        """Return current feedback angles."""
        return {
            sid: servo.read()
            for sid, servo in self.servos.items()
        }

    def close(self):
        self.arm.bus.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()