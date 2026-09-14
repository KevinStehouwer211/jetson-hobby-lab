import cv2
import numpy as np

print("OpenCV version:", cv2.__version__)

CAM_W, CAM_H = 640, 480

WEBCAM_W, WEBCAM_H = 470, 350
TRACKBAR_W, TRACKBAR_H = 300, 300
MASK_W, MASK_H = 300, 120

exit_program = False


def mouse_callback(event, x, y, flags, param):
    global exit_program
    if event == cv2.EVENT_LBUTTONDOWN and 10 <= x <= 130 and 10 <= y <= 65:
        exit_program = True


cv2.namedWindow("WEBCAM", cv2.WINDOW_NORMAL)
cv2.resizeWindow("WEBCAM", WEBCAM_W, WEBCAM_H)
cv2.moveWindow("WEBCAM", 0, 0)
cv2.setMouseCallback("WEBCAM", mouse_callback)

cv2.namedWindow("Trackbars", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Trackbars", TRACKBAR_W, TRACKBAR_H)
cv2.moveWindow("Trackbars", 480, 0)

cv2.namedWindow("MASK", cv2.WINDOW_NORMAL)
cv2.resizeWindow("MASK", MASK_W, MASK_H)
cv2.moveWindow("MASK", 480, 310)


trackbars = [
    ("HUE lower", 50, 179),
    ("HUE upper", 100, 179),
    ("HUE2 lower", 50, 179),
    ("HUE2 upper", 100, 179),
    ("SAT lower", 100, 255),
    ("SAT upper", 255, 255),
    ("VALUE lower", 100, 255),
    ("VALUE upper", 255, 255),
]

for name, value, maximum in trackbars:
    cv2.createTrackbar(name, "Trackbars", value, maximum, lambda x: None)


cam = cv2.VideoCapture(0, cv2.CAP_V4L2)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

if not cam.isOpened():
    raise RuntimeError("Camera could not be opened")


while True:
    ret, frame = cam.read()

    if not ret:
        break

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    h1 = cv2.getTrackbarPos("HUE lower", "Trackbars")
    h2 = cv2.getTrackbarPos("HUE upper", "Trackbars")
    h3 = cv2.getTrackbarPos("HUE2 lower", "Trackbars")
    h4 = cv2.getTrackbarPos("HUE2 upper", "Trackbars")

    s1 = cv2.getTrackbarPos("SAT lower", "Trackbars")
    s2 = cv2.getTrackbarPos("SAT upper", "Trackbars")

    v1 = cv2.getTrackbarPos("VALUE lower", "Trackbars")
    v2 = cv2.getTrackbarPos("VALUE upper", "Trackbars")

    lower1 = np.array([h1, s1, v1])
    upper1 = np.array([h2, s2, v2])

    lower2 = np.array([h3, s1, v1])
    upper2 = np.array([h4, s2, v2])

    mask1 = cv2.inRange(hsv, lower1, upper1)
    mask2 = cv2.inRange(hsv, lower2, upper2)

    mask = cv2.add(mask1, mask2)

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contours = sorted(
        contours,
        key=cv2.contourArea,
        reverse=True
    )

    for cnt in contours:
        if cv2.contourArea(cnt) <= 50:
            continue

        x, y, w, h = cv2.boundingRect(cnt)

        cx = x + w // 2
        cy = y + h // 2

        cv2.drawContours(
            frame,
            [cnt],
            -1,
            (255, 0, 0),
            2
        )

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

        cv2.circle(
            frame,
            (cx, cy),
            5,
            (0, 0, 255),
            -1
        )

        cv2.line(
            frame,
            (cx, 0),
            (cx, CAM_H),
            (0, 255, 0),
            1
        )

        cv2.line(
            frame,
            (0, cy),
            (CAM_W, cy),
            (0, 255, 0),
            1
        )

    webcam = cv2.resize(
        frame,
        (WEBCAM_W, WEBCAM_H)
    )

    mask_display = cv2.resize(
        mask,
        (MASK_W, MASK_H)
    )

    cv2.rectangle(
        webcam,
        (10, 10),
        (130, 65),
        (0, 0, 255),
        -1
    )

    cv2.putText(
        webcam,
        "EXIT",
        (30, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (255, 255, 255),
        3
    )

    cv2.imshow("WEBCAM", webcam)
    cv2.imshow("MASK", mask_display)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q") or exit_program:
        break


cam.release()
cv2.destroyAllWindows()

print("Program terminated.")