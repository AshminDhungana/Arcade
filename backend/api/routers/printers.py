"""Printer discovery API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import require_admin
from backend.models.staff import Staff
from backend.services.printer_discovery import DiscoveredPrinter, discover_printers

router = APIRouter(prefix="/printers", tags=["printers"])


@router.get("/discover", response_model=list[DiscoveredPrinter])
async def discover_printers_endpoint(
    current_user: Staff = Depends(require_admin),  # noqa: B008 – FastAPI DI idiom
) -> list[DiscoveredPrinter]:
    """Discover all OS-installed printers (Admin only)."""
    try:
        printers = await discover_printers()
        return printers
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Printer discovery unavailable: {exc}. "
                "Install platform dependencies."
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Printer discovery failed: {exc}",
        ) from exc
