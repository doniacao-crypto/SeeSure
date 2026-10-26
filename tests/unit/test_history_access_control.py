"""
Deleting a stored score removes clinical data, so it is an administrator-only action and it
is refused outright while nobody is signed in.

The check lives in _delete_history_session rather than in the button's visibility: hiding a
control is a convenience, the authorisation check is the control.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_src_dir = str(Path(__file__).parent.parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


@pytest.fixture(scope="module")
def main_app_module():
    """Import main_app once the real PyQt6 modules are restored by the conftest guard."""
    import main_app
    return main_app


@pytest.fixture(scope="module")
def user_roles():
    from user_manager import USER_ROLE_ADMIN, USER_ROLE_USER
    return USER_ROLE_ADMIN, USER_ROLE_USER


class _FakeSessionHistory:
    def __init__(self):
        self.deleted = []

    def delete_session(self, filename):
        self.deleted.append(filename)
        return True


class _FakeWindow:
    """Just enough of MainWindow for the delete path."""

    FILENAME = "test_horizontal_20260101_000000.json"

    def __init__(self, user):
        self.current_user = user
        self.history_list = SimpleNamespace(
            currentItem=lambda: SimpleNamespace(data=lambda role: self.FILENAME)
        )
        self.session_history = _FakeSessionHistory()
        self.refreshed = 0

    def _refresh_history(self):
        self.refreshed += 1


@pytest.fixture
def dialogs(monkeypatch):
    """Capture the dialogs raised instead of blocking on them."""
    from PyQt6.QtWidgets import QMessageBox

    recorded = {"warnings": [], "questions": []}
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda *args, **kwargs: recorded["warnings"].append(args[2] if len(args) > 2 else ""),
    )
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: recorded["questions"].append(args[2] if len(args) > 2 else "")
        or QMessageBox.StandardButton.Yes,
    )
    return recorded


class TestHistoryDeletion:
    def test_signed_out_cannot_delete(self, main_app_module, dialogs):
        window = _FakeWindow(None)

        main_app_module.MainWindow._delete_history_session(window)

        assert window.session_history.deleted == []
        assert dialogs["warnings"], "the operator must be told why nothing was deleted"

    def test_regular_user_cannot_delete(self, main_app_module, user_roles, dialogs):
        _, role_user = user_roles
        window = _FakeWindow(SimpleNamespace(username="clinician", role=role_user))

        main_app_module.MainWindow._delete_history_session(window)

        assert window.session_history.deleted == []
        assert dialogs["warnings"]

    def test_admin_can_delete(self, main_app_module, user_roles, dialogs):
        role_admin, _ = user_roles
        window = _FakeWindow(SimpleNamespace(username="admin", role=role_admin))

        main_app_module.MainWindow._delete_history_session(window)

        assert window.session_history.deleted == [window.FILENAME]
        assert window.refreshed == 1
        assert not dialogs["warnings"]

    def test_admin_still_needs_a_selection(self, main_app_module, user_roles, dialogs):
        role_admin, _ = user_roles
        window = _FakeWindow(SimpleNamespace(username="admin", role=role_admin))
        window.history_list = SimpleNamespace(currentItem=lambda: None)

        main_app_module.MainWindow._delete_history_session(window)

        assert window.session_history.deleted == []
        assert dialogs["warnings"]


class TestHistoryDisplay:
    """The stored runs must be labelled by what the numbers actually mean."""

    @staticmethod
    def _session():
        return SimpleNamespace(
            filename="test_horizontal_20260101_000000.json",
            timestamp=SimpleNamespace(strftime=lambda fmt: "2026-01-01 00:00"),
            pattern="horizontal",
        )

    def test_current_results_show_tracking_rate_and_speed_match(self, main_app_module):
        data = {
            "timestamp": "2026-01-01 00:00",
            "pattern": "horizontal",
            "metrics": {"tracking_ratio": 100.0, "speed_match_score": 77.0,
                        "accuracy_score": 96.0, "smooth_score": 96.0,
                        "head_stillness_score": 99.0},
            "clinical_metrics": {"accuracy_degrees": 4.9, "pursuit_gain": 0.87},
        }

        text = main_app_module.MainWindow._history_item_text(None, data, self._session())

        assert "Track: 100%" in text
        assert "Speed: 77%" in text
        assert "Match: 96%" in text
        assert "Err: 4.9°" in text

    def test_results_saved_before_the_split_show_the_speed_match(self, main_app_module):
        """An older file stored the speed match under the tracking-rate name."""
        data = {
            "timestamp": "2026-01-01 00:00",
            "pattern": "horizontal",
            "metrics": {"tracking_ratio": 33.0, "accuracy_score": 49.0,
                        "smooth_score": 68.0, "head_stillness_score": 98.0},
        }

        text = main_app_module.MainWindow._history_item_text(None, data, self._session())

        assert "Speed: 33%" in text
        assert "Track:" not in text
