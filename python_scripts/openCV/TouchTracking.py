import cv2
import numpy as np

print("OpenCV version:", cv2.__version__)

# ============================================================
# SCREEN SETTINGS
# ============================================================

# Typical 7-inch HDMI touchscreen resolution
SCREEN_W = 1024
SCREEN_H = 600

# Camera capture resolution
CAM_W = 640
CAM_H = 480

# Display window sizes
WEBCAM_W = 600
WEBCAM_H = 450

TRACKBAR_W = 400
TRACKBAR_H = 390

MASK_W = 400
MASK_H = 180

exit_program = False


# ============================================================
# TOUCHSCREEN CALLBACK
# ============================================================

def mouse_callback(event, x, y, flags, param):
    global exit_program

    if event == cv2.EVENT_LBUTTONDOWN:

        # Because the actual image is resized to 600x450,
        # these coordinates correspond to the DISPLAYED image.

        # EXIT button
        if 10 <= x <= 130 and 10 <= y <= 65:
            exit_program = True


# ============================================================
# CREATE WINDOWS
# ============================================================

# ---------------- TRACKBARS ----------------

cv2.namedWindow(
    'Trackbars',
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    'Trackbars',
    TRACKBAR_W,
    TRACKBAR_H
)

cv2.moveWindow(
    'Trackbars',
    610,
    0
)


# ---------------- WEBCAM ----------------

cv2.namedWindow(
    'WEBCAM',
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    'WEBCAM',
    WEBCAM_W,
    WEBCAM_H
)

cv2.moveWindow(
    'WEBCAM',
    0,
    0
)

cv2.setMouseCallback(
    'WEBCAM',
    mouse_callback
)


# ---------------- MASK ----------------

cv2.namedWindow(
    'MASK',
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    'MASK',
    MASK_W,
    MASK_H
)

cv2.moveWindow(
    'MASK',
    610,
    405
)


# ============================================================
# CREATE TRACKBARS
# ============================================================

cv2.createTrackbar(
    'HUE lower',
    'Trackbars',
    50,
    179,
    lambda x: None
)

cv2.createTrackbar(
    'HUE upper',
    'Trackbars',
    100,
    179,
    lambda x: None
)

cv2.createTrackbar(
    'HUE2 lower',
    'Trackbars',
    50,
    179,
    lambda x: None
)

cv2.createTrackbar(
    'HUE2 upper',
    'Trackbars',
    100,
    179,
    lambda x: None
)

cv2.createTrackbar(
    'SAT lower',
    'Trackbars',
    100,
    255,
    lambda x: None
)

cv2.createTrackbar(
    'SAT upper',
    'Trackbars',
    255,
    255,
    lambda x: None
)

cv2.createTrackbar(
    'VALUE lower',
    'Trackbars',
    100,
    255,
    lambda x: None
)

cv2.createTrackbar(
    'VALUE upper',
    'Trackbars',
    255,
    255,
    lambda x: None
)


# ============================================================
# CAMERA
# ============================================================

cam = cv2.VideoCapture(
    0,
    cv2.CAP_V4L2
)

cam.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    CAM_W
)

cam.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    CAM_H
)


if not cam.isOpened():
    print("ERROR: Camera could not be opened.")
    exit()


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    ret, frame = cam.read()

    if not ret:
        print("ERROR: Could not read camera.")
        break


    # ========================================================
    # CONVERT TO HSV
    # ========================================================

    hsv = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2HSV
    )


    # ========================================================
    # GET TRACKBAR VALUES
    # ========================================================

    h_lower = cv2.getTrackbarPos(
        'HUE lower',
        'Trackbars'
    )

    h_upper = cv2.getTrackbarPos(
        'HUE upper',
        'Trackbars'
    )

    h2_lower = cv2.getTrackbarPos(
        'HUE2 lower',
        'Trackbars'
    )

    h2_upper = cv2.getTrackbarPos(
        'HUE2 upper',
        'Trackbars'
    )

    s_lower = cv2.getTrackbarPos(
        'SAT lower',
        'Trackbars'
    )

    s_upper = cv2.getTrackbarPos(
        'SAT upper',
        'Trackbars'
    )

    v_lower = cv2.getTrackbarPos(
        'VALUE lower',
        'Trackbars'
    )

    v_upper = cv2.getTrackbarPos(
        'VALUE upper',
        'Trackbars'
    )


    # ========================================================
    # HSV LIMITS
    # ========================================================

    lb = np.array([
        h_lower,
        s_lower,
        v_lower
    ])

    ub = np.array([
        h_upper,
        s_upper,
        v_upper
    ])

    lb2 = np.array([
        h2_lower,
        s_lower,
        v_lower
    ])

    ub2 = np.array([
        h2_upper,
        s_upper,
        v_upper
    ])


    # ========================================================
    # MASKS
    # ========================================================

    FG_mask = cv2.inRange(
        hsv,
        lb,
        ub
    )

    FG_mask2 = cv2.inRange(
        hsv,
        lb2,
        ub2
    )

    FG_maskComp = cv2.add(
        FG_mask,
        FG_mask2
    )


    # ========================================================
    # FIND CONTOURS
    # ========================================================

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


    # ========================================================
    # DRAW DETECTIONS
    # ========================================================

    for cnt in contours:

        area = cv2.contourArea(cnt)

        if area > 50:

            x, y, w, h = cv2.boundingRect(cnt)


            # ---------------- CONTOUR ----------------

            cv2.drawContours(
                frame,
                [cnt],
                -1,
                (255, 0, 0),
                2
            )


            # ---------------- BOX ----------------

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )


            # ---------------- CENTER ----------------

            center_x = x + w // 2
            center_y = y + h // 2


            # Center point
            cv2.circle(
                frame,
                (center_x, center_y),
                5,
                (0, 0, 255),
                -1
            )


            # Vertical line
            cv2.line(
                frame,
                (center_x, 0),
                (center_x, CAM_H),
                (0, 255, 0),
                1
            )


            # Horizontal line
            cv2.line(
                frame,
                (0, center_y),
                (CAM_W, center_y),
                (0, 255, 0),
                1
            )


    # ========================================================
    # EXIT BUTTON
    # ========================================================

    # Since detection happens at 640x480, draw button before
    # resizing the image.

    cv2.rectangle(
        frame,
        (10, 10),
        (140, 70),
        (0, 0, 255),
        -1
    )

    cv2.rectangle(
        frame,
        (10, 10),
        (140, 70),
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "EXIT",
        (32, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (255, 255, 255),
        3
    )


    # ========================================================
    # RESIZE FOR 7-INCH SCREEN
    # ========================================================

    webcam_display = cv2.resize(
        frame,
        (WEBCAM_W, WEBCAM_H)
    )

    mask_display = cv2.resize(
        FG_maskComp,
        (MASK_W, MASK_H)
    )


    # ========================================================
    # SHOW WINDOWS
    # ========================================================

    cv2.imshow(
        'WEBCAM',
        webcam_display
    )

    cv2.imshow(
        'MASK',
        mask_display
    )


    # ========================================================
    # EXIT
    # ========================================================

    key = cv2.waitKey(1) & 0xFF


    # Keyboard Q
    if key == ord('q'):
        break


    # Touchscreen EXIT
    if exit_program:
        break


    # Window X
    if cv2.getWindowProperty(
        'WEBCAM',
        cv2.WND_PROP_VISIBLE
    ) < 1:
        break


# ============================================================
# CLEAN SHUTDOWN
# ============================================================

print("Closing camera...")

cam.release()

cv2.destroyAllWindows()

print("Program terminated.")