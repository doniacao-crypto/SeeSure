import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def test_adaptive_filter_presets_exist():
    from constants import (
        FILTER_PRESET_FIXATION,
        FILTER_PRESET_PURSUIT,
        FILTER_PRESET_SACCADE,
    )
    # Fixation: heavy smoothing
    assert FILTER_PRESET_FIXATION['mincutoff'] <= 1.5
    assert FILTER_PRESET_FIXATION['beta'] <= 0.05
    # Pursuit: responsive
    assert FILTER_PRESET_PURSUIT['mincutoff'] >= 3.0
    assert FILTER_PRESET_PURSUIT['beta'] >= 0.3
    # Saccade: minimal filtering
    assert FILTER_PRESET_SACCADE['mincutoff'] >= 10.0
    assert FILTER_PRESET_SACCADE['beta'] >= 0.8
