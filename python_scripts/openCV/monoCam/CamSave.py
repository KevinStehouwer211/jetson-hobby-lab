import cv2
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

print(cv2.__version__)

dispW = 640
dispH = 480

# Open USB webcam
cam = cv2.VideoCapture(0, cv2.CAP_V4L2)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, dispW)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, dispH)
cam.set(cv2.CAP_PROP_FPS, 30)

if not cam.isOpened():
    raise RuntimeError("Could not open webcam")

# Video output
stamp = datetime.now(ZoneInfo('Europe/Amsterdam')).strftime('%Y%m%d_%H%M%S_%f')
output_path = (Path(__file__).resolve().parent / 'stereoCam' / 'CamCalibration' / 'intrinsics' /
               'Dofbot' / f'calibration_{stamp}.avi')
output_path.parent.mkdir(parents=True, exist_ok=True)

fps = 30
fourcc = cv2.VideoWriter_fourcc(*"MJPG")

outVideo = None
recording = False

while True:
    ret, frame = cam.read()

    if not ret:
        print("Failed to read frame")
        break

    # Record only when enabled
    if recording and outVideo is not None:
        outVideo.write(frame)

    # Show recording status on preview only
    preview = frame.copy()

    if recording:
        cv2.circle(preview, (20, 25), 10, (0, 0, 255), -1)
        cv2.putText(preview, "REC", (40, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 0, 255), 2)
    else:
        cv2.putText(preview, "READY", (15, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 255, 0), 2)

    cv2.imshow("WEBCAM", preview)

    key = cv2.waitKey(1) & 0xFF

    # SPACE toggles recording
    if key == ord(" "):
        recording = not recording

        if recording:
            if outVideo is None:
                width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

                outVideo = cv2.VideoWriter(
                    str(output_path), fourcc, fps, (width, height)
                )

                if not outVideo.isOpened():
                    raise RuntimeError("Could not create video file")

            print("Recording started")

        else:
            print("Recording paused")

    # Q quits
    elif key == ord("q"):
        break

# Cleanup
if outVideo is not None:
    outVideo.release()

cam.release()
cv2.destroyAllWindows()

print(f"Video saved to: {output_path}")
