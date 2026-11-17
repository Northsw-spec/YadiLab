"""Explicit, durable project files (.yadilab) with optimistic concurrency."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .model import ProjectValidationError, validate_project

FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class ProjectConflictError(Exception):
    def __init__(self, actual_hash: str):
        super().__init__("project changed or already exists")
        self.actual_hash = actual_hash


class ProjectStore:
    def __init__(self, directory: Path):
        self.root = Path(directory).expanduser().resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def path(self, slug: str) -> Path:
        if not isinstance(slug, str) or not FILENAME_RE.fullmatch(slug):
            raise ProjectValidationError("filename: expected 1–64 letters, numbers, _ or -; must begin alphanumeric")
        return self.root / (slug + ".yadilab")

    @staticmethod
    def _hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def read(self, slug: str) -> dict:
        path = self.path(slug)
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            raise FileNotFoundError("project does not exist") from None
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProjectValidationError("saved project contains invalid JSON") from None
        project = validate_project(document)
        return {"filename": slug, "sha256": self._hash(raw), "bytes": len(raw), "project": project}

    def list(self) -> list[dict]:
        items = []
        for file in self.root.glob("*.yadilab"):
            if not file.is_file() or not FILENAME_RE.fullmatch(file.stem):
                continue
            stat = file.stat()
            items.append({"filename": file.stem, "bytes": stat.st_size, "modifiedAt": stat.st_mtime})
        return sorted(items, key=lambda item: item["filename"])

    def save(self, slug: str, document: object, expected_sha256: str | None = None) -> dict:
        path = self.path(slug)
        project = validate_project(document)
        if expected_sha256 is not None and (not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
            raise ProjectValidationError("expectedSha256: must be a SHA-256 string or null")
        existing = path.read_bytes() if path.exists() else None
        actual = self._hash(existing) if existing is not None else ""
        # No expected hash means create-only; an explicit matching hash means
        # intentional overwrite of the last version that the user loaded.
        if existing is not None and expected_sha256 != actual:
            raise ProjectConflictError(actual)
        if existing is None and expected_sha256 is not None:
            raise ProjectConflictError("")
        data = (json.dumps(project, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        fd, temp_name = tempfile.mkstemp(prefix=".pending-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
            # Make the rename durable on Linux, where directory fsync is supported.
            if hasattr(os, "O_DIRECTORY"):
                dfd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return {"filename": slug, "sha256": self._hash(data), "bytes": len(data), "project": project}
