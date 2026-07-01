from datetime import UTC, datetime

from backend.schemas.analytics import AnalyticsSummary, AnalyticsSummaryRequest


class TestAnalyticsSummary:
    def test_defaults(self) -> None:
        s = AnalyticsSummary()
        assert s.total_revenue_paise == 0
        assert s.session_count == 0


class TestAnalyticsSummaryRequest:
    def test_valid(self) -> None:
        now = datetime.now(UTC)
        r = AnalyticsSummaryRequest(date_from=now, date_to=now)
        assert r.date_from == now
