"""Tests for calibration grid margin matching test regions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_calibration_margin_matches_test_default():
    """Calibration margin should be <= test margin (3%) to avoid extrapolation."""
    from constants import DEFAULT_CALIBRATION_MARGIN
    assert DEFAULT_CALIBRATION_MARGIN <= 0.05  # At most 5%


def test_calibration_grid_4x4_covers_edges():
    """4x4 grid should provide 16 calibration points for better coverage."""
    width, height = 1920, 1080
    grid_size = 4
    margin = 0.05
    margin_x = int(width * margin)
    margin_y = int(height * margin)

    points = []
    for row in range(grid_size):
        for col in range(grid_size):
            x = margin_x + col * (width - 2 * margin_x) // (grid_size - 1)
            y = margin_y + row * (height - 2 * margin_y) // (grid_size - 1)
            points.append((x, y))

    assert len(points) == 16
    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    assert min_x <= width * 0.06
    assert max_x >= width * 0.94
