"""Arcade API routers.

All routers are collected in the ``routers`` list.  :mod:`backend.main`
iterates the list and mounts each router under ``/api/``.

Add new domain routers here as they are implemented in later phases.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.routers.ws import router as ws_router

__all__ = ["routers"]

# Ordered roughly by business priority.
# Placeholder comments keep the list stable so diffs are readable.
# Phase 2: # routers.append(auth_router)
# Phase 2: # routers.append(seat_router)
# Phase 2: # routers.append(session_router)
# Phase 3: # routers.append(pos_router)
# Phase 3: # routers.append(inventory_router)
# Phase 3: # routers.append(billing_router)
# Phase 4: # routers.append(member_router)
# Phase 4: # routers.append(package_router)
# Phase 4: # routers.append(promotion_router)
# Phase 4: # routers.append(voucher_router)
# Phase 5: # routers.append(shift_router)
# Phase 5: # routers.append(reservation_router)
# Phase 5: # routers.append(remote_command_router)
# Phase 6: # routers.append(analytics_router)
# Phase 6: # routers.append(event_router)
# Phase 6: # routers.append(settings_router)

routers: list[APIRouter] = [
    ws_router,
]
