#!/usr/bin/python3
# -*- coding:utf-8 -*-
"""Drive the Yahboom 24-channel servo board over serial.

Protocol (9600 8N1 on the TXD3/RXD3 header, 115200 over USB-C): $<channel><angle>#
  channel: A-X  (A = S1 ... X = S24)
  angle:   3 digits, zero padded, 000-180
  e.g. $A090# centres channel 1

The vendor sample used /dev/ttyTHS1 (Jetson TX3/RX3 header pins) at 9600. We
drive the board over its own USB-C port instead, which enumerates as a CH340 at
/dev/ttyUSB0 and runs at 115200 -- the 9600 in the vendor docs applies only to
the TXD3/RXD3 pin header. The board echoes back every byte it receives on this
port -- valid frames and garbage alike -- so a returned frame confirms the link
is alive but says nothing about whether the command was understood.
"""
import sys
import time
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 115200


def frame(channel, angle):
    return '${}{:03d}#'.format(channel, angle).encode('ascii')


def send(ser, channel, angle):
    pkt = frame(channel, angle)
    ser.write(pkt)
    ser.flush()
    time.sleep(0.05)
    echo = ser.read(len(pkt))
    if echo == pkt:
        print('  TX {!r}  link ok (echo)'.format(pkt))
    else:
        print('  TX {!r}  NO ECHO (got {!r}) -- link problem'.format(pkt, echo))


ser = serial.Serial(PORT, BAUD, bytesize=8, parity='N', stopbits=1, timeout=0.5)
time.sleep(2)  # CH340 adapters reset on open; let the line settle
ser.reset_input_buffer()
ser.reset_output_buffer()

print('serial start on {} @ {} ...'.format(PORT, BAUD))
print("enter a channel A-X, or 'sweep' to wag channel A, CTRL+c to quit")

try:
    while True:
        todao = input('please input way(A-X): ').strip().upper()

        if todao == 'SWEEP':
            for a in (60, 120, 90):
                send(ser, 'A', a)
                time.sleep(0.8)
            continue

        while len(todao) != 1 or todao > 'X' or todao < 'A':
            todao = input('please Reinput way(A-X): ').strip().upper()

        angle = int(input('please input angle(0-180): '))
        while angle > 180 or angle < 0:
            angle = int(input('please Reinput angle(0-180): '))

        send(ser, todao, angle)

except KeyboardInterrupt:
    pass
finally:
    if ser is not None:
        ser.close()
