import cv2
import os
print(cv2.__version__)

VID_PATH = 'python_scripts/saved_vids/output.avi'

print("Video path:", VID_PATH)
print("File exists:", os.path.exists(VID_PATH))
print("File size:", os.path.getsize(VID_PATH), "bytes")

cam = cv2.VideoCapture(VID_PATH)

print("Video opened:", cam.isOpened())
print("Frames:", cam.get(cv2.CAP_PROP_FRAME_COUNT))
print("FPS:", cam.get(cv2.CAP_PROP_FPS))
print("Width:", cam.get(cv2.CAP_PROP_FRAME_WIDTH))
print("Height:", cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

while True:
    ret, frame=cam.read()
    if not ret:
        break
    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)
    # same framerate as the original video
    if cv2.waitKey(30)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()