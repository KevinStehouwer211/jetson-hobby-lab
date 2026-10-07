import cv2
import face_recognition
import os
import pickle
from pathlib import Path

base_dir = Path(__file__).resolve().parent
weights_file = base_dir / 'faceData' / 'savedWeights' / 'weights_demoImages.pkl'
testImage_file = base_dir / 'demoImages' / 'unknown' / 'u11.jpg'

Encodings = []
Names = []

# Load training data
# open(file name, read bytes)
with weights_file.open('rb') as f:
    Names = pickle.load(f)
    Encodings = pickle.load(f)

font = cv2.FONT_HERSHEY_COMPLEX
testImage = face_recognition.load_image_file(testImage_file)
facePositions = face_recognition.face_locations(testImage)
allEncodings = face_recognition.face_encodings(testImage, facePositions)
testImage = cv2.cvtColor(testImage, cv2.COLOR_RGB2BGR)

for (top,right,bottem,left), face_encoding in zip(facePositions, allEncodings):
    name = 'Unknown person'
    matches = face_recognition.compare_faces(Encodings, face_encoding)
    print(matches)
    if True in matches:
        first_match_index = matches.index(True)
        name = Names[first_match_index]
    cv2.rectangle(testImage, (left,top), (right,bottem), (0,255,0), 2)
    cv2.putText(testImage, name, (left,top-6), font, .75, (0,255,0), 2)

testImage = cv2.resize(testImage, (640,480))
cv2.imshow('Picture', testImage)
cv2.moveWindow('Picture',0,0)
if cv2.waitKey(0) == ord('q'):
    cv2.destroyAllWindows()