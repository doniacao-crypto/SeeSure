"""
PHI Encryption Helpers — Fernet symmetric encryption + OS keychain.

Key is stored in the OS keychain (macOS Keychain / Windows Credential Store /
libsecret on Linux) under service="EyeExam", account="phi_encryption_key".

IMPORTANT: If the keychain entry is missing on a machine that has existing
.phi files, those files are unreadable until the key is restored from backup.
See README for key backup/restore procedure.
"""

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
import keyring

_SERVICE = "EyeExam"
_KEY_ACCOUNT = "phi_encryption_key"


class MissingEncryptionKey(RuntimeError):
    """Raised when the PHI encryption key is not found in the OS keychain."""
    pass


def _get_key() -> bytes:
    """
    Retrieve the Fernet key from the OS keychain.

    Raises MissingEncryptionKey if the key is not present — never falls back
    to plaintext.
    """
    raw = keyring.get_password(_SERVICE, _KEY_ACCOUNT)
    if raw is None:
        raise MissingEncryptionKey(
            f"PHI encryption key not found in OS keychain "
            f"(service='{_SERVICE}', account='{_KEY_ACCOUNT}'). "
            "Run 'python -m src.crypto init' to generate a new key, "
            "or restore from your secure key backup."
        )
    return raw.encode()


def init_key() -> None:
    """
    Generate a new Fernet key and store it in the OS keychain.
    Called once on first run. Raises RuntimeError if a key already exists
    (prevents accidental overwrite that would make existing files unreadable).
    """
    existing = keyring.get_password(_SERVICE, _KEY_ACCOUNT)
    if existing is not None:
        raise RuntimeError(
            "PHI encryption key already exists in OS keychain. "
            "To replace it you must first delete the existing entry manually."
        )
    key = Fernet.generate_key()
    keyring.set_password(_SERVICE, _KEY_ACCOUNT, key.decode())


def get_fernet() -> Fernet:
    """Return a Fernet instance using the keychain key."""
    return Fernet(_get_key())


def encrypt_json(data: dict[str, Any]) -> bytes:
    """Serialize dict to JSON and encrypt. Returns ciphertext bytes."""
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return get_fernet().encrypt(plaintext)


def decrypt_json(ciphertext: bytes) -> dict[str, Any]:
    """Decrypt ciphertext and deserialize JSON. Raises InvalidToken if tampered."""
    plaintext = get_fernet().decrypt(ciphertext)
    return json.loads(plaintext.decode("utf-8"))


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "init":
        init_key()
        print("PHI encryption key generated and stored in OS keychain.")
    else:
        print("Usage: python -m src.crypto init")
