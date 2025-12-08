"""Domain service for text normalization and chunking."""
from __future__ import annotations

import re
from typing import List
from logging import Logger


class TextProcessingService:
    """Provides utilities to sanitize and chunk extracted text."""

    def __init__(self, max_chunk_size: int, logger: Logger) -> None:
        self._max_chunk_size = max_chunk_size
        self._logger = logger

    def clean_text(self, text: str) -> str:
        """Normalize whitespace and remove non-printable characters."""
        normalized = re.sub(r"\s+", " ", text).strip()
        self._logger.debug("Normalized text length: %d", len(normalized))
        return normalized

    def chunk_text(self, text: str) -> List[str]:
        """Split text into manageable chunks for model consumption."""
        if not text:
            return []
        chunks = [
            text[i : i + self._max_chunk_size]
            for i in range(0, len(text), self._max_chunk_size)
        ]
        self._logger.debug("Generated %d chunks", len(chunks))
        return chunks
