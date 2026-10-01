import face_recognition
import cv2

donFace = face_recognition.load_image_file('python_scripts/faceRecognizer/demoImages/known/Donald Trump.jpg')
donEncode = face_recognition.face_encodings(donFace)[0]

nancyFace = face_recognition.load_image_file('python_scripts/faceRecognizer/demoImages/known/Nancy Pelosi.jpg')
nancyEncode = face_recognition.face_encodings(nancyFace)[0]

Encodings = [donEncode, nancyEncode]

Names = ['Donald Trump', 'Nancy Palosi']

font = cv2.FONT_HERSHEY_SIMPLEX
testImage = face_recognition.load_image_file('python_scripts/faceRecognizer/demoImages/unknown/u11.jpg')
facePositions = face_recognition.face_locations(testImage)
allEncodings = face_recognition.face_encodings(testImage, facePositions)

testImage = cv2.cvtColor(testImage, cv2.COLOR_RGB2BGR)

for (top, right, bottem, left), face_encoding in zip(facePositions, allEncodings):
    name = 'Unknown person'
    matches = face_recognition.compare_faces(Encodings, face_encoding)

    if True in matches:
        first_match_index = matches.index(True)
        name = Names[first_match_index]

    cv2.rectangle(testImage, (left,top), (right, bottem), (0,255,0), 2)
    cv2.putText(testImage, name, (left,top-6), font, 0.75, (0,255,255), 2)

testImage = cv2.resize(testImage, (640,480))
cv2.imshow('Image', testImage)
cv2.moveWindow('Image', 0,0)

if cv2.waitKey(0) == ord('q'):
    cv2.destroyAllWindows()