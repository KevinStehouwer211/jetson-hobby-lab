"""Run: argus_env/bin/python python_scripts/openCV/stereoCam/test_stereo.py"""
import unittest
import ast
from pathlib import Path
from unittest.mock import Mock, patch
import cv2
import numpy as np

from calibration import ROOT, StereoCalibration, default_dlt, matching_orientation
from live_stereo import DEFAULT_HSV, MAXIMUM, Detection, annotate, detect_candidates, match_candidates
from face_detection import FaceDetector


class StereoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cal = StereoCalibration(ROOT/'intrinsics/camera-profile.txt', default_dlt())
        cls.point = np.array([0., -.1, -.2])

    def test_calibrated_distortion_and_y_origin_roundtrip(self):
        for delta in [np.zeros(3), np.array([.02, .05, .04]), np.array([-.02, -.03, -.05])]:
            point = self.point+delta
            pixels = self.cal.project(point)
            recovered = self.cal.triangulate(pixels)
            np.testing.assert_allclose(recovered.calibration_xyz, point, atol=1e-6)
            self.assertLess(recovered.rms_px, 1e-5)
            self.assertLess(self.cal.epipolar_error(pixels), 1e-3)
            self.assertTrue(np.all(recovered.halfwidth95 > 0))

    def test_red_blob_to_stereo_location_and_boxes(self):
        pixels = self.cal.project(self.point)
        candidates, frames = [], []
        for c in range(2):
            w, h = self.cal.sizes[c]
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.circle(frame, tuple(np.rint(pixels[c]).astype(int)), 10, (0, 0, 255), -1)
            # Blue should not be a red detection.
            cv2.circle(frame, (40, 40), 12, (255, 0, 0), -1)
            found, mask = detect_candidates(frame, DEFAULT_HSV)
            self.assertEqual(len(found), 1)
            self.assertEqual(mask[40, 40], 0)
            candidates.append(found)
            frames.append(frame)
        pair, location, status = match_candidates(self.cal, candidates)
        self.assertEqual(status, 'Tracking')
        self.assertIsNotNone(pair)
        np.testing.assert_allclose(location.xyz, self.point, atol=.01)
        preview = annotate(frames, candidates, pair, location, status, [25, 30], 5., [None, None], False)
        self.assertEqual(preview.shape, (580, 1280, 3))
        self.assertTrue(any(np.any(preview[100:] != np.hstack(frames), axis=2).ravel()))

    def test_missing_and_ambiguous_matches_do_not_produce_xyz(self):
        pixels = self.cal.project(self.point)
        detections = [Detection(p, (1, 1, 10, 10), 100.) for p in pixels]
        for candidate_set in [[[], [detections[1]]], [[detections[0]], []],
                              [[detections[0], detections[0]], [detections[1]]]]:
            pair, location, _ = match_candidates(self.cal, candidate_set)
            self.assertIsNone(pair)
            self.assertIsNone(location)

    def test_inconsistent_stereo_pair_rejected(self):
        pixels = self.cal.project(self.point)
        pixels[1, 1] += 100
        detections = [[Detection(p, (1, 1, 10, 10), 100.)] for p in pixels]
        self.assertIsNone(match_candidates(self.cal, detections)[1])

    def test_roi_keeps_full_frame_coordinates(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(frame, (100, 120), 10, (0, 0, 255), -1)
        cv2.circle(frame, (400, 200), 10, (0, 0, 255), -1)
        found, _ = detect_candidates(frame, DEFAULT_HSV, (70, 90, 60, 60))
        self.assertEqual(len(found), 1)
        np.testing.assert_allclose(found[0].center, [100, 120], atol=.1)

    def test_resolution_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            self.cal.validate_frame(np.zeros((240, 320, 3), dtype=np.uint8), 0)

    def test_reference_orientation_rotates_only_coordinates(self):
        path = matching_orientation(default_dlt())
        self.assertIsNotNone(path)
        oriented = StereoCalibration(self.cal.profile_path, self.cal.dlt_path, path)
        pixels = self.cal.project(self.point)
        result = oriented.triangulate(pixels)
        np.testing.assert_allclose(result.xyz, oriented.rotation@(self.point-oriented.origin), atol=1e-6)
        np.testing.assert_allclose(result.reprojected, pixels, atol=1e-5)

    def test_hsv_controls_match_original_script(self):
        original = Path(__file__).resolve().parent.parent/'HSV.py'
        controls = []
        for node in ast.walk(ast.parse(original.read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'createTrackbar':
                controls.append(tuple(ast.literal_eval(node.args[i]) for i in [0, 2, 3]))
        # Hue defaults intentionally select red; labels, order and limits stay identical.
        self.assertEqual([(name, maximum) for name, initial, maximum in controls], list(MAXIMUM.items()))

    def test_rgb_red_selected_and_green_blue_rejected(self):
        image = np.zeros((100, 240, 3), dtype=np.uint8)
        for center, bgr in [((40, 50), (0, 0, 255)), ((120, 50), (0, 255, 0)), ((200, 50), (255, 0, 0))]:
            cv2.circle(image, center, 12, bgr, -1)
        found, mask = detect_candidates(image, DEFAULT_HSV)
        self.assertEqual(len(found), 1)
        self.assertEqual(mask[50, 40], 255)
        self.assertEqual(mask[50, 120], 0)
        self.assertEqual(mask[50, 200], 0)

    def test_second_hue_range_is_combined_with_first(self):
        image = np.zeros((100, 240, 3), dtype=np.uint8)
        for center, hue in [((40, 50), 5), ((120, 50), 175), ((200, 50), 60)]:
            cv2.circle(image, center, 12, (hue, 220, 220), -1)
        bgr = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
        settings = {**DEFAULT_HSV, 'HUE lower': 0, 'HUE upper': 10,
                    'HUE2 lower': 170, 'HUE2 upper': 179}
        found, mask = detect_candidates(bgr, settings)
        self.assertEqual(len(found), 2)
        self.assertEqual(mask[50, 40], 255)
        self.assertEqual(mask[50, 120], 255)
        self.assertEqual(mask[50, 200], 0)

    def test_face_method_and_roi_coordinates(self):
        face, eye = Mock(), Mock()
        face.empty.return_value = eye.empty.return_value = False
        face.detectMultiScale.return_value = np.array([[5, 8, 40, 50], [10, 12, 20, 20]])
        eye.detectMultiScale.return_value = np.array([[8, 10, 7, 6]])
        with patch('face_detection.cv2.CascadeClassifier', side_effect=[face, eye]):
            detector = FaceDetector()
        frame = np.zeros((480, 640, 3), np.uint8)
        found, mask = detector(frame, roi=(100, 80, 150, 120))
        call = face.detectMultiScale.call_args
        self.assertEqual(call.args[0].shape, (120, 150))
        self.assertEqual(call.args[1:], (1.3, 5))
        self.assertEqual(found[0].box, (105, 88, 40, 50))
        np.testing.assert_array_equal(found[0].center, [125, 113])
        self.assertEqual(found[0].eyes, ((113, 98, 7, 6),))
        self.assertEqual(mask[100, 110], 255)
        self.assertEqual(mask[0, 0], 0)

    def test_face_detections_use_shared_stereo_reconstruction(self):
        face, eye = Mock(), Mock()
        face.empty.return_value = eye.empty.return_value = False
        eye.detectMultiScale.return_value = ()
        pixels = self.cal.project(self.point)
        face.detectMultiScale.side_effect = [np.array([[int(round(x))-20, int(round(y))-25, 40, 50]]) for x, y in pixels]
        with patch('face_detection.cv2.CascadeClassifier', side_effect=[face, eye]):
            detector = FaceDetector()
        frames = [np.zeros((480, 640, 3), np.uint8) for _ in range(2)]
        candidates = [detector(frame)[0] for frame in frames]
        pair, location, status = match_candidates(self.cal, candidates, target='face')
        self.assertEqual(status, 'Tracking')
        np.testing.assert_allclose(location.xyz, self.point, atol=.01)
        _, missing, message = match_candidates(self.cal, [[], candidates[1]], target='face')
        self.assertIsNone(missing)
        self.assertEqual(message, 'No face in cam1')

    def test_real_face_cascades_load_and_empty_scene_has_no_face(self):
        detector = FaceDetector()
        found, mask = detector(np.zeros((480, 640, 3), np.uint8))
        self.assertEqual(found, [])
        self.assertFalse(mask.any())


if __name__ == '__main__':
    unittest.main()
