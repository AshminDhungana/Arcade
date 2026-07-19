"""Arcade API routers.

All routers are collected in the ``routers`` list.  :mod:`backend.main`
iterates the list and mounts each router under ``/api/``.

Add new domain routers here as they are implemented in later phases.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.routers.analytics import router as analytics_router
from backend.api.routers.audit import router as audit_router
from backend.api.routers.auth import router as auth_router
from backend.api.routers.backup import router as backup_router
from backend.api.routers.device_types import router as device_type_router
from backend.api.routers.events import router as event_router
from backend.api.routers.inventory import router as inventory_router
from backend.api.routers.invoices import router as invoices_router
from backend.api.routers.members import router as member_router
from backend.api.routers.menu import router as menu_router
from backend.api.routers.packages import router as package_router
from backend.api.routers.pos import router as pos_router
from backend.api.routers.promotions import router as promotion_router
from backend.api.routers.reservations import router as reservation_router
from backend.api.routers.schedules import router as schedule_router
from backend.api.routers.seats import router as seat_router
from backend.api.routers.sessions import router as session_router
from backend.api.routers.settings import router as settings_router
from backend.api.routers.shifts import router as shift_router
from backend.api.routers.staff import router as staff_router
from backend.api.routers.vouchers import router as voucher_router
from backend.api.routers.zones import router as zone_router

__all__ = ["routers"]

# NOTE: `ws_router` is deliberately NOT in this list. WebSocket routes are
# mounted at the root (``/ws/dashboard``, ``/ws/agent/{seat_id}``) per SDD
# Section 9.2 and consumed by the frontend/agent without an ``/api`` prefix;
# ``backend.main`` mounts it separately. Everything here is under ``/api``.
#
# Ordered roughly by business priority.
# Placeholder comments keep the list stable so diffs are readable.
# Phase 3: # routers.append(pos_router)
# Phase 3: # routers.append(inventory_router)
# Phase 3: # routers.append(billing_router)
# Phase 4: routers.append(member_router)  # DONE
# Phase 4: routers.append(package_router)  # DONE
# Phase 4: routers.append(promotion_router)  # DONE
# Phase 4: routers.append(voucher_router)  # DONE
# Phase 4: routers.append(staff_router)  # DONE
# Phase 5: routers.append(shift_router)  # DONE
# Phase 5: routers.append(reservation_router)  # DONE
# Phase 5: # routers.append(remote_command_router)
# Phase 6: routers.append(analytics_router)  # DONE
# Phase 6: routers.append(event_router)  # DONE
# Phase 6: # routers.append(settings_router)

routers: list[APIRouter] = [
    auth_router,
    backup_router,
    seat_router,
    session_router,
    pos_router,
    inventory_router,
    invoices_router,
    audit_router,
    settings_router,
    member_router,
    package_router,
    promotion_router,
    voucher_router,
    staff_router,
    zone_router,
    device_type_router,
    schedule_router,
    menu_router,
    shift_router,
    reservation_router,
    analytics_router,
    event_router,
]
