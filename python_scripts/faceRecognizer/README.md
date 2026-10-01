# 🙂 faceRecognizer

Face **detection** and face **recognition** on the Jetson Orin Nano using the
[`face_recognition`](https://github.com/ageitgey/face_recognition) library, which
is a thin Python wrapper around **dlib**. dlib was built from source so it runs on
the Jetson's GPU (CUDA).

This is a different approach from [../openCV/FaceDetection.py](../openCV/FaceDetection.py),
which uses OpenCV Haar cascades. Haar cascades can only say *"there is a face"*;
dlib can also say *"this is **whose** face"*.

---

## 📂 Contents

| File | What it does |
|---|---|
| [faceDetection.py](faceDetection.py) | Finds all faces in one image and draws a green box around each one |
| [faceRecognition.py](faceRecognition.py) | Learns two known faces, then finds and **names** the faces in an unknown image |
| `demoImages/known/` | One photo per person, filename = the person's name *(not in git)* |
| `demoImages/unknown/` | Test photos (`u1.jpg` … `u13.jpg`) to run recognition on *(not in git)* |

### 🚫 Not committed (too large)

Some folders are listed in [.gitignore](../../.gitignore) so they don't make the repo big.
A fresh clone **won't have them**, so recreate them locally:

| Path | Size | Why it's ignored | How to get it back |
|---|---|---|---|
| `python_scripts/faceRecognizer/demoImages/` | ~21 MB | Photos, large binary files | Copy your own images into `demoImages/known/` (named `<Person Name>.jpg`) and `demoImages/unknown/` |
| `dlib-19.17/` | ~160 MB | Source + build output | [Step 2](#step-2--download-and-extract-the-dlib-source-archive) below |
| `dlib-19.17.tar.bz2` | ~11 MB | Downloaded archive | [Step 2](#step-2--download-and-extract-the-dlib-source-archive) below |
| `installSwapfile/` | ~200 KB | A separate git repo (has its own `.git`) | [Step 1](#step-1--add-swap-space-first-why-the-swapfile-came-before-dlib) below |

---

## 🧠 How it works

### 1. Detection — *where* are the faces?

```python
image = face_recognition.load_image_file(path)        # loads as RGB numpy array
face_locations = face_recognition.face_locations(image)
```

`face_locations()` runs dlib's HOG face detector (the default, CPU) and returns a
list of boxes, one per face, as `(top, right, bottom, left)` pixel coordinates.
Passing `model="cnn"` uses dlib's CNN detector instead, which is more accurate and
is the one that benefits from the CUDA build.

### 2. Encoding — turn a face into 128 numbers

```python
encoding = face_recognition.face_encodings(image)[0]
```

For each face, dlib runs a pretrained deep neural network (ResNet) that outputs a
**128-dimensional vector** (an *encoding* or *embedding*). The network was trained
so that photos of the same person produce vectors that are close together, and
photos of different people produce vectors far apart.

The pretrained model files come from the `face_recognition_models` package.

### 3. Recognition — compare encodings

```python
matches = face_recognition.compare_faces(known_encodings, unknown_encoding)
```

`compare_faces()` computes the Euclidean distance between the unknown encoding and
every known encoding. Distance **< 0.6** (the default `tolerance`) counts as a
match. It returns a list of `True`/`False`, one per known face.

So the full pipeline in [faceRecognition.py](faceRecognition.py) is:

```
known photos ──► face_encodings ──► list of (encoding, name)
                                              │
unknown photo ──► face_locations ──► face_encodings ──► compare_faces ──► name or "Unknown person"
                                                                 │
                                         draw box + name with OpenCV ──► show window
```

### 4. Displaying with OpenCV

`face_recognition` loads images as **RGB**, but OpenCV expects **BGR**, so both
scripts call `cv2.cvtColor(image, cv2.COLOR_RGB2BGR)` before drawing and showing
the image. The result is resized to 640×480 and shown until a key is pressed.

---

## 🛠️ What I did — step by step (to recreate this setup)

Everything below was done on the **host** (not in a container), from the repo root
`~/jetson-hobby-lab`, on JetPack 6 (L4T R36.4, CUDA 12.6), Python 3.10.

Timeline on 2026-10-01:

| Time | Step |
|---|---|
| 17:41 | Cloned the JetsonHacks `installSwapfile` repo |
| 17:51 | Ran it → 6 GB swap file at `/mnt/swapfile` |
| 17:58 | Downloaded + extracted the dlib 19.17 archive |
| ~18:00 | Patched `cudnn_dlibapi.cpp` and started the build |
| 18:10 | dlib 19.17 build + install finished |
| 20:07 | `pip3 install face_recognition` |

### Step 1 — Add swap space *first* (why the swapfile came before dlib)

**Why:** dlib is a large C++ library built from heavily templated code. Compiling it
means running several `c++` compiler processes in parallel, and a single one can
use 1–2 GB of RAM. The Orin Nano has **8 GB of RAM shared between the CPU and GPU**
(about 7.4 GB usable, and the desktop already takes a few GB). Without extra
memory, the kernel's out-of-memory killer kills the compiler partway through,
and the build fails with a vague error like
`c++: fatal error: Killed signal terminated program cc1plus`, often after you've
already waited a long time.

**Swap** is disk space the kernel uses as extra (slow) memory. When RAM fills up,
pages that aren't being used move to disk, so the compiler can finish. It is
slower than RAM, but a slow build that finishes beats a fast one that crashes.
That's why the swap file has to be in place **before** starting the dlib build.

**How:** I used the JetsonHacks script:

```bash
cd ~/jetson-hobby-lab
git clone https://github.com/JetsonHacksNano/installSwapfile
cd installSwapfile
./installSwapfile.sh          # defaults: 6 GB, in /mnt, enabled on boot
```

What the script does (`installSwapfile/installSwapfile.sh`):

```bash
sudo fallocate -l 6G /mnt/swapfile    # reserve a 6 GB file
sudo chmod 600 /mnt/swapfile          # only root may read it
sudo mkswap /mnt/swapfile             # format it as swap
sudo swapon /mnt/swapfile             # start using it now
echo "/mnt/swapfile swap swap defaults 0 0" | sudo tee -a /etc/fstab   # and on every boot
```

Check it's active:

```bash
swapon --show
```

```
NAME          TYPE SIZE PRIO
/mnt/swapfile file   6G   -2    ← added by the script
/var/8GB.swap file   8G   -3    ← was already on the system
```

### Step 2 — Download and extract the dlib source archive

```bash
cd ~/jetson-hobby-lab
wget http://dlib.net/files/dlib-19.17.tar.bz2
tar xvf dlib-19.17.tar.bz2
cd dlib-19.17
```

Why from source instead of `pip install dlib`: pip would compile dlib anyway (there
are no prebuilt aarch64 wheels on PyPI), and building it yourself lets you patch
the source first (step 3). 19.17 is the version used in the Paul McWhorter Jetson
AI tutorials that the demo images come from.

### Step 3 — Patch the cuDNN code

Open `dlib/cuda/cudnn_dlibapi.cpp` and comment out this line (line 854 in 19.17):

```cpp
//forward_algo = forward_best_algo;
```

Why: on Jetson, the "best" cuDNN convolution algorithm that dlib picks can need
more GPU memory than is available, which causes CUDA/cuDNN errors at runtime. By
commenting the line out, dlib keeps its safer default algorithm.

### Step 4 — Build and install dlib

```bash
sudo python3 setup.py install
```

`setup.py` runs CMake to configure the build, compiles the C++ library and the
Python bindings, and installs the result in
`/usr/local/lib/python3.10/dist-packages/dlib-19.17.0-py3.10-linux-aarch64.egg`.
The ~10 minute build is when the swap from step 1 is needed.

The `dlib-19.17/` folder (~160 MB after building) and the `.tar.bz2` (~11 MB) stay
in the repo root, but they're too large to commit, so they're listed in
[.gitignore](../../.gitignore). Once dlib is installed, they aren't needed to run
anything, so you can delete them to save space.

### Step 5 — Install face_recognition

```bash
pip3 install face_recognition
```

This installs (in `~/.local/lib/python3.10/site-packages`):

| Package | Version | What it is |
|---|---|---|
| face_recognition | 1.3.0 | The easy Python API (`face_locations`, `face_encodings`, `compare_faces`) |
| face_recognition_models | 0.3.0 | Pretrained model weights (face detector, landmarks, 128-d encoder) |
| Click, numpy, Pillow | — | Dependencies |

pip sees dlib is already installed, so it doesn't build it again.

### Step 6 — Verify

```bash
python3 -c "import dlib, face_recognition; print(dlib.__file__, dlib.__version__, dlib.DLIB_USE_CUDA)"
```

```
/usr/local/lib/python3.10/dist-packages/dlib/__init__.py 19.24.6 True
```

### ⚠️ Which dlib is actually used

The check above shows that Python **does not load the 19.17 I built**. There are
two dlibs in `/usr/local/lib/python3.10/dist-packages`:

| dlib | Installed | CUDA | Used? |
|---|---|---|---|
| **19.24.6** (`dlib/` + `_dlib_pybind11…so`) | 2025-01-15, by pip, before this project | ✅ `True` | ✅ **Yes**, this is what `import dlib` loads |
| 19.17.0 (`dlib-19.17.0-…egg`) | 2026-10-01, steps 2–4 above | ❌ `False` | ❌ No |

- The 19.24.6 package folder comes first on Python's search path. The 19.17 egg is
  only added to the end of the path (through `easy-install.pth`), so it's never reached.
- The 19.17 build is **CPU-only**. dlib 19.17 dates from 2019, and its CMake
  check for CUDA/cuDNN doesn't recognise the CUDA 12.6 / cuDNN 9 on JetPack 6, so
  it quietly builds without GPU support.

That turns out fine: the dlib that's used is newer **and** has CUDA. To check the
19.17 build yourself:

```bash
python3 -c "import sys; sys.path.insert(0,'/usr/local/lib/python3.10/dist-packages/dlib-19.17.0-py3.10-linux-aarch64.egg'); import dlib; print(dlib.__version__, dlib.DLIB_USE_CUDA)"
# 19.17.0 False
```

**If recreating this from scratch on a fresh Jetson** (no dlib 19.24.6 already
installed), build a recent dlib with CUDA instead of 19.17. Do steps 1 and 5 as
above, but replace steps 2–4 with:

```bash
wget http://dlib.net/files/dlib-19.24.6.tar.bz2
tar xvf dlib-19.24.6.tar.bz2
cd dlib-19.24.6
sudo python3 setup.py install      # no patch needed for 19.24
```

then confirm `dlib.DLIB_USE_CUDA` prints `True`.

---

## ▶️ Running the scripts

The image paths in the scripts are **relative to the repo root**, so run them from
there (on the host, with a display attached):

```bash
cd ~/jetson-hobby-lab
python3 python_scripts/faceRecognizer/faceDetection.py
python3 python_scripts/faceRecognizer/faceRecognition.py
```

Press `q` in the image window to close it.

To try other images, change the filename in `load_image_file(...)` (e.g.
`unknown/u3.jpg` → `unknown/u7.jpg`). To recognize more people, load their photo
from `demoImages/known/`, add the encoding to `Encodings` and the name to `Names`
(same order).

---

## 💡 Ideas / next steps

- Loop over everything in `demoImages/known/` and use the filename as the name,
  instead of hard-coding each person
- Use `face_recognition.face_distance()` and pick the **closest** match instead of
  the first match
- Use `model="cnn"` in `face_locations()` to use the GPU
- Run it on live camera frames and combine it with [../PanTilt/FaceTracking.py](../PanTilt/FaceTracking.py)
  to only track a specific person
