from datetime import UTC, datetime

from backend.models._enums import AuditAction
from backend.schemas.audit import AuditLogResponse
from backend.schemas.settings import AppSettingsCreate


class TestAppSettingsCreate:
    def test_valid(self) -> None:
        s = AppSettingsCreate(key="debug", value="true")
        assert s.key == "debug"


class TestAuditLogResponse:
    def test_from_orm(self) -> None:
        now = datetime.now(UTC)

        class FakeLog:
            id = "log1"
            timestamp = now
            staff_id = None
            action = AuditAction.SESSION_START
            entity_type = "session"
            entity_id = "sess1"
            detail = None

        r = AuditLogResponse.model_validate(FakeLog())
        assert r.id == "log1"
        assert r.action == AuditAction.SESSION_START
