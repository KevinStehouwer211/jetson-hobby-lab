import cv2
print(cv2.__version__)

dispW=320
dispH=240
flip=2

# read the video file that was saved by CamSave.py
cam=cv2.VideoCapture('python_scripts/saved_vids/output.avi')

while True:
    ret, frame=cam.read()
    cv2.imshow('WEBCAM', frame)
    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()