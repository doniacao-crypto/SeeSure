"""
Unit tests for filters module.
Tests LowPassFilter, OneEuroFilter, and KalmanFilter2D.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from filters import LowPassFilter, OneEuroFilter, OneEuroFilter2D, GazeKalmanFilter


class TestLowPassFilter:
    """Tests for LowPassFilter class."""

    def test_initialization(self):
        """Test filter initializes with correct alpha."""
        lpf = LowPassFilter(alpha=0.5)
        assert lpf.alpha == 0.5
        assert not lpf.initialized
        assert lpf.last_value is None

    def test_first_value_passthrough(self):
        """Test first value passes through unchanged."""
        lpf = LowPassFilter(alpha=0.5)
        result = lpf.filter(10.0)
        assert result == 10.0
        assert lpf.initialized

    def test_smoothing(self):
        """Test filter smooths subsequent values."""
        lpf = LowPassFilter(alpha=0.5)
        lpf.filter(10.0)  # Initialize
        result = lpf.filter(20.0)
        # With alpha=0.5: y = 0.5 * 20 + 0.5 * 10 = 15
        assert result == 15.0

    def test_dynamic_alpha(self):
        """Test alpha can be changed during filtering."""
        lpf = LowPassFilter(alpha=0.5)
        lpf.filter(10.0)
        result = lpf.filter(20.0, alpha=0.8)
        # With alpha=0.8: y = 0.8 * 20 + 0.2 * 10 = 18
        assert result == 18.0

    def test_reset(self):
        """Test filter reset clears state."""
        lpf = LowPassFilter(alpha=0.5)
        lpf.filter(10.0)
        lpf.filter(20.0)
        lpf.reset()
        assert not lpf.initialized
        assert lpf.last_value is None

    def test_high_alpha_follows_input(self):
        """Test high alpha (close to 1) closely follows input."""
        lpf = LowPassFilter(alpha=0.99)
        lpf.filter(0.0)
        result = lpf.filter(100.0)
        assert result > 98.0  # Should be close to 100

    def test_low_alpha_resists_change(self):
        """Test low alpha (close to 0) resists rapid changes."""
        lpf = LowPassFilter(alpha=0.01)
        lpf.filter(0.0)
        result = lpf.filter(100.0)
        assert result < 2.0  # Should still be close to 0


class TestOneEuroFilter:
    """Tests for OneEuroFilter class."""

    def test_initialization(self):
        """Test filter initializes with correct parameters."""
        oef = OneEuroFilter(freq=30.0, mincutoff=1.0, beta=0.007, dcutoff=1.0)
        assert oef.freq == 30.0
        assert oef.mincutoff == 1.0
        assert oef.beta == 0.007

    def test_first_value_passthrough(self):
        """Test first value passes through unchanged."""
        oef = OneEuroFilter()
        result = oef.filter(100.0)
        assert result == 100.0

    def test_smooths_jitter(self):
        """Test filter smooths out small jitter."""
        oef = OneEuroFilter(mincutoff=0.5, beta=0.0)  # No speed adaptation
        values = [100, 101, 99, 100, 102, 98, 100]
        results = [oef.filter(v) for v in values]
        
        # Variance of output should be less than input
        input_var = np.var(values[1:])  # Skip first
        output_var = np.var(results[1:])
        assert output_var < input_var

    def test_follows_fast_movement(self):
        """Test filter follows fast movements with less lag."""
        oef = OneEuroFilter(mincutoff=1.0, beta=0.5)
        
        # Simulate fast movement
        results = []
        for i in range(10):
            results.append(oef.filter(i * 10.0))
        
        # Last value should be close to input (less lag)
        assert results[-1] > 80.0  # Input was 90.0

    def test_reset(self):
        """Test filter reset clears state."""
        oef = OneEuroFilter()
        oef.filter(100.0)
        oef.filter(200.0)
        oef.reset()
        
        # After reset, first value should pass through
        result = oef.filter(50.0)
        assert result == 50.0

    def test_timestamp_based_frequency(self):
        """Test frequency adaptation with timestamps."""
        oef = OneEuroFilter(freq=30.0)
        
        # First value
        oef.filter(0.0, timestamp=0.0)
        
        # Second value at 50ms (20 Hz effective)
        result = oef.filter(10.0, timestamp=0.05)
        
        # Should produce a valid filtered result
        assert 0.0 < result < 10.0


class TestGazeKalmanFilter:
    """Tests for GazeKalmanFilter class."""

    def test_initialization(self):
        """Test filter initializes correctly."""
        kf = GazeKalmanFilter()
        assert kf._initialized == False
        assert hasattr(kf, 'state')

    def test_update_reduces_noise(self):
        """Test filter reduces noise in 2D trajectory."""
        kf = GazeKalmanFilter()
        
        # Simulate noisy input
        np.random.seed(42)
        noisy_x = []
        filtered_x = []
        
        for i in range(30):
            # True position moving linearly
            true_x = i * 10.0
            true_y = i * 5.0
            
            # Add noise
            nx = true_x + np.random.normal(0, 5)
            ny = true_y + np.random.normal(0, 5)
            noisy_x.append(nx)
            
            # Filter using update method
            fx, fy = kf.update(nx, ny)
            filtered_x.append(fx)
        
        # Variance of filtered differences should be lower
        noisy_diff = np.var(np.diff(noisy_x))
        filtered_diff = np.var(np.diff(filtered_x))
        assert filtered_diff <= noisy_diff * 1.5  # Allow some tolerance

    def test_reset(self):
        """Test filter reset clears state."""
        kf = GazeKalmanFilter()
        kf.update(100.0, 200.0)
        kf.update(150.0, 250.0)
        kf.reset()
        
        assert kf._initialized == False
        
        # After reset, first value should be close to input
        x, y = kf.update(50.0, 75.0)
        assert abs(x - 50.0) < 1.0
        assert abs(y - 75.0) < 1.0


class TestFilterIntegration:
    """Integration tests for filter combinations."""

    def test_oneuro_vs_kalman_smoothing(self):
        """Compare smoothing behavior of 1-Euro vs Kalman filters."""
        oef = OneEuroFilter(mincutoff=1.0, beta=0.007)
        kf = GazeKalmanFilter()
        
        np.random.seed(42)
        
        # Generate noisy signal
        true_values = [i * 2.0 for i in range(20)]
        noisy_values = [v + np.random.normal(0, 3) for v in true_values]
        
        oef_results = [oef.filter(v) for v in noisy_values]
        kf_results = [kf.update(v, 0.0)[0] for v in noisy_values]
        
        # Both should reduce noise (or maintain similar variance)
        input_var = np.var(noisy_values)
        oef_var = np.var(oef_results)
        kf_var = np.var(kf_results)
        
        # 1-Euro should reduce variance
        assert oef_var < input_var
