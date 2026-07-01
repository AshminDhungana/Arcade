from backend.schemas.health import HealthMetricsRequest


class TestHealthMetricsRequest:
    def test_valid(self) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        h = HealthMetricsRequest(
            seat_id="seat1",
            cpu_pct=45.5,
            ram_pct=60.0,
            timestamp=now,
        )
        assert h.seat_id == "seat1"
        assert h.cpu_pct == 45.5
