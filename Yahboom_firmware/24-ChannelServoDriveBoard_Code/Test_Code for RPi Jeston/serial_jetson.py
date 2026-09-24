#!/usr/bin/python
# -*- coding:utf-8 -*-
import serial

#ser = serial.Serial("/dev/ttyAMA0",9600,8,'N',1,timeout = 0.5) #树莓派
ser = serial.Serial("/dev/ttyTHS1",9600) #jetson nano

print("serial test start ...")

ser.write(bytes('1','utf-8'))
try:
    while True:
        sss = ser.read()
        print(sss)
        ser.write(bytes('H','utf-8'))
except KeyboardInterrupt:
    if ser != None:
        ser.close()
