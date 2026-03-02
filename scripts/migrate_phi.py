#!/usr/bin/env python3
"""
One-time migration: encrypt existing plain-text patient JSON files.

Usage:
    python scripts/migrate_phi.py [--data-dir data/patients] [--dry-run]

IMPORTANT:
    - Ensure the OS keychain key exists first: python -m src.crypto init
    - The script removes plaintext files only after successful encryption
    - If interrupted, re-running is safe (already-migrated files are skipped)
"""

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crypto import encrypt_json, MissingEncryptionKey


def migrate(data_dir: Path, dry_run: bool = False) -> None:
    plain_files = list(data_dir.glob("*.json"))
    if not plain_files:
        print(f"No plain-text .json files found in {data_dir}. Nothing to migrate.")
        return

    print(f"Found {len(plain_files)} file(s) to migrate.")
    migrated = 0
    skipped = 0

    for plain_file in plain_files:
        enc_file = plain_file.with_suffix(".phi")

        if enc_file.exists():
            print(f"  SKIP  {plain_file.name} — encrypted file already exists")
            skipped += 1
            continue

        try:
            data = json.loads(plain_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ERROR reading {plain_file.name}: {e}")
            continue

        if dry_run:
            print(f"  DRY   {plain_file.name} → {enc_file.name}")
            migrated += 1
            continue

        try:
            enc_file.write_bytes(encrypt_json(data))
        except Exception as e:
            print(f"  ERROR encrypting {plain_file.name}: {e}")
            continue

        # Remove plaintext only after successful write
        plain_file.unlink()
        print(f"  OK    {plain_file.name} → {enc_file.name}")
        migrated += 1

    print(f"\nDone: {migrated} migrated, {skipped} skipped.")
    if dry_run:
        print("(Dry run — no files were changed.)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypt plain-text PHI patient files.")
    parser.add_argument("--data-dir", default="data/patients", help="Path to patient data directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: data directory '{data_dir}' not found.")
        sys.exit(1)

    try:
        migrate(data_dir, dry_run=args.dry_run)
    except MissingEncryptionKey as e:
        print(f"\n[ERROR] {e}")
        print("Run 'python -m src.crypto init' first, then retry migration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
