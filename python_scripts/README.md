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
| [CamSave.py](openCV/CamSave.py) | `VideoWriter` → `saved_vids/output.avi` |
| [CamRead.py](openCV/CamRead.py) | Play that file back, print FPS/frame count |
| [WebCamStream.py](openCV/WebCamStream.py) | Flask MJPEG server on `:5000` — the *no-screen* alternative |

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
├── openCV/      # the scripts
├── images/      # smarties.png, cv.jpg, pi.png, HSV.jpeg — inputs for the mask demos
├── saved_vids/  # output.avi, written by CamSave.py
└── servo/       # empty — next up
```

---

## 🔗 Links

- [OpenCV Python tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [HSV color ranges](https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html)
- Repo root: [README.md](../README.md)
