import face_recognition
import os
import pickle
from pathlib import Path

base_dir = Path(__file__).resolve().parent
save_dir = base_dir / 'faceData' / 'savedWeights'

# Change this to the folder that consists the faces to be trained
image_dir = base_dir / 'faceData' / 'faces'

Encodings = []
Names = []

for root, dirs, files in os.walk(image_dir):
    for file in files:
        path = os.path.join(root,file)
        print('Grabbed image located: \n',path)
        name = os.path.splitext(file)[0]
        print('Training facial recognition data of: \n', name)
        person = face_recognition.load_image_file(path)
        encoding = face_recognition.face_encodings(person)[0]
        Encodings.append(encoding)
        Names.append(name)
print('Saving facial recognition data of: \n', Names)


# Save facial weights in 
save_path = save_dir / 'weights_faces.pkl'
# open(file name, write bytes) write file
with save_path.open('wb') as f:
    pickle.dump(Names, f)
    pickle.dump(Encodings, f)

print(f'Saved facial recognition data to:\n{save_path}')