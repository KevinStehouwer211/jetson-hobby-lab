LIVE STEREO RED TRACKING

RGB (255, 0, 0) is pure red. OpenCV images use BGR, so its pixel value is
(0, 0, 255). The two hue ranges cover red around 0 and 179, with tolerance for
lighting.

From the repository root:
  argus_env/bin/python python_scripts/openCV/stereoCam/live_stereo.py

Files:
  live_stereo.py       Live preview, HSV trackbars, stereo matching and XYZ labels
  live_stereo_face.py  Face-tracking entry point using the same stereo/dashboard pipeline
  face_detection.py   Grayscale Haar face/eye method from PanTilt/FaceTracking.py
  dashboard.py          Screen-sized Qt dashboard, HSV controls and live isometric plot
  calibration.py        Intrinsics, distortion, DLT triangulation and display rotation
  test_stereo.py        Geometry, segmentation and rejection tests (no cameras required)
  CamCalibration/       All intrinsics, wand calibrations, recordings and test analyses

The tracker reuses DualCamSave.vStream: threaded V4L2 capture, 30 fps request,
four buffers, and measured camera rates. Camera ordering matches Argus:
  cam1 = Dashcam = /dev/video2 = MJPG
  cam2 = Dofbot  = /dev/video0 = YUYV
Use --cam1 and --cam2 if USB device names change. Keep camera positions, lens
settings and capture resolution consistent with the calibration. Current input
resolution is 640x480; a mismatch is rejected rather than silently resized.

DASHBOARD AND HSV CONTROLS
One maximized window fits the screen's available work area, keeping camera views,
masks and HSV controls together on the left and a live 3D plot with large XYZ
readouts on the right. It scales with display resolution rather than assuming a
pixel size from the monitor's diagonal. Camera pixels remain at native calibrated
resolution for reconstruction; only the displayed images are scaled, without stretching.
Use --window-size 1366x768 to choose a specific window size if desired.

Each camera has all eight trackbars from HSV.py, with the same names, order,
limits and two-mask combination; hue defaults now select RGB red (255, 0, 0):
  HUE lower      0 / 179      HUE upper      10 / 179
  HUE2 lower   170 / 179      HUE2 upper    179 / 179
  SAT lower    100 / 255      SAT upper    255 / 255
  VALUE lower  100 / 255      VALUE upper  255 / 255
Each slider also has a linked numeric input. The two hue masks share saturation
and value bounds, and are combined with OR just as in HSV.py. Red uses these
defaults; tune thresholds until the mask contains the intended object. Old saved
single-hue settings are loaded with that range duplicated into HUE2 to preserve
their mask. Existing area/morphology filters are retained as detection settings,
rather than adding extra trackbars to the eight HSV controls.

The green box and cross mark the matched centroid. Large color-coded XYZ readouts
show metres. The live plot uses an orthographic isometric view, equal unit scales,
the recent position trail, and conditional per-axis 95% error bars. Current readouts
and the current marker clear when the target is lost; the trail remains historical.
The plot refreshes at 6 fps by default (--plot-fps changes it), independently of
threaded camera acquisition. T clears the trail. Other candidate blobs have gray boxes.

Q / Esc   Quit
S         Save HSV thresholds and ROIs to stereoCam/hsv_settings.json
R         Enable ROI selection; drag on each camera image, or R again to cancel
C         Clear search ROIs
T         Clear the 3D position trail

ROI selection takes place inside the dashboard; no additional windows open.

Use ROIs when other red objects (including clothes) are visible. Both selected
objects must be the same physical object. Epipolar matching rejects inconsistent
pairs; nearly tied matches are suppressed as ambiguous. Geometry and color alone
cannot establish identity when several indistinguishable red objects are visible.

CALIBRATION AND COORDINATES
The default intrinsics are CamCalibration/intrinsics/camera-profile.txt.
The default DLT is the last dated wand_calibration_NN DLT CSV; startup prints
the exact files. Override with --profile PATH and --dlt PATH. No calibration is
computed or modified by the tracker. The current calibration uses a 0.165 m wand,
so XYZ is in metres. Future calibrations must use metre units for these labels.

If an analyzed trial references the exact same DLT hash, its orientation.json
provides the default display frame (+Z up, inferred from its fall). The origin
is that reference trial's initial position, not the live object's current position
or the floor. Use --orientation PATH to choose a reference, or --calibration-frame
to show original Argus coordinates. Without a matching reference, original
calibration coordinates are used and clearly labeled.

Argus stores Y from the image bottom; the tracker converts OpenCV top-left pixel
coordinates before distortion correction and triangulation. It initializes from
all four observations and refines XYZ by raw-pixel least squares. Camera profiles
and DLT columns must be in cam1/cam2 order. A box center is the segmented silhouette
centroid, so different visible silhouettes or occlusion can bias the 3D position.

QUALITY AND TIMING
Default rejection limits: 5 px epipolar/reprojection diagnostic, 25 ms host arrival
gap, 150 ms frame age, and 1 degree ray angle. The controls --max-error-px,
--max-skew-ms, --max-age-ms and --ambiguity-margin adjust these decisions.
These gates do not synchronize exposures. Host arrivals are not sensor exposure
timestamps; fast motion can remain inaccurate even when a pair passes the gates.
The displayed 95% bounds assume 2 px independent marking noise and fixed camera
geometry/orientation. They exclude calibration, timing and model errors. Change
the assumption with --sigma-px; it is not an estimate of total certainty.

OFFLINE CHECKS AND REPLAY
  argus_env/bin/python python_scripts/openCV/stereoCam/test_stereo.py
  argus_env/bin/python python_scripts/openCV/stereoCam/live_stereo.py --help
  argus_env/bin/python python_scripts/openCV/stereoCam/live_stereo.py --videos CAM1.avi CAM2.avi
Add --headless --frames 20 --preview /tmp/stereo-preview.png --log /tmp/stereo.csv
to test without GUI. Replay assumes corresponding video frame indices; it does
not claim exposure synchronization. Close other camera applications before live use.
Without --headless, --preview saves the entire dashboard including the live plot.
The dashboard uses PySide6 and Matplotlib, already installed in argus_env.

OTHER TOOLS
DualCamSave.py and CamSave.py now write calibration/recording files into this
stereoCam/CamCalibration tree. The single shared test-analysis command is:
  argus_env/bin/python python_scripts/openCV/stereoCam/CamCalibration/analysis/analyze.py --all

STEREO FACE TRACKING
  argus_env/bin/python python_scripts/openCV/stereoCam/live_stereo_face.py

This uses exactly the detection method in python_scripts/PanTilt/FaceTracking.py:
  grayscale input
  PreTrainedModels/face.xml -> detectMultiScale(gray, 1.3, 5)
  faces ordered by area; centre = (x + w//2, y + h//2)
  PreTrainedModels/eye.xml -> detectMultiScale(face_gray), with blue eye overlays

The calibrated native resolution is retained, rather than resizing observations
to the original pan/tilt script's 320x240. Cameras stay fixed. This application
shares the capture, stereo matching, calibration, timing gates, XYZ readouts and
isometric plot with live_stereo.py; it does not import/run the servo-control script.
Up to six face candidates per view are geometrically matched; use R to isolate
the same face when several are visible. Both cameras must detect the same face
before XYZ is available. Positions refer to face-box centres, which can differ
between camera views and are approximate rather than fixed anatomical landmarks.
Existing residual/timing limits can suppress incompatible face-centre matches.

The face dashboard replaces HSV controls with face-tracking information and
detected-face region masks. S saves ROIs to face_settings.json, separately from
the color tracker's HSV settings. Q, R, C and T keep their usual behavior.
Optional --face-cascade / --eye-cascade choose cascade files; --face-scale-factor
and --face-min-neighbors override the defaults. All common replay/log/preview
options remain available; use --help for details.
