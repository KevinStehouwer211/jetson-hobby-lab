#!/usr/bin/env python3
"""Run servo_diagnostic under a private bus-7 kernel trace instance.

Requires root for tracefs. Defaults to query-only. Forwarded --move still
requires permission and --confirm-motion. Never alters global trace settings.
"""
import os
from pathlib import Path
import sys
import uuid

import servo_diagnostic


def main():
    root = Path('/sys/kernel/tracing')
    if os.geteuid() != 0:
        print('Run with sudo for private tracefs access.', file=sys.stderr)
        return 2
    instance = root / 'instances' / ('dofbot_' + uuid.uuid4().hex[:12])
    instance.mkdir()
    enabled = []
    try:
        (instance / 'tracing_on').write_text('0')
        for event in ('i2c_write', 'i2c_read', 'i2c_reply', 'i2c_result'):
            base = instance / 'events/i2c' / event
            rule = 'adapter_nr == 7'
            if event != 'i2c_result':
                rule += ' && addr == 21'
            (base / 'filter').write_text(rule)
            (base / 'enable').write_text('1')
            enabled.append(base)
        (instance / 'tracing_on').write_text('1')
        return servo_diagnostic.main(sys.argv[1:])
    finally:
        # Always stop and remove ONLY this unique instance, including on errors.
        (instance / 'tracing_on').write_text('0')
        for base in enabled:
            (base / 'enable').write_text('0')
        print('\nKERNEL I2C TRACE (controller 0x15, bus 7):', flush=True)
        print((instance / 'trace').read_text(), flush=True)
        instance.rmdir()


if __name__ == '__main__':
    sys.exit(main())
