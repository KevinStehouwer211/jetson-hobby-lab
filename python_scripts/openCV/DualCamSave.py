from pathlib import Path
from threading import Event, Thread
import time

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

        self.capture = cv2.VideoCapture(src, cv2.CAP_V4L2)
        if not self.capture.isOpened():
            self.capture.release()
            raise RuntimeError(f"Could not open camera {src}")
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*capture_format))
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture.set(cv2.CAP_PROP_FPS, 30)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 4)
        self.thread = Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        try:
            while not self.stopped.is_set():
                success, frame = self.capture.read()
                if success and frame is not None:
                    self.frame = cv2.resize(frame, (self.width, self.height))
                else:
                    self.stopped.wait(0.01)
        except Exception as error:
            self.error = error

    def getFrame(self):
        if self.error is not None:
            raise RuntimeError(f"Camera failed: {self.output_path}") from self.error
        return self.frame

    def startRecording(self):
        # Open once so pausing/resuming continues in the same file.
        if self.writer is None:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.writer = cv2.VideoWriter(
                str(self.output_path), cv2.VideoWriter_fourcc(*"MJPG"),
                self.fps, (self.width, self.height))
            if not self.writer.isOpened():
                raise RuntimeError(f"Could not create video: {self.output_path}")

    def saveFrame(self, frame):
        self.writer.write(frame)

    def stop(self):
        self.stopped.set()
        self.thread.join()
        self.capture.release()
        if self.writer is not None:
            self.writer.release()
            print(f"Video saved to: {self.output_path}")


def main():
    dispW, dispH = 640, 480
    fps = 7  # Shared output FPS; camera capture is requested at 30 FPS.
    output_dir = Path(__file__).resolve().parents[0] / "saved_vids"
    cameras = []
    recording = False
    next_frame_time = 0
    print("SPACE: record/pause both cameras | Q: quit")

    try:
        # Camera indices: Dofbot = 0, dashcam = 2.
        dofbot = vStream(0, dispW, dispH, output_dir / "dofbot_wand.avi", fps, "YUYV")
        cameras.append(dofbot)
        dashcam = vStream(2, dispW, dispH, output_dir / "dashcam_wand.avi", fps, "MJPG")
        cameras.append(dashcam)

        while True:
            frame1 = dofbot.getFrame()
            frame2 = dashcam.getFrame()
            ready = frame1 is not None and frame2 is not None

            if ready:
                # One clock writes both files together, with equal frame counts.
                # A slower camera repeats its latest frame; exposures may differ.
                now = time.perf_counter()
                while recording and now >= next_frame_time:
                    dofbot.saveFrame(frame1)
                    dashcam.saveFrame(frame2)
                    next_frame_time += 1 / fps

                preview = np.hstack((frame1, frame2))
                status = "REC" if recording else "READY"
                cv2.putText(preview, f"Dofbot | {status} | {fps} output FPS", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(preview, "Dashcam", (dispW + 10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("ComboCam", preview)

            key = cv2.waitKey(1) & 0xFF
            if key == ord(" ") and ready:
                if not recording:
                    dofbot.startRecording()
                    dashcam.startRecording()
                    next_frame_time = time.perf_counter()
                recording = not recording
                print("Recording started" if recording else "Recording paused")
            elif key == ord("q"):
                break
    finally:
        for camera in cameras:
            camera.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
