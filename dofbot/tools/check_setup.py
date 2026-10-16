#!/usr/bin/env python3
"""Check setup without opening I2C, starting ROS, or moving hardware."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--offline', action='store_true', help='Skip device-node and boot-clock checks.')
args = parser.parse_args()
project = Path(__file__).resolve().parents[1]
errors = []
print('Python:', sys.executable)
for module in ('smbus', 'smbus2', 'Arm_Lib'):
    spec = importlib.util.find_spec(module)
    print(f'{module}: {spec.origin if spec else "MISSING"}')
    if spec is None:
        errors.append(f'Missing {module}')
    elif module == 'Arm_Lib' and not Path(spec.origin).resolve().is_relative_to(project / 'colcon_ws/src/Arm_Lib'):
        errors.append('Arm_Lib resolves outside this repository; use tools/run_python.sh')
for module in ('rclpy', 'ipykernel', 'jupyterlab', 'torch', 'cv2', 'numpy'):
    print(f'Optional {module}: {"available" if importlib.util.find_spec(module) else "not installed"}')
if not args.offline:
    device = Path('/dev/i2c-7')
    accessible = device.exists() and os.access(device, os.R_OK | os.W_OK)
    print('I2C7 device accessible:', accessible)
    if not accessible:
        errors.append('Check /dev/i2c-7, bus mapping, and device-group membership')
    clock = Path('/proc/device-tree/bus@0/i2c@c250000/clock-frequency')
    hz = int.from_bytes(clock.read_bytes(), 'big') if clock.exists() else None
    print('Configured bus clock:', hz)
    if hz != 100000:
        errors.append('Select the 100 kHz boot entry; see docs/CLOCK-SETUP.md')
for error in errors:
    print('CHECK FAILED:', error)
print('No I2C device was opened and no controller commands were sent.')
sys.exit(bool(errors))
