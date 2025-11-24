"""
Data integrity protection for extraction results.
"""

import hashlib
import json
import logging
import tempfile
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DataIntegrity:
    """
    Ensures data integrity during extraction with journaling.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.journal_path = self.output_dir / ".extraction_journal"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def start_transaction(self, operation_id: str) -> None:
        """Record start of data operation."""
        self._append_journal(f"START|{operation_id}|{datetime.now().isoformat()}")

    def commit_transaction(self, operation_id: str, data_path: Path) -> None:
        """Commit successful operation with checksum."""
        checksum = self._calculate_file_checksum(data_path)
        self._append_journal(f"COMMIT|{operation_id}|{checksum}|{data_path}")

    def rollback_transaction(self, operation_id: str, reason: str = "") -> None:
        """Mark operation as failed."""
        self._append_journal(f"ROLLBACK|{operation_id}|{reason}")

    def save_atomic(self, data: Dict[str, Any], path: Path) -> str:
        """
        Save data atomically with integrity verification.

        Returns checksum of saved data.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file
        fd, temp_path = tempfile.mkstemp(
            dir=path.parent,
            suffix='.tmp'
        )

        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)

            # Calculate checksum before move
            checksum = self._calculate_file_checksum(Path(temp_path))

            # Atomic rename
            os.replace(temp_path, path)

            # Verify after move
            if self._calculate_file_checksum(path) != checksum:
                raise IOError("Checksum mismatch after save")

            return checksum

        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def verify_integrity(self, path: Path, expected_checksum: str) -> bool:
        """Verify file integrity against expected checksum."""
        actual = self._calculate_file_checksum(path)
        return actual == expected_checksum

    def get_incomplete_operations(self) -> List[str]:
        """Find operations that started but didn't complete."""
        if not self.journal_path.exists():
            return []

        operations = {}

        with open(self.journal_path, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) < 2:
                    continue

                action, op_id = parts[0], parts[1]

                if action == "START":
                    operations[op_id] = "pending"
                elif action == "COMMIT":
                    operations[op_id] = "complete"
                elif action == "ROLLBACK":
                    operations[op_id] = "rolled_back"

        return [op_id for op_id, status in operations.items() if status == "pending"]

    def _append_journal(self, entry: str) -> None:
        """Append entry to journal file."""
        with open(self.journal_path, 'a', encoding='utf-8') as f:
            f.write(entry + '\n')

    def _calculate_file_checksum(self, path: Path) -> str:
        """Calculate MD5 checksum of file."""
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
