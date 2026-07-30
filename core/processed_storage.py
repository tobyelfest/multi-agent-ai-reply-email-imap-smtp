"""Atomic JSON storage for processed message IDs."""

import json
import os
import hashlib
from pathlib import Path
from typing import Set, Union
import tempfile


def generate_message_id_hash(sender: str, subject: str, body: str) -> str:
    """Generate a deterministic hash from email content when Message-ID missing."""
    content = f"{sender}\n{subject}\n{body}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ProcessedStorage:
    """Thread-safe atomic storage of processed email identifiers using JSON."""

    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)
        self._ensure_parent()

    def _ensure_parent(self) -> None:
        """Create parent directory if it doesn't exist."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_data(self) -> Set[str]:
        """Load set of processed IDs from JSON file."""
        if not self.file_path.exists():
            return set()
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("processed_ids", []))
        except (json.JSONDecodeError, OSError):
            return set()

    def _save_data(self, ids: Set[str]) -> None:
        """Atomically write set of IDs to JSON using a temporary file."""
        data = {"processed_ids": list(ids)}
        dir_path = self.file_path.parent
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(dir_path),
            prefix="tmp_",
            suffix=".json",
            delete=False
        ) as tmp:
            json.dump(data, tmp, indent=2)
            tmp_path = tmp.name
        # Atomic rename
        os.replace(tmp_path, self.file_path)

    def add(self, identifier: str) -> None:
        """Add a processed identifier (Message-ID or hash) atomically."""
        ids = self._load_data()
        ids.add(identifier)
        self._save_data(ids)

    def contains(self, identifier: str) -> bool:
        """Check if identifier already processed."""
        ids = self._load_data()
        return identifier in ids

    def add_with_fallback(
        self,
        message_id: Optional[str],
        sender: str,
        subject: str,
        body: str
    ) -> str:
        """Add using Message-ID if available, otherwise generate hash."""
        if message_id and message_id.strip():
            identifier = message_id.strip()
        else:
            identifier = generate_message_id_hash(sender, subject, body)
        self.add(identifier)
        return identifier

    def contains_with_fallback(
        self,
        message_id: Optional[str],
        sender: str,
        subject: str,
        body: str
    ) -> bool:
        """Check using Message-ID if available, otherwise generate hash."""
        if message_id and message_id.strip():
            identifier = message_id.strip()
        else:
            identifier = generate_message_id_hash(sender, subject, body)
        return self.contains(identifier)
