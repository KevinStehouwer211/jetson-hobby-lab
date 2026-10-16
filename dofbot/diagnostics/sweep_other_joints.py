#!/usr/bin/env python3
"""Approved 10-degree out-and-back sweeps of joints 2..6, sequentially.

Stops at first failure. No torque/calibration/mode commands or retries.
Requires explicit approval for all five joints and --confirm-motion.
"""
import argparse
import sys
import time
from servo_diagnostic import Arm_Device, monitor
from repeat_servo1 import clock_hz


def run():
    if clock_hz() != 100000:
        raise RuntimeError('Test requires bus-7 DT setting 100000')
    arm = Arm_Device(i2c_bus=7, strict_errors=True)
    try:
        time.sleep(0.1)
        if arm.read_recovery_s != 0.1:
            raise RuntimeError('Test requires library feedback recovery 100ms')
        if arm.Arm_get_hardversion() is None:
            raise RuntimeError('Controller version unavailable')
        starts = {}
        for sid in range(1, 7):
            ping = arm.Arm_ping_servo(sid)
            time.sleep(0.02)
            angle = arm.Arm_serial_servo_read(sid)
            time.sleep(0.02)
            print(f'Baseline servo {sid}: ping={ping}, angle={angle}', flush=True)
            if ping != 0xDA or angle is None:
                raise RuntimeError('Baseline queries failed; no movement sent')
            starts[sid] = angle
        plan = {}
        for sid in range(2, 7):
            start = starts[sid]
            limit = 270 if sid == 5 else 180
            target = start + 10 if start + 10 <= limit else start - 10
            if not 0 <= start <= limit or not 0 <= target <= limit:
                raise RuntimeError('Baseline outside joint limits')
            plan[sid] = [target, start]
        print(f'Plan: {plan}; 2000ms per leg; joints move sequentially.', flush=True)
        for sid, targets in plan.items():
            expected = starts[sid]
            lower, upper = min(targets), max(targets)
            for leg, target in enumerate(targets, 1):
                before = arm.Arm_serial_servo_read(sid)
                if before is None or abs(before - expected) > 2:
                    raise RuntimeError(f'Servo {sid}: feedback changed before leg {leg}; stopping')
                if not lower - 2 <= before <= upper + 2 or abs(target - before) > 12:
                    raise RuntimeError(f'Servo {sid}: outside approved test envelope')
                print(f'Servo {sid} leg {leg}/2: {before} -> {target}, 2000ms', flush=True)
                arm.Arm_serial_servo_write(sid, target, 2000)
                time.sleep(2.5)
                samples = monitor(arm, sid, 4, 0.5)
                final = samples[-3:]
                passed = len(final) == 3 and all(
                    v is not None and abs(v - target) <= 2 and
                    (v - before) * (target - before) > 0 for v in final)
                print(f'Servo {sid} leg {leg}: {"PASS" if passed else "FAIL"}; '
                      f'target={target}, final={samples[-1]}', flush=True)
                if not passed:
                    print('STOPPED on first failed response; no retry or cleanup movement.')
                    return 3
                expected = samples[-1]
            print(f'SERVO {sid} SWEEP PASS', flush=True)
        print('RESULT: all five joint sweeps passed in feedback; confirm physical motion separately.')
        return 0
    finally:
        arm.bus.close()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--confirm-motion', action='store_true')
    args = p.parse_args(argv)
    if not args.confirm_motion:
        p.error('Obtain permission for the five-joint sequence before --confirm-motion')
    try:
        return run()
    except (OSError, RuntimeError) as exc:
        print(f'STOPPED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
