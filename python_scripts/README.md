# 🐍 python_scripts — OpenCV warm-up lab

Small, self-contained scripts for learning OpenCV on the **Jetson Orin Nano Super**.
No containers, no ROS — plain `python3` + a USB webcam.

**The workflow this folder is built around:** you edit and launch over **SSH**, but
the windows open on the **touchscreen attached to the Jetson**. You look at the
screen and poke it; the terminal stays on your laptop.

---

## 🚀 Run one

```bash
ssh kstehouwer@<jetson>
cd ~/jetson-hobby-lab
export DISPLAY=:0                      # ← without this: "Can't initialize GTK backend"
python3 python_scripts/openCV/TouchTracking.py
```

`DISPLAY=:0` is the whole trick. An SSH session has no display of its own, so
`cv2.imshow`/`namedWindow` abort. Pointing it at `:0` hands the window to the
desktop session already running on the touchscreen.

Make it permanent for SSH logins:

```bash
echo 'export DISPLAY=:0' >> ~/.bashrc
```

If X still refuses the connection, allow local clients once from a terminal **on
the touchscreen**: `xhost +local:`.

> Run from the **repo root** — `CamSave.py` and `CamRead.py` use paths relative to it.
> Everything else resolves images relative to its own file, so it runs from anywhere.

---

## 👆 Touchscreen notes

A touch tap arrives as a normal left click, so `setMouseCallback` is all you need —
but there is no hover, no right click, and no keyboard.

| Problem | What the scripts do |
|---|---|
| `waitKey(ord('q'))` needs a keyboard | Draw an **EXIT** rectangle and watch for a click inside it (`TouchTracking.py`, `ObjectTracking.py`) |
| Windows land off-screen | `cv2.moveWindow(...)` after every `namedWindow` |
| Default windows are too big | `WINDOW_NORMAL` + `resizeWindow` to a fixed tile layout |
| Trackbars are hard to hit | Keep them in their own window, sized generously |

Quitting still works over SSH-with-keyboard too — every loop checks `q` as well.

---

## 🗂️ The scripts

Roughly in the order they're worth reading.

### Camera basics
| Script | What it teaches |
|---|---|
| [CamOpen.py](openCV/CamOpen.py) | Open the webcam, show frames, quit on `q` |
| [CamSave.py](openCV/CamSave.py) | Record Dofbot calibration video into `stereoCam/CamCalibration/intrinsics/Dofbot/` |
| [CamRead.py](openCV/CamRead.py) | Play that file back, print FPS/frame count |
| [DualCamSave.py](openCV/DualCamSave.py) | Preview Dofbot and dashcam together; Space records/pauses separate AVI files, Q saves and quits |
| [benchmark_camera.py](openCV/benchmark_camera.py) | Measure delivered camera FPS; compare formats and capture buffer counts |
| [live_stereo.py](openCV/stereoCam/live_stereo.py) | Adjustable red HSV tracking in both cameras, bounding boxes and calibrated live XYZ |
| [live_stereo_face.py](openCV/stereoCam/live_stereo_face.py) | Haar face/eye detection from FaceTracking.py with the same stereo XYZ dashboard |
| [WebCamStream.py](openCV/WebCamStream.py) | Flask MJPEG server on `:5000` — the *no-screen* alternative |

`DualCamSave.py` requests 30 fps with four capture buffers per camera and saves
at 25 fps by default. Run it with `--fps 30` to test 30 fps recording. The preview
shows measured capture rates, frame age, and counts of reused source frames.
Each recording session creates `openCV/stereoCam/CamCalibration/YYYY-MM-DD/trial_NN/`,
with `cam1.avi` (Dashcam), `cam2.avi` (Dofbot), `recording.json`, and
`frame_timing.csv`. Use `--kind wand_calibration` for `wand_calibration_NN/`
sessions. Shared profiles and Patterns/Calibrate files live in
`openCV/stereoCam/CamCalibration/intrinsics/`. The CSV contains host arrival times and
reuse flags; these are not sensor exposure timestamps or proof of synchronized
exposures. Test both cameras together before relying on a recording rate.

Run the shared analysis for all calibrated trials with:

```bash
argus_env/bin/python python_scripts/openCV/stereoCam/CamCalibration/analysis/analyze.py --all
```

Replace `--all` with `2026-10-17/trial_03` to analyze one test. One shared script
generates the same isometric reconstruction, uncertainty plots, animation and
report in each trial's `analysis/` folder.

For live stereo tracking, run:

```bash
argus_env/bin/python python_scripts/openCV/stereoCam/live_stereo.py
```

The screen-sized dashboard has camera views, masks, all eight HSV.py trackbars
per camera, a live isometric 3D plot, and large XYZ readouts. Press `r` and drag
on the images to select search ROIs, `s` to save thresholds, `t` to clear the 3D
trail, and `q` to quit. The preview shows matched bounding boxes, XYZ in metres,
fit diagnostics and conditional uncertainty. See
[stereoCam/README.txt](openCV/stereoCam/README.txt) for calibration selection and timing limits.

For the face-detection version using `PanTilt/FaceTracking.py`'s Haar face and eye
cascades, run:

```bash
argus_env/bin/python python_scripts/openCV/stereoCam/live_stereo_face.py
```

It uses the same live 3D plot and calibration, with XYZ estimated from matching
face-box centres in the two views. Keep the calibrated cameras fixed.

### Drawing and input
| Script | What it teaches |
|---|---|
| [Drawing_shapes.py](openCV/Drawing_shapes.py) | `rectangle` / `circle` / `putText` on a live frame |
| [BouncingBox.py](openCV/BouncingBox.py) | Animate a box, bounce it off the edges |
| [TrackBars.py](openCV/TrackBars.py) | Sliders driving the box position and size |
| [MouseClick.py](openCV/MouseClick.py) | `setMouseCallback` — collect click coordinates |
| [MouseROI.py](openCV/MouseROI.py) | Drag (button-down → button-up) to select a region |

### Color and masks
| Script | What it teaches |
|---|---|
| [ColorChannels.py](openCV/ColorChannels.py) | `split` / `merge` — isolate B, G, R |
| [HSV_wheel.py](openCV/HSV_wheel.py) | Slice an HSV wheel with sliders — build the intuition first |
| [HSV.py](openCV/HSV.py) | Same sliders, applied to `images/smarties.png` |
| [Bitwise.py](openCV/Bitwise.py) | `and` / `or` / `xor` / `not` on two half-white images |
| [Masks.py](openCV/Masks.py) | Threshold a logo into fg/bg masks, blend it in |
| [MovingMask.py](openCV/MovingMask.py) | That watermark, bouncing around the frame |
| [ColorBouncingBox.py](openCV/ColorBouncingBox.py) | Grayscale frame with a moving color "spotlight" (ROI slicing) |

### Putting it together
| Script | What it teaches |
|---|---|
| [ObjectTracking.py](openCV/ObjectTracking.py) | HSV range → mask → contours → bounding box, blue preset |
| [TouchTracking.py](openCV/TouchTracking.py) | The same tracker, laid out and sized for the touchscreen |

---

## 🎥 Camera notes

USB webcam, V4L2 backend:

```python
cam = cv2.VideoCapture(0, cv2.CAP_V4L2)
```

Every script also carries a commented-out `nvarguscamerasrc` GStreamer pipeline for
a **CSI/Pi camera** — uncomment that pair of lines instead if you swap hardware.

Check what's actually connected:

```bash
ls /dev/video*
v4l2-ctl --list-devices
```

`WebCamStream.py` opens index **1**, the rest open **0** — adjust to match.

---

## 🗃️ Layout

```text
python_scripts/
├── openCV/      # scripts; stereoCam/CamCalibration/ holds calibration and trial data
├── images/      # smarties.png, cv.jpg, pi.png, HSV.jpeg — inputs for the mask demos
└── servo/       # empty — next up
```

---

## 🔗 Links

- [OpenCV Python tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [HSV color ranges](https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html)
- Repo root: [README.md](../README.md)
