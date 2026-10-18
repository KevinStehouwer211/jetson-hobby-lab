import time
from dofbot import Arm


def main():
    with Arm(
        servo_count=6,
        speed=60,
        step_degrees=1,
        traj="smooth",
        i2c_bus=7
    ) as robot:

        robot.move({
            1: 0,
            2: 90,
            3: 90,
            4: 90,
            5: 180,
            6: 90
        })

        robot.move({
            1: 90,
            2: 90,
            3: 90,
            4: 90,
            5: 90,
            6: 170
        })

        robot.reset()


if __name__ == "__main__":
    main()