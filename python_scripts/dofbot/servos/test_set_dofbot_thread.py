"""Offline checks for interleaved steps and bounded feedback failures."""
import contextlib
import io
import unittest
from unittest.mock import patch

import set_dofbot_thread as movement


class FakeArm:
    def __init__(self):
        self.angles = dict.fromkeys(range(1, 7), 90)
        self.closed = False
        self.events = []
        self.bus = self

    def close(self):
        self.events.append(('close',))
        self.closed = True

    def Arm_serial_servo_read(self, sid):
        assert not self.closed
        self.events.append(('read', sid))
        return self.angles[sid]

    def Arm_serial_servo_write(self, sid, target, duration):
        assert not self.closed
        assert abs(target - self.angles[sid]) <= 1
        self.events.append(('write', sid, target, duration))
        self.angles[sid] = target


class InterleavedTests(unittest.TestCase):
    def setUp(self):
        self.arm = FakeArm()
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        self.sleep = patch.object(movement.time, 'sleep')
        self.sleep.start()
        self.addCleanup(self.sleep.stop)
        self.servos = {sid: movement.Servo(self.arm, sid, 0, 270 if sid == 5 else 180)
                       for sid in range(1, 7)}

    def writes(self):
        return [e for e in self.arm.events if e[0] == 'write']

    def test_round_robin_steps_in_both_directions(self):
        targets = {1: 92, 2: 88, 3: 92, 4: 88, 5: 92, 6: 88}
        movement.move_interleaved(self.servos, targets)
        self.assertEqual(self.arm.events[:6], [('read', sid) for sid in range(1, 7)])
        self.assertEqual([e[1] for e in self.writes()], list(range(1, 7)) * 2)
        self.assertEqual([e[2] for e in self.writes()[:6]], [91, 89, 91, 89, 91, 89])
        self.assertEqual(self.arm.angles, targets)
        self.assertTrue(all(e[3] == 34 for e in self.writes()))

    def test_shorter_moves_stop_without_overshoot(self):
        targets = {1: 91, 2: 93, 3: 90, 4: 90, 5: 90, 6: 90}
        movement.move_interleaved(self.servos, targets)
        self.assertEqual([(e[1], e[2]) for e in self.writes()],
                         [(1, 91), (2, 91), (2, 92), (2, 93)])

    def test_missing_initial_feedback_sends_no_commands(self):
        with patch.object(self.arm, 'Arm_serial_servo_read', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'no valid feedback'):
                movement.run(self.arm)
        self.assertEqual(self.writes(), [])
        self.assertTrue(self.arm.closed)

    def test_transient_missing_feedback_retried(self):
        with patch.object(self.arm, 'Arm_serial_servo_read', side_effect=[None, None, 90]):
            self.assertEqual(self.servos[1].read(), 90)

    def test_stuck_joint_detected_at_endpoint_and_skips_reset(self):
        # Controller accepts writes but feedback remains unchanged.
        with patch.object(self.arm, 'Arm_serial_servo_write',
                          side_effect=lambda *args: self.arm.events.append(('write', *args))):
            with self.assertRaisesRegex(RuntimeError, 'remaining moves cancelled'):
                movement.run(self.arm)
        expected = sum(abs(90 - value) for value in movement.TARGETS.values())
        self.assertEqual(len(self.writes()), expected)
        self.assertTrue(self.arm.closed)

    def test_failed_final_feedback_does_not_start_reset(self):
        with patch.object(self.arm, 'Arm_serial_servo_read', side_effect=[90] * 6 + [None] * 3):
            with self.assertRaisesRegex(RuntimeError, 'no valid feedback'):
                movement.run(self.arm)
        expected = sum(abs(90 - value) for value in movement.TARGETS.values())
        self.assertEqual(len(self.writes()), expected)
        self.assertTrue(self.arm.closed)

    def test_full_run_returns_to_90_then_closes(self):
        movement.run(self.arm)
        self.assertEqual(self.arm.angles, dict.fromkeys(range(1, 7), 90))
        self.assertEqual(self.arm.events[-1], ('close',))
        self.assertEqual(len(self.writes()), 2 * sum(abs(90 - value) for value in movement.TARGETS.values()))

    def test_no_feedback_reads_interrupt_long_move(self):
        movement.move_interleaved(self.servos, dict.fromkeys(range(1, 7), 100))
        events = self.arm.events
        first = next(i for i, event in enumerate(events) if event[0] == 'write')
        last = max(i for i, event in enumerate(events) if event[0] == 'write')
        self.assertTrue(all(event[0] == 'write' for event in events[first:last + 1]))
        self.assertEqual(len(self.writes()), 60)
        self.assertEqual(events[last + 1:], [('read', sid) for sid in range(1, 7)])

    def test_invalid_target_rejected_before_any_io(self):
        targets = dict(movement.TARGETS)
        targets[5] = 271
        with self.assertRaises(ValueError):
            movement.move_interleaved(self.servos, targets)
        self.assertEqual(self.arm.events, [])

    def test_feedback_rounding_does_not_accumulate_drift(self):
        original = self.arm.Arm_serial_servo_read
        with patch.object(self.arm, 'Arm_serial_servo_read', side_effect=lambda sid: original(sid) - 1):
            movement.move_interleaved(self.servos, dict.fromkeys(range(1, 7), 95))
        self.assertEqual(self.arm.angles, dict.fromkeys(range(1, 7), 95))
        self.assertTrue(all(e[2] <= 95 for e in self.writes()))


if __name__ == '__main__':
    unittest.main()
