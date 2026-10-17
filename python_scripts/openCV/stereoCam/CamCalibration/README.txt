CAMERA CALIBRATION PROJECT

intrinsics/
  camera-profile.txt            Shared Argus intrinsics (camera order: Dashcam, Dofbot)
  DashCam/                      Dashcam Patterns/Calibrate files and calibration.avi
  Dofbot/                       Dofbot Patterns/Calibrate files and calibration.avi
analysis/
  analyze.py                    One shared analysis script for every trial
2026-10-17/
  wand_calibration_01/
    cam1.avi                    Dashcam wand recording
    cam2.avi                    Dofbot wand recording
    wandpts-*                   Paired wand tracks and calibrated camera/DLT outputs
    unpairedpts-*               Unpaired tracks from the same recording
    referencepts-*              Reference tracks from the same recording
  trial_01/
    cam1.avi, cam2.avi           Original free-fall recording (7 fps)
    freefalltest-*              Argus tracks, XYZ points and uncertainty exports
    analysis/                   Generated reconstruction, figures and report
  trial_02/
    cam1.avi, cam2.avi           Later recording, formerly capture_20261017_120622_660993
    frame_timing.csv
    timing_notes.txt
    analysis/                   Generated results, using the shared script
  trial_03/
    cam1.avi, cam2.avi
    freefalltest3-*              Argus tracking and reconstruction exports
    analysis/                   Generated results, using the shared script

Camera numbering stays consistent throughout the project:
  cam1 = Dashcam, currently /dev/video2
  cam2 = Dofbot, currently /dev/video0
USB device numbers can change after reconnecting cameras; verify their identities.
The recorder currently supports these two cameras. No third camera file is invented.

Existing AVI recordings were moved and renamed without transcoding. Their binary
contents, frame rates and frame counts are unchanged. file-relocations.json records
old/new paths and hashes before the move. Argus YAML paths were updated; reopen
the relocated *-config.yaml files rather than using an already-open old project.
Paired, unpaired and reference projects remain beside their shared wand videos.

FROM THE REPOSITORY ROOT:
  argus_env/bin/python python_scripts/openCV/DualCamSave.py --fps 25
  argus_env/bin/python python_scripts/openCV/DualCamSave.py --fps 25 --kind wand_calibration

The first Space press creates today's Europe/Amsterdam date folder and the next
unused trial_NN or wand_calibration_NN folder. Pause/resume stays in the same folder.
cam1.avi is always Dashcam and cam2.avi Dofbot. Existing sessions are never reused.
Each new session includes recording.json and frame_timing.csv. Select the applicable
wand calibration when opening trials in Argus; it is not chosen automatically.
Capture arrival timing is not a measurement of sensor exposure synchronization.

SHARED ANALYSIS — FROM THE REPOSITORY ROOT:
  argus_env/bin/python python_scripts/openCV/stereoCam/CamCalibration/analysis/analyze.py --all
  argus_env/bin/python python_scripts/openCV/stereoCam/CamCalibration/analysis/analyze.py 2026-10-17/trial_03

Only analysis/analyze.py contains the analysis code. Each trial/analysis/ folder
contains generated outputs, not another copy of the script. Re-running replaces
that trial's generated plots, CSVs and report; source Argus files remain unchanged.
The trial_01 results now use this same output location rather than a nested date folder.

The script reads video paths, tracking points, camera profile and DLT calibration
from the trial's *-config.yaml, and derives FPS from the videos. Tests with no host
timing log are supported; timing remains unknown rather than assumed synchronized.
It supports the current two-camera, one-track pinhole projects. Nonzero camera
offsets require explicit alignment and are rejected instead of silently ignored.

The default focus window is the last run of at least three consecutive stereo
samples. This is a plotting/orientation choice, not detection of physical free fall.
All marked stereo points remain in the full-track plots and CSV. Override it for
one test with --fall-frames START:END (1-based, inclusive); for example:
  argus_env/bin/python python_scripts/openCV/stereoCam/CamCalibration/analysis/analyze.py 2026-10-17/trial_03 --fall-frames 130:139

Use --sigma-px VALUE to change assumed pixel-marking noise (default: 2).
Use --no-animation for static outputs only; an existing GIF is left untouched.
When a trial contains multiple Argus project files, pass the desired config path
instead of its trial folder. --all processes trial folders with a single project.

Fall plot convention: show upward as +Z and the observed fall toward -Z, with
an orthographic isometric 3D view and cam1 (Dashcam) image-right as +X. Preserve
original calibration coordinates and record any display rotation in orientation.json.
When vertical is inferred from the fall, label that assumption; it is not an
independent measurement of gravity. Rotate camera locations and uncertainty
covariances with the points. Every test uses this convention through the shared script.
Different tests infer their display frames independently: use calibration_* CSV
columns when comparing positions in the original shared calibration coordinates.
