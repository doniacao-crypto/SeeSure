"""
Camera discovery.

The app must not assume a single webcam. A laptop camera, an external USB webcam and a
capture card each show up as a separate OpenCV index, and index 0 is not always the one the
operator wants in front of a patient. This module probes the indices and returns the ones
that actually deliver frames.
"""

from dataclasses import dataclass
from typing import List, Optional

import cv2

# How many indices to probe. Machines rarely have more than a few cameras, and every extra
# index costs startup time for nothing.
MAX_DEVICES_TO_PROBE = 6


@dataclass(frozen=True)
class CameraDevice:
    """A camera that delivered a frame when it was probed."""

    index: int
    label: str


def _probe_backend() -> Optional[int]:
    """DirectShow enumerates cameras reliably on Windows; elsewhere use the default."""
    import sys
    if sys.platform.startswith("win") and hasattr(cv2, "CAP_DSHOW"):
        return cv2.CAP_DSHOW
    return None


def enumerate_cameras(max_devices: int = MAX_DEVICES_TO_PROBE) -> List[CameraDevice]:
    """Return the camera indices that deliver frames.

    Probing opens each device, so a camera that another application is already holding
    fails to deliver and is left out of the list.
    """
    backend = _probe_backend()
    devices: List[CameraDevice] = []

    for index in range(max_devices):
        cap = cv2.VideoCapture(index, backend) if backend is not None else cv2.VideoCapture(index)
        try:
            if not cap.isOpened():
                continue
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            devices.append(CameraDevice(
                index=index,
                label=f"Camera {index + 1} (index {index})",
            ))
        finally:
            cap.release()

    return devices
