import serial
import time

# Serial port settings
BAUD = 115200
PORT = '/dev/ttyUSB0'

# Setup serial port
ser = serial.Serial(PORT, BAUD, bytesize=8, parity='N', stopbits=1, timeout=0.5)

# Send a command to the servo controller
def send(ser, channel, angle):
    cmd = frame(channel, angle)
    ser.write(cmd)
    ser.flush()
    print('TX {!r}'.format(cmd))

# Create a command frame for the servo controller specified by Yahboom
def frame(channel, angle):
    return '${}{:03d}#'.format(channel, angle).encode('ascii')

send(ser, 'A', 45)
time.sleep(2)

send(ser, 'B', 90)
time.sleep(2)

ser.close()