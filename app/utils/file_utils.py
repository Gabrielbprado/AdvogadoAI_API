"""Utility helpers for handling files and uploads."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile


def ensure_directory(path: Path) -> Path:
    """Ensure the directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_document_id(prefix: str = "doc") -> str:
    """Generate a unique document identifier."""
    return f"{prefix}-{uuid4()}"


def save_upload_file(upload_file: UploadFile, destination_dir: Path, *, filename: Optional[str] = None) -> Path:
    """Persist an uploaded file to disk and return the absolute path."""
    ensure_directory(destination_dir)
    resolved_name = filename or upload_file.filename or generate_document_id("upload")
    destination = destination_dir / resolved_name
    with destination.open("wb") as buffer:
        contents = upload_file.file.read()
        buffer.write(contents)
    upload_file.file.close()
    return destination


def read_file_bytes(file_path: Path) -> bytes:
    """Read a file and return its content as bytes."""
    return file_path.read_bytes()
