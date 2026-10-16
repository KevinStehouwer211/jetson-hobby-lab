"""Offline safety and error-reporting tests. Never open a real I2C device."""
import contextlib
import io
import unittest
from unittest.mock import patch
import servo_diagnostic as diag


class FakeBus:
    def __init__(self, bus):
        self.writes = []
        self.closed = False
        self.moved = False

    def write_byte_data(self, addr, reg, value):
        assert addr == 0x15 and reg in {0x01, 0x38, *range(0x31, 0x37)}
        self.writes.append((reg, value))

    def read_byte_data(self, addr, reg):
        return 21 if reg == 1 else 0xDA

    def read_word_data(self, addr, reg):
        pos = 2183 if self.moved and reg == 0x31 else 2123
        return ((pos & 255) << 8) | (pos >> 8)

    def write_i2c_block_data(self, addr, reg, data):
        self.writes.append((reg, data))
        self.moved = True

    def close(self):
        self.closed = True


class SafetyTests(unittest.TestCase):
    def execute(self, argv):
        bus = FakeBus(7)
        # Accelerated clock, so the tests need no real sleeps.
        ticks = iter(i * 0.5 for i in range(1000))
        with patch('smbus.SMBus', return_value=bus), \
             patch.object(diag.time, 'sleep'), \
             patch.object(diag.time, 'monotonic', side_effect=lambda: next(ticks)), \
             contextlib.redirect_stdout(io.StringIO()):
            code = diag.main(argv)
        return code, bus

    def test_query_only_uses_query_registers(self):
        code, bus = self.execute(['--seconds', '1'])
        self.assertEqual(code, 0)
        self.assertTrue(bus.closed)
        self.assertTrue(all(reg in {1, 0x38, *range(0x31, 0x37)} for reg, _ in bus.writes))

    def test_unconfirmed_motion_never_opens_bus(self):
        with patch('smbus.SMBus') as constructor, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                diag.main(['--move'])
            constructor.assert_not_called()

    def test_confirmed_motion_sends_one_expected_packet(self):
        code, bus = self.execute(['--move', '--confirm-motion', '--seconds', '4'])
        self.assertEqual(code, 0)
        packets = [(reg, data) for reg, data in bus.writes if isinstance(data, list)]
        self.assertEqual(packets, [(0x11, [0x08, 0x87, 0x07, 0xD0])])

    def test_unchanged_feedback_is_failure(self):
        with patch.object(FakeBus, 'read_word_data', return_value=0x4A08):
            code, _ = self.execute(['--move', '--confirm-motion'])
        self.assertEqual(code, 3)

    def test_oserror_logged_and_strictly_reraised_without_retry(self):
        with patch('smbus.SMBus', return_value=FakeBus(7)):
            arm = diag.Arm_Device(strict_errors=True)
        with patch.object(arm.bus, 'write_i2c_block_data', side_effect=OSError(121, 'Remote I/O error')) as write:
            with self.assertLogs('Arm_Lib.Arm_Lib', level='ERROR') as logs:
                with self.assertRaises(OSError):
                    arm.Arm_serial_servo_write(1, 105, 2000)
            self.assertIn('address=0x15', logs.output[0])
            self.assertIn('Remote I/O error', logs.output[0])
            self.assertEqual(write.call_count, 1)

    def test_raw_transport_sends_one_exact_packet(self):
        with patch('smbus2.SMBus') as raw_constructor:
            code, bus = self.execute(['--move', '--confirm-motion', '--raw-i2c'])
        self.assertEqual(code, 3)  # Fake feedback stays unchanged in this path.
        raw_bus = raw_constructor.return_value.__enter__.return_value
        raw_bus.i2c_rdwr.assert_called_once()
        packet = raw_bus.i2c_rdwr.call_args.args[0]
        self.assertEqual(packet.addr, 0x15)
        self.assertEqual(packet.flags, 0)
        self.assertEqual(list(packet), [0x11, 0x08, 0x87, 0x07, 0xd0])
        self.assertFalse(any(isinstance(data, list) for _, data in bus.writes))

    def test_raw_mode_without_motion_never_opens_bus(self):
        with patch('smbus.SMBus') as constructor, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                diag.main(['--raw-i2c'])
            constructor.assert_not_called()

    def test_position_encoding_for_all_six_servos(self):
        # Fixed expected values, including inversion for 2/3/4 and 270-degree servo 5.
        with patch('smbus.SMBus', return_value=FakeBus(7)):
            arm = diag.Arm_Device()
        expected = {1: 2183, 2: 1816, 3: 1816, 4: 1816, 5: 1671, 6: 2183}
        for sid, raw in expected.items():
            arm.Arm_serial_servo_write(sid, 105, 2000)
            self.assertEqual(arm.bus.writes[-1],
                             (0x10 + sid, [raw >> 8, raw & 255, 7, 208]))

    def test_back_to_back_queries_then_write_respect_controller_recovery(self):
        now = [0.0]
        class RecoveryBus(FakeBus):
            ready = 0.0
            def write_byte_data(self, addr, reg, value):
                if now[0] + 1e-9 < self.ready:
                    raise OSError("Controller still recovering from read")
                super().write_byte_data(addr, reg, value)
            def read_word_data(self, addr, reg):
                value = super().read_word_data(addr, reg)
                self.ready = now[0] + 0.1
                return value
            def write_i2c_block_data(self, addr, reg, data):
                if now[0] + 1e-9 < self.ready:
                    raise OSError("Controller still recovering from read")
                super().write_i2c_block_data(addr, reg, data)
        bus = RecoveryBus(7)
        def advance(seconds):
            now[0] += seconds
        with patch('smbus.SMBus', return_value=bus), \
             patch.object(diag.time, 'sleep', side_effect=advance):
            arm = diag.Arm_Device(strict_errors=True)
            self.assertEqual(arm.Arm_serial_servo_read(1), 100)
            self.assertEqual(arm.Arm_serial_servo_read(1), 100)
            arm.Arm_serial_servo_write(1, 105, 2000)
        self.assertEqual(sum(isinstance(data, list) for _, data in bus.writes), 1)

    def test_invalid_recovery_does_not_open_bus(self):
        with patch('smbus.SMBus') as constructor:
            for value in (-0.1, 2, float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    diag.Arm_Device(read_recovery_s=value)
            constructor.assert_not_called()

    def test_legacy_errors_still_return_none(self):
        with patch('smbus.SMBus', return_value=FakeBus(7)):
            arm = diag.Arm_Device()
        with patch.object(arm.bus, 'read_word_data', side_effect=OSError(121, 'Remote I/O error')):
            with self.assertLogs('Arm_Lib.Arm_Lib', level='ERROR'):
                self.assertIsNone(arm.Arm_serial_servo_read(1))


if __name__ == '__main__':
    unittest.main()
