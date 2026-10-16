#!/usr/bin/env python3
"""DOFBOT query-only diagnostics by default; movement needs explicit opt-in.

Queries use the vendor's request writes to registers 0x01, 0x31..0x36,
and 0x38. No torque, mode, calibration, reset, or ID commands are sent.
"""
import argparse
import inspect
import logging
import math
from pathlib import Path
import sys
import time

# Use this checkout explicitly; show the imported implementation in the report.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'colcon_ws/src/Arm_Lib'))
from Arm_Lib import Arm_Device


def monitor(arm, servo_id, seconds, interval):
    samples = []
    start = time.monotonic()
    while True:
        value = arm.Arm_serial_servo_read(servo_id)
        elapsed = time.monotonic() - start
        print(f't={elapsed:.3f}s servo={servo_id} angle={value}', flush=True)
        samples.append(value)
        if elapsed >= seconds:
            return samples
        time.sleep(min(interval, seconds - elapsed))


def run(args):
    print(f'Python: {sys.executable}\nLibrary: {inspect.getfile(Arm_Device)}', flush=True)
    print(f'Bus: {args.bus}; address: 0x15; mode: ' +
          ('ONE movement command' if args.move else 'QUERY ONLY'), flush=True)
    arm = Arm_Device(i2c_bus=args.bus, strict_errors=True)
    try:
        time.sleep(0.1)  # Vendor example's settling interval.
        version = arm.Arm_get_hardversion()
        print(f'Controller version: {version}')
        healthy = version is not None
        positions = {}
        for sid in range(1, 7):
            ping = arm.Arm_ping_servo(sid)
            time.sleep(0.02)
            positions[sid] = arm.Arm_serial_servo_read(sid)
            print(f'Servo {sid}: ping={hex(ping) if ping is not None else None}, '
                  f'angle={positions[sid]}', flush=True)
            healthy = healthy and ping == 0xDA and positions[sid] is not None
            time.sleep(0.02)
        if not args.move:
            samples = monitor(arm, args.servo, args.seconds, args.interval)
            healthy = healthy and all(v is not None for v in samples)
            print('RESULT: query communication ' + ('PASS' if healthy else 'INCOMPLETE/FAILED') +
                  '; position-command execution was not tested.')
            return 0 if healthy else 2
        if not healthy:
            raise RuntimeError('Movement refused: baseline queries are incomplete or unhealthy')
        before = positions[args.servo]
        target = before + args.delta
        limit = 270 if args.servo == 5 else 180
        if not 0 <= target <= limit:
            raise RuntimeError(f'Movement refused: target {target} outside 0..{limit}')
        # Recheck before movement in case another writer or external motion intervened.
        current = arm.Arm_serial_servo_read(args.servo)
        if current is None or abs(current - before) > 1:
            raise RuntimeError('Movement refused: baseline changed or feedback is unavailable')
        if args.pre_command_seconds:
            print(f'Quiet BEFORE command: {args.pre_command_seconds:.3f}s', flush=True)
            time.sleep(args.pre_command_seconds)
        print(f'COMMAND: servo={args.servo}, before={before}, target={target}, '
              f'duration={args.duration_ms}ms; exactly one write, no retry/return move.', flush=True)
        if args.raw_i2c:
            # Restricted to servo 1: compare identical bytes via I2C_RDWR instead
            # of the native smbus extension's I2C_SMBUS block-write ioctl.
            from smbus2 import SMBus, i2c_msg
            raw = int(2200 * target / 180 + 900)
            packet = [0x11, raw >> 8, raw & 255,
                      args.duration_ms >> 8, args.duration_ms & 255]
            print(f'RAW I2C: address=0x15 bytes={packet}', flush=True)
            with SMBus(args.bus) as raw_bus:
                raw_bus.i2c_rdwr(i2c_msg.write(0x15, packet))
        else:
            arm.Arm_serial_servo_write(args.servo, target, args.duration_ms)
        quiet = args.duration_ms / 1000 + 0.5 if args.quiet_seconds is None else args.quiet_seconds
        print(f'No queries for {quiet:.2f}s after command.', flush=True)
        time.sleep(quiet)
        samples = monitor(arm, args.servo, args.seconds, args.interval)
        valid = [v for v in samples if v is not None]
        # Require multiple final samples near target AND change in target direction.
        reached = (len(valid) >= 3 and all(v is not None for v in samples[-3:]) and
                   all(abs(v - target) <= 2 and (v - before) * args.delta > 0
                       for v in samples[-3:]))
        print('RESULT: ' + ('feedback confirms target response' if reached else
                          'target response NOT confirmed') +
              f'; baseline={before}, target={target}, final={samples[-1]}. '
              'Observe physical motion separately; feedback alone is not visual verification.')
        return 0 if reached else 3
    finally:
        arm.bus.close()  # Closing the host fd sends no torque or movement command.


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bus', type=int, default=7)
    p.add_argument('--servo', type=int, choices=range(1, 7), default=1)
    p.add_argument('--seconds', type=float, default=4)
    p.add_argument('--interval', type=float, default=0.5)
    p.add_argument('--verbose', action='store_true')
    p.add_argument('--raw-i2c', action='store_true', help='Servo-1-only transport comparison; requires authorized --move')
    p.add_argument('--move', action='store_true', help='Send ONE small relative movement (requires user permission)')
    p.add_argument('--confirm-motion', action='store_true', help='Explicit acknowledgement of authorized physical movement')
    p.add_argument('--delta', type=int, default=5, help='Relative angle: -5..-3 or 3..5 degrees')
    p.add_argument('--duration-ms', type=int, default=2000)
    p.add_argument('--pre-command-seconds', type=float, default=0, help='Quiet interval after final feedback read, before the one command')
    p.add_argument('--quiet-seconds', type=float, help='Override post-command quiet interval; 0 enables immediate polling')
    args = p.parse_args(argv)
    if not math.isfinite(args.seconds) or not 1 <= args.seconds <= 60:
        p.error('--seconds must be finite and between 1 and 60')
    if not math.isfinite(args.interval) or not 0.1 <= args.interval <= 1:
        p.error('--interval must be finite and between 0.1 and 1')
    if not math.isfinite(args.pre_command_seconds) or not 0 <= args.pre_command_seconds <= 5:
        p.error('--pre-command-seconds must be finite and between 0 and 5')
    if args.quiet_seconds is not None and (not math.isfinite(args.quiet_seconds) or not 0 <= args.quiet_seconds <= 60):
        p.error('--quiet-seconds must be finite and between 0 and 60')
    if args.raw_i2c and (not args.move or args.servo != 1):
        p.error('--raw-i2c requires --move and --servo 1')
    if args.move and not args.confirm_motion:
        p.error('--move requires --confirm-motion after obtaining permission')
    if args.confirm_motion and not args.move:
        p.error('--confirm-motion requires --move')
    if abs(args.delta) not in (3, 4, 5) or not 1000 <= args.duration_ms <= 5000:
        p.error('movement requires abs(delta)=3..5 and duration=1000..5000ms')
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    try:
        return run(args)
    except (OSError, RuntimeError) as exc:
        logging.error('%s: %s', type(exc).__name__, exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())
