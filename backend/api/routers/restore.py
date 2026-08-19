"""Admin restore endpoint."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.api.deps import require_admin
from backend.core.config import get_config
from backend.core.database import AsyncSessionLocal
from backend.models._enums import AuditAction
from backend.models.staff import Staff
from backend.services import audit_service
from backend.services.backup_service import load_manifest, verify_backup_integrity

require_admin_dep = Depends(require_admin)

router = APIRouter(prefix="/admin", tags=["admin-restore"])


class RestoreRequest(BaseModel):
    backup_filename: str | None = None


@router.post("/restore", status_code=status.HTTP_202_ACCEPTED)
def restore_backup(
    request: RestoreRequest,
    current_admin: Staff = require_admin_dep,
) -> dict[str, str]:
    config = get_config()
    backup_dir = Path(config.backup_dir)
    manifest = load_manifest(backup_dir)

    if not manifest:
        raise HTTPException(status_code=404, detail="No backups available")

    # Determine which backup to restore
    if request.backup_filename:
        backup_filename = request.backup_filename
        # Validate it exists in manifest
        entry = next((e for e in manifest if e["filename"] == backup_filename), None)
        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Backup not found: {backup_filename}",
            )
    else:
        # Latest by created_at
        entry = max(manifest, key=lambda e: e["created_at"])
        backup_filename = entry["filename"]

    backup_path = backup_dir / backup_filename

    # Verify integrity
    if not verify_backup_integrity(backup_path, manifest):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Backup integrity check failed: SHA256 mismatch for {backup_filename}"
            ),
        )

    # Write signal file for launcher
    signal_path = Path(".") / ".restore_requested"
    signal_data = {
        "backup_filename": backup_filename,
        "requested_by": current_admin.id,
        "requested_at": datetime.now(UTC).isoformat(),
    }
    # Atomic write
    tmp_path = signal_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(signal_data, indent=2))
    os.replace(tmp_path, signal_path)

    # Audit log via background thread (DB may be closed during restart)
    def _audit_restore(backup_filename: str, staff_id: str) -> None:
        db = AsyncSessionLocal()
        try:
            import asyncio

            asyncio.run(
                audit_service.log(
                    db,
                    action=AuditAction.BACKUP_RESTORED,
                    entity_type="backup",
                    entity_id=backup_filename,
                    staff_id=staff_id,
                    detail="restored via API",
                )
            )
        finally:
            asyncio.run(db.close())

    Thread(
        target=_audit_restore,
        args=(backup_filename, current_admin.id),
        daemon=True,
    ).start()

    return {
        "message": "Restore queued. Server will restart.",
        "backup_file": backup_filename,
    }
