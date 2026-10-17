"""Argus pinhole/DLT stereo geometry shared by the live color tracker.

Argus points use bottom-left pixel Y; OpenCV frames use top-left Y.
Public observation/projection methods here use OpenCV pixels.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares


ROOT = Path(__file__).resolve().parent / 'CamCalibration'


def default_dlt():
    files = sorted(ROOT.glob('*/wand_calibration_*/*-dlt-coefficients.csv'))
    if not files:
        raise ValueError('No wand DLT calibration found; supply --dlt PATH.')
    return files[-1]


def matching_orientation(dlt):
    """Use an existing display rotation only when it references this exact DLT."""
    digest = hashlib.sha256(Path(dlt).read_bytes()).hexdigest()
    for orientation in sorted(ROOT.glob('*/trial_*/analysis/orientation.json'), reverse=True):
        manifest = orientation.with_name('input_manifest.json')
        if not manifest.exists():
            continue
        entries = json.loads(manifest.read_text())
        if any(Path(e['path']).name == Path(dlt).name and e['sha256'] == digest for e in entries):
            return orientation
    return None


@dataclass
class Location:
    calibration_xyz: np.ndarray
    xyz: np.ndarray
    halfwidth95: np.ndarray
    rms_px: float
    ray_angle_deg: float
    reprojected: np.ndarray


class StereoCalibration:
    def __init__(self, profile, dlt, orientation=None):
        self.profile_path = Path(profile).resolve()
        self.dlt_path = Path(dlt).resolve()
        self.profile = np.loadtxt(self.profile_path)
        coeff = np.loadtxt(self.dlt_path, delimiter=',')
        if self.profile.shape != (2, 12) or coeff.shape != (11, 2):
            raise ValueError('Expected two native 12-column Argus profiles and an 11x2 DLT CSV.')
        if not np.isfinite(self.profile).all() or not np.isfinite(coeff).all():
            raise ValueError('Calibration contains nonfinite values.')
        self.sizes = self.profile[:, 2:4].astype(int)
        if (self.sizes <= 0).any() or (self.profile[:, 1] <= 0).any() or (self.profile[:, 6] <= 0).any():
            raise ValueError('Invalid image sizes or focal length/aspect ratio in camera profile.')
        self.P = np.array([np.r_[c, 1.].reshape(3, 4) for c in coeff.T])
        self.K = np.array([[[r[1], 0., r[4]], [0., r[1]*r[6], r[5]], [0., 0., 1.]] for r in self.profile])
        self.dist = self.profile[:, -5:]
        self.centers = np.array([-np.linalg.solve(p[:, :3], p[:, 3]) for p in self.P])
        # Fundamental matrix derived from calibrated cameras, in undistorted Argus pixels.
        epipole = self.P[1] @ np.r_[self.centers[0], 1.]
        a, b, c = epipole
        cross = np.array([[0., -c, b], [c, 0., -a], [-b, a, 0.]])
        self.F = cross @ self.P[1] @ np.linalg.pinv(self.P[0])
        norm = np.linalg.norm(self.F)
        if norm < 1e-12:
            raise ValueError('Degenerate stereo camera geometry.')
        self.F /= norm
        self.rotation = np.eye(3)
        self.origin = np.zeros(3)
        self.orientation_path = None
        if orientation:
            self.orientation_path = Path(orientation).resolve()
            data = json.loads(self.orientation_path.read_text())
            self.rotation = np.array(data['rotation'], dtype=float)
            self.origin = np.array(data['origin_calibration_m'], dtype=float)
            if (self.rotation.shape != (3, 3) or self.origin.shape != (3,) or
                    not np.isfinite(self.origin).all() or
                    not np.allclose(self.rotation @ self.rotation.T, np.eye(3), atol=1e-6) or
                    not np.isclose(np.linalg.det(self.rotation), 1., atol=1e-6)):
                raise ValueError('Invalid orientation transform.')

    def validate_frame(self, frame, camera):
        expected = tuple(self.sizes[camera][::-1])
        if frame.shape[:2] != expected:
            raise ValueError(f'cam{camera+1} frame is {frame.shape[1]}x{frame.shape[0]}, '
                             f'but calibration requires {self.sizes[camera,0]}x{self.sizes[camera,1]}. '
                             'Use the calibrated camera mode; do not resize to hide a mismatch.')

    def argus_pixels(self, pixels):
        uv = np.asarray(pixels, dtype=float).copy().reshape(2, 2)
        uv[:, 1] = self.sizes[:, 1] - uv[:, 1]
        return uv

    def undistorted(self, pixels):
        uv = self.argus_pixels(pixels)
        return np.array([cv2.undistortPoints(uv[c].reshape(1, 1, 2), self.K[c],
                         self.dist[c], P=self.K[c]).reshape(2) for c in range(2)])

    def project(self, xyz):
        """Distorted OpenCV pixels for a point in the original calibration frame."""
        q = self.P @ np.r_[xyz, 1.]
        if np.any(np.abs(q[:, 2]) < 1e-12):
            raise ValueError('Point projects at infinity.')
        ideal = q[:, :2] / q[:, 2:]
        a = (ideal[:, 0] - self.K[:, 0, 2]) / self.K[:, 0, 0]
        b = (ideal[:, 1] - self.K[:, 1, 2]) / self.K[:, 1, 1]
        r = a*a + b*b
        k1, k2, p1, p2, k3 = self.dist.T
        radial = 1. + k1*r + k2*r*r + k3*r**3
        uv = np.column_stack((a*radial + 2*p1*a*b + p2*(r+2*a*a),
                              b*radial + p1*(r+2*b*b) + 2*p2*a*b))
        uv[:, 0] = uv[:, 0]*self.K[:, 0, 0] + self.K[:, 0, 2]
        uv[:, 1] = uv[:, 1]*self.K[:, 1, 1] + self.K[:, 1, 2]
        uv[:, 1] = self.sizes[:, 1] - uv[:, 1]
        return uv

    def epipolar_error(self, pixels):
        uv = self.undistorted(pixels)
        p1, p2 = np.c_[uv, np.ones(2)]
        line2, line1 = self.F @ p1, self.F.T @ p2
        denominator = np.sum(line2[:2]**2) + np.sum(line1[:2]**2)
        if denominator <= 1e-15:
            return float('inf')
        return float(abs(p2 @ self.F @ p1) / np.sqrt(denominator))

    def triangulate(self, pixels, sigma_px=2.):
        pixels = np.asarray(pixels, dtype=float).reshape(2, 2)
        if not np.isfinite(pixels).all():
            raise ValueError('Nonfinite object pixels.')
        und = self.undistorted(pixels)
        homogeneous = cv2.triangulatePoints(self.P[0], self.P[1],
                                            und[0].reshape(2, 1), und[1].reshape(2, 1))
        if abs(homogeneous[3, 0]) < 1e-12:
            raise ValueError('Stereo rays meet at infinity.')
        seed = homogeneous[:3, 0] / homogeneous[3, 0]
        fit = least_squares(lambda x: (self.project(x)-pixels).ravel(), seed, max_nfev=40)
        if not fit.success or not np.isfinite(fit.x).all():
            raise ValueError('Stereo fit did not converge.')
        normal = fit.jac.T @ fit.jac
        if np.linalg.cond(normal) > 1e10:
            raise ValueError('Stereo depth is poorly constrained.')
        cov = sigma_px**2 * np.linalg.inv(normal)
        rays = fit.x - self.centers
        cosine = np.dot(*rays) / np.prod(np.linalg.norm(rays, axis=1))
        angle = float(np.degrees(np.arccos(np.clip(abs(cosine), 0., 1.))))
        displayed = self.rotation @ (fit.x-self.origin)
        cov = self.rotation @ cov @ self.rotation.T
        predicted = self.project(fit.x)
        return Location(fit.x, displayed, 1.96*np.sqrt(np.diag(cov)),
                        float(np.sqrt(np.mean((predicted-pixels)**2))), angle, predicted)
