"""Offline authorization, joint-limit and bounded-motion checks."""
import contextlib
import io
import unittest
from unittest.mock import Mock, patch
import sweep_other_joints as sweep


class FakeArm:
    read_recovery_s = 0.1
    def __init__(self):
        self.angles = {1: 113, 2: 100, 3: 83, 4: 23, 5: 265, 6: 152}
        self.writes = []
        self.bus = Mock()
    def Arm_get_hardversion(self): return '0.21'
    def Arm_ping_servo(self, sid): return 0xDA
    def Arm_serial_servo_read(self, sid): return self.angles[sid]
    def Arm_serial_servo_write(self, sid, target, duration):
        assert duration == 2000
        self.writes.append((sid, target))
        self.angles[sid] = target - 1


class OtherSweepTests(unittest.TestCase):
    def test_confirmation_required_before_bus_open(self):
        with patch.object(sweep, 'Arm_Device') as ctor, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit): sweep.main([])
            ctor.assert_not_called()

    def test_sequential_fixed_endpoints_and_joint5_limit(self):
        arm = FakeArm()
        with patch.object(sweep, 'clock_hz', return_value=100000), \
             patch.object(sweep, 'Arm_Device', return_value=arm), \
             patch.object(sweep.time, 'sleep'), \
             patch.object(sweep, 'monitor', side_effect=lambda a, sid, *rest: [a.angles[sid]] * 8), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sweep.main(['--confirm-motion']), 0)
        self.assertEqual(arm.writes, [(2,110),(2,100),(3,93),(3,83),(4,33),(4,23),(5,255),(5,265),(6,162),(6,152)])
        arm.bus.close.assert_called_once()

    def test_failure_prevents_return_and_later_joints(self):
        arm = FakeArm()
        with patch.object(sweep, 'clock_hz', return_value=100000), \
             patch.object(sweep, 'Arm_Device', return_value=arm), \
             patch.object(sweep.time, 'sleep'), \
             patch.object(sweep, 'monitor', return_value=[100] * 8), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sweep.main(['--confirm-motion']), 3)
        self.assertEqual(arm.writes, [(2,110)])


if __name__ == '__main__': unittest.main()
