"""
Unit tests for PHI encryption — src/crypto.py and PatientManager integration.

All tests use a temporary keychain mock (monkeypatch) so no real OS keychain
entries are created or required during CI.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet, InvalidToken

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_fernet_key() -> str:
    return Fernet.generate_key().decode()


# ── crypto.py unit tests ──────────────────────────────────────────────────────

class TestEncryptDecryptRoundtrip:
    def test_simple_dict(self, monkeypatch):
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)

        from src import crypto
        # Force fresh Fernet on each call
        data = {"name": "Jane Doe", "dob": "1985-04-12", "notes": "follow-up required"}
        ciphertext = crypto.encrypt_json(data)
        recovered = crypto.decrypt_json(ciphertext)
        assert recovered == data

    def test_unicode_strings(self, monkeypatch):
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)

        from src import crypto
        data = {"name": "张伟", "notes": "Chinese characters: 你好"}
        assert crypto.decrypt_json(crypto.encrypt_json(data)) == data

    def test_empty_dict(self, monkeypatch):
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)

        from src import crypto
        assert crypto.decrypt_json(crypto.encrypt_json({})) == {}


class TestTamperedCiphertextRaises:
    def test_flipped_byte_raises_invalid_token(self, monkeypatch):
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)

        from src import crypto
        ciphertext = bytearray(crypto.encrypt_json({"x": 1}))
        ciphertext[-5] ^= 0xFF  # flip bits in last few bytes
        with pytest.raises(InvalidToken):
            crypto.decrypt_json(bytes(ciphertext))

    def test_wrong_key_raises_invalid_token(self, monkeypatch):
        key1 = make_fernet_key()
        key2 = make_fernet_key()

        monkeypatch.setattr("keyring.get_password", lambda s, a: key1)
        from src import crypto
        ciphertext = crypto.encrypt_json({"secret": "data"})

        monkeypatch.setattr("keyring.get_password", lambda s, a: key2)
        with pytest.raises(InvalidToken):
            crypto.decrypt_json(ciphertext)


class TestMissingKeyFailsLoudly:
    def test_missing_keychain_key_raises(self, monkeypatch):
        monkeypatch.setattr("keyring.get_password", lambda s, a: None)

        from src.crypto import MissingEncryptionKey, encrypt_json
        with pytest.raises(MissingEncryptionKey):
            encrypt_json({"patient": "data"})

    def test_error_message_is_actionable(self, monkeypatch):
        monkeypatch.setattr("keyring.get_password", lambda s, a: None)

        from src.crypto import MissingEncryptionKey, encrypt_json
        with pytest.raises(MissingEncryptionKey, match="python -m src.crypto init"):
            encrypt_json({})


class TestInitKey:
    def test_generates_and_stores_key(self, monkeypatch):
        stored = {}
        monkeypatch.setattr("keyring.get_password", lambda s, a: stored.get((s, a)))
        monkeypatch.setattr("keyring.set_password", lambda s, a, v: stored.__setitem__((s, a), v))

        from src import crypto
        crypto.init_key()
        assert ("EyeExam", "phi_encryption_key") in stored

    def test_second_init_raises(self, monkeypatch):
        existing_key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: existing_key)

        from src import crypto
        with pytest.raises(RuntimeError, match="already exists"):
            crypto.init_key()


# ── PatientManager integration tests ─────────────────────────────────────────

class TestPatientManagerEncryption:
    def _make_manager(self, tmp_path, monkeypatch):
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)
        # Reload to pick up monkeypatched keyring
        import importlib, src.crypto as cm
        importlib.reload(cm)
        import src.patient_manager as pm_mod
        importlib.reload(pm_mod)
        mgr = pm_mod.PatientManager(data_dir=tmp_path)
        return mgr, pm_mod

    def test_no_plaintext_json_written(self, tmp_path, monkeypatch):
        mgr, _ = self._make_manager(tmp_path, monkeypatch)
        mgr.create(name="Alice Test", date_of_birth="2000-01-01")
        json_files = list(tmp_path.glob("*.json"))
        assert json_files == [], f"Plaintext JSON found: {json_files}"

    def test_phi_file_is_opaque(self, tmp_path, monkeypatch):
        mgr, _ = self._make_manager(tmp_path, monkeypatch)
        p = mgr.create(name="Bob Secret", date_of_birth="1990-06-15")
        phi_file = tmp_path / f"{p.id}.phi"
        assert phi_file.exists()
        raw = phi_file.read_bytes()
        assert b"Bob Secret" not in raw, "Patient name visible in ciphertext"

    def test_load_roundtrip(self, tmp_path, monkeypatch):
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)
        import importlib, src.crypto as cm, src.patient_manager as pm_mod
        importlib.reload(cm); importlib.reload(pm_mod)

        mgr1 = pm_mod.PatientManager(data_dir=tmp_path)
        p = mgr1.create(name="Carol Reload", date_of_birth="1975-03-20", notes="test note")

        # Fresh manager loads from disk
        mgr2 = pm_mod.PatientManager(data_dir=tmp_path)
        loaded = mgr2.get(p.id)
        assert loaded is not None
        assert loaded.name == "Carol Reload"
        assert loaded.notes == "test note"

    def test_missing_key_raises_on_load(self, tmp_path, monkeypatch):
        # First create with valid key
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)
        import importlib, src.crypto as cm, src.patient_manager as pm_mod
        importlib.reload(cm); importlib.reload(pm_mod)
        mgr = pm_mod.PatientManager(data_dir=tmp_path)
        mgr.create(name="Dan PHI", date_of_birth="1980-11-30")

        # Now simulate missing key
        monkeypatch.setattr("keyring.get_password", lambda s, a: None)
        importlib.reload(cm); importlib.reload(pm_mod)
        from crypto import MissingEncryptionKey
        with pytest.raises(MissingEncryptionKey):
            pm_mod.PatientManager(data_dir=tmp_path)


# ── Migration script tests ────────────────────────────────────────────────────

class TestMigrationScript:
    def test_migrates_json_to_phi(self, tmp_path, monkeypatch):
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)
        import importlib, src.crypto as cm
        importlib.reload(cm)

        # Write a plain patient file
        plain = tmp_path / "P001.json"
        plain.write_text(json.dumps({"id": "P001", "name": "Eve Plain"}))

        from scripts.migrate_phi import migrate
        migrate(tmp_path)

        assert not plain.exists(), "Plaintext file should be removed"
        assert (tmp_path / "P001.phi").exists(), ".phi file should be created"

    def test_skips_already_migrated(self, tmp_path, monkeypatch):
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)
        import importlib, src.crypto as cm
        importlib.reload(cm)
        from src.crypto import encrypt_json

        # Pre-existing .phi + a stray .json with same stem
        (tmp_path / "P002.phi").write_bytes(encrypt_json({"id": "P002", "name": "Frank"}))
        plain = tmp_path / "P002.json"
        plain.write_text(json.dumps({"id": "P002", "name": "Frank"}))

        from scripts.migrate_phi import migrate
        migrate(tmp_path)

        # .json should still be there (skipped because .phi already existed)
        assert plain.exists()

    def test_dry_run_leaves_files_unchanged(self, tmp_path, monkeypatch):
        key = make_fernet_key()
        monkeypatch.setattr("keyring.get_password", lambda s, a: key)
        import importlib, src.crypto as cm
        importlib.reload(cm)

        plain = tmp_path / "P003.json"
        plain.write_text(json.dumps({"id": "P003", "name": "Grace DryRun"}))

        from scripts.migrate_phi import migrate
        migrate(tmp_path, dry_run=True)

        assert plain.exists(), "Dry run should not delete plaintext files"
        assert not (tmp_path / "P003.phi").exists()
