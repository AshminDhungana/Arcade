"""Backup API router — manual backup trigger (Admin only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.schemas.backup import BackupRunResponse
from backend.services import backup_service

router = APIRouter(prefix="/backup", tags=["backup"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[Staff, Depends(require_admin)]


@router.post("/run", response_model=BackupRunResponse)
async def run_backup(db: DbDep, staff: AdminDep) -> BackupRunResponse:
    result = await backup_service.run_backup(db, staff_id=staff.id)
    return BackupRunResponse(
        backup_file=result.backup_path.name,
        pruned_count=result.pruned_count,
    )
