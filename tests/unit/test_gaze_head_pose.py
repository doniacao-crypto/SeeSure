"""
Head-pose robustness of the gaze estimator.

Regression cover for the defect that caused the long-standing accuracy plateau: when calibration is
performed with the head held still, the observed spread of head pitch/yaw is solvePnP landmark noise
rather than signal. StandardScaler then adopts that noise as its unit, and the pitch/yaw coefficients
become unidentifiable -- so the model learns no head compensation and gaze collapses to the screen
edge the moment the subject turns their head.
"""

import numpy as np
import pytest

from eye_tracker import EyeData
from gaze_estimator import GazeEstimator

SCREEN_W, SCREEN_H = 1920, 1080
IRIS_NOISE = 0.004  # independent per-frame landmark noise, normalised eye-width units

# Forward model constants: how screen position and head pose map to iris offset.
GAIN_X, GAIN_Y = 0.16, 0.13
YAW_TO_IRIS, PITCH_TO_IRIS = 0.0021, 0.0018


def _eye(rng, screen_x, screen_y, pitch=0.0, yaw=0.0, jitter=0.3, noisy=True):
    """Synthesise EyeData for a subject at (screen_x, screen_y) with a given head pose."""
    if noisy:
        pitch = pitch + rng.normal(0, jitter)
        yaw = yaw + rng.normal(0, jitter)

    nx = screen_x / SCREEN_W - 0.5
    ny = screen_y / SCREEN_H - 0.5
    offset_x = GAIN_X * nx + YAW_TO_IRIS * yaw
    offset_y = GAIN_Y * ny - PITCH_TO_IRIS * pitch

    if noisy:
        offset_x += rng.normal(0, IRIS_NOISE)
        offset_y += rng.normal(0, IRIS_NOISE)

    iris = (0.5 - offset_x, 0.5 + offset_y)
    return EyeData(
        left_iris_center=iris,
        right_iris_center=iris,
        head_pitch=pitch,
        head_yaw=yaw,
        head_roll=0.0,
        face_detected=True,
    )


def _grid():
    return [
        (int(SCREEN_W * gx), int(SCREEN_H * gy))
        for gy in (0.1, 0.5, 0.9)
        for gx in (0.1, 0.5, 0.9)
    ]


def _calibrate(poses, seed=11):
    """Calibrate over the 3x3 grid, visiting each dot once per head pose in `poses`."""
    rng = np.random.default_rng(seed)
    est = GazeEstimator(SCREEN_W, SCREEN_H, filter_mode='none')
    est.start_calibration("test")

    for (screen_x, screen_y) in _grid():
        est.start_collecting_samples()
        for (pitch, yaw) in poses:
            for _ in range(10):
                est.add_calibration_sample(
                    _eye(rng, screen_x, screen_y, pitch=pitch, yaw=yaw, jitter=0.3)
                )
        est.finish_collecting_samples(screen_x, screen_y)

    assert est.finish_calibration()
    return est, rng


STILL = [(0.0, 0.0)]
POSE_VARIED = [(0.0, 0.0), (0.0, -15.0), (0.0, 15.0), (-10.0, 0.0), (10.0, 0.0)]


def _centre_error_deg(est, rng, yaw):
    """Gaze error, in degrees, while fixating screen centre with the head turned by `yaw`."""
    data = _eye(rng, SCREEN_W // 2, SCREEN_H // 2, yaw=yaw, noisy=False)
    pred = est.estimate_gaze(data, apply_smoothing=False)
    assert pred is not None
    px_per_deg = 35.0  # ~24" 1080p at 60 cm
    return float(np.hypot(pred[0] - SCREEN_W // 2, pred[1] - SCREEN_H // 2)) / px_per_deg


class TestHeadPoseScaleFloor:
    def test_still_head_calibration_does_not_scale_head_pose_by_noise(self):
        """A still subject must not make landmark noise the unit of head pose."""
        est, _ = _calibrate(STILL)
        # Without the floor, these would be the ~0.3 deg std of solvePnP noise.
        assert est._scaler.scale_[2] >= GazeEstimator.HEAD_POSE_SCALE_DEG
        assert est._scaler.scale_[3] >= GazeEstimator.HEAD_POSE_SCALE_DEG

    def test_pose_varied_calibration_keeps_the_real_spread(self):
        """When head pose genuinely varies, the real std is signal and must be preserved."""
        est, _ = _calibrate(POSE_VARIED)
        assert est._scaler.scale_[3] > GazeEstimator.HEAD_POSE_SCALE_DEG


class TestHeadPoseSpreadReporting:
    def test_still_head_calibration_is_flagged(self):
        est, _ = _calibrate(STILL)
        quality = est.get_calibration_quality()
        assert quality['head_pose_ok'] is False
        assert quality['head_yaw_spread_deg'] < GazeEstimator.MIN_HEAD_POSE_SPREAD_DEG

    def test_pose_varied_calibration_passes(self):
        est, _ = _calibrate(POSE_VARIED)
        quality = est.get_calibration_quality()
        assert quality['head_pose_ok'] is True
        assert quality['head_yaw_spread_deg'] >= GazeEstimator.MIN_HEAD_POSE_SPREAD_DEG


class TestHeadTurnRobustness:
    @pytest.mark.parametrize("yaw", [5.0, 12.0, 20.0])
    def test_pose_varied_calibration_survives_head_turns(self, yaw):
        """The whole point: a head turn must not destroy the gaze estimate."""
        est, rng = _calibrate(POSE_VARIED)
        assert _centre_error_deg(est, rng, yaw) < 2.0

    def test_pose_varied_beats_still_head_under_head_turn(self):
        """Pose-varied calibration must be strictly better once the head moves."""
        still, rng_a = _calibrate(STILL)
        varied, rng_b = _calibrate(POSE_VARIED)
        assert _centre_error_deg(varied, rng_b, 12.0) < _centre_error_deg(still, rng_a, 12.0)


class TestCrossValidationGrouping:
    def test_cv_groups_are_keyed_by_screen_location_not_point_index(self):
        """
        Pose-varied calibration visits each dot several times. Grouping by point index would put the
        same screen location in both CV folds and leak, flattering the held-out error.
        """
        est, _ = _calibrate(POSE_VARIED)
        assert len(np.unique(est._cv_groups)) == len(_grid())
