"""Offline checks for the bounded three-command hardware diagnostic."""
import contextlib
import io
import unittest
from unittest.mock import patch
import repeat_servo1 as repeat


class FakeArm:
    def __init__(self, **kwargs):
        self.read_recovery_s = 0.1
        self.angle = 95
        self.targets = []
        self.durations = []
        from unittest.mock import Mock
        self.bus = Mock()

    def Arm_get_hardversion(self):
        return '0.21'

    def Arm_ping_servo(self, sid):
        return 0xDA

    def Arm_serial_servo_read(self, sid):
        return self.angle if sid == 1 else 90

    def Arm_serial_servo_write(self, sid, target, duration):
        assert sid == 1 and duration in (0, 2000)
        self.targets.append(target)
        self.durations.append(duration)
        self.angle = target - 1  # Model the observed integer feedback offset.


class RepeatSafetyTests(unittest.TestCase):
    def test_no_confirmation_never_opens_bus(self):
        with patch.object(repeat, 'Arm_Device') as ctor, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                repeat.main([])
            ctor.assert_not_called()

    def test_wrong_clock_never_opens_bus(self):
        with patch.object(repeat, 'clock_hz', return_value=400000), \
             patch.object(repeat, 'Arm_Device') as ctor, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(repeat.main(['--confirm-motion']), 2)
            ctor.assert_not_called()

    def test_fixed_targets_do_not_accumulate_feedback_offset(self):
        arm = FakeArm()
        with patch.object(repeat, 'clock_hz', return_value=100000), \
             patch.object(repeat, 'Arm_Device', return_value=arm), \
             patch.object(repeat.time, 'sleep'), \
             patch.object(repeat, 'monitor', side_effect=lambda *a: [arm.angle] * 9), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(repeat.main(['--confirm-motion']), 0)
        self.assertEqual(arm.targets, [100, 95, 100])
        arm.bus.close.assert_called_once()

    def test_fifteen_degree_targets_stay_fixed(self):
        arm = FakeArm()
        with patch.object(repeat, 'clock_hz', return_value=100000), \
             patch.object(repeat, 'Arm_Device', return_value=arm), \
             patch.object(repeat.time, 'sleep'), \
             patch.object(repeat, 'monitor', side_effect=lambda *a: [arm.angle] * 9), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(repeat.main(['--confirm-motion', '--step-degrees', '15']), 0)
        self.assertEqual(arm.targets, [110, 95, 110])

    def test_fifteen_degree_out_of_range_baseline_sends_no_movement(self):
        arm = FakeArm()
        arm.angle = 170
        with patch.object(repeat, 'clock_hz', return_value=100000), \
             patch.object(repeat, 'Arm_Device', return_value=arm), \
             patch.object(repeat.time, 'sleep'), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(repeat.main(['--confirm-motion', '--step-degrees', '15']), 2)
        self.assertEqual(arm.targets, [])

    def test_two_move_sweep_commands_out_and_back_only(self):
        arm = FakeArm()
        with patch.object(repeat, 'clock_hz', return_value=100000), \
             patch.object(repeat, 'Arm_Device', return_value=arm), \
             patch.object(repeat.time, 'sleep'), \
             patch.object(repeat, 'monitor', side_effect=lambda *a: [arm.angle] * 9), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(repeat.main(['--confirm-motion', '--step-degrees', '15', '--moves', '2']), 0)
        self.assertEqual(arm.targets, [110, 95])

    def test_fast_45degree_sweep_is_exactly_two_commands(self):
        arm = FakeArm()
        with patch.object(repeat, 'clock_hz', return_value=100000), \
             patch.object(repeat, 'Arm_Device', return_value=arm), \
             patch.object(repeat.time, 'sleep'), \
             patch.object(repeat, 'monitor', side_effect=lambda *a: [arm.angle] * 9), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(repeat.main(['--confirm-motion', '--step-degrees', '45',
                                         '--moves', '2', '--duration-ms', '0']), 0)
        self.assertEqual(arm.targets, [140, 95])
        self.assertEqual(arm.durations, [0, 0])

    def test_fast_sweep_out_of_range_sends_no_command(self):
        arm = FakeArm()
        arm.angle = 140
        with patch.object(repeat, 'clock_hz', return_value=100000), \
             patch.object(repeat, 'Arm_Device', return_value=arm), \
             patch.object(repeat.time, 'sleep'), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(repeat.main(['--confirm-motion', '--step-degrees', '45',
                                         '--moves', '2', '--duration-ms', '0']), 2)
        self.assertEqual(arm.targets, [])

    def test_first_failed_response_stops_remaining_moves(self):
        arm = FakeArm()
        with patch.object(repeat, 'clock_hz', return_value=100000), \
             patch.object(repeat, 'Arm_Device', return_value=arm), \
             patch.object(repeat.time, 'sleep'), \
             patch.object(repeat, 'monitor', return_value=[95] * 9), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(repeat.main(['--confirm-motion']), 3)
        self.assertEqual(arm.targets, [100])
        arm.bus.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
