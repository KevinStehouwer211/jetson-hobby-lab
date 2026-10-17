"""Live red-object stereo tracking with adjustable HSV and calibrated XYZ.

Run from the repository root:
  argus_env/bin/python python_scripts/openCV/stereoCam/live_stereo.py
Q/Esc: quit. S: save HSV/ROI settings. R: select an ROI in each view. C: clear ROIs.
Camera 1 is Dashcam (/dev/video2); camera 2 is Dofbot (/dev/video0).
"""
import argparse
from dataclasses import dataclass
import csv
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

from calibration import ROOT, StereoCalibration, default_dlt, matching_orientation

# Reuse the recorder's threaded V4L2 capture, four buffers and measured frame rates.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from python_scripts.openCV.stereoCam.DualCamSave import vStream


# Same eight controls as HSV.py; hue defaults target RGB red (255, 0, 0).
DEFAULT_HSV = {'HUE lower': 0, 'HUE upper': 10, 'HUE2 lower': 170, 'HUE2 upper': 179,
               'SAT lower': 100, 'SAT upper': 255, 'VALUE lower': 100, 'VALUE upper': 255}
MAXIMUM = {key: 179 if key.startswith('HUE') else 255 for key in DEFAULT_HSV}
FILTER_DEFAULTS = {'MIN area': 40, 'MAX area': 20000, 'Kernel': 3}
FILTER_LIMITS = {'MIN area': 10000, 'MAX area': 100000, 'Kernel': 15}
NAMES = ['cam1 Dashcam', 'cam2 Dofbot']


@dataclass
class Detection:
    center: np.ndarray
    box: tuple
    area: float


def detect_candidates(frame, settings, roi=None):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    low = [settings['HUE lower'], settings['SAT lower'], settings['VALUE lower']]
    high = [settings['HUE upper'], settings['SAT upper'], settings['VALUE upper']]
    low2 = [settings.get('HUE2 lower', low[0]), *low[1:]]
    high2 = [settings.get('HUE2 upper', high[0]), *high[1:]]
    # Same union of two HSV masks as HSV.py, including shared saturation/value bounds.
    mask = cv2.inRange(hsv, np.array(low), np.array(high))
    mask |= cv2.inRange(hsv, np.array(low2), np.array(high2))
    k = max(1, int(settings.get('Kernel', FILTER_DEFAULTS['Kernel']))) | 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    if roi is not None:
        x, y, w, h = map(int, roi)
        keep = np.zeros_like(mask)
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(mask.shape[1], x+w), min(mask.shape[0], y+h)
        if x1 > x0 and y1 > y0:
            keep[y0:y1, x0:x1] = mask[y0:y1, x0:x1]
        mask = keep
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if not max(1, settings.get('MIN area', 40)) <= area <= settings.get('MAX area', 20000):
            continue
        moments = cv2.moments(contour)
        if moments['m00'] <= 0:
            continue
        center = np.array([moments['m10']/moments['m00'], moments['m01']/moments['m00']])
        candidates.append(Detection(center, cv2.boundingRect(contour), area))
    return sorted(candidates, key=lambda d: d.area, reverse=True)[:6], mask


def match_candidates(calibration, candidates, max_error=5., ambiguity_margin=.5, sigma=2., target='red object'):
    if not candidates[0] or not candidates[1]:
        missing = 'cam1' if not candidates[0] else 'cam2'
        return None, None, f'No {target} in {missing}'
    ranked = []
    for left in candidates[0]:
        for right in candidates[1]:
            pixels = np.array([left.center, right.center])
            error = calibration.epipolar_error(pixels)
            if np.isfinite(error) and error <= max_error:
                ranked.append((error, left, right))
    ranked.sort(key=lambda r: r[0])
    if not ranked:
        return None, None, f'{target.capitalize()} detections do not match stereo geometry'
    if len(ranked) > 1 and ranked[1][0]-ranked[0][0] < ambiguity_margin:
        return None, None, ('Ambiguous faces: select matching-face ROIs (R)' if target == 'face' else
                            'Ambiguous red objects: narrow HSV or select ROIs (R)')
    _, left, right = ranked[0]
    try:
        location = calibration.triangulate([left.center, right.center], sigma)
    except (ValueError, np.linalg.LinAlgError) as error:
        return None, None, str(error)
    if location.rms_px > max_error:
        return None, None, f'Poor stereo fit: {location.rms_px:.1f} px RMS'
    if location.ray_angle_deg < 1.:
        return None, None, 'Stereo rays nearly parallel: depth unreliable'
    return (left, right), location, 'Tracking'


def annotate(frames, candidates, match, location, status, rates, skew_ms, rois, rotated, target='red object'):
    images = [image.copy() for image in frames]
    for c, image in enumerate(images):
        for detection in candidates[c]:
            x, y, w, h = detection.box
            cv2.rectangle(image, (x, y), (x+w, y+h), (140, 140, 140), 1)
            for ex, ey, ew, eh in getattr(detection, 'eyes', ()):
                cv2.circle(image, (ex+ew//2, ey+eh//2), max(1, eh//2), (255, 0, 0), 1)
        if rois[c] is not None:
            x, y, w, h = map(int, rois[c])
            cv2.rectangle(image, (x, y), (x+w, y+h), (255, 160, 0), 1)
        if match is not None:
            detection = match[c]
            x, y, w, h = detection.box
            cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.drawMarker(image, tuple(np.rint(detection.center).astype(int)), (0, 255, 255),
                           cv2.MARKER_CROSS, 13, 2)
            line = 'XYZ: ' + ' '.join(f'{v:+.3f}' for v in location.xyz) + ' m'
            cv2.putText(image, line, (max(5, min(x, image.shape[1]-390)), min(y+h+20, image.shape[0]-10)),
                        cv2.FONT_HERSHEY_SIMPLEX, .48, (0, 255, 0), 1, cv2.LINE_AA)
    view = np.hstack(images)
    banner = np.zeros((100, view.shape[1], 3), dtype=np.uint8)
    color = (0, 255, 0) if location is not None else (0, 190, 255)
    cv2.putText(banner, status, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, .6, color, 1, cv2.LINE_AA)
    if location is not None:
        uncertainty = 'Conditional 95% +/- XYZ: ' + ' '.join(f'{v*1000:.1f}' for v in location.halfwidth95) + ' mm'
        detail = f'{uncertainty} | fit {location.rms_px:.2f} px'
    else:
        detail = f'XYZ unavailable until a usable {target} match is visible in both cameras'
    cv2.putText(banner, detail, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, .48, (220, 220, 220), 1)
    timing = f'host arrival gap {skew_ms:.1f} ms' if skew_ms is not None else 'replay: exposure synchronization unknown'
    axes = '+Z up (reference fall)' if rotated else 'original calibration axes'
    cv2.putText(banner, f'{NAMES[0]} {rates[0]:.1f} fps | {NAMES[1]} {rates[1]:.1f} fps | {timing} | {axes}',
                (10, 68), cv2.FONT_HERSHEY_SIMPLEX, .43, (220, 220, 220), 1)
    cv2.putText(banner, 'Q: quit | S: save HSV | R: select object ROIs | C: clear ROIs',
                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, .43, (220, 220, 220), 1)
    return np.vstack([banner, view])


def device(value):
    return int(value) if value.isdigit() else value


def window_size(value):
    try:
        width, height = map(int, value.lower().split('x'))
        if width < 900 or height < 600:
            raise ValueError
        return width, height
    except ValueError:
        raise argparse.ArgumentTypeError('Use WIDTHxHEIGHT, at least 900x600 (default: fit screen).')


def main(mode='color'):
    face_mode = mode == 'face'
    target = 'face' if face_mode else 'red object'
    description = ('Live stereo face tracking with the grayscale Haar face/eye method from FaceTracking.py. '
                   'Bounding-box centers are reconstructed in 3D; cameras remain fixed.' if face_mode else __doc__)
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cam1', default='/dev/video2', help='Dashcam device (calibration camera 1).')
    parser.add_argument('--cam2', default='/dev/video0', help='Dofbot device (calibration camera 2).')
    parser.add_argument('--dlt', type=Path, help='DLT CSV; default is the latest dated wand calibration.')
    parser.add_argument('--profile', type=Path, default=ROOT/'intrinsics/camera-profile.txt')
    parser.add_argument('--orientation', type=Path, help='Display rotation JSON; default finds a matching analyzed trial.')
    parser.add_argument('--calibration-frame', action='store_true', help='Show original calibration coordinates instead of the fall-aligned frame.')
    parser.add_argument('--settings', type=Path, default=Path(__file__).with_name('face_settings.json' if face_mode else 'hsv_settings.json'))
    parser.add_argument('--max-skew-ms', type=float, default=25., help='Maximum host arrival gap (not an exposure timestamp), default 25 ms.')
    parser.add_argument('--max-age-ms', type=float, default=150., help='Reject frames older than this on the host.')
    parser.add_argument('--max-error-px', type=float, default=5., help='Maximum epipolar and raw reprojection RMS diagnostic.')
    parser.add_argument('--sigma-px', type=float, default=2., help='Assumed pixel noise for conditional uncertainty.')
    parser.add_argument('--ambiguity-margin', type=float, default=.5, help='Reject stereo pairs whose epipolar scores differ by less than this.')
    parser.add_argument('--videos', nargs=2, type=Path, metavar=('CAM1_VIDEO', 'CAM2_VIDEO'), help='Replay calibrated-size videos instead of live capture.')
    parser.add_argument('--headless', action='store_true', help='Replay without GUI, for testing; requires --videos.')
    parser.add_argument('--frames', type=int, default=0, help='Stop after N processed pairs (0: until quit/end).')
    parser.add_argument('--preview', type=Path, help='Save the last annotated pair as a PNG.')
    parser.add_argument('--log', type=Path, help='Optional CSV of current locations and rejection statuses.')
    parser.add_argument('--window-size', type=window_size, help='Optional dashboard size, e.g. 1366x768; default maximizes to the available screen.')
    parser.add_argument('--plot-fps', type=float, default=6., help='3D plot refresh rate, independent of camera capture (default: 6).')
    if face_mode:
        from face_detection import FaceDetector, MODELS
        parser.add_argument('--face-cascade', type=Path, default=MODELS/'face.xml')
        parser.add_argument('--eye-cascade', type=Path, default=MODELS/'eye.xml')
        parser.add_argument('--face-scale-factor', type=float, default=1.3)
        parser.add_argument('--face-min-neighbors', type=int, default=5)
    args = parser.parse_args()
    detector = (FaceDetector(args.face_cascade, args.eye_cascade, args.face_scale_factor,
                             args.face_min_neighbors) if face_mode else detect_candidates)
    values = [args.max_skew_ms, args.max_age_ms, args.max_error_px, args.sigma_px, args.plot_fps]
    if any(not np.isfinite(v) or v <= 0 for v in values) or args.frames < 0:
        parser.error('Timing, error and noise limits must be finite/positive; frames must be nonnegative.')
    if not np.isfinite(args.ambiguity_margin) or args.ambiguity_margin < 0:
        parser.error('--ambiguity-margin must be finite and nonnegative.')
    if args.headless and not args.videos:
        parser.error('--headless requires --videos.')
    if args.calibration_frame and args.orientation:
        parser.error('Choose --calibration-frame or --orientation, not both.')
    dlt = args.dlt or default_dlt()
    orientation = None if args.calibration_frame else (args.orientation or matching_orientation(dlt))
    calibration = StereoCalibration(args.profile, dlt, orientation)
    print(f'Intrinsics: {calibration.profile_path}\nDLT: {calibration.dlt_path}\n'
          f'Coordinates: {orientation or "original calibration frame"}', flush=True)
    print('3D units follow the wand calibration (current wand: 0.165 m). '
          'Host timing and pixel-noise bounds do not measure total accuracy.', flush=True)
    settings = [{**DEFAULT_HSV, **FILTER_DEFAULTS} for _ in range(2)]
    rois = [None, None]
    if args.settings.exists():
        saved = json.loads(args.settings.read_text())
        for c in range(2):
            limits = {**MAXIMUM, **FILTER_LIMITS}
            previous = saved.get(f'cam{c+1}', {})
            settings[c].update({k: max(0, min(limits[k], int(v))) for k, v in previous.items() if k in limits})
            # Older saved settings had one hue range: duplicate it to preserve their mask.
            for bound in ['lower', 'upper']:
                if 'HUE2 '+bound not in previous:
                    settings[c]['HUE2 '+bound] = settings[c]['HUE '+bound]
        rois = saved.get('rois', rois)
        if len(rois) != 2 or any(r is not None and (len(r) != 4 or any(not isinstance(v, (int, float)) or not np.isfinite(v) for v in r)) for r in rois):
            raise ValueError('Invalid saved ROIs; remove or repair the settings file.')
    dashboard = None
    if not args.headless:
        from dashboard import StereoDashboard
        dashboard = StereoDashboard(settings, MAXIMUM, orientation is not None, args.plot_fps, args.window_size,
                                    mode=mode)

    def handle_actions():
        for action in dashboard.poll():
            if isinstance(action, tuple):
                _, camera, rectangle = action
                rois[camera] = list(rectangle)
            elif action == 'q':
                return False
            elif action == 's':
                # Read controls at save time, including edits since the last processed frame.
                for c, values in enumerate(dashboard.settings()):
                    settings[c].update(values)
                args.settings.parent.mkdir(parents=True, exist_ok=True)
                saved = {'rois': rois} if face_mode else {'cam1': settings[0], 'cam2': settings[1], 'rois': rois}
                args.settings.write_text(json.dumps(saved, indent=2)+'\n')
                dashboard.hint.setText('Face search ROIs saved.' if face_mode else 'HSV settings and ROIs saved.')
                print(f'Saved settings: {args.settings}', flush=True)
            elif action == 'c':
                rois[:] = [None, None]
                dashboard.clear_rois()
            elif action == 'r':
                dashboard.select_rois()
            elif action == 't':
                dashboard.plot.clear()
        return True
    streams, replay = [], []
    logfile = None
    preview = None
    processed, valid = 0, 0
    last_token = None
    try:
        if args.log:
            args.log.parent.mkdir(parents=True, exist_ok=True)
            logfile = args.log.open('w', newline='')
            writer = csv.writer(logfile)
            writer.writerow(['pair', 'status', 'x_m', 'y_m', 'z_m', 'x_95_halfwidth_m', 'y_95_halfwidth_m',
                             'z_95_halfwidth_m', 'rms_px', 'host_arrival_gap_ms'])
        if args.videos:
            replay = [cv2.VideoCapture(str(path)) for path in args.videos]
            if not all(cap.isOpened() for cap in replay):
                raise ValueError('Could not open both replay videos.')
            rates = [cap.get(cv2.CAP_PROP_FPS) for cap in replay]
            if rates[0] <= 0 or not np.isclose(rates[0], rates[1]):
                raise ValueError('Replay videos need matching positive frame rates.')
        else:
            for c, source in enumerate([args.cam1, args.cam2]):
                w, h = map(int, calibration.sizes[c])
                streams.append(vStream(device(source), w, h, ROOT/f'cam{c+1}.avi', 25., ['MJPG', 'YUYV'][c]))
        started = time.perf_counter()
        next_replay = started
        while True:
            if dashboard and not handle_actions():
                break
            if args.videos and dashboard and time.perf_counter() < next_replay:
                time.sleep(max(0., min(.01, next_replay-time.perf_counter())))
                continue
            if args.videos:
                pairs = [cap.read() for cap in replay]
                if not all(ok and frame is not None for ok, frame in pairs):
                    break
                frames = [frame for _, frame in pairs]
                skew, age = None, 0.
                token = processed + 1
                next_replay = max(next_replay+1/rates[0], time.perf_counter())
            else:
                snapshots = [stream.snapshot() for stream in streams]
                if any(s[0] is None for s in snapshots):
                    if time.perf_counter()-started > 10:
                        raise ValueError('No frames from both cameras within ten seconds.')
                    time.sleep(.01)
                    continue
                frames = [s[0] for s in snapshots]
                rates = [s[3] for s in snapshots]
                now = time.perf_counter()
                skew = abs(snapshots[0][2]-snapshots[1][2])*1000
                age = max(now-s[2] for s in snapshots)*1000
                token = tuple(s[1] for s in snapshots)
            for c in range(2):
                calibration.validate_frame(frames[c], c)
            if dashboard:
                for c, values in enumerate(dashboard.settings()):
                    settings[c].update(values)
            detections = [detector(frames[c], settings[c], rois[c]) for c in range(2)]
            candidates = [d[0] for d in detections]
            match, location = None, None
            if age > args.max_age_ms:
                status = f'Stale capture ({age:.0f} ms): XYZ unavailable'
            elif skew is not None and skew > args.max_skew_ms:
                status = f'Frames too far apart ({skew:.1f} ms): XYZ unavailable'
            else:
                match, location, status = match_candidates(calibration, candidates, args.max_error_px,
                                                           args.ambiguity_margin, args.sigma_px, target=target)
            preview = annotate(frames, candidates, match, location, status, rates, skew, rois,
                               orientation is not None, target=target)
            new_pair = token != last_token
            if new_pair:
                processed += 1
                valid += int(location is not None)
                if logfile:
                    writer.writerow([processed, status, *(location.xyz if location else ['', '', '']),
                                     *(location.halfwidth95 if location else ['', '', '']),
                                     location.rms_px if location else '', skew if skew is not None else ''])
                last_token = token
            if dashboard:
                dashboard.update(preview, [d[1] for d in detections], location, status, rates, skew, new_pair)
            if args.frames and processed >= args.frames:
                break
    finally:
        if logfile:
            logfile.close()
        for stream in streams:
            stream.stop()
        for cap in replay:
            cap.release()
        if args.preview and preview is not None:
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            saved = dashboard.save_preview(args.preview) if dashboard else cv2.imwrite(str(args.preview), preview)
            if not saved:
                raise ValueError(f'Cannot save preview to {args.preview}')
        if dashboard:
            dashboard.close()
    print(f'Processed {processed} frame pairs; {valid} accepted 3D matches.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, np.linalg.LinAlgError) as error:
        raise SystemExit(str(error))
