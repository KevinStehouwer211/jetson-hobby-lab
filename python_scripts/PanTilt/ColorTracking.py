import cv2
print(cv2.__version__)

import os
import sys
import time
import numpy as np

# Allow importing local modules from python_scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from servo.Servo import servo as Servo


# =========================
# SERVO SETTINGS
# =========================

PORT = '/dev/ttyUSB0'
BAUD = 115200

PAN_MIN = 20
PAN_MAX = 160

TILT_MIN = 20
TILT_MAX = 160

pan = 90.0
tilt = 90.0

last_pan_sent = None
last_tilt_sent = None

ser = Servo(PORT, BAUD)

ser.send('A', int(round(pan)))
ser.send('B', int(round(tilt)))


# =========================
# CONTROL SETTINGS
# =========================

# Only update the servos every 50 ms
# 0.05 = 20 Hz
CONTROL_DT = 0.005

# Ignore small errors around image center
DEADBAND_X = 15
DEADBAND_Y = 15

# Proportional gain
KP_PAN = 0.1
KP_TILT = 0.1

# Never move the commanded target more than this
# per control update
MAX_STEP_PAN = 1.0
MAX_STEP_TILT = 1.0

last_control_time = time.monotonic()


# =========================
# CAMERA SETTINGS
# =========================

dispW = 320
dispH = 240

cam = cv2.VideoCapture(0, cv2.CAP_V4L2)

cam.set(cv2.CAP_PROP_FRAME_WIDTH, dispW)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, dispH)

if not cam.isOpened():
    print("Could not open camera")
    ser.close()
    sys.exit(1)


# =========================
# GUI
# =========================

exit_program = False


def mouse_callback(event, x, y, flags, param):
    global exit_program

    if event == cv2.EVENT_LBUTTONDOWN:
        if 10 <= x <= 130 and 10 <= y <= 65:
            exit_program = True


cv2.namedWindow('Trackbars')
cv2.moveWindow('Trackbars', 800, 0)

cv2.createTrackbar('HUE lower', 'Trackbars', 80, 179, lambda x: None)
cv2.createTrackbar('HUE upper', 'Trackbars', 120, 179, lambda x: None)

cv2.createTrackbar('HUE2 lower', 'Trackbars', 179, 179, lambda x: None)
cv2.createTrackbar('HUE2 upper', 'Trackbars', 179, 179, lambda x: None)

cv2.createTrackbar('SAT lower', 'Trackbars', 130, 255, lambda x: None)
cv2.createTrackbar('SAT upper', 'Trackbars', 255, 255, lambda x: None)

cv2.createTrackbar('VALUE lower', 'Trackbars', 70, 255, lambda x: None)
cv2.createTrackbar('VALUE upper', 'Trackbars', 140, 255, lambda x: None)


cv2.namedWindow('WEBCAM', cv2.WINDOW_NORMAL)
cv2.setMouseCallback('WEBCAM', mouse_callback)

cv2.namedWindow('FG_MASKCOMP', cv2.WINDOW_NORMAL)


# =========================
# MAIN LOOP
# =========================

try:

    while True:

        ret, frame = cam.read()

        if not ret:
            print("Failed to read camera frame")
            break

        frame = cv2.resize(frame, (dispW, dispH))

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)


        # =========================
        # GET TRACKBAR VALUES
        # =========================

        h_lower = cv2.getTrackbarPos('HUE lower', 'Trackbars')
        h_upper = cv2.getTrackbarPos('HUE upper', 'Trackbars')

        h2_lower = cv2.getTrackbarPos('HUE2 lower', 'Trackbars')
        h2_upper = cv2.getTrackbarPos('HUE2 upper', 'Trackbars')

        s_lower = cv2.getTrackbarPos('SAT lower', 'Trackbars')
        s_upper = cv2.getTrackbarPos('SAT upper', 'Trackbars')

        v_lower = cv2.getTrackbarPos('VALUE lower', 'Trackbars')
        v_upper = cv2.getTrackbarPos('VALUE upper', 'Trackbars')


        lb = np.array([h_lower, s_lower, v_lower])
        ub = np.array([h_upper, s_upper, v_upper])

        lb2 = np.array([h2_lower, s_lower, v_lower])
        ub2 = np.array([h2_upper, s_upper, v_upper])


        # =========================
        # CREATE MASK
        # =========================

        FG_mask = cv2.inRange(hsv, lb, ub)
        FG_mask2 = cv2.inRange(hsv, lb2, ub2)

        FG_maskComp = cv2.add(FG_mask, FG_mask2)

        cv2.imshow('FG_MASKCOMP', FG_maskComp)
        cv2.moveWindow('FG_MASKCOMP', 0, 300)


        # =========================
        # FIND OBJECT
        # =========================

        contours, _ = cv2.findContours(
            FG_maskComp,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        contours = sorted(
            contours,
            key=cv2.contourArea,
            reverse=True
        )


        if contours:

            cnt = contours[0]

            area = cv2.contourArea(cnt)

            if area > 50:

                x, y, w, h = cv2.boundingRect(cnt)

                cv2.drawContours(
                    frame,
                    [cnt],
                    0,
                    (255, 0, 0),
                    3
                )

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )


                # Object center
                objX = x + w // 2
                objY = y + h // 2


                # Draw object center lines
                cv2.line(
                    frame,
                    (objX, 0),
                    (objX, dispH),
                    (0, 255, 0),
                    1
                )

                cv2.line(
                    frame,
                    (0, objY),
                    (dispW, objY),
                    (0, 255, 0),
                    1
                )


                # Draw frame center
                centerX = dispW // 2
                centerY = dispH // 2

                cv2.circle(
                    frame,
                    (centerX, centerY),
                    5,
                    (0, 0, 255),
                    -1
                )


                # =========================
                # ERROR
                # =========================

                errorPan = -(objX - centerX)
                errorTilt = -(objY - centerY)


                # Display errors
                cv2.putText(
                    frame,
                    f"Pan err: {errorPan}",
                    (150, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1
                )

                cv2.putText(
                    frame,
                    f"Tilt err: {errorTilt}",
                    (150, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1
                )


                # =========================
                # SERVO CONTROL
                # =========================

                now = time.monotonic()

                if now - last_control_time >= CONTROL_DT:

                    # PAN
                    if abs(errorPan) > DEADBAND_X:

                        correction_pan = KP_PAN * errorPan

                        correction_pan = np.clip(
                            correction_pan,
                            -MAX_STEP_PAN,
                            MAX_STEP_PAN
                        )

                        pan += correction_pan


                    # TILT
                    if abs(errorTilt) > DEADBAND_Y:

                        correction_tilt = KP_TILT * errorTilt

                        correction_tilt = np.clip(
                            correction_tilt,
                            -MAX_STEP_TILT,
                            MAX_STEP_TILT
                        )

                        tilt += correction_tilt


                    # Limit servo range
                    pan = np.clip(
                        pan,
                        PAN_MIN,
                        PAN_MAX
                    )

                    tilt = np.clip(
                        tilt,
                        TILT_MIN,
                        TILT_MAX
                    )


                    # Convert to integer because current
                    # firmware protocol uses integer angles
                    pan_out = int(round(pan))
                    tilt_out = int(round(tilt))


                    # Only send if position actually changed
                    if pan_out != last_pan_sent:

                        ser.send('A', pan_out)

                        last_pan_sent = pan_out


                    if tilt_out != last_tilt_sent:

                        ser.send('B', tilt_out)

                        last_tilt_sent = tilt_out


                    last_control_time = now


        # =========================
        # EXIT BUTTON
        # =========================

        cv2.rectangle(
            frame,
            (10, 10),
            (130, 65),
            (0, 0, 255),
            -1
        )

        cv2.rectangle(
            frame,
            (10, 10),
            (130, 65),
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            'EXIT',
            (28, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (255, 255, 255),
            3
        )


        cv2.imshow('WEBCAM', frame)
        cv2.moveWindow('WEBCAM', 0, 0)


        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or exit_program:
            break


finally:

    cam.release()

    ser.close()

    cv2.destroyAllWindows()