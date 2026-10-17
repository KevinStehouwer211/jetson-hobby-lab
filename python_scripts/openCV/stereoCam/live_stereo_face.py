"""Live stereo face-box centers using FaceTracking.py's Haar face/eye method.

Run: argus_env/bin/python python_scripts/openCV/stereoCam/live_stereo_face.py
Uses the same calibration, quality gates, XYZ readouts and live 3D dashboard as
live_stereo.py. Both cameras must see the same face; R selects search ROIs.
"""
from numpy.linalg import LinAlgError
from live_stereo import main


if __name__ == '__main__':
    try:
        main(mode='face')
    except (ValueError, OSError, RuntimeError, LinAlgError) as error:
        raise SystemExit(str(error))
