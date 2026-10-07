import cv2
import face_recognition
import time
import pickle
from pathlib import Path

base_dir = Path(__file__).resolve().parent
weights_file = base_dir / 'faceData' / 'savedWeights' / 'weights_faces.pkl'

dispW = 640
dispH = 480
font = cv2.FONT_HERSHEY_COMPLEX
fpsReport = 0

Encodings = []
Names = []

# Load training data
# open(file name, read bytes)
with weights_file.open('rb') as f:
    Names = pickle.load(f)
    Encodings = pickle.load(f)

cam = cv2.VideoCapture(0, cv2.CAP_V4L2)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, dispW)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, dispH)

if not cam.isOpened():
    print("Could not open camera")

timeStamp = time.time()

while True:
    _, frame = cam.read()
    frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    facePositions = face_recognition.face_locations(frameRGB, model='cnn')
    allEncodings = face_recognition.face_encodings(frameRGB, facePositions)
    for (top,right,bottem,left), face_encodings in zip(facePositions, allEncodings):
        name = 'Unknown Person'
        matches = face_recognition.compare_faces(Encodings, face_encodings)
        if True in matches:
            first_match_index = matches.index(True)
            name = Names[first_match_index]
        cv2.rectangle(frame, (left,top), (right,bottem), (0,255,0), 2)
        cv2.putText(frame, name, (left,top-6), font, .75, (0,255,0), 2)

    # Determine fps
    dt = time.time() - timeStamp
    fps = 1/dt
    fpsReport = fpsReport * 0.90 + fps * 0.1
    cv2.rectangle(frame, (0,0), (100,40), (255,255,255), -1)
    cv2.putText(frame, str(round(fpsReport,2))+'fps', (5,25), font, .75, (0,0,0))
    #print(f"fps is: {round(fpsReport,2)}")
    timeStamp = time.time()

    cv2.imshow('Live', frame)
    cv2.moveWindow('Live', 0, 0)
    if cv2.waitKey(1) == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()