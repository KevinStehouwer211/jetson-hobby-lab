"""Compare delivered camera rates without preview, resizing, or video writing.

Close other camera apps first. From the repository root:
argus_env/bin/python python_scripts/openCV/benchmark_camera.py
v4l2-ctl -d /dev/video0 --list-formats-ext

Rates measure frames delivered to this process, not exposure timestamps.
The default uses four buffers, matching the direct V4L2 test. To compare:
  --device /dev/video2 --formats YUYV --buffers 1 4 --seconds 20
Add --grab-only to skip image retrieval and BGR conversion.
Unsupported mode requests may fall back: check the negotiated settings in output.
"""
import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np


def benchmark(args, capture_format, buffers):
    cap = cv2.VideoCapture(args.device, cv2.CAP_V4L2)
    result = {'requested_format': capture_format, 'requested_width': args.width,
              'requested_height': args.height, 'requested_fps': args.fps,
              'requested_buffers': buffers,
              'measurement_mode': 'grab_only' if args.grab_only else 'decoded_read'}
    try:
        if not cap.isOpened():
            return {**result, 'error': 'Cannot open camera; check device and close other camera apps.'}
        settings = [(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*capture_format)),
                    (cv2.CAP_PROP_FRAME_WIDTH, args.width),
                    (cv2.CAP_PROP_FRAME_HEIGHT, args.height),
                    (cv2.CAP_PROP_FPS, args.fps), (cv2.CAP_PROP_BUFFERSIZE, buffers)]
        result['set_accepted'] = [bool(cap.set(key, value)) for key, value in settings]
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        result.update(negotiated_format=''.join(chr((fourcc >> (8*i)) & 255) for i in range(4)),
                      negotiated_width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                      negotiated_height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                      driver_reported_fps=cap.get(cv2.CAP_PROP_FPS),
                      negotiated_buffers=cap.get(cv2.CAP_PROP_BUFFERSIZE))

        def receive():
            if args.grab_only:
                return cap.grab(), None
            return cap.read()

        # Drain startup frames and allow auto exposure to settle.
        warmup_end = time.perf_counter() + 2
        while time.perf_counter() < warmup_end:
            ok, frame = receive()
            if not ok or (not args.grab_only and frame is None):
                return {**result, 'error': 'Camera failed during warmup.'}
        arrivals = []
        start = time.perf_counter()
        while time.perf_counter() - start < args.seconds:
            ok, frame = receive()
            if not ok or (not args.grab_only and frame is None):
                return {**result, 'error': 'Camera read failed during measurement.'}
            arrivals.append(time.perf_counter())
        elapsed = time.perf_counter() - start
        gaps = np.diff(arrivals)
        result.update(frames_received=len(arrivals), elapsed_seconds=elapsed,
                      delivered_fps=len(arrivals)/elapsed)
        if frame is not None:
            result['frame_shape'] = list(frame.shape)
        if len(gaps):
            result.update(median_interval_ms=float(np.median(gaps)*1000),
                          p95_interval_ms=float(np.quantile(gaps,.95)*1000),
                          max_interval_ms=float(gaps.max()*1000))
        return result
    finally:
        cap.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--device', default='/dev/video0')
    parser.add_argument('--width', type=int, default=640)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--fps', type=float, default=30)
    parser.add_argument('--seconds', type=float, default=10)
    parser.add_argument('--formats', nargs='+', default=['YUYV','MJPG'])
    parser.add_argument('--buffers', nargs='+', type=int, default=[4],
                        help='Capture buffer counts to test, sequentially (default: 4).')
    parser.add_argument('--grab-only', action='store_true',
                        help='Measure capture without retrieving/converting images.')
    parser.add_argument('--output', type=Path, help='Optional JSON results file.')
    args = parser.parse_args()
    if min(args.width,args.height,args.fps,args.seconds,*args.buffers) <= 0 or any(len(f)!=4 for f in args.formats):
        parser.error('Dimensions, fps, seconds and buffers must be positive; formats must have four characters.')
    results = []
    for capture_format in args.formats:
        for buffers in args.buffers:
            print(f'Testing {capture_format} at {args.width}x{args.height}, requesting {args.fps:g} fps, '
                  f'{buffers} buffers ({"grab only" if args.grab_only else "decoded read"})...', flush=True)
            result = benchmark(args,capture_format,buffers)
            results.append(result)
            print(json.dumps(result,indent=2),flush=True)
    if args.output:
        args.output.write_text(json.dumps(results,indent=2)+'\n')
    return 1 if all('error' in r for r in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
