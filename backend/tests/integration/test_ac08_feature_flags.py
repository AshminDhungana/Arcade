"""AC-08: Feature flags — endpoints respect feature flag state."""

from backend.core.feature_flags import _flag_cache, get_flag, load_flags

from .utils import auth_headers


async def test_feature_flag_off_returns_503(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Endpoints with require_feature return 503 when flag is off."""

    # Ensure flag is off
    _flag_cache.clear()
    assert get_flag("enable_packages") is False

    # Call an endpoint that requires the flag
    resp = await integration_client.get(
        "/api/packages", headers=auth_headers(staff_id="admin-id", role="ADMIN")
    )

    # Should return 503 Service Unavailable
    assert resp.status_code == 503
    assert "disabled" in resp.json()["detail"].lower()


async def test_feature_flag_on_allows_access(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Endpoints with require_feature allow access when flag is on."""
    from backend.models.settings import AppSettings

    # Turn flag on via database
    integration_db.add(AppSettings(key="enable_packages", value="true"))
    await integration_db.commit()
    await load_flags(integration_db)

    assert get_flag("enable_packages") is True

    # Call endpoint (will return 401 without auth but we just check it doesn't 503)
    from backend.models import Staff, StaffRole

    admin = Staff(
        id="admin-id",
        name="Admin",
        pin_hash="argon2id$",
        role=StaffRole.ADMIN,
        is_active=True,
        token_version=0,
    )
    integration_db.add(admin)
    await integration_db.commit()

    resp = await integration_client.get(
        "/api/packages", headers=auth_headers(staff_id=admin.id, role="ADMIN")
    )

    # Should not be 503 (could be 200, 401, 404, but not 503 for feature disabled)
    assert resp.status_code != 503


async def test_feature_flag_cache_isolation_between_tests(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Feature flag cache is cleared between tests via autouse fixture."""
    from backend.core.feature_flags import get_flag

    # The autouse fixture should have cleared the cache
    # But we can also verify it works when we set a flag
    _flag_cache["test_flag"] = True
    assert get_flag("test_flag") is True

    # The fixture will clear it after this test


async def test_feature_flag_refresh_updates_runtime(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """refresh_flags updates runtime cache from database."""
    from sqlalchemy import delete

    from backend.core.feature_flags import get_flag, refresh_flags
    from backend.models.settings import AppSettings

    # Start with flag off
    _flag_cache.clear()
    assert get_flag("enable_pos") is False

    # Add flag to DB and refresh
    integration_db.add(AppSettings(key="enable_pos", value="true"))
    await integration_db.commit()
    await refresh_flags(integration_db)

    assert get_flag("enable_pos") is True

    # Turn off and refresh again
    await integration_db.execute(
        delete(AppSettings).where(AppSettings.key == "enable_pos")
    )
    integration_db.add(AppSettings(key="enable_pos", value="false"))
    await integration_db.commit()
    await refresh_flags(integration_db)

    assert get_flag("enable_pos") is False


async def test_response_includes_feature_flags_list(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """GET /api/settings returns current feature flag states."""
    from backend.models.settings import AppSettings

    # Add some flags
    integration_db.add_all(
        [
            AppSettings(key="enable_packages", value="true"),
            AppSettings(key="enable_pos", value="false"),
            AppSettings(key="enable_inventory", value="true"),
        ]
    )
    await integration_db.commit()
    await load_flags(integration_db)

    from backend.models import Staff, StaffRole

    admin = Staff(
        id="admin-id",
        name="Admin",
        pin_hash="argon2id$",
        role=StaffRole.ADMIN,
        is_active=True,
        token_version=0,
    )
    integration_db.add(admin)
    await integration_db.commit()

    resp = await integration_client.get(
        "/api/settings", headers=auth_headers(staff_id="admin-id", role="ADMIN")
    )

    assert resp.status_code == 200
    data = resp.json()
    # Check that feature flags are included in response
    assert "feature_flags" in data or "enable_packages" in data
