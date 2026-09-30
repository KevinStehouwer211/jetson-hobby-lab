import cv2
print(cv2.__version__)

dispW=320
dispH=240
flip=2

# Haar cascade installed with the source-built OpenCV
path_face = '/home/kstehouwer/jetson-hobby-lab/python_scripts/openCV/machine_learning/face.xml'
path_eye = '/home/kstehouwer/jetson-hobby-lab/python_scripts/openCV/machine_learning/eye.xml'
# For Pi camera, use the following line:
# camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

# For USB webcam, use the following line:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)

# Load face classifier
face_cascade = cv2.CascadeClassifier(path_face)
if face_cascade.empty():
    raise SystemExit('Could not load face cascade: ' + path_face)

# Load eye classifier
eye_cascade = cv2.CascadeClassifier(path_eye)
if eye_cascade.empty():
    raise SystemExit('Could not load face cascade: ' + path_eye)

while True:
    ret, frame=cam.read()
    frame = cv2.resize(frame, (dispW, dispH))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for x1,y1,w1,h1 in faces:
        #cv2.rectangle(frame, (x1,y1), (x1+w1,y1+h1), (0,255,0), 1)
        cv2.circle(frame, (x1+w1//2, y1+h1//2), w1//2, (0,255,0))

        face_gray = gray[y1:y1+h1, x1:x1+w1]
        eyes = eye_cascade.detectMultiScale(face_gray)

        for x2,y2,w2,h2 in eyes:
            cv2.circle(frame, (x1+x2+w2//2, y1+y2+h2//2), h2//2, (255,0,0), 1)

    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)
    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()