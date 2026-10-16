#!/usr/bin/env python3
"""Two or three explicitly approved servo-1 moves between fixed endpoints.

Requires --confirm-motion before opening I2C. Duration 2000 ms or 0 (fastest),
100 ms recovery inside Arm_Lib feedback reads; no script-added pre-command
pause, automatic retries or cleanup movement.
"""
import argparse
from pathlib import Path
import sys
import time
from servo_diagnostic import Arm_Device, monitor


def clock_hz():
    p = Path('/proc/device-tree/bus@0/i2c@c250000/clock-frequency')
    return int.from_bytes(p.read_bytes(), 'big')


def run(step_degrees=5, moves=3, duration_ms=2000):
    if clock_hz() != 100000:
        raise RuntimeError('Refusing movement: test requires bus-7 DT setting 100000')
    arm = Arm_Device(i2c_bus=7, strict_errors=True)
    try:
        time.sleep(0.1)
        if arm.read_recovery_s != 0.1:
            raise RuntimeError("Repeatability test requires library read_recovery_s=0.1")
        print("Library feedback recovery: 100 ms; no script-added pre-command pause.", flush=True)
        if arm.Arm_get_hardversion() is None:
            raise RuntimeError('No controller version')
        positions = []
        for sid in range(1, 7):
            ping = arm.Arm_ping_servo(sid)
            time.sleep(0.02)
            angle = arm.Arm_serial_servo_read(sid)
            time.sleep(0.02)
            print(f'Baseline servo {sid}: ping={ping}, angle={angle}', flush=True)
            if ping != 0xDA or angle is None:
                raise RuntimeError('Baseline check failed; no movement sent')
            positions.append(angle)
        baseline = positions[0]
        if not 0 <= baseline <= 180 - step_degrees:
            raise RuntimeError('Baseline outside the allowed test range')
        targets = [baseline + step_degrees, baseline, baseline + step_degrees][:moves]
        expected = baseline
        print(f'Fixed target sequence: {targets}; {duration_ms} ms per move.', flush=True)
        for number, target in enumerate(targets, 1):
            before = arm.Arm_serial_servo_read(1)
            if before is None or abs(before - expected) > 1:
                raise RuntimeError('Feedback changed between steps; stopping')
            if not baseline - 2 <= before <= baseline + step_degrees + 2 or abs(target - before) > step_degrees + 2:
                raise RuntimeError('Feedback outside the approved test envelope; stopping')
            print(f'Move {number}/{len(targets)}: servo 1 {before} -> {target}, {duration_ms} ms', flush=True)
            arm.Arm_serial_servo_write(1, target, duration_ms)
            time.sleep(2.5)
            samples = monitor(arm, 1, 4, 0.5)
            final = samples[-3:]
            passed = (len(final) == 3 and all(v is not None and abs(v - target) <= 2 and
                      (v - before) * (target - before) > 0 for v in final))
            print(f'Move {number}: {"PASS" if passed else "FAIL"}; target={target}, final={samples[-1]}', flush=True)
            if not passed:
                print('Stopped on first failure; no retry or return movement.')
                return 3
            expected = samples[-1]
        print(f'RESULT: all {len(targets)} feedback responses passed; physical observation still required.')
        return 0
    finally:
        arm.bus.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-motion', action='store_true')
    parser.add_argument('--moves', type=int, choices=(2, 3), default=3,
                        help='Two commands sweep out and back; three end at the upper angle')
    parser.add_argument('--duration-ms', type=int, choices=(0, 2000), default=2000,
                        help='0 is the controller fastest-speed setting; requires approval')
    parser.add_argument('--step-degrees', type=int, choices=(5, 15, 45), default=5,
                        help='Approved span between the two fixed endpoints')
    args = parser.parse_args(argv)
    if not args.confirm_motion:
        parser.error('Obtain permission for the full movement sequence, then use --confirm-motion')
    try:
        return run(args.step_degrees, args.moves, args.duration_ms)
    except (OSError, RuntimeError) as exc:
        print(f'STOPPED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
