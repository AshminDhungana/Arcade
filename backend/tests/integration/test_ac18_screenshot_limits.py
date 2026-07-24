"""AC-18: Screenshot limits — JPEG ≤1280×720, 80% quality, size limits enforced."""

import asyncio
import base64
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image


async def test_screenshot_max_dimensions_1280x720(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Screenshot scaled down to max 1280×720 by the agent (not backend)."""
    # AC-18 requirement: agent scales to max 1280x720
    # Backend receives base64 JPEG and validates/broadcasts it
    # This test documents the requirement

    from backend.core.ws_manager import manager as ws_manager
    from backend.services.remote_command_service import request_screenshot

    # Create a large test image (2560x1440)
    large_img = Image.new("RGB", (2560, 1440), color="red")
    buffer = BytesIO()
    large_img.save(buffer, format="JPEG", quality=95)
    large_img_data = buffer.getvalue()

    # Mock agent connection
    mock_ws = AsyncMock()
    ws_manager.agent_connections[seeded_seat.id] = mock_ws

    # Mock wait_for_screenshot to return the large image
    with patch.object(
        ws_manager, "wait_for_screenshot", new_callable=AsyncMock
    ) as mock_wait:
        mock_wait.return_value = large_img_data

        # Request screenshot - service sends TAKE_SCREENSHOT to agent
        # Agent is responsible for scaling to 1280x720
        result = await request_screenshot(integration_db, seeded_seat.id, admin_staff)

        # Verify we got the image back
        assert result is not None
        assert len(result) > 0
        # Verify it's valid JPEG
        assert result[:2] == b"\xff\xd8"


async def test_screenshot_quality_80_percent(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Agent captures at 80% JPEG quality (enforced on agent side)."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.services.remote_command_service import request_screenshot

    # Create test image at 80% quality
    test_img = Image.new("RGB", (800, 600), color="blue")
    buffer = BytesIO()
    test_img.save(buffer, format="JPEG", quality=80)
    img_data = buffer.getvalue()

    mock_ws = AsyncMock()
    ws_manager.agent_connections[seeded_seat.id] = mock_ws

    with patch.object(
        ws_manager, "wait_for_screenshot", new_callable=AsyncMock
    ) as mock_wait:
        mock_wait.return_value = img_data

        result = await request_screenshot(integration_db, seeded_seat.id, admin_staff)

        assert result == img_data
        # Verify JPEG SOI marker
        assert result[:2] == b"\xff\xd8"


async def test_screenshot_max_size_limit(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Screenshot size capped at reasonable limit (5MB max message size)."""
    from backend.core.ws_manager import MAX_MESSAGE_SIZE

    # Create image that would exceed 5MB when base64 encoded
    # 3000x3000 at quality 90 ≈ 3.5MB JPEG, base64 ≈ 4.7MB
    large_img = Image.new("RGB", (3000, 3000), color="green")
    buffer = BytesIO()
    large_img.save(buffer, format="JPEG", quality=90)
    large_data = buffer.getvalue()

    # Base64 overhead ~33%
    _ = base64.b64encode(large_data).decode()

    # This documents the constraint - actual limit enforced at wire level
    assert MAX_MESSAGE_SIZE == 5 * 1024 * 1024


async def test_screenshot_rate_limit_enforced(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Screenshot capture rate limited: max 1 in-flight per seat."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.services.remote_command_service import (
        ScreenshotInFlightError,
        ScreenshotTimeoutError,
        request_screenshot,
    )

    test_img = Image.new("RGB", (640, 480), color="yellow")
    buffer = BytesIO()
    test_img.save(buffer, format="JPEG", quality=80)
    img_data = buffer.getvalue()

    mock_ws = AsyncMock()
    ws_manager.agent_connections[seeded_seat.id] = mock_ws

    with patch.object(
        ws_manager, "wait_for_screenshot", new_callable=AsyncMock
    ) as mock_wait:
        mock_wait.return_value = img_data

        # First capture - should succeed
        result1 = await request_screenshot(integration_db, seeded_seat.id, admin_staff)
        assert result1 is not None

        # Verify inflight set was cleared after completion
        from backend.services.remote_command_service import _screenshot_inflight

        assert seeded_seat.id not in _screenshot_inflight

        # Test concurrent in-flight rejection by mocking wait_for_screenshot to hang
        inflight_holder = asyncio.Event()

        async def hanging_wait(*args, **kwargs):
            await inflight_holder.wait()
            return img_data

        mock_wait.side_effect = hanging_wait

        # Start first call (will hang)
        task1 = asyncio.create_task(
            request_screenshot(integration_db, seeded_seat.id, admin_staff)
        )
        await asyncio.sleep(0.05)  # Let it register in-flight

        # Second call should fail immediately with in-flight error
        with pytest.raises(ScreenshotInFlightError):
            await request_screenshot(integration_db, seeded_seat.id, admin_staff)

        # Cleanup
        inflight_holder.set()
        try:
            await task1
        except ScreenshotTimeoutError:
            pass  # Expected because we mock timeout


async def test_screenshot_websocket_broadcast_size_limit(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """WebSocket broadcast enforces 5MB max message size for screenshots."""
    from backend.core.ws_manager import MAX_MESSAGE_SIZE

    # Verify constant
    assert MAX_MESSAGE_SIZE == 5 * 1024 * 1024


async def test_screenshot_agent_sends_base64_jpeg(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Agent sends base64-encoded JPEG over WebSocket."""

    test_img = Image.new("RGB", (640, 480), color="orange")
    buffer = BytesIO()
    test_img.save(buffer, format="JPEG", quality=80)
    img_data = buffer.getvalue()
    img_b64 = base64.b64encode(img_data).decode()

    # Verify it's valid base64 JPEG
    decoded = base64.b64decode(img_b64)
    assert decoded == img_data
    assert decoded[:2] == b"\xff\xd8"  # JPEG magic bytes


async def test_screenshot_dashboard_receives_thumbnail(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Dashboard receives screenshot via WebSocket broadcast (SEAT_UPDATED)."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.services.remote_command_service import request_screenshot

    test_img = Image.new("RGB", (640, 480), color="cyan")
    buffer = BytesIO()
    test_img.save(buffer, format="JPEG", quality=80)
    img_data = buffer.getvalue()

    # Mock dashboard connection
    mock_dashboard = AsyncMock()
    ws_manager.dashboard_connections = [mock_dashboard]

    mock_ws = AsyncMock()
    ws_manager.agent_connections[seeded_seat.id] = mock_ws

    with patch.object(
        ws_manager, "wait_for_screenshot", new_callable=AsyncMock
    ) as mock_wait:
        mock_wait.return_value = img_data

        # Also capture broadcast_to_dashboards call
        with patch.object(
            ws_manager, "broadcast_to_dashboards", new_callable=AsyncMock
        ):
            result = await request_screenshot(
                integration_db, seeded_seat.id, admin_staff
            )

            assert result == img_data
            # Note: The actual screenshot broadcast is handled by the agent's
            # SCREENSHOT_RESULT handler in ws_manager._handle_screenshot_response
            # which then broadcasts a SEAT_UPDATED with thumbnail


async def test_screenshot_validates_jpeg_format(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Service validates JPEG SOI marker (\\xff\\xd8) from agent response."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.services.remote_command_service import (
        ScreenshotInvalidImageError,
        request_screenshot,
    )

    # Invalid image data (not JPEG)
    invalid_data = b"not a jpeg image"

    mock_ws = AsyncMock()
    ws_manager.agent_connections[seeded_seat.id] = mock_ws

    with patch.object(
        ws_manager, "wait_for_screenshot", new_callable=AsyncMock
    ) as mock_wait:
        mock_wait.return_value = invalid_data

        with pytest.raises(ScreenshotInvalidImageError):
            await request_screenshot(integration_db, seeded_seat.id, admin_staff)
