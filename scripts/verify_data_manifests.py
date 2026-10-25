#!/usr/bin/env python3
"""Validate FloodShift AI dataset manifests and verify artifact checksums."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "data" / "manifests"
REQUIRED_FIELDS = {
    "file_name",
    "url",
    "provider",
    "access_date",
    "geographic_coverage",
    "period",
    "licence_terms_link",
    "sha256",
    "source_type",
    "processing_steps",
}
ALLOWED_SOURCE_TYPES = {"observed", "official_forecast", "derived", "synthetic"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return urlparse(value).scheme in {"http", "https", "synthetic"}


def validate_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"{path.name}: invalid JSON ({error.msg})"]
    missing = REQUIRED_FIELDS - manifest.keys()
    if missing:
        errors.append(f"{path.name}: missing fields: {', '.join(sorted(missing))}")
        return errors
    if manifest["source_type"] not in ALLOWED_SOURCE_TYPES:
        errors.append(f"{path.name}: invalid source_type {manifest['source_type']!r}")
    if not is_url(manifest["url"]) or not is_url(manifest["licence_terms_link"]):
        errors.append(f"{path.name}: url and licence_terms_link must be absolute URLs")
    if not isinstance(manifest["processing_steps"], list) or not manifest["processing_steps"]:
        errors.append(f"{path.name}: processing_steps must be a non-empty list")
    artifact = ROOT / manifest["file_name"]
    if not artifact.is_file():
        errors.append(f"{path.name}: referenced artifact is missing: {manifest['file_name']}")
    elif sha256(artifact) != manifest["sha256"]:
        errors.append(f"{path.name}: SHA-256 mismatch for {manifest['file_name']}")
    if manifest["source_type"] == "synthetic" and not str(manifest["file_name"]).startswith("data/synthetic/"):
        errors.append(f"{path.name}: synthetic artifact must be under data/synthetic/")
    return errors


def main() -> int:
    manifests = sorted(MANIFEST_DIR.glob("*.manifest.json"))
    if not manifests:
        print("No manifests found.", file=sys.stderr)
        return 1
    errors = [error for path in manifests for error in validate_manifest(path)]
    if errors:
        print("Manifest verification failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"Verified {len(manifests)} manifest(s) and artifact checksums.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
