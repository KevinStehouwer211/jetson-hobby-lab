import argparse
from collections import deque
import csv
from datetime import datetime
import json
from pathlib import Path
from threading import Event, Lock, Thread
import time
from zoneinfo import ZoneInfo

import cv2
import numpy as np


class vStream:
    def __init__(self, src, width, height, output_path, fps, capture_format):
        self.width = width
        self.height = height
        self.output_path = Path(output_path)
        self.fps = fps
        self.frame = None
        self.writer = None
        self.error = None
        self.stopped = Event()
        self.lock = Lock()
        self.sequence = 0
        self.received_at = None
        self.arrivals = deque(maxlen=90)
        self.last_saved_sequence = None
        self.repeats = 0

        self.capture = cv2.VideoCapture(src, cv2.CAP_V4L2)
        if not self.capture.isOpened():
            self.capture.release()
            raise RuntimeError(f"Could not open camera {src}")
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*capture_format))
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture.set(cv2.CAP_PROP_FPS, 30)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 4)
        fourcc = int(self.capture.get(cv2.CAP_PROP_FOURCC))
        negotiated = ''.join(chr((fourcc >> (8*i)) & 255) for i in range(4))
        print(f'Camera {src}: {negotiated}, '
              f'{self.capture.get(cv2.CAP_PROP_FRAME_WIDTH):g}x'
              f'{self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT):g}, '
              f'{self.capture.get(cv2.CAP_PROP_FPS):g} driver FPS, '
              f'{self.capture.get(cv2.CAP_PROP_BUFFERSIZE):g} buffers')
        self.thread = Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        try:
            while not self.stopped.is_set():
                success, frame = self.capture.read()
                if success and frame is not None:
                    received_at = time.perf_counter()
                    if frame.shape[:2] != (self.height, self.width):
                        raise RuntimeError(f'Unexpected camera resolution: {frame.shape}; '
                                           'check capture settings and calibration')
                    with self.lock:
                        self.frame = frame
                        self.sequence += 1
                        self.received_at = received_at
                        self.arrivals.append(received_at)
                else:
                    self.stopped.wait(0.01)
        except Exception as error:
            self.error = error

    def snapshot(self):
        if self.error is not None:
            raise RuntimeError(f"Camera failed: {self.output_path}") from self.error
        with self.lock:
            rate = ((len(self.arrivals)-1) / (self.arrivals[-1]-self.arrivals[0])
                    if len(self.arrivals)>1 and self.arrivals[-1]>self.arrivals[0] else 0.)
            return self.frame, self.sequence, self.received_at, rate

    def startRecording(self):
        # Open once so pausing/resuming continues in the same file.
        if self.writer is None:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.writer = cv2.VideoWriter(
                str(self.output_path), cv2.VideoWriter_fourcc(*"MJPG"),
                self.fps, (self.width, self.height))
            if not self.writer.isOpened():
                raise RuntimeError(f"Could not create video: {self.output_path}")

    def saveFrame(self, frame, sequence):
        self.writer.write(frame)
        repeated = sequence == self.last_saved_sequence
        self.repeats += int(repeated)
        self.last_saved_sequence = sequence
        return repeated

    def stop(self):
        self.stopped.set()
        self.thread.join()
        self.capture.release()
        if self.writer is not None:
            self.writer.release()
            print(f"Video saved to: {self.output_path} | repeated source frames: {self.repeats}")


def create_recording_dir(root, kind, day):
    date_dir = root / day
    date_dir.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        folder = date_dir / f'{kind}_{number:02d}'
        try:
            folder.mkdir()
            return folder
        except FileExistsError:
            number += 1


def main():
    parser = argparse.ArgumentParser(description='Record both cameras with four capture buffers and arrival timing logs.')
    parser.add_argument('--fps', type=float, default=25,
                        help='Shared AVI output rate (default: 25); capture requests 30 fps.')
    parser.add_argument('--kind', choices=['trial', 'wand_calibration'], default='trial',
                        help='Recording folder type (default: trial).')
    args = parser.parse_args()
    if not np.isfinite(args.fps) or args.fps <= 0:
        parser.error('--fps must be finite and positive')
    dispW, dispH = 640, 480
    fps = args.fps
    calibration_root = Path(__file__).resolve().parent / 'CamCalibration' 
    output_dir = None
    cameras = []
    recording = False
    next_frame_time = 0
    timing_file = None
    frame_index = 0
    segment = 0
    print("SPACE: record/pause both cameras | Q: quit")

    try:
        # Camera indices: Dofbot = 0, dashcam = 2.
        dofbot = vStream(0, dispW, dispH, calibration_root / 'cam2.avi', fps, 'YUYV')
        cameras.append(dofbot)
        dashcam = vStream(2, dispW, dispH, calibration_root / 'cam1.avi', fps, 'MJPG')
        cameras.append(dashcam)

        while True:
            frame1, seq1, arrival1, rate1 = dofbot.snapshot()
            frame2, seq2, arrival2, rate2 = dashcam.snapshot()
            ready = frame1 is not None and frame2 is not None

            if ready:
                # One clock writes both files together, with equal frame counts.
                # A slower camera repeats its latest frame; exposures may differ.
                now = time.perf_counter()
                while recording and now >= next_frame_time:
                    repeat1 = dofbot.saveFrame(frame1, seq1)
                    repeat2 = dashcam.saveFrame(frame2, seq2)
                    frame_index += 1
                    timing.writerow([frame_index, segment, (frame_index-1)/fps,
                                     next_frame_time, now, seq1, seq2, arrival1, arrival2,
                                     now-arrival1, now-arrival2, repeat1, repeat2,
                                     arrival1-arrival2])
                    next_frame_time += 1 / fps

                preview = np.hstack((frame1, frame2))
                status = "REC" if recording else "READY"
                for x, label, rate, repeats, age in [(10,'Dofbot',rate1,dofbot.repeats,now-arrival1),
                                                    (dispW+10,'Dashcam',rate2,dashcam.repeats,now-arrival2)]:
                    color = (0,255,0) if rate >= fps*.95 and age < 2/fps else (0,165,255)
                    cv2.putText(preview, f'{label} | {status} | capture {rate:.1f} fps', (x,30),
                                cv2.FONT_HERSHEY_SIMPLEX, .6, color, 2)
                    cv2.putText(preview, f'Output {fps:g} fps | repeats {repeats} | age {age*1000:.0f} ms', (x,55),
                                cv2.FONT_HERSHEY_SIMPLEX, .5, color, 1)
                cv2.imshow("ComboCam", preview)

            key = cv2.waitKey(1) & 0xFF
            if key == ord(" ") and ready:
                if not recording:
                    if output_dir is None:
                        started = datetime.now(ZoneInfo('Europe/Amsterdam'))
                        output_dir = create_recording_dir(calibration_root, args.kind, started.date().isoformat())
                        dofbot.output_path = output_dir / 'cam2.avi'
                        dashcam.output_path = output_dir / 'cam1.avi'
                        (output_dir/'recording.json').write_text(json.dumps({
                            'started_at': started.isoformat(), 'kind': args.kind,
                            'output_fps': fps, 'resolution': [dispW, dispH],
                            'cameras': {
                                'cam1': {'name': 'Dashcam', 'device': '/dev/video2', 'file': 'cam1.avi', 'capture_format': 'MJPG'},
                                'cam2': {'name': 'Dofbot', 'device': '/dev/video0', 'file': 'cam2.avi', 'capture_format': 'YUYV'}},
                            'shared_intrinsics': str(calibration_root/'intrinsics/camera-profile.txt'),
                            'wand_calibration': None,
                            'note': 'Select the applicable wand calibration in Argus; equal output frame counts do not establish synchronized exposures.'
                        }, indent=2)+'\n')
                    dofbot.startRecording()
                    dashcam.startRecording()
                    if timing_file is None:
                        timing_file = (output_dir/'frame_timing.csv').open('w', newline='')
                        timing = csv.writer(timing_file)
                        timing.writerow(['output_frame','segment','video_time_s','scheduled_monotonic_s',
                                         'write_loop_monotonic_s','dofbot_source_sequence','dashcam_source_sequence',
                                         'dofbot_arrival_monotonic_s','dashcam_arrival_monotonic_s',
                                         'dofbot_frame_age_s','dashcam_frame_age_s',
                                         'dofbot_repeated','dashcam_repeated','arrival_difference_s'])
                        (output_dir/'timing_notes.txt').write_text(
                            f'Output FPS: {fps:g}; capture requests 30 FPS; four buffers per camera.\n'
                            'Arrival times use the host monotonic clock immediately after OpenCV read().\n'
                            'They are not sensor exposure timestamps and do not establish synchronization.\n'
                            'Source sequences count successful reads; repeats flag reuse of the same read.\n'
                            'Identical exposures returned as separate reads cannot be detected this way.\n'
                            'Late output slots repeat the latest frames and are flagged in the CSV.\n'
                            'Segments identify recording resumes; pauses are omitted from AVI time.\n')
                        print(f'Recording folder: {output_dir}')
                    segment += 1
                    next_frame_time = time.perf_counter()
                elif timing_file is not None:
                    timing_file.flush()
                recording = not recording
                print("Recording started" if recording else "Recording paused")
            elif key == ord("q"):
                break
    finally:
        if timing_file is not None:
            timing_file.close()
        for camera in cameras:
            camera.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
