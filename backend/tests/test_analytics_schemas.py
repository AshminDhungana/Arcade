from backend.schemas.analytics import AnalyticsSummary


def test_summary_constructs() -> None:
    s = AnalyticsSummary(
        total_revenue_paise=5000,
        session_count=1,
        average_duration_seconds=3600.0,
        weekly_revenue=[{"date": "2026-07-14", "total_paise": 5000}],
        member_stats={"new_today": 1, "active_last_30d": 1, "top_spenders": []},
    )
    assert s.total_revenue_paise == 5000
    assert s.member_stats.new_today == 1
    assert s.busiest_hour is None
