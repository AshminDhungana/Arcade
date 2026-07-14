"""Pydantic schemas for the Backup API."""

from __future__ import annotations

from pydantic import BaseModel


class BackupRunResponse(BaseModel):
    """Result of a manual or scheduled backup run."""

    backup_file: str
    pruned_count: int
